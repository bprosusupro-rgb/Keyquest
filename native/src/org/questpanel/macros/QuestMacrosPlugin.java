package org.questpanel.macros;

import android.app.Activity;
import android.content.Intent;
import android.content.Context;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.provider.Settings;
import org.godotengine.godot.Godot;
import org.godotengine.godot.plugin.GodotPlugin;
import org.godotengine.godot.plugin.UsedByGodot;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONException;
import java.util.List;
import java.util.HashSet;
import java.util.Comparator;

public final class QuestMacrosPlugin extends GodotPlugin {
    public QuestMacrosPlugin(Godot godot) {
        super(godot);
    }

    @Override
    public String getPluginName() {
        return "QuestMacros";
    }

    @UsedByGodot
    public void openSettings() {
        Activity activity = getActivity();
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            try {
                activity.startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
            } catch (android.content.ActivityNotFoundException | SecurityException error) {
                MacroService.status = "Android accessibility settings are unavailable on this firmware.";
            }
        });
    }

    @UsedByGodot
    public String listApps() {
        Activity activity = getActivity();
        JSONArray apps = new JSONArray();
        if (activity == null) return apps.toString();
        PackageManager manager = activity.getPackageManager();
        Intent launcher = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> matches = manager.queryIntentActivities(launcher, 0);
        matches.sort(Comparator.comparing(app -> app.loadLabel(manager).toString(),
                                           String.CASE_INSENSITIVE_ORDER));
        HashSet<String> seen = new HashSet<>();
        seen.add(activity.getPackageName());
        for (ResolveInfo match : matches) {
            String name = match.activityInfo.packageName;
            if (!seen.add(name)) continue;
            try {
                apps.put(new JSONObject().put("label", match.loadLabel(manager).toString())
                        .put("package", name));
            } catch (JSONException impossible) {
                throw new IllegalStateException(impossible);
            }
        }
        return apps.toString();
    }

    @UsedByGodot
    public String loadMacro() {
        Activity activity = getActivity();
        return activity == null ? "{}" :
                activity.getSharedPreferences("macro", Context.MODE_PRIVATE).getString("last", "{}");
    }

    @UsedByGodot
    public void arm(String target, String coordinates, int repeats, String payload, boolean pick) {
        Activity activity = getActivity();
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            MacroService service = MacroService.active;
            if (service == null) {
                MacroService.status = "Enable Keyquest in Android accessibility settings, then return here.";
                openSettings();
                return;
            }
            service.arm(activity, target, coordinates, repeats, payload, pick);
        });
    }

    @UsedByGodot
    public boolean isServiceReady() {
        return MacroService.active != null;
    }

    @UsedByGodot
    public void openKeyboard(String target) {
        Activity activity = getActivity();
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            MacroService service = MacroService.active;
            if (service == null) {
                MacroService.status = "Enable Keyquest in Android accessibility settings, then return here.";
                openSettings();
                return;
            }
            service.openKeyboard(activity, target);
        });
    }

    @UsedByGodot
    public void sendKey(String target, String key) {
        Activity activity = getActivity();
        if (activity == null) return;
        activity.runOnUiThread(() -> {
            MacroService service = MacroService.active;
            if (service == null) {
                MacroService.status = "Enable Keyquest in Android accessibility settings, then retry.";
                return;
            }
            service.sendKey(activity, target, key);
        });
    }

    @UsedByGodot
    public void stop() {
        Activity activity = getActivity();
        if (activity != null) activity.runOnUiThread(() -> {
            if (MacroService.active != null) MacroService.active.stop("Stopped.");
        });
    }

    @UsedByGodot
    public String getStatus() {
        return MacroService.status;
    }

    @UsedByGodot
    public String takePoint() {
        return MacroService.point.getAndSet("");
    }
}
