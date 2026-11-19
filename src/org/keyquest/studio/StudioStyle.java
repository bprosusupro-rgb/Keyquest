package org.keyquest.studio;

import android.content.res.ColorStateList;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.graphics.drawable.StateListDrawable;

final class StudioStyle {
    static final int BACKGROUND = 0xff090f1c;
    static final int PANEL = 0xff162236;
    static final int CONTROL = 0xff243752;
    static final int BORDER = 0xff394f6a;
    static final int TEXT = 0xfff3f8ff;
    static final int MUTED = 0xffb6c8de;
    static final int ACCENT = 0xffa5f4df;

    private StudioStyle() {}

    static GradientDrawable surface(int fill, int radius, int strokeWidth, int stroke) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(fill);
        shape.setCornerRadius(radius);
        if (strokeWidth > 0) shape.setStroke(strokeWidth, stroke);
        return shape;
    }

    static GradientDrawable backdrop() {
        return new GradientDrawable(GradientDrawable.Orientation.TL_BR,
                new int[]{0xff172b49, BACKGROUND, 0xff080e19});
    }

    static RippleDrawable button(boolean primary, int radius, int strokeWidth) {
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[]{-android.R.attr.state_enabled},
                surface(0xff203047, radius, strokeWidth, 0xff354860));
        states.addState(new int[]{android.R.attr.state_focused},
                surface(primary ? ACCENT : CONTROL, radius, strokeWidth, 0xff6bbbab));
        states.addState(new int[]{android.R.attr.state_hovered},
                surface(primary ? 0xffc7ffef : 0xff365272, radius, strokeWidth, 0xff6bbbab));
        states.addState(new int[0], surface(primary ? ACCENT : CONTROL, radius,
                strokeWidth, primary ? 0xffc4f6ea : BORDER));
        return new RippleDrawable(ColorStateList.valueOf(0x4473b5b4), states,
                surface(0xffffffff, radius, 0, 0));
    }
}
