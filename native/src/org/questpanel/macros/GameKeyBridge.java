package org.questpanel.macros;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** Shell-side entry point. An authorized ADB session starts it explicitly. */
public final class GameKeyBridge {
    private static final int PORT = 38941;
    private static final InetAddress LOOPBACK = loopback();
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final Pattern PACKAGE = Pattern.compile("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+");
    private static final Pattern DISPLAY = Pattern.compile("^\\s*Display: mDisplayId=(\\d+).*");
    private static final Pattern FOCUSED = Pattern.compile("mCurrentFocus=Window\\{.*?\\s([A-Za-z0-9_.]+)/");
    private static final String SELF = "org.questpanel.macros";

    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !args[0].matches("[a-f0-9]{32}")) return;
        try (ServerSocket server = new ServerSocket(PORT, 8, LOOPBACK)) {
            server.setSoTimeout(30_000);
            System.out.println("Keyquest game-key bridge ready.");
            long deadline = System.nanoTime() + TimeUnit.HOURS.toNanos(2);
            while (System.nanoTime() < deadline) {
                try (Socket socket = server.accept()) {
                    if (serve(socket, args[0])) return;
                } catch (IOException ignored) {
                    // Unavailable clients do not terminate the session.
                }
            }
        }
    }

    private static boolean serve(Socket socket, String secret) throws IOException {
        socket.setSoTimeout(1000);
        DataInputStream input = new DataInputStream(socket.getInputStream());
        DataOutputStream output = new DataOutputStream(socket.getOutputStream());
        String nonce = newCode();
        output.writeUTF(nonce);
        output.flush();
        String message = input.readUTF();
        String proof = input.readUTF();
        if (message.length() > 250 || !equal(proof, sign(secret, nonce + ":request:" + message))) return false;
        String result;
        if ("check".equals(message)) result = "Game-key bridge connected.";
        else if ("stop".equals(message)) result = "Game-key bridge stopped.";
        else {
            String[] parts = message.split(":", -1);
            result = parts.length == 3 ? inject(parts[0], parts[1], parts[2]) : "Invalid key request.";
        }
        output.writeUTF(result);
        output.writeUTF(sign(secret, nonce + ":response:" + result));
        output.flush();
        return "stop".equals(message);
    }

    static String request(String secret, String message) throws IOException {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(LOOPBACK, PORT), 400);
            socket.setSoTimeout(4500);
            DataInputStream input = new DataInputStream(socket.getInputStream());
            DataOutputStream output = new DataOutputStream(socket.getOutputStream());
            String nonce = input.readUTF();
            if (!nonce.matches("[a-f0-9]{32}")) throw new IOException("Invalid challenge");
            output.writeUTF(message);
            output.writeUTF(sign(secret, nonce + ":request:" + message));
            output.flush();
            String response = input.readUTF();
            if (!equal(input.readUTF(), sign(secret, nonce + ":response:" + response))) {
                throw new IOException("Invalid bridge response");
            }
            return response;
        }
    }

    private static String inject(String game, String display, String code) {
        if (!PACKAGE.matcher(game).matches() || SELF.equals(game)
                || !display.matches("\\d{1,5}") || !code.matches("\\d{1,2}")) return "Invalid game or display.";
        int keyCode = Integer.parseInt(code);
        if (!(keyCode >= 7 && keyCode <= 16 || keyCode >= 29 && keyCode <= 54
                || keyCode == 62 || keyCode == 66 || keyCode == 67)) return "Unsupported game key.";
        try {
            boolean hasFocus = focused(game, display);
            if (!hasFocus) {
                run("/system/bin/am", "start", "--display", display, "-a", "android.intent.action.MAIN",
                    "-c", "android.intent.category.LAUNCHER", "-p", game);
                for (int attempt = 0; attempt < 4 && !hasFocus; attempt++) {
                    Thread.sleep(125);
                    hasFocus = focused(game, display);
                }
            }
            if (!hasFocus) return "Game focus could not be confirmed. Check the package and display ID.";
            run("/system/bin/input", "-d", display, "keyevent", code);
            return "Game key sent.";
        } catch (IOException | InterruptedException error) {
            return "Android rejected the game-key request.";
        }
    }

    private static boolean focused(String game, String wantedDisplay) throws IOException, InterruptedException {
        String display = "";
        for (String line : run("/system/bin/dumpsys", "-t", "1", "window", "displays").split("\\n")) {
            Matcher header = DISPLAY.matcher(line);
            if (header.matches()) display = header.group(1);
            Matcher focus = FOCUSED.matcher(line);
            if (wantedDisplay.equals(display) && focus.find() && game.equals(focus.group(1))) return true;
        }
        return false;
    }

    private static String run(String... command) throws IOException, InterruptedException {
        Process child = new ProcessBuilder(command).redirectErrorStream(true).start();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(child.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder result = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) result.append(line).append('\n');
            if (!child.waitFor(500, TimeUnit.MILLISECONDS) || child.exitValue() != 0
                    || result.indexOf("Error:") >= 0) throw new IOException("Command failed");
            return result.toString();
        } finally {
            child.destroy();
        }
    }

    static String newCode() {
        byte[] bytes = new byte[16];
        RANDOM.nextBytes(bytes);
        return hex(bytes);
    }

    private static String sign(String secret, String message) throws IOException {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.US_ASCII), "HmacSHA256"));
            return hex(mac.doFinal(message.getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.GeneralSecurityException error) {
            throw new IOException(error);
        }
    }

    private static String hex(byte[] data) {
        StringBuilder result = new StringBuilder();
        for (byte value : data) {
            result.append(Character.forDigit((value & 255) >>> 4, 16));
            result.append(Character.forDigit(value & 15, 16));
        }
        return result.toString();
    }

    private static boolean equal(String left, String right) {
        return MessageDigest.isEqual(left.getBytes(StandardCharsets.US_ASCII), right.getBytes(StandardCharsets.US_ASCII));
    }

    private static InetAddress loopback() {
        try {
            return InetAddress.getByAddress(new byte[] {127, 0, 0, 1});
        } catch (UnknownHostException impossible) {
            throw new AssertionError(impossible);
        }
    }
}
