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

正在对补充 Release 发布步骤后的工作流进行完整验证；完成后补充长期下载链接与最终产物校验结果。

默认示例验证范围：原生文件格式和 CPU 架构、CLI 自检、中文资源加载、HTTP 健康接口、压缩包 SHA-256。

Spring Boot、Quarkus、Javalin、Gradle、GUI 文档目前是接入示例，不等同于对应应用已经经过五平台构建验证。
