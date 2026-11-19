package org.keyquest.studio;

import com.android.apksig.ApkSigner;
import com.android.apksig.ApkVerifier;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.zip.*;

final class ApkBuilder {
    static final String OVERLAY = "assets/x-game/x-keyquest_overlay.rpyc";
    static final String VALUES = "assets/x-game/x-keyquest_values.rpyc";
    static final String AUTOMATION = "assets/x-game/x-keyquest_automation.rpyc";
    static final String OCR = "assets/x-game/x-keyquest_ocr.rpyc";
    static final String[] ARTWORK = {"logo", "panel", "panel_mint", "key", "key_focus", "sheet"};

    static String artworkPath(String name) {
        return "assets/x-game/x-keyquest_" + name + ".png";
    }

    private static boolean studioAsset(String path) {
        if (path.equals(OVERLAY) || path.equals(VALUES) || path.equals(AUTOMATION) || path.equals(OCR)) return true;
        for (String name : ARTWORK) {
            if (path.equals(artworkPath(name))) return true;
        }
        return false;
    }
    private static final long LIMIT = 3_000_000_000L;

    interface Observer {
        void update(String stage, long copied, long total);
    }

    static void build(File source, File unsigned, File result, Map<String, byte[]> assets,
                      ApkSigner.SignerConfig signer) throws Exception {
        rebuild(source, unsigned, assets, null, (stage, copied, total) -> {});
        sign(unsigned, result, assets, signer, (stage, copied, total) -> {});
    }

    static void build(File source, File unsigned, File result, Map<String, byte[]> assets,
                      ApkSigner.SignerConfig signer, String label, Observer observer) throws Exception {
        rebuild(source, unsigned, assets, label, observer);
        sign(unsigned, result, assets, signer, observer);
    }

    private static void sign(File unsigned, File result, Map<String, byte[]> assets, ApkSigner.SignerConfig signer, Observer observer)
            throws Exception {
        observer.update("Signing", 0, 0);
        new ApkSigner.Builder(Collections.singletonList(signer))
                .setInputApk(unsigned).setOutputApk(result).setMinSdkVersion(24)
                .setV1SigningEnabled(false).setV2SigningEnabled(true)
                .setV3SigningEnabled(true).setV4SigningEnabled(false).build().sign();
        observer.update("Verifying", 0, 0);
        if (!new ApkVerifier.Builder(result).setMinCheckedPlatformVersion(24).build().verify().isVerified()) {
            throw new IOException("The rebuilt APK did not pass signature verification.");
        }
        try (ZipFile archive = new ZipFile(result)) {
            for (Map.Entry<String, byte[]> asset : assets.entrySet()) {
                ZipEntry entry = archive.getEntry(asset.getKey());
                if (entry == null || entry.getSize() != asset.getValue().length) {
                    throw new IOException("The rebuilt APK is missing a Keyquest asset.");
                }
            }
        }
    }

    static void rebuild(File source, File result, Map<String, byte[]> assets) throws IOException {
        rebuild(source, result, assets, null, (stage, copied, total) -> {});
    }

    private static void rebuild(File source, File result, Map<String, byte[]> assets, String label, Observer observer)
            throws IOException {
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
            boolean update = names.contains(OVERLAY);
            for (String asset : assets.keySet()) {
                if (names.contains(asset) && (!update || !studioAsset(asset))) {
                    throw new IOException("The game already uses one of Keyquest’s asset names.");
                }
            }

            try (Counter bytes = new Counter(new BufferedOutputStream(Files.newOutputStream(result.toPath())));
                 ZipOutputStream output = new ZipOutputStream(bytes)) {
                output.setLevel(1);
                long completed = 0;
                long total = size;
                observer.update("Repacking", 0, total);
                for (ZipEntry original : Collections.list(input.entries())) {
                    String name = original.getName();
                    if (signature(name) || update && studioAsset(name)) {
                        completed += original.getSize();
                        continue;
                    }
                    if (label != null && "AndroidManifest.xml".equals(name)) {
                        try (InputStream data = input.getInputStream(original);
                             ByteArrayOutputStream manifest = new ByteArrayOutputStream()) {
                            copy(data, manifest, 8 * 1024 * 1024);
                            output.putNextEntry(new ZipEntry(name));
                            output.write(ManifestLabel.rename(manifest.toByteArray(), label));
                            output.closeEntry();
                        }
                        completed += original.getSize();
                        continue;
                    }
                    ZipEntry entry = new ZipEntry(name);
                    entry.setMethod(original.getMethod());
                    if (entry.getMethod() == ZipEntry.STORED) {
                        entry.setSize(original.getSize());
                        entry.setCrc(original.getCrc());
                        align(entry, bytes.count, name.startsWith("lib/") && name.endsWith(".so") ? 16384 : 4);
                    }
                    output.putNextEntry(entry);
                    try (InputStream data = input.getInputStream(original)) {
                        long before = completed;
                        copy(data, output, original.getSize(),
                                progress -> observer.update("Repacking", before + progress, total));
                    }
                    output.closeEntry();
                    completed += original.getSize();
                }
                observer.update("Adding controls", total, total);
                for (Map.Entry<String, byte[]> asset : assets.entrySet()) {
                    ZipEntry injected = new ZipEntry(asset.getKey());
                    byte[] data = asset.getValue();
                    CRC32 checksum = new CRC32();
                    checksum.update(data);
                    injected.setMethod(ZipEntry.STORED);
                    injected.setSize(data.length);
                    injected.setCrc(checksum.getValue());
                    align(injected, bytes.count, 4);
                    output.putNextEntry(injected);
                    output.write(data);
                    output.closeEntry();
                }
            }
        }
    }

    static void copy(InputStream input, OutputStream output, long limit) throws IOException {
        copy(input, output, limit, null);
    }

    private static void copy(InputStream input, OutputStream output, long limit,
                             java.util.function.LongConsumer observer) throws IOException {
        byte[] buffer = new byte[128 * 1024];
        long initial = limit;
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (count > limit) throw new IOException("Input exceeded its expected size.");
            output.write(buffer, 0, count);
            limit -= count;
            if (observer != null) observer.accept(initial - limit);
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
