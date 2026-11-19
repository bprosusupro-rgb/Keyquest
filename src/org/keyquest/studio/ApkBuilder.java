package org.keyquest.studio;

import com.android.apksig.ApkSigner;
import com.android.apksig.ApkVerifier;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.zip.*;

final class ApkBuilder {
    private static final String OVERLAY = "assets/x-game/x-keyquest_overlay.rpyc";
    private static final long LIMIT = 3_000_000_000L;

    static void build(File source, File unsigned, File result, byte[] overlay,
                      ApkSigner.SignerConfig signer) throws Exception {
        rebuild(source, unsigned, overlay);
        new ApkSigner.Builder(Collections.singletonList(signer))
                .setInputApk(unsigned).setOutputApk(result).setMinSdkVersion(24)
                .setV1SigningEnabled(false).setV2SigningEnabled(true)
                .setV3SigningEnabled(true).setV4SigningEnabled(false).build().sign();
        if (!new ApkVerifier.Builder(result).setMinCheckedPlatformVersion(24).build().verify().isVerified()) {
            throw new IOException("The rebuilt APK did not pass signature verification.");
        }
    }

    static void rebuild(File source, File result, byte[] overlay) throws IOException {
        try (ZipFile input = new ZipFile(source)) {
            Set<String> names = new HashSet<>();
            boolean scripts = false;
            long size = 0;
            for (ZipEntry entry : Collections.list(input.entries())) {
                String name = entry.getName();
                long entrySize = entry.getSize();
                if (!names.add(name) || entrySize < 0 || entrySize > LIMIT - size) {
                    throw new IOException("APK contains duplicate entries or is too large.");
                }
                size += entrySize;
                scripts |= name.startsWith("assets/x-game/") &&
                        (name.endsWith(".rpyc") || name.endsWith(".rpa"));
            }
            if (!names.contains("AndroidManifest.xml") || !names.contains("assets/private.mp3") || !scripts) {
                throw new IOException("Choose a single Ren’Py APK with the standard universal layout.");
            }
            if (names.contains(OVERLAY)) throw new IOException("This game already contains Keyquest.");

            try (Counter bytes = new Counter(new BufferedOutputStream(Files.newOutputStream(result.toPath())));
                 ZipOutputStream output = new ZipOutputStream(bytes)) {
                output.setLevel(1);
                for (ZipEntry original : Collections.list(input.entries())) {
                    String name = original.getName();
                    if (signature(name)) continue;
                    ZipEntry entry = new ZipEntry(name);
                    entry.setMethod(original.getMethod());
                    if (entry.getMethod() == ZipEntry.STORED) {
                        entry.setSize(original.getSize());
                        entry.setCrc(original.getCrc());
                        align(entry, bytes.count, name.startsWith("lib/") && name.endsWith(".so") ? 16384 : 4);
                    }
                    output.putNextEntry(entry);
                    try (InputStream data = input.getInputStream(original)) {
                        copy(data, output, original.getSize());
                    }
                    output.closeEntry();
                }
                ZipEntry script = new ZipEntry(OVERLAY);
                output.putNextEntry(script);
                output.write(overlay);
                output.closeEntry();
            }
        }
    }

    static void copy(InputStream input, OutputStream output, long limit) throws IOException {
        byte[] buffer = new byte[128 * 1024];
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (count > limit) throw new IOException("Input exceeded its expected size.");
            output.write(buffer, 0, count);
            limit -= count;
        }
    }

    private static boolean signature(String name) {
        return name.toUpperCase(Locale.ROOT).matches("META-INF/[^/]+\\.(SF|RSA|DSA|EC|MF)");
    }

    private static void align(ZipEntry entry, long offset, int boundary) {
        long header = offset + 30 + entry.getName().getBytes(StandardCharsets.UTF_8).length;
        int padding = (int) ((boundary - header % boundary) % boundary);
        if (padding == 0) return;
        if (padding < 4) padding += boundary;
        byte[] field = new byte[padding];
        field[0] = 0x35;
        field[1] = (byte) 0xd9;
        field[2] = (byte) ((padding - 4) & 255);
        field[3] = (byte) ((padding - 4) >>> 8);
        entry.setExtra(field);
    }

    private static final class Counter extends FilterOutputStream {
        long count;
        Counter(OutputStream output) { super(output); }
        @Override public void write(int value) throws IOException { out.write(value); count++; }
        @Override public void write(byte[] values, int start, int length) throws IOException {
            out.write(values, start, length);
            count += length;
        }
    }
}
