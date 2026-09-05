# 框架接入示例

下面是接入契约和配置片段，**不是已对所有框架、版本和 GUI 工具包跑过的兼容性认证**。本仓库默认构建的是根目录的 JDK CLI/HTTP 示例。框架项目应选用与 GraalVM for JDK 21 兼容的版本，并遵循该版本自己的原生构建文档。

## 普通 Java / CLI / Javalin（Maven）

根目录 `pom.xml` 是完整可运行示例：native profile 中配置 `native-maven-plugin`、入口类、输出名、`--no-fallback` 和 `-march=compatibility`。接入 CLI 时替换 `mainClass`、`imageName`，使用以下变量：

```yaml
BUILD_TOOL: maven
BUILD_ARGS_JSON: '["--batch-mode", "clean", "package", "-Pnative"]'
BINARY_PATH: 'target/my-cli{exe}'
ARTIFACT_NAME: my-cli
SMOKE_MODE: cli
CLI_ARGS_JSON: '["--version"]'
CLI_EXPECT: 'my-cli'
```

Javalin 可以使用相同的 Maven Native Build Tools 方式，入口换成启动 Javalin 的 `main` 类，使用自己项目的依赖。典型健康路由：

```java
Javalin.create().get("/health", ctx -> ctx.result("UP")).start(8080);
```

对应工作流变量：

```yaml
SMOKE_MODE: http
HTTP_ARGS_JSON: '[]'
HEALTH_URL: 'http://127.0.0.1:8080/health'
HEALTH_EXPECT: 'UP'
```

Jetty、日志框架、JSON 映射、Thymeleaf 模板、静态资源等依赖要分别适配。特别是 JSON 实体反射、模板资源和 WebSocket，健康接口通过不代表这些路径也通过。不要直接复制旧版 Javalin/Jetty 的整套反射配置；使用你实际依赖版本的共享元数据、agent 采集和功能测试。

参考：[Javalin 官方 Native Image 示例](https://javalin.io/2018/09/27/javalin-graalvm-example.html)（历史文章，只作思路参考，版本与参数不能直接照搬）。

## Spring Boot（Maven）

使用支持 Java 21 Native Image 的 Spring Boot 项目，例如带 GraalVM Native Support 的 Spring Initializr 项目。保留 Spring Boot parent/BOM、`spring-boot-maven-plugin` 和生成的 native 支持。若项目继承 `spring-boot-starter-parent`，其 native profile 负责 Spring AOT；原生插件配置示例：

```xml
<plugin>
  <groupId>org.graalvm.buildtools</groupId>
  <artifactId>native-maven-plugin</artifactId>
  <!-- 在 Spring Boot parent 管理版本时不另写不匹配的插件版本。 -->
  <configuration>
    <imageName>my-service</imageName>
    <buildArgs>
      <buildArg>--no-fallback</buildArg>
      <buildArg>-march=compatibility</buildArg>
    </buildArgs>
  </configuration>
</plugin>
```

```yaml
BUILD_TOOL: maven
BUILD_ARGS_JSON: '["--batch-mode", "--no-transfer-progress", "clean", "-Pnative", "native:compile"]'
BINARY_PATH: 'target/my-service{exe}'
ARTIFACT_NAME: my-service
SMOKE_MODE: http
HTTP_ARGS_JSON: '["--server.port=18080"]'
HEALTH_URL: 'http://127.0.0.1:18080/actuator/health'
HEALTH_EXPECT: '"status":"UP"'
```

上述健康接口需要 Actuator，且允许 runner 访问；也可以换成你自己的 `/health`。若没有继承 Spring Boot parent，需要按文档配置 `process-aot` 的执行。不要绕过 Spring AOT，直接对可执行 fat JAR 调 `native-image -jar`。

参考：[Spring Boot 原生构建](https://docs.spring.io/spring-boot/3.5/how-to/native-image/developing-your-first-application.html)、[Spring Boot 3.5 要求](https://docs.spring.io/spring-boot/3.5/system-requirements.html)。

## Quarkus（Maven）

保留 Quarkus 生成项目自带的 BOM、Maven 插件和 native profile。使用该 Quarkus 版本要求的 GraalVM 21 补丁版本，不能假设所有新版本 Quarkus 都支持旧 GraalVM。

```yaml
BUILD_TOOL: maven
BUILD_ARGS_JSON: '["--batch-mode", "--no-transfer-progress", "clean", "package", "-Dnative", "-Dquarkus.native.container-build=false", "-Dquarkus.native.march=compatibility", "-Dquarkus.package.output-name=my-service"]'
BINARY_PATH: 'target/my-service-runner{exe}'
ARTIFACT_NAME: my-service
SMOKE_MODE: http
HTTP_ARGS_JSON: '["-Dquarkus.http.port=18080"]'
HEALTH_URL: 'http://127.0.0.1:18080/q/health'
HEALTH_EXPECT: '"status":'
```

`/q/health` 需要 `quarkus-smallrye-health` 扩展，也可换成自定义接口。必须使用本机 native 构建：如果开容器构建，Windows/macOS job 也可能生成 Linux 文件，架构检查会拒绝。按项目需要加 `-DskipITs=false` 执行 Quarkus 原生集成测试；模板本身的健康检查不替代这些测试。

参考：[Quarkus 3.20 原生构建文档](https://quarkus.io/version/3.20/guides/building-native-image/)。

## Gradle（普通 Java / CLI）

后续迁移到 Gradle 不需要更换平台矩阵。先提交项目的 Gradle Wrapper，使用兼容 Java 21 的 Gradle 版本，在 `build.gradle` 中合并如下配置（Groovy DSL）：

```groovy
plugins {
    id 'application'
    id 'org.graalvm.buildtools.native' version '0.10.6'
}
java {
    toolchain { languageVersion = JavaLanguageVersion.of(21) }
}
application { mainClass = 'example.Main' }
graalvmNative {
    // 使用 Actions 已设置的 GraalVM，不另外下载另一份 JDK。
    toolchainDetection = false
    metadataRepository { enabled = true }
    binaries {
        main {
            imageName = 'my-app'
            mainClass = 'example.Main'
            buildArgs.addAll('--no-fallback', '-march=compatibility')
        }
    }
}
```

```yaml
BUILD_TOOL: gradle
BUILD_ARGS_JSON: '["--no-daemon", "clean", "test", "nativeCompile"]'
BINARY_PATH: 'build/native/nativeCompile/my-app{exe}'
ARTIFACT_NAME: my-app
SMOKE_MODE: cli
CLI_ARGS_JSON: '["--self-test"]'
CLI_EXPECT: 'SELF_TEST_OK'
```

Spring Boot Gradle 项目保留 Spring Boot/AOT 插件；Quarkus Gradle 项目使用自己的 `quarkusBuild` 和 native 参数，不照搬普通 Java 的任务名。

参考：[Native Build Tools 0.10.6 Gradle 插件](https://graalvm.github.io/native-build-tools/0.10.6/gradle-plugin.html)。

## GUI 桌面应用：需要确定工具包后适配

工作流允许构建和携带 GUI 程序的资源，但 **Oracle GraalVM 21 + 普通 native-maven-plugin 不是任意 Swing/AWT/JavaFX 应用的通用编译器**。JavaFX 的原生化通常涉及 GluonFX、专用 GraalVM、静态 JavaFX 库、平台 SDK；它们的支持矩阵和版本必须匹配。仅改 `BUILD_ARGS_JSON` 并不充分。

GUI 项目的接入步骤：

1. 先确认 Swing、JavaFX、SWT 或其他工具包，以及它对 Java 21 和目标平台的支持。
2. 如需专用发行版，在工作流的工具链步骤中配置它，并添加该工具包要求的 runner 系统依赖。默认工作流不声称已经提供这部分。
3. 把该项目经验证的 Maven/Gradle 构建参数放到 `BUILD_ARGS_JSON`，实际可执行文件放到 `BINARY_PATH`，DLL/资源目录放到 `PACKAGE_FILES_JSON`。
4. 提供不打开窗口、能够退出的 `--self-test`，选择 `SMOKE_MODE: cli`。若用 `none`，运行摘要会明确显示没有执行验证。
5. 窗口绘制、输入、字体、系统托盘、图标、安装器、签名和公证需额外的桌面测试与打包步骤。

参考：[GluonFX 平台与工具链文档](https://docs.gluonhq.com/)。如果目标只是“双击运行，无需用户安装 Java”，可另外选择 `jpackage` 捆绑运行时，但那属于另一种交付方式，当前模板没有混用。
