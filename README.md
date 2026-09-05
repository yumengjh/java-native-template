# Java 21 原生二进制工作流模板

把 Java 项目通过 **Oracle GraalVM for JDK 21 Native Image** 编译为可直接运行的程序。手动触发 GitHub Actions，按系统和 CPU 架构分别构建、检查、运行、压缩并上传产物。

这是一个可复制的构建模板，包含能运行的 **Maven CLI + HTTP 示例**。框架的 AOT、反射元数据、GUI 工具包适配属于项目配置，不能由一个通用 YAML 自动推断。Spring Boot、Quarkus、Javalin、Gradle 和 GUI 的接入示例见 [框架接入说明](docs/adapters.md)。

## 平台

| 目标 | GitHub runner | 状态 |
| --- | --- | --- |
| Linux AMD64 | `ubuntu-22.04` | 原生构建 + CLI/HTTP 验证 |
| Linux ARM64 | `ubuntu-22.04-arm` | 原生构建 + CLI/HTTP 验证 |
| macOS AMD64 / Intel | `macos-15-intel` | 原生构建 + CLI/HTTP 验证 |
| macOS ARM64 / Apple Silicon | `macos-14` | 原生构建 + CLI/HTTP 验证 |
| Windows AMD64 | `windows-2022` | 原生构建 + CLI/HTTP 验证 |
| Windows ARM64 | — | **GraalVM 21 暂不支持，不产生伪装成 ARM64 的 AMD64 文件** |

表中验证方式是工作流配置；实际执行记录见 [验证记录](docs/verification.md)。不使用一个平台去交叉编译另一个平台，所有构建都在对应系统和架构的 runner 上执行。

## 在 GitHub 上运行

1. 将本项目推送到 GitHub 默认分支。
2. 打开 **Actions → Java 21 原生二进制 → Run workflow**，选择分支并运行。
3. 等待五个平台任务完成，在该次运行的 **Artifacts** 区下载对应目标。
4. 下载后先解开 Actions 提供的外层 ZIP，再校验并解压内部 `tar.gz` 或 `zip`。

工作流没有 `push`、`pull_request` 或标签触发，不会自动发布 Release。公开仓库使用标准 runner；私有仓库应自行确认 Actions 配额。

macOS ARM64 示例（在下载产物目录执行）：

```bash
shasum -a 256 -c native-demo-macos-arm64.tar.gz.sha256
tar -xzf native-demo-macos-arm64.tar.gz
./native-demo-macos-arm64/native-demo --version
./native-demo-macos-arm64/native-demo --self-test
./native-demo-macos-arm64/native-demo --serve 8080
# 另开终端：
curl http://127.0.0.1:8080/health
```

启动服务后可按 Ctrl+C 停止。Windows 解压后执行 `native-demo.exe --self-test`。原生程序运行不要求安装 JDK，但系统库、GUI/JNI 动态库仍可能是必要依赖。

## 接入已有项目

复制这两个文件，保留路径：

```text
.github/workflows/native.yml
.github/scripts/native_ci.py
```

然后在项目的 `pom.xml` 或 `build.gradle` 中配置 Native Image 构建，再编辑工作流顶部 `env`。**不必复制本仓库的 Java 示例。**

| 变量 | 作用 |
| --- | --- |
| `GRAALVM_DISTRIBUTION` / `JAVA_VERSION` | 默认 Oracle GraalVM / Java 21；`21` 会随可用补丁更新，可改成已发布的具体版本 |
| `PROJECT_DIR` | 构建目录；单仓多模块可设为应用目录或聚合根目录 |
| `BUILD_TOOL` / `BUILD_ARGS_JSON` | Maven 或 Gradle，以及完整参数列表 |
| `BINARY_PATH` | 相对构建目录的确切原生文件路径；`{exe}` 处理 Windows 后缀 |
| `ARTIFACT_NAME` | 分发压缩包和 Actions artifact 的名称前缀 |
| `TARGETS_JSON` / `RUNNERS_JSON` | 启用目标和对应 runner 标签 |
| `SMOKE_MODE` | `cli`、`http`、`both` 或 `none` |
| `CLI_ARGS_JSON` / `CLI_EXPECT` | CLI 自检参数及输出中必须出现的文本 |
| `HTTP_ARGS_JSON` / `HEALTH_URL` / `HEALTH_EXPECT` | 服务启动参数、本地健康接口、预期响应内容 |
| `SMOKE_TIMEOUT_SECONDS` | 单项运行验证的超时；默认 45 秒 |
| `PACKAGE_FILES_JSON` | 需要随程序分发的额外文件或目录；默认不带其他文件 |
| `RETENTION_DAYS` | 产物及日志保留时间；默认 14 天 |

所有 `*_ARGS_JSON` 都是 JSON 字符串数组，每个命令行参数单独一项。不要填写 `mvn` / `./gradlew`，脚本会优先选择项目 Wrapper。没有 Maven Wrapper 时使用 runner 自带 Maven；Gradle 必须提交 Wrapper，包括它的配置文件和 JAR。

例如应用位于多模块仓库的 `apps/server`，从根构建：

```yaml
PROJECT_DIR: '.'
BUILD_ARGS_JSON: '["--batch-mode", "clean", "package", "-Pnative", "-pl", "apps/server", "-am"]'
BINARY_PATH: 'apps/server/target/server{exe}'
```

聚合构建时需要把 native 插件放在真正可执行的应用模块，避免所有库模块都尝试编译入口类。

## 原生构建为什么需要项目适配

- **资源**：模板用 `greeting.txt` 演示资源注册和中文读取；入口类通过 `--self-test` 验证资源确实在产物里。
- **反射、动态代理、序列化、JNI**：构建器无法总是推断运行时访问的内容，须补充元数据或框架 hints。
- **第三方库**：Native Build Tools 可以加载共享元数据仓库，但不是每个库、版本、调用路径都已覆盖。
- **初始化时机**：不要全局强行 `--initialize-at-build-time`；读取环境变量、网络、随机数的初始化一般应保留到运行时。
- **失败边界**：示例开启 `--no-fallback`；构建失败即失败，不用依赖 JVM 的 fallback 代替原生成功。
- **真实架构**：脚本解析 PE / ELF / Mach-O 文件头；JAR、脚本、与目标不一致的二进制都会被拒绝。
- **验证范围**：CLI 自检和健康检查只是冒烟测试；迁移真实服务时还应验证 JSON、数据库、模板、TLS 等使用到的路径。

详细配置和采集命令见 [Native Image 配置示例](docs/native-image.md)。

## 兼容性与分发

Linux 默认在 Ubuntu 22.04 上使用 glibc 工具链，建议部署到 Ubuntu 22.04 或更新的兼容系统。不能据此保证所有 glibc 2.35 以上发行版、旧版 CentOS、Alpine 都能运行；实际最低要求由依赖的系统库和生成文件共同决定。可在 runner 日志之外自行检查 `ldd` / `readelf`，并在最低目标系统验证。Alpine 需要单独的 musl 静态构建配置，不属于本模板的默认产物。

示例使用 `-march=compatibility` 选择较保守 CPU 指令集。迁移到框架自有 native 配置时也应显式设置这一选项。它不能消除 OS/系统库最低版本要求。

macOS runner 固定为 macOS 14 ARM64、macOS 15 Intel；默认只验证这两个构建环境，旧系统需另外验证。产物未做 Developer ID 签名和 Apple 公证，也未创建 `.app` / DMG。Windows 未做 Authenticode 签名或安装器，某些程序可能需要 Visual C++ 运行库或额外 DLL。桌面分发需要由 GUI 工具包和发布流程处理这些内容。

`PACKAGE_FILES_JSON` 可加入 DLL、资源目录或外部配置；每项按文件/目录名拷贝到包根目录，目录内部结构不变。缺失路径、同名冲突或符号链接会失败。不要加入 `.env`、密钥、凭据或整个项目目录。程序应以可执行文件所在目录为依据定位这些资源，不能依赖开发机路径。

## 排查失败

在 Actions 对应 job 查看失败步骤，并下载 `logs-<target>`，里面包含实际 GraalVM 版本、构建输出和程序启动日志。各平台互不取消，能一次看到完整结果。构建可通过但验证失败时，不上传可分发产物。

本模板不会给本机安装依赖。GitHub runner 会下载构建所需的 GraalVM、Maven/Gradle 依赖及 C 工具链；有意在本机执行 `mvn` / Wrapper 时，则由构建工具按自身配置获取依赖。

## 官方参考

- [GraalVM GitHub Action](https://github.com/graalvm/setup-graalvm)
- [GraalVM JDK 21 平台与安装](https://www.graalvm.org/jdk21/docs/getting-started/)
- [GraalVM Community JDK 21 平台列表](https://github.com/graalvm/graalvm-ce-builds/releases/tag/jdk-21.0.2)
- [GitHub 标准 runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Native Image 元数据](https://www.graalvm.org/jdk21/reference-manual/native-image/metadata/)
