package example;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpExchange;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/** JDK 21 自带 API：一个二进制演示 CLI、资源加载和长期运行的 HTTP 服务。 */
public final class Main {
    private static final Map<String, String> CONTENT_TYPES = Map.of(
            "html", "text/html; charset=utf-8", "css", "text/css; charset=utf-8",
            "js", "text/javascript; charset=utf-8", "png", "image/png",
            "svg", "image/svg+xml", "jpg", "image/jpeg", "ico", "image/x-icon");

    private Main() {}

    public static void main(String[] args) throws Exception {
        // 标准输出也固定 UTF-8，避免 Windows 控制台编码影响中文重定向日志。
        System.setOut(new PrintStream(System.out, true, StandardCharsets.UTF_8));
        System.setErr(new PrintStream(System.err, true, StandardCharsets.UTF_8));
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
        byte[] bytes = resource("/greeting.txt");
        if (bytes == null) throw new IllegalStateException("greeting.txt 未被打包");
        return new String(bytes, StandardCharsets.UTF_8).strip();
    }

    private static byte[] resource(String name) throws IOException {
        // 直接读取 classpath 流；原生程序内的资源不一定对应磁盘文件，不能转 File。
        try (InputStream input = Main.class.getResourceAsStream(name)) {
            return input == null ? null : input.readAllBytes();
        }
    }

    private static void respond(HttpExchange exchange, int status, String type, byte[] body)
            throws IOException {
        exchange.getResponseHeaders().set("Content-Type", type);
        exchange.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        if (exchange.getRequestMethod().equals("HEAD")) {
            exchange.getResponseHeaders().set("Content-Length", Integer.toString(body.length));
            exchange.sendResponseHeaders(status, -1);
            exchange.close();
        } else {
            exchange.sendResponseHeaders(status, body.length);
            try (var output = exchange.getResponseBody()) { output.write(body); }
        }
    }

    private static void handle(HttpExchange exchange) throws IOException {
        String method = exchange.getRequestMethod();
        if (!method.equals("GET") && !method.equals("HEAD")) {
            exchange.getResponseHeaders().set("Allow", "GET, HEAD");
            respond(exchange, 405, "text/plain; charset=utf-8", "Method Not Allowed".getBytes(StandardCharsets.UTF_8));
            return;
        }
        // URI#getPath 已解码。禁止越级路径，不把 classpath 根目录或源码作为静态目录。
        String path = exchange.getRequestURI().getPath();
        for (String part : path.split("/")) {
            if (part.equals(".") || part.equals("..") || part.contains("\\") || part.contains("\0")) {
                respond(exchange, 400, "text/plain; charset=utf-8", "Bad Request".getBytes(StandardCharsets.UTF_8));
                return;
            }
        }
        if (path.equals("/health")) {
            byte[] body = ("{\"status\":\"UP\",\"message\":\"" + greeting() + "\"}").getBytes(StandardCharsets.UTF_8);
            respond(exchange, 200, "application/json; charset=utf-8", body);
            return;
        }
        if (path.equals("/")) path = "/index.html";
        byte[] body = resource("/public" + path);
        if (body == null) {
            // 缺失 JS/图片必须返回 404，不能返回 HTML 假装资源存在。
            respond(exchange, 404, "text/plain; charset=utf-8", "Not Found".getBytes(StandardCharsets.UTF_8));
            return;
        }
        String extension = path.substring(path.lastIndexOf('.') + 1);
        respond(exchange, 200, CONTENT_TYPES.getOrDefault(extension, "application/octet-stream"), body);
    }

    private static void serve(int port) throws IOException {
        // 示例仅监听 loopback，避免本机验证时意外暴露网络端口。
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/", Main::handle);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
        server.start();
        System.out.println("Listening on http://127.0.0.1:" + server.getAddress().getPort());
    }
}
