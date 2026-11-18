package org.questpanel.macros;

import android.accessibilityservice.InputMethod;
import android.content.Context;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.os.SystemClock;
import android.view.Gravity;
import android.view.KeyCharacterMap;
import android.view.KeyEvent;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.function.Supplier;

final class KeyboardOverlay {
    private static final int PANEL = Color.rgb(15, 24, 37);
    private static final int KEY = Color.rgb(39, 56, 77);
    private static final int ACCENT = Color.rgb(196, 255, 106);
    private static final int INK = Color.rgb(13, 26, 22);
    private static final int FOREGROUND = Color.rgb(237, 246, 251);
    private static final int MUTED = Color.rgb(171, 192, 210);
    private static final String[] LETTERS = {"qwertyuiop", "asdfghjkl", "zxcvbnm"};
    private static final String[] SYMBOLS = {"1234567890", "@#%&?!:;_", "()[]+-=/"};

    private final Context context;
    private final WindowManager manager;
    private final LinearLayout root;
    private final WindowManager.LayoutParams params;
    private final Supplier<InputMethod.AccessibilityInputConnection> connection;
    private final Runnable onClose;
    private final Rect dock = new Rect();
    private TextView message;
    private boolean capitals;
    private boolean symbols;
    private boolean atTop;
    private boolean visible;
    private int keyHeight;

    KeyboardOverlay(Context context, Rect bounds,
                    Supplier<InputMethod.AccessibilityInputConnection> connection, Runnable onClose) {
        this.context = context;
        this.connection = connection;
        this.onClose = onClose;
        manager = context.getSystemService(WindowManager.class);
        root = new LinearLayout(context);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(8), dp(5), dp(8), dp(6));
        root.setBackground(surface(PANEL, dp(14)));
        params = new WindowManager.LayoutParams(1, WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP | Gravity.LEFT;
        params.setTitle("Keyquest keyboard");
        update(bounds);
        rebuild();
    }

    void show() {
        manager.addView(root, params);
        visible = true;
    }

    void close() {
        if (!visible) return;
        visible = false;
        try {
            manager.removeViewImmediate(root);
        } catch (IllegalArgumentException alreadyRemoved) {
            // The display may have disconnected.
        }
    }

    void update(Rect bounds) {
        if (dock.equals(bounds)) return;
        dock.set(bounds);
        int previousHeight = keyHeight;
        keyHeight = Math.min(dp(42), Math.max(dp(24), (bounds.height() - dp(64)) / 5));
        position();
        if (visible && keyHeight != previousHeight) rebuild();
    }

    private void position() {
        int width = Math.min(dp(660), Math.max(1, dock.width() - dp(12)));
        int height = dp(5) + dp(6) + dp(6) + keyHeight * 5;
        params.width = width;
        params.x = dock.left + (dock.width() - width) / 2;
        params.y = atTop ? dock.top + dp(3) : Math.max(dock.top, dock.bottom - height - dp(3));
        if (visible) manager.updateViewLayout(root, params);
    }

    private void rebuild() {
        root.removeAllViews();
        LinearLayout header = row();
        message = new TextView(context);
        message.setText("KEYQUEST  ·  Focus the game’s text field");
        message.setTextColor(MUTED);
        message.setTextSize(12);
        message.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        message.setMaxLines(2);
        message.setGravity(Gravity.CENTER_VERTICAL);
        message.setPadding(dp(6), 0, 0, 0);
        header.addView(message, new LinearLayout.LayoutParams(0, keyHeight, 3));
        button(header, atTop ? "Move down" : "Move up", 1, false, () -> {
            atTop = !atTop;
            position();
            rebuild();
        });
        button(header, "Close", 0.8f, false, onClose);

        for (String line : symbols ? SYMBOLS : LETTERS) {
            LinearLayout keys = row();
            for (char character : line.toCharArray()) {
                String value = String.valueOf(capitals ? Character.toUpperCase(character) : character);
                button(keys, value, 1, false, () -> type(value));
            }
        }

        LinearLayout tools = row();
        button(tools, "Shift", 1, capitals, () -> { capitals = !capitals; rebuild(); });
        button(tools, symbols ? "ABC" : "123?", 1, symbols, () -> { symbols = !symbols; rebuild(); });
        button(tools, "Space", 2, false, () -> type(" "));
        button(tools, "⌫", 0.8f, false, () -> key(KeyEvent.KEYCODE_DEL));
        button(tools, "Enter", 1, true, () -> key(KeyEvent.KEYCODE_ENTER));
    }

    private void type(String value) {
        InputMethod.AccessibilityInputConnection input = connection.get();
        if (input == null) {
            message.setText("Tap the game’s text field, then try again.");
            return;
        }
        input.commitText(value, 1, null);
        if (capitals && !symbols) {
            capitals = false;
            rebuild();
        }
        message.setText("KEYQUEST  ·  Typing in the game");
    }

    private void key(int code) {
        InputMethod.AccessibilityInputConnection input = connection.get();
        if (input == null) {
            message.setText("Tap the game’s text field, then try again.");
            return;
        }
        long now = SystemClock.uptimeMillis();
        int flags = KeyEvent.FLAG_SOFT_KEYBOARD | KeyEvent.FLAG_KEEP_TOUCH_MODE;
        input.sendKeyEvent(new KeyEvent(now, now, KeyEvent.ACTION_DOWN, code, 0, 0,
                KeyCharacterMap.VIRTUAL_KEYBOARD, 0, flags));
        input.sendKeyEvent(new KeyEvent(now, now, KeyEvent.ACTION_UP, code, 0, 0,
                KeyCharacterMap.VIRTUAL_KEYBOARD, 0, flags));
    }

    private LinearLayout row() {
        LinearLayout row = new LinearLayout(context);
        root.addView(row, new LinearLayout.LayoutParams(-1, keyHeight));
        return row;
    }

    private void button(LinearLayout row, String title, float width, boolean accent, Runnable onClick) {
        TextView key = new TextView(context);
        key.setText(title);
        if ("⌫".equals(title)) key.setContentDescription("Backspace");
        key.setTextSize(title.length() > 2 ? 12 : 17);
        key.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        key.setGravity(Gravity.CENTER);
        key.setTextColor(accent ? INK : FOREGROUND);
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[] { android.R.attr.state_pressed }, surface(Color.rgb(108, 137, 151), dp(7)));
        states.addState(new int[] { android.R.attr.state_hovered }, surface(Color.rgb(66, 94, 118), dp(7)));
        states.addState(new int[0], surface(accent ? ACCENT : KEY, dp(7)));
        key.setBackground(states);
        key.setOnClickListener(view -> onClick.run());
        LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(0, -1, width);
        layout.setMargins(dp(2), dp(2), dp(2), dp(2));
        row.addView(key, layout);
    }

    private int dp(int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }

    private static GradientDrawable surface(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(radius);
        return shape;
    }
}
