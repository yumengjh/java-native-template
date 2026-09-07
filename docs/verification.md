# 验证记录

## 当前源码：内嵌静态资源（本地离线验证，尚未发布新 Release）

此项变更不属于下方历史 `native-3` 产物。为遵守流量计费约束，本轮未触发远程构建、未下载依赖或新产物。

- 使用本机已经安装的 Oracle GraalVM 21+35.1，直接调用 javac/native-image，开启 `--no-fallback -march=compatibility`；没有运行 Maven/Gradle 下载。
- 本地生成 Mac ARM64 可执行文件，18,867,288 bytes；HTML、JS、CSS 和 PNG 图片内嵌。
- 使用更新后的工作流辅助脚本先打包，再解压到源码之外的操作系统临时目录执行验证。
- 压缩包只包含 `native-demo` 和 `build-info.json` 两个普通文件，没有散落的静态资源。
- 禁用 PATH/JAVA_HOME/GRAALVM_HOME 后，CLI 中文自检、HTTP 健康检查、四种资源的 HTTP 200/MIME/完整字节比较全部通过。
- 单独复制一个可执行文件到空目录，验证缺失资源 404、内部资源不暴露、健康路由精确匹配、路径越级拒绝、405 和 HEAD 行为通过。
- `python3 -m unittest discover -s tests -v`：11 项回归检查通过，包含内容/类型不匹配、外部 URL、损坏压缩包、越级解压、Unix tar 与 Windows zip 解压路径。
- Python 语法、YAML 解析、JS 语法及 Git diff 格式检查通过。
- 本轮未执行浏览器 UI 自动化；新版本的 Windows/Linux 原生运行尚未重新验证，不能将历史五平台结果当成本次结果。

本地输出（均被 Git 忽略）：

```text
.verification/embedded/native-demo       # 可直接运行的 Mac ARM64 单二进制
.verification/embedded/native-build.log  # 本机离线编译日志
.verification/embedded/result.json       # 验证摘要
dist/native-demo-macos-arm64.tar.gz      # 本次本地构建的分发包，尚未发布
```

本次本地压缩包 SHA-256：`2667aaf8d334357f2a69d771ed176ad7917a853b8cf71db2f7df4e0458a29a2b`。

## 已通过的构建与本机验证

- [第二轮 Actions：33972073643](https://github.com/yumengjh/java-native-template/actions/runs/33972073643)，提交 `9594d86c6cb449e6f45933591af74132c6a2ab65`。
- Linux AMD64 / ARM64、macOS AMD64 / ARM64、Windows AMD64 五个目标全部通过编译、真实文件头检查、CLI 自检、HTTP 冒烟及打包。
- 实际使用 Oracle GraalVM 21.0.12，配置的 `21` 解析到可用的 Java 21 更新版本。
- 在本机 macOS 26.5.1 / Apple Silicon 下载并验证了本次 macOS ARM64 产物。
- SHA-256 校验通过；二进制为 Mach-O ARM64，17,661,096 bytes。
- 本机验证时将 PATH、JAVA_HOME、GRAALVM_HOME 指向不存在路径，CLI 中文资源自检与 HTTP 健康接口仍通过，服务进程已回收。
- 第一轮遇到 Windows CP1252 中文输出错误；已修复 Python 和 Java 示例的 UTF-8 输出，第二轮 Windows 完整通过。

## Release 发布

- [最终完整 Actions：33972744774](https://github.com/yumengjh/java-native-template/actions/runs/33972744774)：五种原生目标、Release 发布、最终汇总全部成功。
- [正式 Release native-3](https://github.com/yumengjh/java-native-template/releases/tag/native-3)，源码提交 `a9bfd6eb52f3ba30c845dadca57e5611ef32ed8f`。
- Release 已公开，包含五个压缩包、五个 SHA-256 文件，共十个资产。每个包内有构建信息，资产在 GitHub runner 汇总时复核了完整性与校验和。
- [最新 Mac ARM64 直接下载](https://github.com/yumengjh/java-native-template/releases/latest/download/native-demo-macos-arm64.tar.gz)。
- 已从正式 Release 下载 macOS ARM64 包并在本机重新验证，而非只复用上一轮 Actions artifact。
- Release Mac 包大小 7,156,296 bytes；解压二进制 17,661,096 bytes。
- Release Mac 包 SHA-256：`b18d111510fac9219957da20fc8cc2fb97ff4c476073f4ad8016bed08b9d265b`。
- 内嵌提交与运行 ID 与 Release 对应；在不可用 PATH / JAVA_HOME / GRAALVM_HOME 下，CLI 中文资源自检和 HTTP 检查再次通过，服务进程已回收。
- 本地仅保留 `downloads/native-3/` 中的最终 Mac 下载包、校验文件和解压结果；已清理上一轮重复的下载目录。没有下载或安装额外工具、Maven/Gradle 依赖。

默认示例验证范围：原生文件格式和 CPU 架构、CLI 自检、中文资源加载、HTTP 健康接口、压缩包 SHA-256。

Spring Boot、Quarkus、Javalin、Gradle、GUI 文档目前是接入示例，不等同于对应应用已经经过五平台构建验证。
