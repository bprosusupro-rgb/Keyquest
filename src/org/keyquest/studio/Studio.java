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
    private TextView selection, status, timeline, timing;
    private EditText outputTitle;
    private String filename;
    private final String[] phases = {"Repacking", "Adding controls", "Signing", "Verifying"};
    private Button browse, installed, build, save, options;
    private ProgressBar progress;
    private CheckBox valuesAddon, renameInLibrary;
    private Spinner profile;
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
        profile = new Spinner(this, Spinner.MODE_DIALOG);
        profile.setPrompt("Select the game’s Ren’Py version");
        profile.setMinimumHeight(dp(52));
        ArrayList<String> versions = new ArrayList<>();
        versions.add("Choose the game’s Ren’Py version");
        for (String family : ApkInspection.ENGINE_FAMILIES) versions.add("Ren’Py " + family + ".x");
        profile.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, versions));
        output.addView(profile);
        valuesAddon = option(output, "Include local value editor");
        label(output, "Output name", 15, MUTED, true);
        outputTitle = new EditText(this);
        outputTitle.setHint("Game name");
        outputTitle.setHintTextColor(MUTED);
        outputTitle.setTextColor(TEXT);
        outputTitle.setSingleLine(true);
        outputTitle.setTextSize(17);
        outputTitle.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(80)});
        outputTitle.setMinHeight(dp(50));
        outputTitle.setPadding(dp(12), 0, dp(12), 0);
        outputTitle.setBackground(surface(CONTROL, dp(12), dp(1), BORDER));
        output.addView(outputTitle);
        renameInLibrary = option(output, "Rename in app library");
        renameInLibrary.setChecked(false);
        label(output, "Back up game saves before installing the re-signed copy.", 14, MUTED, false);
        build = button(output, "Build APK", true, view -> confirmBuild());
        save = button(output, "Save to Downloads", true, view -> saveToDownloads());
        options = button(output, "Change build options", false, view -> {
            discardOutput();
            timeline.setText("");
            timing.setText("");
            status.setText("");
            refresh();
        });
        timeline = label(output, "", 15, TEXT, true);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(true);
        progress.setIndeterminateTintList(ColorStateList.valueOf(ACCENT));
        output.addView(progress, new LinearLayout.LayoutParams(-1, dp(14)));
        timing = label(output, "", 15, MUTED, false);
        status = label(output, "", 15, MUTED, false);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        workspace.addOnLayoutChangeListener((view, left, top, right, bottom,
                oldLeft, oldTop, oldRight, oldBottom) -> arrange(workspace, inputs, output, right - left));

        profile.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                refresh();
            }
            @Override public void onNothingSelected(AdapterView<?> parent) {
                refresh();
            }
        });
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
        timeline.setText("");
        timing.setText("");
        outputTitle.setText("");
        profile.setSelection(0);
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
                if (selectedApk != null) {
                    String title = name.split("\n", 2)[0].replaceFirst("(?i)\\.apk$", "").trim();
                    if (title.length() > 65) title = title.substring(0, 65);
                    outputTitle.setText(title + " • Keyquest");
                }
                status.setText(outcome);
                refresh();
            });
        }, "keyquest-inspect").start();
    }

    private static String describeInspection(ApkInspection result) {
        if (!result.universalRenpy) return "No supported Ren’Py universal APK layout detected.";
        if (result.alreadyPatched) return "Ren’Py game detected. This APK already contains Keyquest.";
        if (result.engineVersion == null) return "Ren’Py game detected. Confirm the engine version to continue.";
        if (!result.canBuild()) return "Ren’Py " + result.engineVersion
                + " detected. Built-in profiles cover 7.8 and 8.0–8.5.";
        return "Ren’Py " + result.engineVersion + " detected. Ready to build.";
    }

    private boolean canBuild() {
        return !busy && selectedApk != null && inspection != null && inspection.canBuild()
                && chosenFamily() != null;
    }

    private String chosenFamily() {
        if (inspection == null) return null;
        if (inspection.engineVersion != null) return ApkInspection.family(inspection.engineVersion);
        int position = profile.getSelectedItemPosition() - 1;
        return position >= 0 && position < ApkInspection.ENGINE_FAMILIES.length
                ? ApkInspection.ENGINE_FAMILIES[position] : null;
    }

    private void confirmBuild() {
        if (!canBuild()) return;
        String title = outputTitle.getText().toString().trim();
        if (title.isEmpty()) {
            status.setText("Enter an output name.");
            return;
        }
        discardOutput();
        busy = true;
        filename = title.replaceAll("[^\\p{L}\\p{N}._ -]+", "-").replaceAll(" +", " ").trim() + ".apk";
        final String libraryLabel = renameInLibrary.isChecked() ? title : null;
        final String family = chosenFamily();
        status.setText("Checking the source APK for Ren’Py " + family + ".x…");
        timeline.setText("");
        timing.setText("");
        progress.setIndeterminate(true);
        refresh();
        final File source = selectedApk;
        final boolean includeValues = valuesAddon.isChecked();
        final String profileKey = family.replace('.', '_');
        new Thread(() -> {
            File unsigned = null, result = null;
            String message;
            try {
                ApkInspection current = ApkInspection.scan(source, true);
                if (!current.canBuild() || (current.engineVersion != null
                        && !family.equals(ApkInspection.family(current.engineVersion)))) {
                    throw new IOException("The APK has changed or is incompatible. Select it again.");
                }
                unsigned = File.createTempFile("rebuild-", ".apk", getCacheDir());
                result = File.createTempFile("keyboard-", ".apk", getCacheDir());
                Map<String, byte[]> gameAssets = new LinkedHashMap<>();
                gameAssets.put("assets/x-game/x-keyquest_overlay.rpyc", readAsset("keyquest_" + profileKey + ".rpyc"));
                for (String artwork : new String[]{"logo", "panel", "panel_mint", "key", "key_focus", "sheet"}) {
                    String filename = "keyquest_" + artwork + ".png";
                    gameAssets.put("assets/x-game/x-" + filename, readAsset(filename));
                }
                if (includeValues) {
                    gameAssets.put("assets/x-game/x-keyquest_values.rpyc", readAsset("keyquest_values_" + profileKey + ".rpyc"));
                }
                ApkBuilder.build(source, unsigned, result, gameAssets, signer(), libraryLabel, new BuildTimeline());
                message = String.format(Locale.getDefault(), "Verified · %.1f MB\n%s",
                        result.length() / 1_000_000.0, filename);
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
                timeline.setText(completed == null ? "Build stopped" : "✓ Repacked   ✓ Added controls   ✓ Signed   ✓ Verified");
                timing.setText("");
                status.setText(outcome);
                refresh();
            });
        }, "keyquest-build").start();
    }

    private final class BuildTimeline implements ApkBuilder.Observer {
        private final long started = android.os.SystemClock.elapsedRealtime();
        private long stageStarted = started, sent;
        private String current = "";

        @Override public void update(String stage, long copied, long total) {
            long now = android.os.SystemClock.elapsedRealtime();
            boolean changed = !stage.equals(current);
            if (changed) {
                current = stage;
                stageStarted = now;
            } else if (now - sent < 180 && copied < total) {
                return;
            }
            sent = now;
            int index = Arrays.asList(phases).indexOf(stage);
            long elapsed = now - stageStarted;
            boolean measured = index == 0 && total > 0;
            int percent = measured ? (int) Math.min(100, copied * 100 / total) : 0;
            String estimate = measured && elapsed >= 750 && copied > 0 && copied < total
                    ? " · about " + Math.max(1, Math.round((total - copied) * (elapsed / (double) copied) / 1000.0))
                        + " s left to repack" : "";
            String metrics = measured
                    ? String.format(Locale.getDefault(), "%.1f / %.1f MB · %d%%", copied / 1e6, total / 1e6, percent)
                    : "Elapsed " + Math.max(0, (now - started) / 1000) + " s";
            runOnUiThread(() -> {
                if (isDestroyed()) return;
                timeline.setText((index + 1) + " / " + phases.length + "   " + stage);
                timing.setText(metrics + estimate);
                progress.setIndeterminate(!measured);
                if (measured) progress.setProgress(percent);
            });
        }
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
                values.put(android.provider.MediaStore.Downloads.DISPLAY_NAME, filename);
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
                message = "Saved in Downloads · " + filename;
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
        valuesAddon.setEnabled(!busy && ready == null);
        outputTitle.setEnabled(!busy && ready == null && selectedApk != null);
        renameInLibrary.setEnabled(!busy && ready == null && selectedApk != null);
        options.setVisibility(ready == null ? View.GONE : View.VISIBLE);
        options.setEnabled(!busy);
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
