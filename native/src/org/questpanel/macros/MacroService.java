package org.questpanel.macros;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.accessibilityservice.InputMethod;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.hardware.display.DisplayManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.SparseArray;
import android.view.Display;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import android.view.inputmethod.EditorInfo;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONException;
import org.json.JSONObject;

public final class MacroService extends AccessibilityService {
    static volatile MacroService active;
    static volatile String status = "Enable Keyquest in Android accessibility settings.";
    static final AtomicReference<String> point = new AtomicReference<>("");
    private final Handler handler = new Handler(Looper.getMainLooper());
    private Runnable operation;
    private WindowManager pickerManager;
    private TextView picker;
    private int generation;
    private KeyboardOverlay keyboard;

    private static final class Step {
        final double x, y;
        final int delay;

        Step(String line) {
            String[] parts = line.trim().split(",", -1);
            if (parts.length != 3) throw new IllegalArgumentException("Each line needs x%, y%, delay.");
            x = Double.parseDouble(parts[0].trim());
            y = Double.parseDouble(parts[1].trim());
            delay = Integer.parseInt(parts[2].trim());
            if (!(x >= 0 && x <= 100 && y >= 0 && y <= 100) || delay < 100 || delay > 30000) {
                throw new IllegalArgumentException("Coordinates must be 0–100 and delays 100–30,000 ms.");
            }
        }
    }

    private static final class Target {
        final int display;
        final Rect bounds = new Rect();

        Target(int display, AccessibilityWindowInfo window) {
            this.display = display;
            window.getBoundsInScreen(bounds);
        }
    }

    @Override
    protected void onServiceConnected() {
        active = this;
        status = "Ready. Select an app and run a macro or find a tap point.";
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // The scheduled runner reads the current window immediately before every action.
    }

    @Override
    public void onInterrupt() {
        stop("Interrupted.");
    }

    @Override
    public void onDestroy() {
        stop("Accessibility service disconnected.");
        if (active == this) active = null;
        super.onDestroy();
    }

    void arm(Activity activity, String target, String coordinates, int repeats, String payload, boolean pick) {
        arm(activity, target, coordinates, repeats, payload, pick, false);
    }

    void openKeyboard(Activity activity, String target) {
        if (Build.VERSION.SDK_INT < 33) {
            stop("The in-game keyboard requires Android 13 or newer.");
            return;
        }
        arm(activity, target, "", 1, "", false, true);
    }

    private void arm(Activity activity, String target, String coordinates, int repeats,
                     String payload, boolean pick, boolean typing) {
        stop("Preparing…");
        if (!target.matches("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+")
                || target.equals(getPackageName())) {
            status = "Select another installed app or enter its Android package name.";
            return;
        }
        List<Step> steps = new ArrayList<>();
        try {
            if (!pick && !typing) {
                for (String line : coordinates.split("\\R")) {
                    if (!line.trim().isEmpty()) steps.add(new Step(line));
                }
                if (steps.size() > 30 || (steps.isEmpty() && payload.isEmpty())
                        || repeats < 1 || repeats > 100 || payload.length() > 500) {
                    throw new IllegalArgumentException("Use up to 30 steps, 100 repeats and 500 text characters.");
                }
                long length = 0;
                for (Step step : steps) length += step.delay + 55;
                if (length * repeats > 600_000) {
                    throw new IllegalArgumentException("Each run must finish within 10 minutes.");
                }
                JSONObject saved = new JSONObject().put("package", target)
                        .put("steps", coordinates).put("repeats", repeats);
                getSharedPreferences("macro", MODE_PRIVATE).edit().putString("last", saved.toString()).apply();
            }
        } catch (NumberFormatException invalid) {
            status = "Use numeric coordinates and a whole-number delay.";
            return;
        } catch (IllegalArgumentException | JSONException invalid) {
            status = invalid.getMessage();
            return;
        }

        status = "Waiting for " + target + ". Open its panel within 30 seconds.";
        long deadline = SystemClock.uptimeMillis() + 30_000;
        int ticket = generation;
        operation = new Runnable() {
            @Override public void run() {
                if (ticket != generation) return;
                Target window = findTarget(target, typing);
                if (window != null) {
                    if (pick) showPicker(target, window);
                    else if (typing) showKeyboard(target, window);
                    else schedule(() -> runStep(ticket, target, window.display, steps,
                                                 repeats, payload, 0), 1200);
                    return;
                }
                if (SystemClock.uptimeMillis() >= deadline) {
                    stop("Target not detected. Confirm the app is focused and exposed to Android accessibility.");
                } else {
                    handler.postDelayed(this, 250);
                }
            }
        };
        handler.postDelayed(operation, 350);
        Intent launch = getPackageManager().getLaunchIntentForPackage(target);
        if (launch != null) {
            try {
                activity.startActivity(launch);
            } catch (android.content.ActivityNotFoundException | SecurityException ignored) {
                // The user can select the target in the headset launcher.
            }
        }
    }

    private Target findTarget(String packageName) {
        return findTarget(packageName, false);
    }

    private Target findTarget(String packageName, boolean allowInactive) {
        if (Build.VERSION.SDK_INT >= 30) {
            SparseArray<List<AccessibilityWindowInfo>> displays = getWindowsOnAllDisplays();
            for (int i = 0; i < displays.size(); i++) {
                Target result = findInDisplay(displays.keyAt(i), displays.valueAt(i), packageName, allowInactive);
                if (result != null) return result;
            }
            return null;
        }
        return findInDisplay(Display.DEFAULT_DISPLAY, getWindows(), packageName, allowInactive);
    }

    private Target findInDisplay(int display, List<AccessibilityWindowInfo> windows,
                                 String packageName, boolean allowInactive) {
        for (AccessibilityWindowInfo window : windows) {
            if (window.getType() != AccessibilityWindowInfo.TYPE_APPLICATION
                    || !window.isFocused() || (!allowInactive && !window.isActive())) continue;
            AccessibilityNodeInfo root = window.getRoot();
            if (root != null && packageName.contentEquals(root.getPackageName() == null ? "" : root.getPackageName())) {
                Target target = new Target(display, window);
                if (!target.bounds.isEmpty()) return target;
            }
        }
        return null;
    }

    private void runStep(int ticket, String target, int display, List<Step> steps,
                         int repeats, String payload, int index) {
        if (ticket != generation) return;
        Target window = findTarget(target);
        if (window == null || window.display != display) {
            stop("Stopped because the target lost focus or moved displays.");
            return;
        }
        int total = steps.size() * repeats;
        if (index >= total) {
            boolean entered = payload.isEmpty() || enterText(target, payload);
            stop(entered ? "Macro finished · " + total + " tap(s)." :
                    "Taps finished. No compatible focused text input was found.");
            return;
        }

        Step step = steps.get(index % steps.size());
        Rect area = window.bounds;
        float x = (float) (area.left + (area.width() - 1) * step.x / 100);
        float y = (float) (area.top + (area.height() - 1) * step.y / 100);
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.Builder gesture = new GestureDescription.Builder()
                .addStroke(new GestureDescription.StrokeDescription(path, 0, 55));
        if (Build.VERSION.SDK_INT >= 30) gesture.setDisplayId(display);
        status = "Tapping " + (index + 1) + " of " + total + ". Switch apps to stop.";
        boolean dispatched = dispatchGesture(gesture.build(), new GestureResultCallback() {
            @Override public void onCompleted(GestureDescription ignored) {
                if (ticket == generation) schedule(() -> runStep(ticket, target, display,
                        steps, repeats, payload, index + 1), step.delay);
            }

            @Override public void onCancelled(GestureDescription ignored) {
                if (ticket == generation) stop("Android cancelled the simulated tap.");
            }
        }, handler);
        if (!dispatched) stop("Android rejected the simulated tap on this display.");
    }

    private boolean enterText(String target, String payload) {
        AccessibilityNodeInfo field = findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
        if (field != null && target.contentEquals(field.getPackageName() == null ? "" : field.getPackageName())
                && field.isEditable()) {
            Bundle arguments = new Bundle();
            arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, payload);
            if (field.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SET_TEXT.getId(), arguments)) {
                return true;
            }
        }
        Target window = findTarget(target);
        if (window != null) {
            InputMethod.AccessibilityInputConnection input = keyboardConnection(target, window.display);
            if (input != null) {
                input.commitText(payload, 1, null);
                return true;
            }
        }
        return false;
    }

    private void showKeyboard(String target, Target window) {
        try {
            Context context = overlayContext(window.display);
            if (context == null) {
                stop("Horizon OS did not expose the target display for a keyboard overlay.");
                return;
            }
            keyboard = new KeyboardOverlay(context, window.bounds,
                    () -> keyboardConnection(target, window.display),
                    () -> stop("Keyboard closed."));
            keyboard.show();
            status = "Keyboard open in the selected app.";
            monitorKeyboard(target, window.display);
        } catch (RuntimeException blocked) {
            stop("Horizon OS did not allow a keyboard overlay on this display.");
        }
    }

    private void monitorKeyboard(String target, int display) {
        schedule(() -> {
            Target current = findTarget(target, true);
            if (current == null || current.display != display) {
                stop("Keyboard closed because the target lost focus.");
                return;
            }
            try {
                keyboard.update(current.bounds);
                monitorKeyboard(target, display);
            } catch (RuntimeException unavailable) {
                stop("The keyboard overlay is no longer available.");
            }
        }, 350);
    }

    private InputMethod.AccessibilityInputConnection keyboardConnection(String target, int display) {
        if (Build.VERSION.SDK_INT < 33) return null;
        Target current = findTarget(target, true);
        if (current == null || current.display != display) return null;
        InputMethod method = getInputMethod();
        if (method == null) return null;
        EditorInfo editor = method.getCurrentInputEditorInfo();
        return editor != null && target.equals(editor.packageName)
                ? method.getCurrentInputConnection() : null;
    }

    private Context overlayContext(int displayId) {
        DisplayManager displays = getSystemService(DisplayManager.class);
        Display display = displays == null ? null : displays.getDisplay(displayId);
        if (display == null) return null;
        Context context = createDisplayContext(display);
        return Build.VERSION.SDK_INT >= 30
                ? context.createWindowContext(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY, null)
                : context;
    }

    private void showPicker(String target, Target window) {
        try {
            Context context = overlayContext(window.display);
            if (context == null) {
                stop("This display does not expose a tap-point picker. Enter percentages manually.");
                return;
            }
            pickerManager = context.getSystemService(WindowManager.class);
            picker = new TextView(context);
            picker.setText("Tap the point to capture");
            picker.setGravity(Gravity.TOP | Gravity.CENTER_HORIZONTAL);
            picker.setTextSize(20);
            picker.setTextColor(Color.WHITE);
            picker.setBackgroundColor(0x332b83a6);
            picker.setOnTouchListener((view, event) -> {
                if (event.getActionMasked() == MotionEvent.ACTION_UP) {
                    Rect bounds = window.bounds;
                    double x = 100.0 * (event.getRawX() - bounds.left) / Math.max(1, bounds.width() - 1);
                    double y = 100.0 * (event.getRawY() - bounds.top) / Math.max(1, bounds.height() - 1);
                    if (x >= 0 && x <= 100 && y >= 0 && y <= 100 && findTarget(target, true) != null) {
                        point.set(String.format(Locale.ROOT, "%.1f, %.1f, 500", x, y));
                        stop("Point captured. Return to Keyquest.");
                    } else {
                        stop("Point was outside the focused target. Try again or enter percentages.");
                    }
                }
                return true;
            });
            WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                    WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                    PixelFormat.TRANSLUCENT);
            pickerManager.addView(picker, params);
            status = "Tap the desired point in the target panel.";
            schedule(() -> stop("Point picker timed out."), 15_000);
        } catch (RuntimeException denied) {
            stop("This display does not permit the picker. Enter percentages manually.");
        }
    }

    private void schedule(Runnable next, long delay) {
        operation = next;
        handler.postDelayed(next, delay);
    }

    void stop(String reason) {
        generation++;
        if (operation != null) {
            handler.removeCallbacks(operation);
            operation = null;
        }
        if (keyboard != null) {
            keyboard.close();
            keyboard = null;
        }
        if (picker != null) {
            if (picker.isAttachedToWindow()) pickerManager.removeView(picker);
            picker = null;
            pickerManager = null;
        }
        status = reason;
    }
}
