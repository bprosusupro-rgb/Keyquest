package org.keyquest.studio;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Enumeration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.*;

final class ApkInspection {
    static final String[] ENGINE_FAMILIES = {"7.8", "8.0", "8.1", "8.2", "8.3", "8.4", "8.5"};

    static String family(String version) {
        if (version == null) return null;
        for (String candidate : ENGINE_FAMILIES) {
            if (version.equals(candidate) || version.startsWith(candidate + ".")) return candidate;
        }
        return null;
    }
    private static final String PRIVATE_ARCHIVE = "assets/private.mp3";
    private static final long TAR_SCAN_LIMIT = 96L * 1024 * 1024;
    private static final Pattern SOURCE_VERSION = Pattern.compile(
            "(?m)^\\s*version\\s*=\\s*['\"](\\d+\\.\\d+\\.\\d+)(?:[.][^'\"]*)?['\"]");
    private static final Pattern COMPILED_VERSION = Pattern.compile(
            "(?<![0-9.])(\\d+\\.\\d+\\.\\d+)\\.\\d{5,}(?![0-9.])");

    final boolean universalRenpy;
    final boolean alreadyPatched;
    final String engineVersion;
    final String pythonAbi;
    final String fingerprintFamily;
    final String fingerprintSuggestion;

    private ApkInspection(boolean universalRenpy, boolean alreadyPatched, String engineVersion, String pythonAbi,
                          String fingerprintFamily, String fingerprintSuggestion) {
        this.universalRenpy = universalRenpy;
        this.alreadyPatched = alreadyPatched;
        this.engineVersion = engineVersion;
        this.pythonAbi = pythonAbi;
        this.fingerprintFamily = fingerprintFamily;
        this.fingerprintSuggestion = fingerprintSuggestion;
    }

    String automaticFamily() {
        return engineVersion == null ? fingerprintFamily : family(engineVersion);
    }

    boolean canBuild() {
        return universalRenpy && !alreadyPatched
                && (engineVersion == null || family(engineVersion) != null);
    }

    static ApkInspection scan(File file, boolean readEngine) throws IOException {
        try (ZipFile apk = new ZipFile(file)) {
            if (apk.getEntry("AndroidManifest.xml") == null) {
                throw new IOException("This file is missing the Android manifest.");
            }
            ZipEntry archive = apk.getEntry(PRIVATE_ARCHIVE);
            boolean gameScripts = false;
            String pythonAbi = null;
            if (archive != null) {
                Enumeration<? extends ZipEntry> entries = apk.entries();
                while (entries.hasMoreElements()) {
                    String name = entries.nextElement().getName();
                    if (name.startsWith("assets/x-game/") && (name.endsWith(".rpyc") || name.endsWith(".rpa"))) {
                        gameScripts = true;
                        if (!readEngine) break;
                    }
                    if (readEngine && name.startsWith("lib/")) {
                        String filename = name.substring(name.lastIndexOf('/') + 1);
                        for (String abi : new String[]{"2.7", "3.9", "3.12"}) {
                            if (filename.equals("libpython" + abi + ".so")
                                    || filename.equals("libpython" + abi + "m.so")) {
                                if (pythonAbi == null) pythonAbi = abi;
                                else if (!pythonAbi.equals(abi)) pythonAbi = "";
                            }
                        }
                    }
                }
            }
            String version = readEngine && gameScripts ? readVersionSafely(apk, archive) : null;
            if (version == null && readEngine && gameScripts) {
                version = readLooseVersion(apk);
            }
            EngineFingerprints fingerprint = version == null && readEngine && gameScripts
                    ? EngineFingerprints.scan(apk, pythonAbi) : null;
            return new ApkInspection(gameScripts,
                    apk.getEntry("assets/x-game/x-keyquest_overlay.rpyc") != null, version, pythonAbi,
                    fingerprint == null ? null : fingerprint.verifiedFamily,
                    fingerprint == null ? null : fingerprint.suggestedFamily);
        }
    }

    String versionSuggestion() {
        if (engineVersion != null && family(engineVersion) != null) {
            return "Recommended profile: Ren’Py " + family(engineVersion) + ".x (engine metadata).";
        }
        if (engineVersion != null) return "This detected engine version has no bundled profile.";
        if (fingerprintFamily != null) return "Recommended profile: Ren’Py " + fingerprintFamily
                + ".x (matched bundled engine files).";
        if (fingerprintSuggestion != null) return "Engine files resemble Ren’Py " + fingerprintSuggestion
                + ".x. Check the game version before selecting this profile.";
        if ("2.7".equals(pythonAbi)) return "Python 2.7 found. Ren’Py 7.8 is the available 7.x profile; confirm your game uses it.";
        if ("3.9".equals(pythonAbi)) return "Python 3.9 found. Check the game’s version against the 8.0–8.3 profiles.";
        if ("3.12".equals(pythonAbi)) return "Python 3.12 found. Check whether the game uses 8.4 or 8.5; newer engines can also use this Python version.";
        return "No engine or Python marker found. Check the game’s version before choosing a profile.";
    }

    private static String readLooseVersion(ZipFile apk) throws IOException {
        Enumeration<? extends ZipEntry> entries = apk.entries();
        while (entries.hasMoreElements()) {
            ZipEntry entry = entries.nextElement();
            String name = entry.getName();
            if (!(name.startsWith("assets/x-renpy/") || name.startsWith("assets/renpy/"))) continue;
            if (!versionModule(name) || entry.getSize() <= 0 || entry.getSize() > 65_536) continue;
            byte[] bytes = new byte[(int) entry.getSize()];
            try (DataInputStream input = new DataInputStream(apk.getInputStream(entry))) {
                input.readFully(bytes);
            }
            String version = parseVersion(name, bytes);
            if (version != null) return version;
        }
        return null;
    }

    private static boolean versionModule(String path) {
        String basename = path.substring(path.lastIndexOf('/') + 1);
        if (basename.startsWith("x-")) basename = basename.substring(2);
        return basename.equals("vc_version.py") || basename.equals("vc_version.pyc")
                || basename.equals("vc_version.pyo")
                || basename.startsWith("vc_version.cpython-") && basename.endsWith(".pyc");
    }

    private static String parseVersion(String name, byte[] bytes) {
        Matcher matcher = (name.endsWith(".py") ? SOURCE_VERSION : COMPILED_VERSION)
                .matcher(new String(bytes, StandardCharsets.ISO_8859_1));
        return matcher.find() ? matcher.group(1) : null;
    }

    private static String readVersionSafely(ZipFile apk, ZipEntry entry) {
        try (InputStream tar = new BufferedInputStream(new GZIPInputStream(apk.getInputStream(entry)))) {
            return readVersion(tar);
        } catch (IOException | NumberFormatException unknownLayout) {
            return null;
        }
    }

    private static String readVersion(InputStream tar) throws IOException {
        DataInputStream archive = new DataInputStream(tar);
        byte[] header = new byte[512];
        long scanned = 0;
        while (scanned <= TAR_SCAN_LIMIT - header.length) {
            archive.readFully(header);
            scanned += header.length;
            String name = field(header, 0, 100);
            if (name.startsWith("./")) name = name.substring(2);
            if (name.isEmpty()) return null;
            long size = Long.parseLong(field(header, 124, 12).trim(), 8);
            if (size < 0 || size > TAR_SCAN_LIMIT - scanned) return null;
            long padded = ((size + 511) / 512) * 512;
            if (padded > TAR_SCAN_LIMIT - scanned) return null;
            if (size <= 65_536 && name.startsWith("renpy/") && versionModule(name)) {
                byte[] bytes = new byte[(int) size];
                archive.readFully(bytes);
                String version = parseVersion(name, bytes);
                if (version != null) return version;
                skip(tar, padded - size);
            } else {
                skip(tar, padded);
            }
            scanned += padded;
        }
        return null;
    }

    private static void skip(InputStream stream, long count) throws IOException {
        while (count > 0) {
            long passed = stream.skip(count);
            if (passed > 0) count -= passed;
            else if (stream.read() == -1) throw new EOFException("Incomplete archive.");
            else count--;
        }
    }

    private static String field(byte[] bytes, int start, int length) {
        int end = start;
        while (end < start + length && bytes[end] != 0) end++;
        return new String(bytes, start, end - start, StandardCharsets.UTF_8);
    }
}
