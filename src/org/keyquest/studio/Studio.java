package org.keyquest.studio;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.ResolveInfo;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.widget.*;
import com.android.apksig.ApkSigner;
import java.io.*;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.cert.X509Certificate;
import java.util.*;

import static org.keyquest.studio.StudioStyle.*;

public final class Studio extends Activity {
    private static final int OPEN = 1;
    private TextView selection, status;
    private Button browse, installed, build, save;
    private ProgressBar progress;
    private CheckBox profile, valuesAddon;
    private File selectedApk, cachedApk;
    private ApkInspection inspection;
    private File ready;
    private boolean busy;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        scroll.setBackground(StudioStyle.backdrop());
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets safe = insets.getInsets(
                    WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            view.setPadding(safe.left, safe.top, safe.right, safe.bottom);
            return insets;
        });
        LinearLayout column = stack();
        column.setPadding(dp(24), dp(24), dp(24), dp(24));
        scroll.addView(column);
        setContentView(scroll);

        LinearLayout brand = new LinearLayout(this);
        brand.setGravity(Gravity.CENTER_VERTICAL);
        column.addView(brand);
        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("studio_brand", "drawable", getPackageName()));
        LinearLayout.LayoutParams logoLayout = new LinearLayout.LayoutParams(dp(58), dp(58));
        logoLayout.rightMargin = dp(12);
        brand.addView(logo, logoLayout);
        LinearLayout brandText = stack();
        brand.addView(brandText, new LinearLayout.LayoutParams(0, -2, 1));
        label(brandText, "Keyquest Studio", 32, TEXT, true);
        label(brandText, "Add an in-game keyboard to a Ren’Py APK.", 16, MUTED, false);

        LinearLayout workspace = stack();
        column.addView(workspace);
        LinearLayout inputs = card(workspace);
        heading(inputs, "Game source");
        selection = label(inputs, "No game selected", 16, MUTED, false);
        selection.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        browse = button(inputs, "Choose APK file", false, view -> pickApk());
        installed = button(inputs, "Choose installed game", false, view -> pickInstalled());

        LinearLayout output = card(workspace);
        heading(output, "Build keyboard APK");
        profile = option(output, "My game uses Ren’Py 8.4.1");
        valuesAddon = option(output, "Include local value editor");
        label(output, "Back up game saves before installing the re-signed copy.", 14, MUTED, false);
        build = button(output, "Build APK", true, view -> confirmBuild());
        save = button(output, "Save to Downloads", true, view -> saveToDownloads());
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(true);
        progress.setIndeterminateTintList(ColorStateList.valueOf(ACCENT));
        output.addView(progress, new LinearLayout.LayoutParams(-1, dp(14)));
        status = label(output, "", 15, MUTED, false);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        workspace.addOnLayoutChangeListener((view, left, top, right, bottom,
                oldLeft, oldTop, oldRight, oldBottom) -> arrange(workspace, inputs, output, right - left));

        profile.setOnCheckedChangeListener((view, checked) -> refresh());
        refresh();
    }

    private void pickApk() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        try {
            startActivityForResult(intent, OPEN);
        } catch (android.content.ActivityNotFoundException unavailable) {
            status.setText("This headset has no Android file picker. Use Choose installed game.");
        }
    }

    private void pickInstalled() {
        Intent launcher = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> entries = getPackageManager().queryIntentActivities(launcher, 0);
        Map<String, ApplicationInfo> candidates = new HashMap<>();
        for (ResolveInfo info : entries) {
            ApplicationInfo app = info.activityInfo.applicationInfo;
            if ((app.flags & ApplicationInfo.FLAG_SYSTEM) == 0 && !app.packageName.equals(getPackageName())
                    && (app.splitSourceDirs == null || app.splitSourceDirs.length == 0)) {
                candidates.put(app.packageName, app);
            }
        }
        busy = true;
        status.setText("Finding installed Ren’Py games…");
        refresh();
        new Thread(() -> {
            List<ApplicationInfo> games = new ArrayList<>();
            for (ApplicationInfo app : candidates.values()) {
                try {
                    if (ApkInspection.scan(new File(app.sourceDir), false).universalRenpy) games.add(app);
                } catch (IOException unreadable) {
                    // The APK file picker also supports APKs from another source.
                }
            }
            games.sort(Comparator.comparing(app -> app.loadLabel(getPackageManager()).toString(),
                    String.CASE_INSENSITIVE_ORDER));
            String[] names = games.stream().map(app -> app.loadLabel(getPackageManager()) + "\n" + app.packageName)
                    .toArray(String[]::new);
            runOnUiThread(() -> {
                if (isDestroyed()) return;
                busy = false;
                refresh();
                if (games.isEmpty()) {
                    status.setText("No installed single-APK Ren’Py games detected. Choose a downloaded APK instead.");
                    return;
                }
                status.setText("");
                new AlertDialog.Builder(this).setTitle("Installed Ren’Py games")
                        .setItems(names, (dialog, index) -> inspect(null,
                                new File(games.get(index).sourceDir), names[index]))
                        .setNegativeButton("Cancel", null).show();
            });
        }, "keyquest-discover").start();
    }

    private void inspect(Uri uri, File installedApk, String fallbackName) {
        discardOutput();
        if (cachedApk != null) cachedApk.delete();
        cachedApk = null;
        selectedApk = null;
        inspection = null;
        profile.setChecked(false);
        selection.setText(fallbackName);
        status.setText("Scanning the APK…");
        busy = true;
        refresh();
        new Thread(() -> {
            File copied = null;
            ApkInspection result = null;
            String label = fallbackName;
            String message;
            try {
                if (uri != null) {
                    copied = File.createTempFile("source-", ".apk", getCacheDir());
                    try (InputStream input = getContentResolver().openInputStream(uri);
                         OutputStream output = new FileOutputStream(copied)) {
                        if (input == null) throw new IOException("Could not read the chosen APK.");
                        ApkBuilder.copy(input, output, 3_000_000_000L);
                    }
                }
                File source = copied == null ? installedApk : copied;
                PackageInfo metadata = getPackageManager().getPackageArchiveInfo(source.getAbsolutePath(), 0);
                if (metadata != null) {
                    if (metadata.applicationInfo != null) {
                        metadata.applicationInfo.sourceDir = source.getAbsolutePath();
                        metadata.applicationInfo.publicSourceDir = source.getAbsolutePath();
                        label = metadata.applicationInfo.loadLabel(getPackageManager()).toString();
                    }
                    label += "\n" + metadata.packageName;
                    if (metadata.versionName != null) label += " · " + metadata.versionName;
                }
                result = ApkInspection.scan(source, true);
                message = describeInspection(result);
            } catch (Exception error) {
                message = "Could not scan the APK. " + describe(error);
            }
            final File completed = copied;
            final ApkInspection findings = result;
            final String name = label;
            final String outcome = message;
            runOnUiThread(() -> {
                if (isDestroyed()) {
                    if (completed != null) completed.delete();
                    return;
                }
                if (findings != null && findings.canBuild()) {
                    cachedApk = completed;
                    selectedApk = completed == null ? installedApk : completed;
                } else if (completed != null) {
                    completed.delete();
                }
                inspection = findings;
                busy = false;
                selection.setText(name);
                status.setText(outcome);
                refresh();
            });
        }, "keyquest-inspect").start();
    }

    private static String describeInspection(ApkInspection result) {
        if (!result.universalRenpy) return "No supported Ren’Py universal APK layout detected.";
        if (result.alreadyPatched) return "Ren’Py game detected. This APK already contains Keyquest.";
        if (result.engineVersion == null) return "Ren’Py game detected. Confirm the engine version to continue.";
        if (!result.canBuild()) return "Ren’Py " + result.engineVersion + " detected. This build supports Ren’Py "
                + ApkInspection.SUPPORTED_VERSION + ".";
        return "Ren’Py " + result.engineVersion + " detected. Ready to build.";
    }

    private boolean canBuild() {
        return !busy && selectedApk != null && inspection != null && inspection.canBuild()
                && (inspection.engineVersion != null || profile.isChecked());
    }

    private void confirmBuild() {
        if (!canBuild()) return;
        discardOutput();
        busy = true;
        status.setText("Reading, rebuilding, and signing…");
        refresh();
        final File source = selectedApk;
        final boolean includeValues = valuesAddon.isChecked();
        new Thread(() -> {
            File unsigned = null, result = null;
            String message;
            try {
                if (!ApkInspection.scan(source, true).canBuild()) {
                    throw new IOException("The APK has changed or is incompatible. Select it again.");
                }
                unsigned = File.createTempFile("rebuild-", ".apk", getCacheDir());
                result = File.createTempFile("keyboard-", ".apk", getCacheDir());
                Map<String, byte[]> gameAssets = new LinkedHashMap<>();
                gameAssets.put("assets/x-game/x-keyquest_overlay.rpyc", readAsset("keyquest_8_4_1.rpyc"));
                for (String artwork : new String[]{"logo", "panel", "panel_mint", "key", "key_focus", "sheet"}) {
                    String filename = "keyquest_" + artwork + ".png";
                    gameAssets.put("assets/x-game/x-" + filename, readAsset(filename));
                }
                if (includeValues) {
                    gameAssets.put("assets/x-game/x-keyquest_values.rpyc", readAsset("keyquest_values_8_4_1.rpyc"));
                }
                ApkBuilder.build(source, unsigned, result, gameAssets, signer());
                message = "APK verified. Save it to Downloads.";
            } catch (Exception error) {
                if (result != null) result.delete();
                result = null;
                message = "Build failed. " + describe(error);
            } finally {
                if (unsigned != null) unsigned.delete();
            }
            final File completed = result;
            final String outcome = message;
            runOnUiThread(() -> {
                if (isDestroyed()) {
                    if (completed != null) completed.delete();
                    return;
                }
                ready = completed;
                busy = false;
                status.setText(outcome);
                refresh();
            });
        }, "keyquest-build").start();
    }

    private byte[] readAsset(String name) throws IOException {
        try (InputStream input = getAssets().open(name);
             ByteArrayOutputStream data = new ByteArrayOutputStream()) {
            ApkBuilder.copy(input, data, 1024 * 1024);
            return data.toByteArray();
        }
    }

    private static ApkSigner.SignerConfig signer() throws Exception {
        String alias = "keyquest-patched-games";
        KeyStore keys = KeyStore.getInstance("AndroidKeyStore");
        keys.load(null);
        if (!keys.containsAlias(alias)) {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA", "AndroidKeyStore");
            generator.initialize(new KeyGenParameterSpec.Builder(alias,
                    KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                    .setKeySize(2048).setDigests(KeyProperties.DIGEST_SHA256,
                            KeyProperties.DIGEST_SHA512, KeyProperties.DIGEST_SHA1)
                    .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1,
                            KeyProperties.SIGNATURE_PADDING_RSA_PSS).build());
            generator.generateKeyPair();
        }
        KeyStore.PrivateKeyEntry entry = (KeyStore.PrivateKeyEntry) keys.getEntry(alias, null);
        return new ApkSigner.SignerConfig.Builder("KEYQUEST", entry.getPrivateKey(),
                Collections.singletonList((X509Certificate) entry.getCertificate())).build();
    }

    private void saveToDownloads() {
        if (ready == null || busy) return;
        final File source = ready;
        busy = true;
        refresh();
        new Thread(() -> {
            String message;
            Uri uri = null;
            try {
                android.content.ContentValues values = new android.content.ContentValues();
                values.put(android.provider.MediaStore.Downloads.DISPLAY_NAME, "game-keyboard.apk");
                values.put(android.provider.MediaStore.Downloads.MIME_TYPE, "application/vnd.android.package-archive");
                values.put(android.provider.MediaStore.Downloads.IS_PENDING, 1);
                uri = getContentResolver().insert(android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                if (uri == null) throw new IOException("Downloads is unavailable.");
                try (InputStream input = new FileInputStream(source);
                     OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                    if (output == null) throw new IOException("Could not open Downloads.");
                    ApkBuilder.copy(input, output, source.length());
                }
                values.clear();
                values.put(android.provider.MediaStore.Downloads.IS_PENDING, 0);
                if (getContentResolver().update(uri, values, null, null) != 1) {
                    throw new IOException("Could not publish the download.");
                }
                message = "Saved in Downloads as game-keyboard.apk.";
            } catch (Exception error) {
                if (uri != null) {
                    try { getContentResolver().delete(uri, null, null); }
                    catch (RuntimeException ignored) { }
                }
                message = "Save failed. " + describe(error);
            }
            final String outcome = message;
            runOnUiThread(() -> {
                busy = false;
                status.setText(outcome);
                refresh();
            });
        }, "keyquest-save").start();
    }

    @Override protected void onActivityResult(int request, int resultCode, Intent data) {
        super.onActivityResult(request, resultCode, data);
        if (request != OPEN || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        String name = "Downloaded APK";
        try (android.database.Cursor record = getContentResolver().query(uri,
                new String[] {android.provider.OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (record != null && record.moveToFirst() && record.getString(0) != null) name = record.getString(0);
        } catch (RuntimeException ignored) { }
        inspect(uri, null, name);
    }

    @Override protected void onDestroy() {
        if (cachedApk != null) cachedApk.delete();
        discardOutput();
        super.onDestroy();
    }

    private void discardOutput() {
        if (ready != null) ready.delete();
        ready = null;
    }

    private void refresh() {
        browse.setEnabled(!busy);
        installed.setEnabled(!busy);
        profile.setVisibility(inspection != null && inspection.canBuild() && inspection.engineVersion == null
                ? View.VISIBLE : View.GONE);
        profile.setEnabled(!busy);
        valuesAddon.setEnabled(!busy);
        build.setEnabled(canBuild());
        save.setVisibility(ready == null ? View.GONE : View.VISIBLE);
        save.setEnabled(!busy);
        build.setVisibility(ready == null ? View.VISIBLE : View.GONE);
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
    }

    private static String describe(Exception error) {
        return error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
    }

    private LinearLayout stack() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        return layout;
    }

    private LinearLayout card(LinearLayout parent) {
        LinearLayout card = stack();
        card.setPadding(dp(20), dp(16), dp(20), dp(20));
        card.setBackground(surface(PANEL, dp(24), dp(1), BORDER));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.topMargin = dp(16);
        parent.addView(card, params);
        return card;
    }

    private void arrange(LinearLayout workspace, LinearLayout source, LinearLayout output, int width) {
        boolean wide = width >= dp(700);
        int direction = wide ? LinearLayout.HORIZONTAL : LinearLayout.VERTICAL;
        if (workspace.getOrientation() == direction) return;
        workspace.setOrientation(direction);
        for (LinearLayout card : new LinearLayout[]{source, output}) {
            LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(wide ? 0 : -1, -2, wide ? 1 : 0);
            layout.topMargin = dp(20);
            if (wide && card == source) layout.rightMargin = dp(16);
            card.setLayoutParams(layout);
        }
    }

    private void heading(LinearLayout parent, String title) {
        label(parent, title, 22, TEXT, true).setAccessibilityHeading(true);
    }

    private CheckBox option(LinearLayout parent, String title) {
        CheckBox check = new CheckBox(this);
        check.setText(title);
        check.setTextColor(TEXT);
        check.setTextSize(16);
        check.setMinHeight(dp(48));
        check.setButtonTintList(ColorStateList.valueOf(ACCENT));
        parent.addView(check);
        return check;
    }

    private TextView label(LinearLayout parent, String value, int size, int color, boolean bold) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(size);
        text.setTextColor(color);
        if (bold) text.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        text.setPadding(0, dp(4), 0, dp(4));
        parent.addView(text);
        return text;
    }

    private Button button(LinearLayout parent, String value, boolean primary, View.OnClickListener action) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(value);
        button.setTextSize(16);
        button.setTextColor(new ColorStateList(new int[][]{{-android.R.attr.state_enabled}, {}},
                new int[]{MUTED, primary ? BACKGROUND : TEXT}));
        button.setGravity(Gravity.CENTER);
        button.setBackground(StudioStyle.button(primary, dp(16), dp(1)));
        button.setOnClickListener(action);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(52));
        params.topMargin = dp(8);
        parent.addView(button, params);
        return button;
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
