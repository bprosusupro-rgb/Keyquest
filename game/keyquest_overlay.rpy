# Add this file to the game/ directory of a Ren'Py project you can modify.

init python:
    def _keyquest_press(name, text=""):
        import pygame
        key = getattr(pygame, "K_" + name)
        mods = pygame.KMOD_SHIFT if text and text.isupper() else 0
        # Ren'Py's keymap reads repeat on both press and release.
        for kind, characters in ((pygame.KEYDOWN, text), (pygame.KEYUP, "")):
            pygame.event.post(pygame.event.Event(
                kind, key=key, mod=mods, unicode=characters, repeat=False))

    def _keyquest_dragged(drags, drop):
        if drags:
            persistent.keyquest_position = (max(0, int(drags[0].x)), max(0, int(drags[0].y)))

    def _keyquest_float_dragged(drags, drop):
        if drags:
            drag = drags[0]
            positions = dict(persistent.keyquest_panel_positions)
            # Relative free space keeps the panel visible if its contents change size.
            x = float(drag.x) / max(1, drag.parent_width - drag.w)
            y = float(drag.y) / max(1, drag.parent_height - drag.h)
            positions[drag.drag_name] = (min(1.0, max(0.0, x)), min(1.0, max(0.0, y)))
            persistent.keyquest_panel_positions = positions
            renpy.restart_interaction()

    def _keyquest_reset_panels():
        persistent.keyquest_position = None
        persistent.keyquest_panel_positions = {}
        renpy.hide_screen("_keyquest_keyboard")
        renpy.show_screen("_keyquest_keyboard")

    _keyquest_screens = getattr(config, "always_shown_screens", config.overlay_screens)
    if "_keyquest_launcher" not in _keyquest_screens:
        _keyquest_screens.append("_keyquest_launcher")

default persistent.keyquest_top = False
default persistent.keyquest_position = None
default persistent.keyquest_panel_positions = {}
default persistent.keyquest_compact = False
default persistent.keyquest_light_accent = False
default persistent.keyquest_quick_one = "s"
default persistent.keyquest_quick_two = "i"

style keyquest_key is button:
    background Frame("keyquest_key.png", 12, 12)
    hover_background Frame("keyquest_key_focus.png", 12, 12)
    selected_background Frame("keyquest_key_focus.png", 12, 12)
    padding (14, 9)
    yminimum 48

style keyquest_key_text is button_text:
    color "#152538"
    size 24

screen _keyquest_launcher():
    zorder 990
    $ visibility = 0.0 if renpy.get_screen("_keyquest_ocr_capture") else 1.0
    if visibility:
        $ position = persistent.keyquest_panel_positions.get("keyquest-launcher")
        draggroup:
            drag:
                drag_name "keyquest-launcher"
                drag_offscreen False
                droppable False
                dragged _keyquest_float_dragged
                drag_handle (0, 0, 46, 1.0)
                align ((0.98, 0.95) if position is None else position)
                frame:
                    background Frame("keyquest_panel.png", 24, 24)
                    padding (4, 4)
                    hbox:
                        spacing 2
                        text "⠿" color "#b9d3e8" size 28 xsize 40 text_align 0.5 yalign 0.5
                        button:
                            background None
                            hover_background Frame("keyquest_panel_mint.png", 24, 24)
                            padding (8, 4)
                            action ToggleScreen("_keyquest_keyboard")
                            alt "Keyquest keyboard"
                            alternate (ToggleScreen("_keyquest_values") if renpy.has_screen("_keyquest_values") else NullAction())
                            hbox:
                                spacing 7
                                if renpy.loadable("keyquest_logo.png"):
                                    add "keyquest_logo.png" xysize (48, 48) yalign 0.5
                                text "Keyboard" color "#eff8ff" size 22 yalign 0.5

screen _keyquest_floating(panel, title, width, height, alignment=(0.5, 0.25), light=False):
    $ scale = min(1.0, config.screen_width / float(width + 20), config.screen_height / float(height + 20))
    $ drag_id = "keyquest-" + panel
    $ position = persistent.keyquest_panel_positions.get(drag_id)
    draggroup:
        drag:
            drag_name drag_id
            droppable False
            drag_offscreen False
            dragged _keyquest_float_dragged
            drag_handle (0, 0, 1.0, int(49 * scale))
            align (alignment if position is None else position)
            frame:
                xsize width
                at Transform(zoom=scale)
                padding (16, 11)
                background Frame("keyquest_sheet.png" if light else "keyquest_panel.png", 24, 24)
                vbox:
                    spacing 8
                    fixed:
                        ysize 35
                        text title color ("#152538" if light else "#eff8ff") size 24 align (0.0, 0.5)
                        text "⠿  Drag to move" color ("#405264" if light else "#b9d3e8") size 18 align (1.0, 0.5)
                    transclude

style keyquest_deck_key is keyquest_key:
    background Frame("keyquest_panel.png", 16, 16)
    hover_background Frame("keyquest_panel_mint.png", 16, 16)
    selected_background Frame("keyquest_panel_mint.png", 16, 16)
    padding (9, 7)
    ysize 47

style keyquest_deck_key_text is keyquest_key_text:
    color "#f0f7ff"
    size 22
    xalign 0.5

style keyquest_deck_accent is keyquest_key:
    background Frame("keyquest_key_focus.png", 12, 12)
    padding (12, 7)
    ysize 47

style keyquest_deck_accent_text is keyquest_key_text:
    size 22

screen _keyquest_keyboard():
    zorder 991
    default caps = False
    default settings_open = False
    default editing_slot = 1
    $ scale = min(1.0, config.screen_width / 650.0, config.screen_height / 510.0) * (0.80 if persistent.keyquest_compact else 1.0)
    $ position = persistent.keyquest_position
    $ panel_height = 505 if settings_open else 400
    draggroup:
        drag:
            drag_name "keyquest-floating-keyboard"
            draggable True
            droppable False
            drag_offscreen False
            drag_handle (0, 0, 1.0, int(54 * scale))
            dragged _keyquest_dragged
            xpos (0.5 if position is None else min(position[0], max(0, config.screen_width - int(636 * scale))))
            ypos ((0.12 if persistent.keyquest_top else 0.92) if position is None else min(position[1], max(0, config.screen_height - int(panel_height * scale))))
            xanchor (0.5 if position is None else 0.0)
            yanchor ((0.0 if persistent.keyquest_top else 1.0) if position is None else 0.0)
            frame:
                xsize 636
                background Frame("keyquest_panel_mint.png" if persistent.keyquest_light_accent else "keyquest_panel.png", 24, 24)
                at Transform(zoom=scale)
                padding (14, 10)
                vbox:
                    spacing 7
                    fixed:
                        ysize 42
                        text "Keyboard" color "#eff8ff" size 24 align (0.0, 0.5)
                        text "⠿  Drag to move" color "#b9d3e8" size 18 align (1.0, 0.5)
                    hbox:
                        spacing 6
                        for quick in (persistent.keyquest_quick_one, persistent.keyquest_quick_two):
                            textbutton quick.upper() style "keyquest_deck_accent" action Function(_keyquest_press, quick, quick, _update_screens=False)
                        if renpy.has_screen("_keyquest_values"):
                            textbutton "Values" style "keyquest_deck_key" action [Hide("_keyquest_keyboard"), ToggleScreen("_keyquest_values")]
                        if renpy.has_screen("_keyquest_automation"):
                            textbutton "Macros" style "keyquest_deck_key" action [Hide("_keyquest_keyboard"), Show("_keyquest_automation")]
                        if renpy.has_screen("_keyquest_smart_input"):
                            textbutton "OCR" style "keyquest_deck_key" action [Hide("_keyquest_keyboard"), Show("_keyquest_smart_input")]
                        textbutton ("Done" if settings_open else "Settings") style "keyquest_deck_key" action ToggleScreenVariable("settings_open")
                        textbutton "Close" style "keyquest_deck_key" action Hide("_keyquest_keyboard")
                    if settings_open:
                        hbox:
                            spacing 6
                            textbutton "Reset positions" style "keyquest_deck_key" action Function(_keyquest_reset_panels)
                            textbutton ("Dock bottom" if persistent.keyquest_top else "Dock top") style "keyquest_deck_key" action [ToggleField(persistent, "keyquest_top"), SetField(persistent, "keyquest_position", None)]
                            textbutton ("Full size" if persistent.keyquest_compact else "Compact") style "keyquest_deck_key" action ToggleField(persistent, "keyquest_compact")
                            textbutton "Theme" style "keyquest_deck_key" action ToggleField(persistent, "keyquest_light_accent")
                        hbox:
                            spacing 6
                            textbutton "Shortcut 1" style "keyquest_deck_key" action SetScreenVariable("editing_slot", 1)
                            textbutton "Shortcut 2" style "keyquest_deck_key" action SetScreenVariable("editing_slot", 2)
                            text "Choose a key for shortcut [editing_slot]" color "#b9d3e8" size 18 yalign 0.5
                    for row in ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"):
                        hbox:
                            xalign 0.5
                            spacing 5
                            for letter in row:
                                $ caption = letter.upper() if caps else letter
                                textbutton caption:
                                    style "keyquest_deck_key"
                                    xsize 52
                                    action (SetField(persistent, "keyquest_quick_one" if editing_slot == 1 else "keyquest_quick_two", letter) if settings_open else Function(_keyquest_press, letter, caption, _update_screens=False))
                    hbox:
                        xalign 0.5
                        spacing 5
                        textbutton "Shift" style "keyquest_deck_key" action SetScreenVariable("caps", not caps)
                        textbutton "Space" style "keyquest_deck_key" xsize 144 action Function(_keyquest_press, "SPACE", " ", _update_screens=False)
                        textbutton "." style "keyquest_deck_key" action Function(_keyquest_press, "PERIOD", ".", _update_screens=False)
                        textbutton "-" style "keyquest_deck_key" action Function(_keyquest_press, "MINUS", "-", _update_screens=False)
                        textbutton "_" style "keyquest_deck_key" action Function(_keyquest_press, "MINUS", "_", _update_screens=False)
                        textbutton "⌫" style "keyquest_deck_key" alt "Backspace" action Function(_keyquest_press, "BACKSPACE", _update_screens=False)
                        textbutton "Enter" style "keyquest_deck_accent" action Function(_keyquest_press, "RETURN", _update_screens=False)
