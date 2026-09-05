# 验证记录

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
