package org.keyquest.studio;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/** Changes literal labels in Android's compiled XML without changing the package or resource IDs. */
final class ManifestLabel {
    private static final int LABEL = 0x01010001;
    private static final int CATEGORY_NAME = 0x01010003;
    private static final int START = 0x0102;
    private static final int END = 0x0103;

    private ManifestLabel() {}

    static byte[] rename(byte[] source, String label) throws IOException {
        if (label.isEmpty() || label.length() > 80) throw new IOException("Enter a game name of 1–80 characters.");
        byte[] bytes = source.clone();
        ByteBuffer xml = buffer(bytes);
        if (bytes.length < 36 || u16(xml, 0) != 3 || xml.getInt(4) != bytes.length) throw invalid();
        int pool = u16(xml, 2);
        if (pool < 8 || pool > bytes.length - 28 || u16(xml, pool) != 1) throw invalid();
        int poolSize = chunkSize(xml, pool);
        int header = u16(xml, pool + 2);
        int count = xml.getInt(pool + 8);
        int styleCount = xml.getInt(pool + 12);
        int flags = xml.getInt(pool + 16);
        int strings = xml.getInt(pool + 20);
        int styles = xml.getInt(pool + 24);
        boolean utf8 = (flags & 256) != 0;
        if (header < 28 || count < 0 || styleCount < 0 || strings < header
                || ((long) count + styleCount) * 4 > strings - header || strings > poolSize
                || styles != 0 && (styles < strings || styles > poolSize)) throw invalid();
        int stringEnd = styles == 0 ? poolSize : styles;
        int[] ids = {};
        Deque<Node> nodes = new ArrayDeque<>();
        List<Integer> edits = new ArrayList<>();
        boolean appHasLabel = false;
        for (int off = pool + poolSize; off < bytes.length; ) {
            int size = chunkSize(xml, off);
            int kind = u16(xml, off);
            if (kind == 0x0180) {
                int mapHeader = u16(xml, off + 2);
                if ((size - mapHeader) % 4 != 0) throw invalid();
                ids = new int[(size - mapHeader) / 4];
                for (int i = 0; i < ids.length; i++) ids[i] = xml.getInt(off + mapHeader + i * 4);
            } else if (kind == START) {
                if (size < 36) throw invalid();
                String name = string(xml, pool, header, count, strings, stringEnd, utf8, xml.getInt(off + 20));
                Node node = new Node(name);
                int first = 16 + u16(xml, off + 24);
                int width = u16(xml, off + 26);
                int attributes = u16(xml, off + 28);
                if (first < 36 || width < 20 || first + (long) width * attributes > size) throw invalid();
                for (int i = 0; i < attributes; i++) {
                    int attr = off + first + i * width;
                    int index = xml.getInt(attr + 4);
                    int id = index >= 0 && index < ids.length ? ids[index] : 0;
                    if (id == LABEL) {
                        if ("application".equals(name)) {
                            edits.add(attr);
                            appHasLabel = true;
                        } else if (node.activity) {
                            node.label = attr;
                        }
                    }
                    if (id == CATEGORY_NAME && "category".equals(name) && (bytes[attr + 15] & 255) == 3
                            && "android.intent.category.LAUNCHER".equals(string(xml, pool, header, count,
                            strings, stringEnd, utf8, xml.getInt(attr + 16)))) {
                        Node parent = nodes.peek();
                        if (parent != null && "intent-filter".equals(parent.name)) {
                            for (Node ancestor : nodes) {
                                if (ancestor.activity) {
                                    ancestor.launcher = true;
                                    break;
                                }
                            }
                        }
                    }
                }
                nodes.push(node);
            } else if (kind == END) {
                if (nodes.isEmpty()) throw invalid();
                Node node = nodes.pop();
                if (node.launcher && node.label >= 0) edits.add(node.label);
            }
            off += size;
        }
        if (!appHasLabel) throw new IOException("This APK has no application label to rename. Turn off Rename in app library.");
        for (int attr : edits) {
            xml.putInt(attr + 8, count);
            xml.put(attr + 15, (byte) 3);
            xml.putInt(attr + 16, count);
        }

        byte[] encoded = encode(label, utf8);
        int dataPadding = (encoded.length + 3) & ~3;
        int growth = 4 + dataPadding;
        xml.putInt(4, bytes.length + growth);
        xml.putInt(pool + 4, poolSize + growth);
        xml.putInt(pool + 8, count + 1);
        xml.putInt(pool + 16, flags & ~1);
        xml.putInt(pool + 20, strings + 4);
        if (styles != 0) xml.putInt(pool + 24, styles + growth);
        int offsetsEnd = pool + header + count * 4;
        ByteArrayOutputStream result = new ByteArrayOutputStream(bytes.length + growth);
        result.write(bytes, 0, offsetsEnd);
        result.write(buffer(new byte[4]).putInt(stringEnd - strings).array());
        result.write(bytes, offsetsEnd, pool + stringEnd - offsetsEnd);
        result.write(encoded);
        result.write(new byte[dataPadding - encoded.length]);
        result.write(bytes, pool + stringEnd, bytes.length - pool - stringEnd);
        return result.toByteArray();
    }

    private static byte[] encode(String label, boolean utf8) {
        if (!utf8) {
            byte[] data = label.getBytes(StandardCharsets.UTF_16LE);
            return buffer(new byte[data.length + 4]).putShort((short) label.length()).put(data).array();
        }
        byte[] data = label.getBytes(StandardCharsets.UTF_8);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        output.write(label.length());
        if (data.length >= 128) output.write(0x80 | (data.length >>> 8));
        output.write(data.length & 255);
        output.write(data, 0, data.length);
        output.write(0);
        return output.toByteArray();
    }

    private static String string(ByteBuffer xml, int pool, int header, int count, int start, int end,
                                 boolean utf8, int index) throws IOException {
        if (index < 0 || index >= count) throw invalid();
        int offset = xml.getInt(pool + header + index * 4);
        if (offset < 0 || offset >= end - start) throw invalid();
        int position = pool + start + offset;
        int limit = pool + end;
        if (utf8) {
            if ((xml.get(position++) & 128) != 0) position++;
            if (position >= limit) throw invalid();
            int length = xml.get(position++) & 255;
            if ((length & 128) != 0) {
                if (position >= limit) throw invalid();
                length = ((length & 127) << 8) | (xml.get(position++) & 255);
            }
            if (length > limit - position) throw invalid();
            return new String(xml.array(), position, length, StandardCharsets.UTF_8);
        }
        if (limit - position < 2) throw invalid();
        int length = u16(xml, position);
        position += 2;
        if ((length & 0x8000) != 0 || length > (limit - position) / 2) throw invalid();
        return new String(xml.array(), position, length * 2, StandardCharsets.UTF_16LE);
    }

    private static int chunkSize(ByteBuffer xml, int offset) throws IOException {
        if (offset > xml.limit() - 8) throw invalid();
        int header = u16(xml, offset + 2);
        int size = xml.getInt(offset + 4);
        if (header < 8 || size < header || size > xml.limit() - offset) throw invalid();
        return size;
    }

    private static ByteBuffer buffer(byte[] array) { return ByteBuffer.wrap(array).order(ByteOrder.LITTLE_ENDIAN); }
    private static int u16(ByteBuffer buffer, int offset) { return buffer.getShort(offset) & 65535; }
    private static IOException invalid() { return new IOException("APK manifest could not be read safely."); }

    private static final class Node {
        final String name;
        final boolean activity;
        int label = -1;
        boolean launcher;
        Node(String name) {
            this.name = name;
            activity = "activity".equals(name) || "activity-alias".equals(name);
        }
    }
}
