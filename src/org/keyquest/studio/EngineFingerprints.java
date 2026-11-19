package org.keyquest.studio;

import java.io.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

final class EngineFingerprints {
    private static final String[] SCRIPTS = {
        "000statements", "000atl", "00action_control", "00action_other",
        "00keymap", "00start", "00preferences"
    };
    // Full SHA-256 and Ren'Py source digest from the representative profile SDKs.
    // Regenerate rows with tools/fingerprint-sdk.py.
    private static final Profile[] PROFILES = {
        new Profile("7.8",
            "1e2e700eee93aaa7bd81f8b88ca0eeb5fe345860be49d860d3f896fecd98e7f5:999b4cdfcf8169435c8be3af0257ce08",
            "0993a5ecd6fd151e951ec0cb15eb0059435ef56337878910d29462108b083c97:21e09385b0ebdeb3e647f1f74864bedb",
            "ca019d7c73a86af24248898337f48fcd89beec3a83c7aea7ada0404452c263bb:0ac03c799dc576b8c766e6449e6c35ed",
            "1b4356da6ce00a55ea831834ebf18563d7cde7070aa3c88c6d55a11bc9f9acce:84e946f3dd927fbd9fc0a4684fdd4b92",
            "d59ac760f9d7dfcfac23e06f2ce8a8b74d04e0070033edbf14f6bb36c0c060e4:dac684dc2469f0ad320294693e16b11c",
            "697e74540db42c89f304d540b655755778857daf2bfb209ee47ac0bce5c61d20:fd88aa06cb693638826cec2fd6cb1a24",
            "ec41500b41e0c7a386da8b6e8c334b8bffdb5778a5f39c557588f7ea00b4b755:8abb3e970a9eed488c3b87f9a77eb654"),
        new Profile("8.0",
            "8edb9329a6654ec65d34d1f736b600c626c9f17fc3acf2039fcebab0dd9d5a01:0bc24277301a0e5dc5252c629d9f99a8",
            "513120f312e67fca971a9ac0b5526e9d9af614600cc73616c22d687e73074339:b248858374614b987be668addd1e5311",
            "844b6aa6b92eaf0260ee7e31d99f5b38ab5b9180495671f8e8d3fdf2a36a9505:4a06f239d5f0d298e57c67fcb123e9fb",
            "c112120d6f3f25a7cb5aa8544c3f267e855466965a5915f6562647695ca802a8:0432efe73d8bb920b67d28e5cad4e32d",
            "93684c176520af5880768473a5a22050513def5fb0077d0ee22214e6cbeb64d2:028804065d7ab291b0f13ae9edeed462",
            "1cf373be42d55b5b4d43f51857967992d9dd7bec359122ce4bd23b93273183f4:c6f87f317ada29a7ed48b04b0482241f",
            "00e6afe0b2e38f2854bf7470eb8a0cc5bcee18ba2cbb944062a515508f107da3:66cacb5d9284b56fc4ba53a4b068b7e0"),
        new Profile("8.1",
            "dd02810c2ba4133beb5c729521af73f02f3299504f8c46197bb218afbc581b4c:65aea941216d48f0bec0637e8d881aa2",
            "45497b1ddf9b26c28bfce086d98547dc85068eac5785d3542e5f802d4d35eea5:2cf4be4bc6d554a8af86f331b89c7d02",
            "6ea0b49e05a60bb6b1e3430b3788d8bc81a3b16749c134e76b794a50b25e44d1:78902b97f1e4aa72d8002001c9872ebc",
            "e28639b4c08207b4c9d926b00ef9bb371c016683651389fe502532771247d93f:dfb77d495c2d212f88fca5d6167cd0a8",
            "e47396e3610d01694673520b7b8d86e60df8da4b31272e6cb5b6f1fe76116c24:231a34b0b8679df1f0b984855c072e39",
            "fa48f354625fdc927319133b888d94970828b5bc501124c055a0f341da8580db:752343739264dba232c688b7f06aadec",
            "d96949a04a37a1df4257a366fa8fea8158f8b3e4ea08b03a589552d36e994791:8a8c0d01235c4bdd4dbaed093be9fa16"),
        new Profile("8.2",
            "1cd64eb8f62387ea97a94c903a891d70f78ee76a4352c92692ee373bd3165217:b9da74ab115325c3446827b609f1d173",
            "f6412babbc2efa0944308e0e340f3532bc97b3ef95010f1c9a525065038a0cb8:81e35341ec16843bfa562464d7ccbd88",
            "019513212ea7c00dbfa35b1046e688d08e733aaf836ec471c044c6d2e492ec38:a89800445c121f7d9cc6465bac9f861b",
            "b55694494f121064971de18ae8887ddba30282e6984dd051556b62a7804c9ffb:6e79d576d03a601c0b10a2042d611d59",
            "bafe52704ea5490a96e13410250b4921eccef92dc2b976c51486c16ae7627115:4261bc3440a3eb12e8c2b83fba75f9ec",
            "8a7be7bc9dce522083094336ff833f93c2befdc8c02dc2396dce80184e3769fc:3babdca539f0c51059729a332c440ecf",
            "a12f498cc3a2401a8c5a1da3495842000d2c2dc77e00fb33ffbddb4bc01c52e7:00112a782aabcd9212698a14e85c9a77"),
        new Profile("8.3",
            "850fffd3e14cf6227a7f99315902709b4a5832bfc8c67c11617159cea249910c:999b4cdfcf8169435c8be3af0257ce08",
            "5fbdce595d36e8e06a3032ab128a223c5cc4a0d661098f14dfce1278e7da7472:21e09385b0ebdeb3e647f1f74864bedb",
            "7053595e84866782a379aafb7486a52852989a17a693be6ea43422b58d331775:0ac03c799dc576b8c766e6449e6c35ed",
            "a98803a14beedd447d9a381a46fe80d68f84aed3cc32ee3af1af3e19d54acac3:84e946f3dd927fbd9fc0a4684fdd4b92",
            "8a72ae21fee668dc3a644937deb92ae814edd31a8aa8dcd4bb128199f2bbdfad:dac684dc2469f0ad320294693e16b11c",
            "69d7f23fd400129045a69950799d3a4c9efde93eff3cfde6bcbad2706dba5a18:fd88aa06cb693638826cec2fd6cb1a24",
            "78ef29e981370687db8387337e937330e63309de19f177826bef71cb3358d85e:8abb3e970a9eed488c3b87f9a77eb654"),
        new Profile("8.4",
            "2a5b11ac0f22cd55219b04c7e0efe505279f76f77d7da0b2fe1276c35182ae75:9e3c0954d99beb093889a1a19b50eaed",
            "634150cb86bd2abc02af08382cfc15ec7351c9b6c6d9b08da62ec77e35d55884:1eb436546dce6f5ce286be2c3e2e1fef",
            "045599cd3b0eced6807bc99a69b74b5abf4d6b71aadca7cf54d3451b981f33c5:3d18104205ebca01b4adc976d569a50e",
            "363e9f9843224aaff9c5a424d5cdbb26e42d825e836a4b7176ff642c29506d83:dff8fa7ace6af80deed569ee40615281",
            "16dc89cb55c7591598d58a0680e3ce4d0fe8ad80565ec733c3208f2ee4f6da09:79ace0b05cd760566df26fda4e12e414",
            "606eb482e9e643ea6a135f0cb6c9790a344522d1d81910cfb7c237e4648f5d79:bb85d3d51a17e1c0c1d52f0eaafb7bc3",
            "d7978dc4e41ccf9800867e0de3fc12e977497a2347194fd964a437dff83f4441:03017294c6c2bb1dad805de01b2e5d48"),
        new Profile("8.5",
            "e9c6a93aaf9d6dab2bd927288fb852901418362a273f8105cc69793136df684d:0bd37a8ed0f12948def0ee4e8f42e287",
            "83603ab9890879e2ed4cc945ed8947c1b4650865927cca79a3cd78a362830042:d2b3ac190625e5bbac65c67392f4a232",
            "9b3b7813f22f8fc53b11ab2c80b2652e5976d038c35742dcde324b55b25be417:489e71d9e40def3555b80dcfa0854a8d",
            "11fcf150db6ca02eeb16c3b755af8960e94c0c8de92e4563f4f2b748b3aeafea:6da46a17a2e34e5e1742e04bf5bbb530",
            "e677e0aebeb7fa1453b56d228b070428487f786d62fc8ee3e414d5f6b431629b:6773bf927843edf302875ef48510962b",
            "b89a67a9e77a4edd89396de6db710039ce7c7577dc43e5c524a0bc3df4a6b54c:0345f62a95d730f4d638e4dc41236f0e",
            "84a80036e5d5d427e5ca429db94777411ff4d5b66e770caf91ec5e8b906a1350:0eaa9edcda38cc538324da084a0ad412"),
    };

    final String verifiedFamily;
    final String suggestedFamily;

    private EngineFingerprints(String verifiedFamily, String suggestedFamily) {
        this.verifiedFamily = verifiedFamily;
        this.suggestedFamily = suggestedFamily;
    }

    static EngineFingerprints scan(ZipFile apk, String abi) throws IOException {
        String[] complete = new String[SCRIPTS.length];
        String[] trailers = new String[SCRIPTS.length];
        int checked = 0;
        for (int i = 0; i < SCRIPTS.length; i++) {
            ZipEntry entry = apk.getEntry("assets/x-renpy/x-common/x-" + SCRIPTS[i] + ".rpyc");
            if (entry == null) entry = apk.getEntry("assets/renpy/common/" + SCRIPTS[i] + ".rpyc");
            if (entry == null || entry.getSize() < 32 || entry.getSize() > 2 * 1024 * 1024) continue;
            try (InputStream input = apk.getInputStream(entry); ByteArrayOutputStream data = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[16_384];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (count > entry.getSize() - data.size()) throw new IOException("Invalid Ren’Py archive entry.");
                    data.write(buffer, 0, count);
                }
                byte[] bytes = data.toByteArray();
                if (bytes.length != entry.getSize()) throw new IOException("Truncated Ren’Py archive entry.");
                complete[i] = hex(sha256(bytes), 0);
                trailers[i] = hex(bytes, bytes.length - 16);
                checked++;
            }
        }
        if (checked < 4) return new EngineFingerprints(null, null);
        List<String> exact = new ArrayList<>();
        List<String> clues = new ArrayList<>();
        for (Profile profile : PROFILES) {
            if (!abiAgrees(abi, profile.family)) continue;
            int whole = 0;
            int source = 0;
            for (int i = 0; i < SCRIPTS.length; i++) {
                if (complete[i] == null) continue;
                if (profile.digests[i].startsWith(complete[i] + ":")) whole++;
                if (profile.digests[i].endsWith(":" + trailers[i])) source++;
            }
            if (whole == checked) exact.add(profile.family);
            if (source == checked) clues.add(profile.family);
        }
        return new EngineFingerprints(exact.size() == 1 ? exact.get(0) : null,
                clues.size() == 1 ? clues.get(0) : null);
    }

    private static boolean abiAgrees(String abi, String family) {
        if (abi == null || abi.isEmpty()) return true;
        if ("2.7".equals(abi)) return family.startsWith("7.");
        if ("3.12".equals(abi)) return family.equals("8.4") || family.equals("8.5");
        return !family.startsWith("7.") && !family.equals("8.4") && !family.equals("8.5");
    }

    private static byte[] sha256(byte[] bytes) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(bytes);
        } catch (NoSuchAlgorithmException impossible) {
            throw new AssertionError(impossible);
        }
    }

    private static String hex(byte[] bytes, int start) {
        StringBuilder builder = new StringBuilder((bytes.length - start) * 2);
        for (int i = start; i < bytes.length; i++) {
            builder.append(Character.forDigit((bytes[i] >>> 4) & 15, 16));
            builder.append(Character.forDigit(bytes[i] & 15, 16));
        }
        return builder.toString();
    }

    private static final class Profile {
        final String family;
        final String[] digests;

        Profile(String family, String... digests) {
            this.family = family;
            this.digests = digests;
        }
    }
}
