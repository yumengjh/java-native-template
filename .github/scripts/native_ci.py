#!/usr/bin/env python3
"""仅使用 Python 标准库，跨 Windows/macOS/Linux 执行，不需要 pip install。"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import struct
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile


ROOT = Path.cwd().resolve()
LOGS = ROOT / "native-logs"
SUPPORTED = {"linux-amd64", "linux-arm64", "macos-amd64", "macos-arm64", "windows-amd64"}


def setting(name):
    return os.environ[name]


def json_list(name):
    value = json.loads(setting(name))
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"{name} 必须是字符串 JSON 数组")
    return value


def inside(base, relative):
    """配置路径必须在项目内；拒绝绝对路径及越界的 ../、符号链接。"""
    path = (base / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(base):
        raise ValueError(f"路径必须位于 {base} 内：{relative}")
    return path


def project():
    return inside(ROOT, setting("PROJECT_DIR"))


def binary():
    suffix = ".exe" if setting("NATIVE_TARGET").startswith("windows-") else ""
    return inside(project(), setting("BINARY_PATH").replace("{exe}", suffix))


def summary(message):
    print(message, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(setting("GITHUB_STEP_SUMMARY"), "a", encoding="utf-8") as out:
            out.write(message + "\n")


def configure():
    targets = json_list("TARGETS_JSON")
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("目标列表不能为空，也不能重复")
    unsupported = set(targets) - SUPPORTED
    if unsupported:
        raise ValueError(f"GraalVM 21 不支持这些目标：{sorted(unsupported)}；Windows ARM64 暂无工具链")
    runners = json.loads(setting("RUNNERS_JSON"))
    matrix = {"include": [{"target": t, "runner": runners[t]} for t in targets]}
    if not all(isinstance(row["runner"], str) and row["runner"] for row in matrix["include"]):
        raise ValueError("每个目标需要一个非空 runner 标签")
    if setting("BUILD_TOOL") not in {"maven", "gradle"}:
        raise ValueError("BUILD_TOOL 只能是 maven 或 gradle")
    if setting("SMOKE_MODE") not in {"cli", "http", "both", "none"}:
        raise ValueError("无效的 SMOKE_MODE")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", setting("ARTIFACT_NAME")):
        raise ValueError("ARTIFACT_NAME 只能含字母、数字、点、横杠、下划线")
    if not json_list("BUILD_ARGS_JSON"):
        raise ValueError("构建参数不能为空")
    for name in ("CLI_ARGS_JSON", "HTTP_ARGS_JSON", "PACKAGE_FILES_JSON"):
        json_list(name)
    if not 1 <= int(setting("SMOKE_TIMEOUT_SECONDS")) <= 600:
        raise ValueError("冒烟超时应为 1 到 600 秒")
    if not 1 <= int(setting("RETENTION_DAYS")) <= 90:
        raise ValueError("公开仓库 artifact 保留天数应为 1 到 90")
    if not project().is_dir():
        raise ValueError("PROJECT_DIR 不存在")
    if ".." in Path(setting("BINARY_PATH")).parts or not setting("BINARY_PATH"):
        raise ValueError("请指定项目内的二进制路径")
    with open(setting("GITHUB_OUTPUT"), "a", encoding="utf-8") as out:
        out.write("matrix=" + json.dumps(matrix, separators=(",", ":")) + "\n")
    summary("目标：" + ", ".join(targets))
    summary("Windows ARM64：GraalVM 21 暂不支持，未加入构建矩阵。")


def logged_run(command, name, timeout=None):
    LOGS.mkdir(exist_ok=True)
    print("执行：" + repr([str(x) for x in command]), flush=True)
    # 不使用 eval/shell 拼接；JSON 数组中的参数保持原来的边界。
    with (LOGS / name).open("w", encoding="utf-8") as log:
        if timeout is not None:
            subprocess.run(command, cwd=project(), stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=timeout)
        else:
            with subprocess.Popen(command, cwd=project(), stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                  errors="replace") as process:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode, command)
    return (LOGS / name).read_text(encoding="utf-8", errors="replace")


def build():
    LOGS.mkdir(exist_ok=True)
    # 留下实际版本，方便以后定位工具链更新带来的差异。
    java = shutil.which("java")
    native_image = shutil.which("native-image")
    if not java or not native_image:
        raise ValueError("必须先安装并启用 GraalVM Native Image")
    logged_run([java, "-version"], "java-version.log")
    logged_run([native_image, "--version"], "native-image-version.log")
    tool = setting("BUILD_TOOL")
    wrapper_name = ("mvnw" if tool == "maven" else "gradlew") + (".cmd" if os.name == "nt" and tool == "maven" else ".bat" if os.name == "nt" else "")
    wrapper = project() / wrapper_name
    if wrapper.is_file():
        command = [str(wrapper)] if os.name == "nt" else ["bash", str(wrapper)]
    elif tool == "maven" and shutil.which("mvn"):
        command = [shutil.which("mvn")]
    else:
        raise ValueError("找不到构建工具；Gradle 项目请提交 Gradle Wrapper，Maven 可使用 runner 自带 mvn")
    # 删除旧输出，避免错误构建命令碰巧捡到仓库内遗留的二进制。
    output = binary()
    if output.is_file():
        output.unlink()
    logged_run(command + json_list("BUILD_ARGS_JSON"), "build.log")


def inspect_binary(path):
    """读取 ELF / Mach-O / PE 文件头，防止 JAR、脚本或错误架构混入产物。"""
    with path.open("rb") as source:
        header = source.read(64)
        if header[:4] == b"\x7fELF":
            if header[4:6] != b"\x02\x01":
                raise ValueError("只接受 64 位小端 ELF")
            machine = struct.unpack_from("<H", header, 18)[0]
            return "linux-" + {62: "amd64", 183: "arm64"}[machine]
        if header[:4] == b"\xcf\xfa\xed\xfe":
            machine = struct.unpack_from("<I", header, 4)[0]
            return "macos-" + {0x01000007: "amd64", 0x0100000C: "arm64"}[machine]
        if header[:2] == b"MZ":
            source.seek(struct.unpack_from("<I", header, 60)[0])
            pe = source.read(6)
            if pe[:4] == b"PE\0\0":
                machine = struct.unpack_from("<H", pe, 4)[0]
                return "windows-" + {0x8664: "amd64", 0xAA64: "arm64"}[machine]
    raise ValueError(f"不是支持的原生二进制：{path}")


def verify():
    output = binary()
    detected = inspect_binary(output)
    if detected != setting("NATIVE_TARGET"):
        raise ValueError(f"实际架构 {detected} 与目标 {setting('NATIVE_TARGET')} 不一致")
    summary(f"文件头检查通过：{detected}，{output.stat().st_size} bytes")
    timeout = int(setting("SMOKE_TIMEOUT_SECONDS"))
    mode = setting("SMOKE_MODE")
    if mode not in {"cli", "http", "both", "none"}:
        raise ValueError("无效冒烟模式")
    if mode in {"cli", "both"}:
        result = logged_run([str(output)] + json_list("CLI_ARGS_JSON"), "cli.log", timeout)
        print(result, flush=True)
        if setting("CLI_EXPECT") not in result:
            raise ValueError("CLI 输出不含预期文本")
        summary("CLI 冒烟验证通过")
    if mode in {"http", "both"}:
        LOGS.mkdir(exist_ok=True)
        # 禁用 HTTP 代理，只检查由本次进程启动的本地服务。
        url = urllib.parse.urlparse(setting("HEALTH_URL"))
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("健康检查必须使用 loopback HTTP 地址")
        # 先检查端口未被占用，避免误把另一项服务判定为本次构建成功。
        with socket.socket(socket.AF_INET6 if url.hostname == "::1" else socket.AF_INET) as probe:
            probe.bind((url.hostname, url.port or 80))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with (LOGS / "http.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(output)] + json_list("HTTP_ARGS_JSON"),
                                       cwd=project(), stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"HTTP 服务提前退出：{process.returncode}")
                    try:
                        with opener.open(setting("HEALTH_URL"), timeout=2) as response:
                            body = response.read().decode("utf-8")
                            if response.status == 200 and setting("HEALTH_EXPECT") in body:
                                print(body, flush=True)
                                break
                    except (urllib.error.URLError, TimeoutError, ConnectionError):
                        pass
                    time.sleep(0.25)
                else:
                    raise TimeoutError("健康检查超时")
                if process.poll() is not None:
                    raise RuntimeError("健康检查期间服务退出")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        summary("HTTP 冒烟验证通过，验证进程已回收")
    if mode == "none":
        summary("运行验证已显式关闭；仅验证文件格式与架构。")


def package():
    output = binary()
    target = setting("NATIVE_TARGET")
    if inspect_binary(output) != target:
        raise ValueError("打包前架构复检失败")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    name = setting("ARTIFACT_NAME") + "-" + target
    # stage 位于构建目录中，避免 upload-artifact 把未压缩目录也上传。
    stage = ROOT / "build" / "native-bundle" / name
    stage.mkdir(parents=True, exist_ok=False)
    shutil.copy2(output, stage / output.name)
    for item in json_list("PACKAGE_FILES_JSON"):
        source = inside(project(), item)
        destination = stage / source.name
        if source == project() or not source.exists() or destination.exists():
            raise ValueError(f"额外文件不存在、过于宽泛或文件名冲突：{item}")
        # 不跟随额外目录中的符号链接，避免把目录外的文件纳入分发包。
        if (project() / item).is_symlink() or (source.is_dir() and any(p.is_symlink() for p in source.rglob("*"))):
            raise ValueError(f"额外分发目录不允许符号链接：{item}")
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    info = {"target": target, "commit": os.environ.get("GITHUB_SHA", "local"),
            "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "runner_os": platform.platform(), "distribution": setting("GRAALVM_DISTRIBUTION"),
            "requested_java_version": setting("JAVA_VERSION"), "smoke_mode": setting("SMOKE_MODE"),
            "native_image_version": (LOGS / "native-image-version.log").read_text(encoding="utf-8")}
    (stage / "build-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    if target.startswith("windows-"):
        archive = dist / (name + ".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for item in stage.rglob("*"):
                if item.is_file():
                    bundle.write(item, item.relative_to(stage.parent))
    else:
        archive = dist / (name + ".tar.gz")
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(stage, arcname=name)
    hasher = hashlib.sha256()
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    (dist / (archive.name + ".sha256")).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    summary(f"已打包：{archive.name}；SHA-256：{digest}")


if __name__ == "__main__":
    commands = {"configure": configure, "build": build, "verify": verify, "package": package}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit("用法：native_ci.py configure|build|verify|package")
    try:
        commands[sys.argv[1]]()
    except Exception as error:
        print(f"::error::{type(error).__name__}: {error}", file=sys.stderr)
        raise
