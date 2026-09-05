package example;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

/** JDK 21 自带 API：一个二进制演示 CLI、资源加载和长期运行的 HTTP 服务。 */
public final class Main {
    private Main() {}

    public static void main(String[] args) throws Exception {
        String command = args.length == 0 ? "--help" : args[0];
        switch (command) {
            case "--help" -> System.out.println("native-demo: --version | --self-test | --serve [port]");
            case "--version" -> System.out.println("native-demo 1.0.0");
            case "--self-test" -> {
                // 确认真实读取了被打包的资源；不能只打印成功来冒充验证。
                if (!greeting().equals("你好，Native Image！")) {
                    throw new IllegalStateException("资源内容不正确");
                }
                System.out.println("SELF_TEST_OK: " + greeting());
            }
            case "--serve" -> serve(args.length > 1 ? Integer.parseInt(args[1]) : 8080);
            default -> {
                System.err.println("未知参数：" + command);
                System.exit(2);
            }
        }
    }

    private static String greeting() throws IOException {
        // 资源进入 native image 的规则见 META-INF/native-image/example/native-demo。
        try (InputStream input = Main.class.getResourceAsStream("/greeting.txt")) {
            if (input == null) throw new IllegalStateException("greeting.txt 未被打包");
            return new String(input.readAllBytes(), StandardCharsets.UTF_8).strip();
        }
    }

    private static void serve(int port) throws IOException {
        // 示例仅监听 loopback，避免本机验证时意外暴露网络端口。
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/health", exchange -> {
            byte[] response = ("{\"status\":\"UP\",\"message\":\"" + greeting() + "\"}")
                    .getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            exchange.sendResponseHeaders(200, response.length);
            try (var output = exchange.getResponseBody()) { output.write(response); }
        });
        Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
        server.start();
        System.out.println("Listening on http://127.0.0.1:" + server.getAddress().getPort());
    }
}
