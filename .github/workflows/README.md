# Java 21 原生二进制工作流使用说明

工作流文件：[native.yml](native.yml)。通常只需编辑它顶部的 `env` 配置区。

本模板把已经具备 Native Image 构建能力的 Java 项目，在对应系统和架构的 GitHub runner 上编译、打包、验证，全部选定目标成功后发布 GitHub Release。默认示例是 **Maven + GraalVM 21，单二进制，内嵌 HTML、JS、CSS 和图片，同时支持 CLI 与 HTTP 服务**。

工作流负责组织构建和交付；反射、框架 AOT、资源加载、JNI 等原生兼容性需要项目自身配置。不能只把任意 JAR 的文件名填进来就得到可用的原生程序。

## 1. 文件位置与阅读入口

| 文件 | 用途 |
| --- | --- |
| [native.yml](native.yml) | 手动触发、顶部配置、平台矩阵、构建与发布步骤 |
| [../scripts/native_ci.py](../scripts/native_ci.py) | 必需的跨平台辅助脚本，只使用 Python 标准库 |
| [../../pom.xml](../../pom.xml) | 普通 Java Maven 原生构建的完整示例 |
| [../../src/main/java/example/Main.java](../../src/main/java/example/Main.java) | CLI、自检、健康接口、内嵌静态资源服务示例 |
| [../../docs/adapters.md](../../docs/adapters.md) | Javalin、Spring Boot、Quarkus、Gradle 和 GUI 的适配说明 |
| [../../docs/native-image.md](../../docs/native-image.md) | 资源、反射元数据及原生构建问题 |
| [../../docs/verification.md](../../docs/verification.md) | 实际执行过的验证、对应版本及未验证范围 |

上述链接相对于本文件。迁移到自己的仓库时，两个运行必需文件是 `native.yml` 和 `native_ci.py`，必须保留原来的 `.github/` 路径。建议一起复制本说明；示例源码与 `docs/` 按需复制，不复制时应调整相应链接。

## 2. 第一次使用

### 直接体验本模板

1. 用本仓库创建自己的模板仓库，或将完整源码放入自己的仓库。
2. 保留默认配置，即构建示例的五个平台版本。
3. 打开 GitHub **Actions → Java 21 原生二进制 → Run workflow**，选择分支并运行。
4. 等待构建、验证与发布全部成功，再从 **Releases** 下载所需平台的压缩包和 `.sha256`。

提交代码、推送标签都不会自动触发。**一次手动运行成功后会自动发布正式 Release**，不是只做编译预览。工作流文件应先提交到默认分支，以便在 Actions 页面使用手动触发入口。

### 接入自己的 Java 项目

1. 复制 `.github/workflows/native.yml`、`.github/scripts/native_ci.py`；建议同时复制本说明。
2. 在项目的 Maven/Gradle 配置中准备原生编译入口、主类、输出名称和必要的元数据。普通 Java 可参考本模板 `pom.xml`；框架项目保留自身 AOT/native 配置，见适配说明。
3. 修改 `PROJECT_DIR`、`BUILD_TOOL`、`BUILD_ARGS_JSON`、`BINARY_PATH`、`ARTIFACT_NAME`。
4. 按程序类型选择 `SMOKE_MODE`，修改启动参数、健康接口或 CLI 输出预期；纯 API/CLI 应把 `HTTP_RESOURCES_JSON` 改为 `'[]'`。
5. 选择目标平台，检查 Release 标签，再提交配置并手动运行。

不要求先在本地安装或下载 GraalVM。工作流在 GitHub runner 安装工具链并获取依赖。若自己在本地运行 Maven/Gradle，仍可能下载依赖；本模板没有把这些命令自动变成离线构建。

## 3. 顶部变量完整说明

### 构建与输出

| 变量 | 默认值 / 示例 | 含义 |
| --- | --- | --- |
| `GRAALVM_DISTRIBUTION` | `graalvm` | Oracle GraalVM；社区版可设 `graalvm-community`，要另行确认项目兼容性 |
| `JAVA_VERSION` | `'21'` | 获取该发行版可用的 Java 21 更新；不是固定的 `21+35.1`。需要锁版本时填写发行版提供的具体版本 |
| `PROJECT_DIR` | `'.'` | 相对于仓库根目录的构建目录，必须已经存在 |
| `BUILD_TOOL` | `maven` | 只接受 `maven` 或 `gradle` |
| `BUILD_ARGS_JSON` | `'["--batch-mode", "--no-transfer-progress", "clean", "package", "-Pnative"]'` | 传给构建工具的参数数组；项目须有对应的 profile/任务 |
| `BINARY_PATH` | `'target/native-demo{exe}'` | 相对于 `PROJECT_DIR` 的确切原生可执行文件路径，不接受通配匹配 |
| `ARTIFACT_NAME` | `native-demo` | 压缩包、解压目录与 Actions artifact 的名称前缀，不会重命名实际可执行文件 |
| `PACKAGE_FILES_JSON` | `'[]'` | 随程序额外分发的文件/目录，路径相对于 `PROJECT_DIR`；保持空数组即不附带外置资源 |

`{exe}` 在 Windows 替换为 `.exe`，在 macOS/Linux 替换为空。比如项目实际生成 `target/server.exe` / `target/server`，就填 `target/server{exe}`；不要填 JAR、目录、`target/*` 或 `java -jar ...`。

所有 `*_ARGS_JSON` 都是 **JSON 字符串数组**，每个参数单独一项。不写 `mvn`、`./gradlew`，不写 `&&`、管道或重定向，不依赖 shell 展开 `$变量`。路径带空格时直接作为一项字符串，勿再加 shell 引号。

脚本在 `PROJECT_DIR` 查找 Wrapper：Maven 使用 `mvnw` / `mvnw.cmd`，Gradle 使用 `gradlew` / `gradlew.bat`。没有 Maven Wrapper 时可使用 runner 上的 `mvn`；Gradle 必须提交完整 Wrapper，包括配置和 JAR。构建工作目录也是 `PROJECT_DIR`。

### 平台

| 变量 | 含义 |
| --- | --- |
| `TARGETS_JSON` | 启用目标的 JSON 字符串数组；至少一个，不能重复 |
| `RUNNERS_JSON` | 目标名称到 runner 标签的 JSON 对象；每个启用目标必须有对应项 |

默认目标与 runner 如下；标签可用性会随 GitHub 调整，运行时以实际可用标签为准。

| 目标名称 | 默认 runner |
| --- | --- |
| `linux-amd64` | `ubuntu-22.04` |
| `linux-arm64` | `ubuntu-22.04-arm` |
| `macos-amd64` | `macos-15-intel` |
| `macos-arm64` | `macos-14` |
| `windows-amd64` | `windows-2022` |

GraalVM 21 下本模板不支持 Windows ARM64，添加 `windows-arm64` 会在配置预检失败。各目标在对应系统和架构上原生编译；更改文件名或 runner 标签不会实现交叉编译。

例如先只构建 Linux AMD64 与 Apple Silicon，修改这一项即可，`RUNNERS_JSON` 可以保留完整映射：

```yaml
TARGETS_JSON: '["linux-amd64", "macos-arm64"]'
```

所有目标目前共用构建参数、程序路径和额外文件列表，仅自动替换 `{exe}`。需要各平台不同命令、SDK 或不同 DLL 列表时，要进一步修改工作流，不能仅靠顶部现有变量表达。

### 运行验证

| 变量 | 默认值 / 要求 |
| --- | --- |
| `SMOKE_MODE` | `both`；可选 `cli`、`http`、`both`、`none` |
| `CLI_ARGS_JSON` | `'["--self-test"]'`；传给程序的参数，程序必须自行退出 |
| `CLI_EXPECT` | `SELF_TEST_OK`；CLI 标准输出/错误输出中必须包含的文本 |
| `HTTP_ARGS_JSON` | `'["--serve", "18080"]'`；必须换成自己程序支持的服务启动参数 |
| `HEALTH_URL` | `http://127.0.0.1:18080/health`；仅接受 loopback HTTP，端口须与服务一致 |
| `HEALTH_EXPECT` | `'"status":"UP"'`；健康响应必须包含的文本，是子串比较，不是 JSON 结构匹配 |
| `HTTP_RESOURCES_JSON` | 静态资源检查列表；纯 API/CLI 填 `'[]'`，有资源时见第 5 节 |
| `SMOKE_TIMEOUT_SECONDS` | `'45'`；允许 1–600 秒，用于 CLI 执行及 HTTP 启动等待；资源请求另有逐请求超时 |

即使使用 `cli` 或 `none`，也请保留顶部其他配置项，不使用的参数数组可填 `'[]'`。配置预检仍会解析相关 JSON。

### 发布与保留

| 变量 | 默认值 / 含义 |
| --- | --- |
| `RELEASE_TAG` | `'native-${{ github.run_number }}'`；每次新运行生成独立标签，也可指定 `v1.0.0` |
| `RETENTION_DAYS` | `'14'`；Actions 分发包与日志保留天数，脚本允许 1–90；不控制 Release 保留期 |

名称建议使用英文字母、数字、点、横杠、下划线，例如 `my-service`、`v1.0.0`。不要使用含空格、中文或斜杠的标签和资产前缀；Release 标签还禁止 `..` 和结尾的点。

## 4. 三种常用配置

以下片段是 **替换 `native.yml` 顶部 `env` 中对应项**，不是另一个完整工作流。未列出的项保留原值；不要重复定义同名变量。

### A. CLI 工具

假设原生构建已经生成 `target/my-cli` / `target/my-cli.exe`，`--version` 会正常退出并输出 `my-cli`：

```yaml
BUILD_TOOL: maven
BUILD_ARGS_JSON: '["--batch-mode", "--no-transfer-progress", "clean", "package", "-Pnative"]'
BINARY_PATH: 'target/my-cli{exe}'
ARTIFACT_NAME: my-cli
SMOKE_MODE: cli
CLI_ARGS_JSON: '["--version"]'
CLI_EXPECT: 'my-cli'
HTTP_RESOURCES_JSON: '[]'
PACKAGE_FILES_JSON: '[]'
```

更有价值的自检是提供 `--self-test`，覆盖关键资源和核心计算，并返回明确成功标记。版本检查只能证明能启动，不能证明主要功能可用。

### B. 纯后端 API

假设程序无需参数即可前台启动，监听 8080，`GET /health` 返回 200 和 `UP`，构建输出名是 `my-service`：

```yaml
BINARY_PATH: 'target/my-service{exe}'
ARTIFACT_NAME: my-service
SMOKE_MODE: http
HTTP_ARGS_JSON: '[]'
HEALTH_URL: 'http://127.0.0.1:8080/health'
HEALTH_EXPECT: 'UP'
HTTP_RESOURCES_JSON: '[]'
PACKAGE_FILES_JSON: '[]'
```

此片段沿用默认 Maven native profile 命令，只适用于该命令确实生成此程序的项目。Spring Boot、Quarkus 的构建命令、端口参数和健康接口见 [框架适配](../../docs/adapters.md)，不能把示例的 `--serve` 当作所有框架的通用参数。

程序需要保持前台运行，验证器会在结束后终止它。健康接口应无需登录且不重定向。模板没有自动创建数据库、Redis、消息队列或注入业务凭据；依赖这些服务的项目要自行准备 CI 测试环境，并增加业务集成测试。

### C. 后端 + 内嵌网页

本仓库默认配置就是完整示例，无需修改即可构建。其关键项如下，适用于本示例的启动接口：

```yaml
SMOKE_MODE: both
CLI_ARGS_JSON: '["--self-test"]'
CLI_EXPECT: 'SELF_TEST_OK'
HTTP_ARGS_JSON: '["--serve", "18080"]'
HEALTH_URL: 'http://127.0.0.1:18080/health'
HEALTH_EXPECT: '"status":"UP"'
HTTP_RESOURCES_JSON: >-
  [{"path":"/", "source":"src/main/resources/public/index.html", "content_type":"text/html"},
   {"path":"/app.js", "source":"src/main/resources/public/app.js", "content_type":"text/javascript"},
   {"path":"/app.css", "source":"src/main/resources/public/app.css", "content_type":"text/css"},
   {"path":"/logo.png", "source":"src/main/resources/public/logo.png", "content_type":"image/png"}]
PACKAGE_FILES_JSON: '[]'
```

如果自己的服务没有 CLI 自检，把 `SMOKE_MODE` 改成 `http`。如果资源路径不同，必须同步修改 Java/框架资源路由、原生资源配置和上述检查列表。

### 多模块仓库与 Gradle

例如从聚合根构建 `apps/server` 模块：

```yaml
PROJECT_DIR: '.'
BUILD_ARGS_JSON: '["--batch-mode", "--no-transfer-progress", "clean", "package", "-Pnative", "-pl", "apps/server", "-am"]'
BINARY_PATH: 'apps/server/target/server{exe}'
ARTIFACT_NAME: server
```

native 插件应应用到真正有入口类的应用模块，避免让所有依赖库模块都执行原生编译。资源检查的 `source` 也要相对于 `PROJECT_DIR`，此时通常带上 `apps/server/` 前缀。

改用 Gradle 时，先准备 Native Build Tools 和完整 Wrapper，再替换构建工具、任务参数及二进制输出路径。完整配置见 [框架适配文档中的 Gradle 示例](../../docs/adapters.md)；框架自己的 native 任务应遵循对应框架配置。

## 5. HTML、JS、CSS、图片如何内嵌

固定资源推荐内嵌：程序与页面一起发布，分发时只需一个可执行文件。用户上传、数据库、运行时生成文件留在外部可写目录；密码、密钥和部署配置通过环境变量或外部配置传入。**内嵌不是加密，不能用于隐藏秘密。**

### 三件事必须同时配置

1. **进入 Java classpath**：普通 Maven 项目把固定资源放在 `src/main/resources/public/`，构建时复制到资源输出目录。
2. **进入 Native Image**：为资源配置包含规则；仅放进 JAR 不代表一定进入原生程序。
3. **程序正确读取**：使用 `getResourceAsStream` 或框架支持的 classpath 资源 API，不能把内嵌资源当磁盘 `File`。

本仓库的 [resource-config.json](../../src/main/resources/META-INF/native-image/example/native-demo/resource-config.json) 位于 `src/main/resources/META-INF/native-image/example/native-demo/`：

```json
{
  "resources": {
    "includes": [
      {"pattern": "\\Qgreeting.txt\\E"},
      {"pattern": "\\Qpublic/\\E.*"}
    ]
  }
}
```

这里匹配的是 classpath 内的 `public/...`，不是 `src/main/resources/public/...`。`example/native-demo` 可按自己的 group/artifact 调整。框架项目也可以使用该版本支持的资源 hints/AOT 机制，具体见 [Native Image 说明](../../docs/native-image.md)。

普通 Java 读取示例：

```java
try (var input = Main.class.getResourceAsStream("/public/index.html")) {
    if (input == null) throw new IllegalStateException("缺少内嵌首页");
    byte[] html = input.readAllBytes();
    // 在 HTTP 路由中返回这些字节，并设置 text/html; charset=utf-8。
}
```

把 `Main` 换成自己的类。HTTP 服务器如何将 URL 映射到 classpath，由应用配置；模板不会自动给任意 Javalin/Spring 项目注册静态目录。

### 使用 Vue / React 等前端

构建顺序是：**前端构建 → 复制静态产物到 Java 资源目录 → 原生编译 → 打包 → 验证**。可由项目 Maven/Gradle 生命周期组织，也可在工作流原生构建步骤之前添加明确的前端步骤。当前模板没有默认安装 Node、下载 npm 依赖或运行前端构建。

`HTTP_RESOURCES_JSON` 的 `source` 指向原生构建后实际存在的对应文件。例如将前端产物放入 `target/classes/public/`，就填写该目录下的具体路径。带内容哈希的 `assets/app-xxxx.js` 要与本次生成文件名一致；脚本不支持通配符、自动读取前端 manifest 或自动展开检查列表。

原生资源包含规则与 HTTP 检查列表是两件事：包含规则决定哪些文件进入程序；检查列表决定请求哪些文件验证。没列出的文件不会逐个检查，但仍可被资源规则内嵌。

### 静态资源检查的精确要求

每项必须恰好包含三个非空字符串字段：

| 字段 | 含义 |
| --- | --- |
| `path` | 同一服务的 URL 路径，例如 `/assets/app.css`；不是远程网址 |
| `source` | 相对于 `PROJECT_DIR` 的对照文件，构建后必须存在；不是运行时外部资源依赖 |
| `content_type` | 预期 MIME 主类型，例如 `text/css`；不写 `; charset=utf-8` |

验证器要求 HTTP 200、MIME 主类型一致、完整响应字节与对照文件一致。误把首页 HTML 返回给 JS/图片、返回旧资源或漏打包都会失败。若服务会动态改写 HTML、压缩/转换字节，应选适合精确比较的静态接口，或另加针对动态响应的验证；当前脚本不提供这些响应转换适配。

SPA 的页面路由回退由应用实现，不能把缺失 JS/CSS/图片也回退成首页。本示例对缺失文件返回 404。资源检查不运行浏览器中的 JavaScript，不证明页面交互或 GUI 已测试。

### 确实需要外置资源时

```yaml
PACKAGE_FILES_JSON: '["config", "target/extra-assets"]'
```

路径相对于 `PROJECT_DIR`，复制到包内时使用各自最后一级名称，上例成为包根目录下的 `config/`、`extra-assets/`，目录内部结构保留。应用必须按这个分发结构寻找文件。

不支持通配符、源到目标重命名映射、项目外路径和符号链接。缺失文件、同名冲突或选择整个项目目录会失败。启用此项后交付就是“可执行文件 + 附带文件”，不能再声称运行只需单文件。

## 6. 成功到底验证了什么

执行顺序：**校验配置 → 各目标构建 → 检查文件头并打包 → 校验 SHA-256 并独立解压 → 运行检查 → 上传产物 → 汇总校验并发布**。

- 文件头检查：必须是目标架构的 ELF、Mach-O 或 PE，拒绝 JAR、脚本和不匹配的架构。
- 分发检查：验证的是刚生成的压缩包；解压位置在源码目录之外，以解压目录为运行工作目录，避免依赖源码相对路径造成假成功。这不是文件系统沙箱，也不能证明程序不存在任何绝对路径依赖。
- `cli`：程序在超时前以状态码 0 退出，输出包含 `CLI_EXPECT`。
- `http`：先检查端口可用，再启动程序，等待健康接口 HTTP 200 且包含 `HEALTH_EXPECT`，然后检查所列静态资源；结束后回收服务进程。
- `both`：先 CLI，后 HTTP，分别启动进程。
- `none`：仍检查压缩包校验和、可执行文件格式与架构，但**不执行程序**，不能理解为运行通过。

HTTP 检查禁用代理和重定向，仅访问本机 loopback 地址。健康接口如果返回登录跳转、需要授权或只提供 HTTPS，需要为 CI 提供合适的本地检查入口或扩展验证器。

这只是冒烟测试。数据库访问、TLS、JSON 序列化、反射路径、业务接口、并发、浏览器交互以及桌面窗口仍需项目自己的测试。

实际结果以 [验证记录](../../docs/verification.md) 为准：早期示例有五平台成功发布记录；新增内嵌资源版本已做本地 Mac ARM64 原生验证，尚未完成这版的五平台 CI 验证。该版本边界不能因文档说明或工作流配置存在而省略。

## 7. Release、下载链接和使用者收到的文件

所有选定目标的构建、验证、上传成功后，发布任务才会执行。它先检查资产集合及 SHA-256，再创建草稿 Release、上传资产，最后转为正式 Release 并设置为 latest。任一目标失败不发布新的正式 Release；其他目标可继续完成以便排查。

默认五目标会上传 **5 个压缩包 + 5 个 `.sha256`**。例如：

```text
native-demo-linux-amd64.tar.gz
native-demo-linux-amd64.tar.gz.sha256
native-demo-macos-arm64.tar.gz
native-demo-macos-arm64.tar.gz.sha256
native-demo-windows-amd64.zip
native-demo-windows-amd64.zip.sha256
```

每个压缩包包含一个同名平台目录，其中默认只有可执行文件与 `build-info.json`。可执行文件使用 `BINARY_PATH` 的文件名，元信息记录提交、目标和工具链等；元信息不是运行依赖。单二进制不等于完全静态链接，系统库或项目 JNI 库仍可能需要另行满足。

| 位置 | 用途与保留 |
| --- | --- |
| GitHub Release | 给使用者下载的正式资产；不受 `RETENTION_DAYS` 影响 |
| Actions Artifacts | 构建排查用的分发包与 `logs-<目标>`；默认 14 天过期 |
| runner 的 `dist/` | 工作流执行期间生成的压缩包和校验文件；不会自动出现在你的电脑 |

固定版本下载地址格式：`https://github.com/<owner>/<repo>/releases/download/<tag>/<文件名>`。

最新版本下载地址格式：`https://github.com/<owner>/<repo>/releases/latest/download/<文件名>`。它会跟随新的正式发布变化；需要可复现下载时使用固定标签。模板复制到别的仓库后，要把 owner/repo 换成自己的。

Release 链接可长期使用，但不是永久托管保证；删除仓库、Release、资产或修改访问权限都会影响下载。GitHub 自动显示的 Source code 压缩包是源码，不是这里构建的原生程序。

重新运行同一次 Actions run 不会增加 `github.run_number`。如果同名 Release 已存在，脚本会失败而不覆盖资产；正常发布新版本应发起新的手动运行，固定标签则需先改成新的版本号。发布中断可能留下草稿，检查其资产与校验和后再决定如何处理，不要盲目覆盖已发布版本。

### 校验并运行：macOS / Linux

先在 Release 页面手动下载本机对应压缩包和 `.sha256`，把两个文件放在同一目录。以下命令只操作已下载文件，不会下载新内容。

macOS ARM64 示例：

```bash
shasum -a 256 -c native-demo-macos-arm64.tar.gz.sha256
# 上一步显示 OK 后再解压、运行。
tar -xzf native-demo-macos-arm64.tar.gz
./native-demo-macos-arm64/native-demo --self-test
./native-demo-macos-arm64/native-demo --serve 8080
```

Linux AMD64 对应使用 `sha256sum -c native-demo-linux-amd64.tar.gz.sha256`，校验通过后解压并运行相应目录中的程序。参数是本示例的接口，自己的应用按自己的参数运行。

示例服务启动后在本机浏览器访问 `http://127.0.0.1:8080/`，终端 Ctrl+C 停止。示例只绑定本机地址；要对外部署须在应用中配置监听地址，并由项目自行处理部署需求。

### 校验并运行：Windows PowerShell

在两个已下载文件所在目录执行：

```powershell
$archive = 'native-demo-windows-amd64.zip'
$expected = ((Get-Content "$archive.sha256" -Raw).Trim() -split '\s+')[0]
$actual = (Get-FileHash $archive -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw 'SHA-256 校验失败' }
Expand-Archive $archive -DestinationPath '.\native-unpacked'
.\native-unpacked\native-demo-windows-amd64\native-demo.exe --self-test
```

## 8. 常见失败与适用边界

| 现象 | 优先检查 |
| --- | --- |
| Actions 没有手动运行按钮 | 工作流是否已在默认分支、Actions 是否启用、当前账号是否有运行权限 |
| 配置预检失败 | JSON 格式、目标是否重复或含 Windows ARM64、目录是否存在、runner 映射是否齐全 |
| 找不到 native profile / task | 项目是否真的配置了原生插件与相应 profile；框架是否需要不同构建命令 |
| 构建结束但找不到程序 | `BINARY_PATH` 是否与实际输出名、模块目录及 `{exe}` 后缀一致 |
| 实际是 Linux 文件，却在 Windows/macOS job | 是否误启用容器构建；模板要求目标平台的本机构建 |
| CLI 超时 | 是否误启动了长期服务，是否需要非交互、自行退出的自检参数 |
| HTTP 服务提前退出 / 健康超时 | `native-logs/http.log`、启动参数、端口、健康路径、外部依赖及反射配置 |
| 资源检查找不到对照文件 | `source` 是否相对于 `PROJECT_DIR`，前端构建是否已生成对应文件 |
| 资源 404 / MIME 或字节不符 | classpath 包含规则、服务路由、SPA 回退、实际生成文件名、是否返回旧版资源 |
| 独立目录运行失败 | 是否从源码目录读取资源，是否遗漏外部配置/库，程序相对路径是否符合包内结构 |
| 发布权限不足 | Release job 的 `contents: write`、仓库/组织的 Actions 限制；默认使用内置 `GITHUB_TOKEN` |
| Release 标签已存在 | 新建一次手动运行或修改固定版本标签；不会自动覆盖旧资产 |

先看失败 job 的具体步骤与日志，必要时只下载该目标的 `logs-<目标>` artifact，无需把五个平台的二进制全部下载到本机。

**后端与 CLI** 是本模板的重点，仍需按实际依赖完成原生适配。Spring/Javalin/Quarkus/Gradle 配置是接入参考，不是所有版本都跑过的兼容认证。

**浏览器页面** 可以由内嵌资源的 HTTP 服务提供。**Swing/AWT/JavaFX 等原生桌面窗口** 则取决于 GUI 工具包和专用工具链，当前模板未提供通用 GUI 支持或桌面验证。`SMOKE_MODE: none` 不能解决 GUI 编译问题，CLI 自检也不代表窗口已测试。

当前不生成 `.app`、DMG、MSI、安装器、签名或 macOS 公证。Linux 默认使用 glibc，不承诺 Alpine/musl 或更旧系统兼容；macOS 最低版本、系统库与 CPU 要求也应按产物实际测试确认。

## 9. 流量与本地操作

编辑、阅读本地说明不会触发构建或下载。手动运行 Actions 后，GraalVM、构建依赖及 runner 之间的资产传输发生在 GitHub 执行环境；查看日志页面、拉取源码、下载 Release/Artifacts 仍会消耗本机网络流量。

处于按流量计费网络时，只下载自己所需平台的一个包及其小型校验文件；不批量下载五平台产物，不为阅读或改配置在本地安装 GraalVM、Gradle、Node 或拉取容器镜像。需要本地构建时，先确认已有工具和依赖缓存，不要把普通 Maven/Gradle 构建当作零下载操作。
