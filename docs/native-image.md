# Native Image 元数据与排错示例

## 示例中的资源注册

`src/main/resources/META-INF/native-image/example/native-demo/resource-config.json`：

```json
{"resources":{"includes":[{"pattern":"\\Qgreeting.txt\\E"}]}}
```

它告诉构建器把 `greeting.txt` 放进二进制。实际项目应精准包含需要的模板、静态文件、证书或国际化资源，不要无差别包含整个 classpath。

## 反射注册示例

若程序通过运行时字符串执行 `Class.forName`、调用反射构造函数或字段，可能需要在同目录添加 `reflect-config.json`。下面只是结构示例，把类名换成实际类名并按实际访问范围缩小权限；不要把不存在的示例类直接加入项目：

```json
[
  {
    "name": "com.example.Person",
    "allDeclaredConstructors": true,
    "fields": [{"name": "name"}]
  }
]
```

Spring Boot 优先使用框架的 `RuntimeHints`；Quarkus 优先使用其扩展或 `@RegisterForReflection`。不要同时维护多套冲突配置。

## 用 Tracing Agent 收集实际路径

在你专门选择的开发/测试环境中，先用 GraalVM JVM 跑应用并覆盖实际功能。以下以本仓库示例为例；这些是给使用者的操作示例，不由默认工作流自动在本地执行：

```bash
mvn package
java -agentlib:native-image-agent=config-output-dir=target/native-agent \
  -jar target/native-demo.jar --self-test
```

Web 应用应在 agent 下启动服务，调用真实业务接口后正常关闭进程，检查生成的文件，再把必要配置放入 `META-INF/native-image/<group>/<artifact>/`。只启动一次不会收集未执行的路径。依赖数据库、外部服务的采集应放到明确的测试环境，不能让通用模板猜测或自动连接生产环境。

## 常见失败

| 表现 | 检查方向 |
| --- | --- |
| 构建成功，访问接口时才报反射错误 | 检查对应类/构造器/方法的 hints 或元数据；增加能覆盖该接口的原生测试 |
| 模板、配置、国际化文件丢失 | 检查 resources 配置及路径大小写；区分内置 classpath 资源与外部文件 |
| Windows 找不到编译器 | 检查 setup-graalvm 日志和 MSVC/Windows SDK；不要用 Linux 容器生成 exe |
| Linux 提示 GLIBC 版本不足 | 构建环境比部署环境新；在兼容的旧基线上重建并验证，不在目标机替换系统 glibc |
| macOS 显示架构不匹配 | Apple Silicon 选 arm64，Intel 选 amd64；检查文件头，不依赖压缩包名字 |
| 编译 OOM 或超时 | 原生编译耗费 CPU/内存；根据项目选择更大 runner、限制构建内存或调整超时 |
| `UnsupportedFeatureError` | 先判断是否为不支持的动态行为/GUI 工具包，不靠广泛初始化参数强压通过 |
| 健康检查失败 | 下载 http.log，检查启动参数、端口、数据库/配置依赖和就绪时间 |

参考：[GraalVM JDK 21 元数据](https://www.graalvm.org/jdk21/reference-manual/native-image/metadata/)、[Tracing Agent](https://www.graalvm.org/jdk21/reference-manual/native-image/metadata/AutomaticMetadataCollection/)、[Maven 插件](https://graalvm.github.io/native-build-tools/0.10.6/maven-plugin.html)。
