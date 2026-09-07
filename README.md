# Java 21 原生二进制工作流模板

把 Java 项目通过 **Oracle GraalVM for JDK 21 Native Image** 编译为可直接运行的程序。手动触发 GitHub Actions，按系统和 CPU 架构分别构建、检查、运行、压缩，全部成功后发布到 **GitHub Release**，提供长期下载。

这是一个可复制的构建模板，默认交付 **单二进制，内嵌 HTML、JS、CSS 和 PNG 图片**，包含能运行的 Maven CLI + HTTP 示例。当前重点是普通 Java/独立混合服务，框架与 GUI 接入说明属于后续适配参考，不能视为已验证支持。

**使用入口：[工作流详细中文说明](.github/workflows/README.md)**。说明放在工作流旁，包含接入步骤、完整变量说明、CLI / API / 内嵌网页配置示例、资源处理、验证、Release 下载和故障排查。

## 单二进制内嵌静态资源

```text
src/main/resources/
├── greeting.txt
├── public/
│   ├── index.html
│   ├── app.js
│   ├── app.css
│   └── logo.png
└── META-INF/native-image/example/native-demo/resource-config.json
```

`public/` 中的前端文件通过 Native Image 资源配置打入二进制。示例服务使用 `getResourceAsStream` 读取 classpath 内容，不转换成磁盘 `File`，不依赖源码目录或启动位置，也不把资源解压到用户磁盘。

运行 `native-demo --serve 8080` 后访问 `http://127.0.0.1:8080/` 可打开示例页面；JS 请求同一个服务的 `/health`。页面没有 CDN、远程字体、遥测或后台轮询。

- **固定 HTML、JS、CSS、图标、图片**：默认内嵌，前后端随同一个程序版本发布；修改资源后要重新构建。
- **上传文件、运行时生成的数据**：放外部可写目录，不写回内嵌资源。
- **密码、密钥、部署参数**：通过环境变量或外部配置传入，不放入 `public/` 或二进制。

使用 Vue/React 等前端时，先在构建过程中生成静态产物，再将产物复制到 `src/main/resources/public/` 或 Maven 的资源输出目录，最后执行原生编译。只有被复制到 Java 资源中、且匹配 Native Image 资源规则的文件才会进入二进制。此处没有默认安装 Node 或执行前端依赖下载；项目按实际需要接入自己的构建步骤。

默认 `PACKAGE_FILES_JSON: '[]'`，运行只需解压后的可执行文件；压缩包中的 `build-info.json` 仅记录构建信息。静态资源不会作为散文件放进压缩包。若项目显式配置额外文件，则交付方式变为“程序加附带文件”。

示例只提供静态文件和精确的 `/health` 路由；缺失资源返回 404。需要 SPA history 路由回退时，项目需区分页面路由与 JS/CSS/图片请求，避免用 index.html 掩盖资源丢失。

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
3. 等待五个平台与 Release 发布任务完成，在仓库 **Releases** 页面下载对应目标和 `.sha256`。
4. 校验并解压 `tar.gz` 或 `zip`，直接运行程序。

工作流没有 `push`、`pull_request` 或标签触发；**每次手动构建成功都会自动创建一个 Release**。默认标签为 `native-<运行序号>`，可以在顶部改成自己的版本号；已有 Release 不会被覆盖。公开仓库使用标准 runner；私有仓库应自行确认 Actions 配额。

## 最终文件在哪里，链接保留多久

| 位置 | 内容 | 保留方式 |
| --- | --- | --- |
| GitHub Release | 五种原生压缩包、各自的 SHA-256；包内含 build-info.json | 不受 Actions 过期策略影响，保留到仓库/Release/资产被删除 |
| Actions Artifacts | 同次运行的分发包和故障排查日志 | 默认 14 天，顶部可调整 |
| 本机项目的 downloads/ | 仅下载用于本机验证的 Mac 产物 | 本地保留，已被 Git 忽略，不上传仓库源码 |

本仓库的 [最新正式 Release](https://github.com/yumengjh/java-native-template/releases/latest) 是长期入口。
固定版本链接格式为 `https://github.com/<owner>/<repo>/releases/download/<tag>/<文件名>`；最新 macOS ARM64 压缩包入口为 [下载最新 Mac ARM64](https://github.com/yumengjh/java-native-template/releases/latest/download/native-demo-macos-arm64.tar.gz)。
固定版本 URL 指向那一版，`latest` URL 会跟随后续正式发布。公开仓库 Release 可直接下载，无需 Actions 页面权限。这不意味着永久托管保证：删除仓库、Release、资产，或改变访问权限都会影响下载。

Actions 的 artifact 下载仍可用于调试，但需要先解开它的外层 ZIP，且会过期。不要把它当作面向使用者的最终发布链接。

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

建议同时复制 `.github/workflows/README.md`，方便维护者就近查阅；它是说明文档，不参与构建。文中的示例和进阶文档链接指向本模板内的文件，按需一起复制或改为本模板的 GitHub 链接。

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
| `HTTP_RESOURCES_JSON` | 静态资源请求路径、预期 MIME 类型和对照源文件；纯 CLI/API 项目设为 `[]` |
| `SMOKE_TIMEOUT_SECONDS` | 单项运行验证的超时；默认 45 秒 |
| `PACKAGE_FILES_JSON` | 需要随程序分发的额外文件或目录；默认不带其他文件 |
| `RELEASE_TAG` | 正式 Release 的版本标签；默认每次运行生成独立标签 |
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

- **资源**：模板用 `greeting.txt` 演示中文读取，用 `public/` 演示页面、脚本、样式和 PNG 图片内嵌。
- **反射、动态代理、序列化、JNI**：构建器无法总是推断运行时访问的内容，须补充元数据或框架 hints。
- **第三方库**：Native Build Tools 可以加载共享元数据仓库，但不是每个库、版本、调用路径都已覆盖。
- **初始化时机**：不要全局强行 `--initialize-at-build-time`；读取环境变量、网络、随机数的初始化一般应保留到运行时。
- **失败边界**：示例开启 `--no-fallback`；构建失败即失败，不用依赖 JVM 的 fallback 代替原生成功。
- **真实架构**：脚本解析 PE / ELF / Mach-O 文件头；JAR、脚本、与目标不一致的二进制都会被拒绝。
- **分发验证**：先打包再解压到源码目录外，在解压目录中执行 CLI/HTTP 验证；静态资源必须返回 HTTP 200、正确 MIME 类型和与对照文件完全一致的字节。误返回 HTML、错误版本或图片损坏都不能通过。验证结束后清理服务进程和临时解压目录。
- **验证范围**：这些检查不执行浏览器里的 JS，也不替代 UI/数据库/TLS 等业务测试。原生程序运行所需资源必须来自内嵌内容或明确的附带文件；验证器仅为比较字节而读取源文件。

例如只验证首页和图片：

```yaml
HTTP_RESOURCES_JSON: >-
  [{"path":"/", "source":"src/main/resources/public/index.html", "content_type":"text/html"},
   {"path":"/logo.png", "source":"src/main/resources/public/logo.png", "content_type":"image/png"}]
```

`source` 相对 `PROJECT_DIR`；如果前端文件由构建生成，应指向生成后的文件。资源请求只访问健康接口所在的本地服务，不跟随重定向。纯 CLI 或没有静态资源的 API 服务请设为 `HTTP_RESOURCES_JSON: '[]'`。

详细配置和采集命令见 [Native Image 配置示例](docs/native-image.md)。

## 兼容性与分发

Linux 默认在 Ubuntu 22.04 上使用 glibc 工具链，建议部署到 Ubuntu 22.04 或更新的兼容系统。不能据此保证所有 glibc 2.35 以上发行版、旧版 CentOS、Alpine 都能运行；实际最低要求由依赖的系统库和生成文件共同决定。可在 runner 日志之外自行检查 `ldd` / `readelf`，并在最低目标系统验证。Alpine 需要单独的 musl 静态构建配置，不属于本模板的默认产物。

示例使用 `-march=compatibility` 选择较保守 CPU 指令集。迁移到框架自有 native 配置时也应显式设置这一选项。它不能消除 OS/系统库最低版本要求。

macOS runner 固定为 macOS 14 ARM64、macOS 15 Intel；默认只验证这两个构建环境，旧系统需另外验证。产物未做 Developer ID 签名和 Apple 公证，也未创建 `.app` / DMG。Windows 未做 Authenticode 签名或安装器，某些程序可能需要 Visual C++ 运行库或额外 DLL。桌面分发需要由 GUI 工具包和发布流程处理这些内容。

`PACKAGE_FILES_JSON` 可加入 DLL、资源目录或外部配置；每项按文件/目录名拷贝到包根目录，目录内部结构不变。缺失路径、同名冲突或符号链接会失败。不要加入 `.env`、密钥、凭据或整个项目目录。程序应以可执行文件所在目录为依据定位这些资源，不能依赖开发机路径。

## 排查失败

在 Actions 对应 job 查看失败步骤，并下载 `logs-<target>`，里面包含实际 GraalVM 版本、构建输出和程序启动日志。各平台互不取消，能一次看到完整结果。构建可通过但验证失败时，不上传该平台的可分发产物；任一平台失败，整个 Release 都不会发布。资产会先上传到草稿，全部上传成功后才公开。如果发布上传中断留下草稿，检查原因后删除未完成草稿再重试，或使用新版本标签；模板不会覆盖已经发布的资产。

本模板不会给本机安装依赖。GitHub runner 会下载构建所需的 GraalVM、Maven/Gradle 依赖及 C 工具链；有意在本机执行 `mvn` / Wrapper 时，则由构建工具按自身配置获取依赖。

## 官方参考

- [GraalVM GitHub Action](https://github.com/graalvm/setup-graalvm)
- [GraalVM JDK 21 平台与安装](https://www.graalvm.org/jdk21/docs/getting-started/)
- [GraalVM Community JDK 21 平台列表](https://github.com/graalvm/graalvm-ce-builds/releases/tag/jdk-21.0.2)
- [GitHub 标准 runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Native Image 元数据](https://www.graalvm.org/jdk21/reference-manual/native-image/metadata/)
- [GitHub Release 固定与 latest 下载链接](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)
