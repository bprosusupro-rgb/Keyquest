# Add this file to the game/ directory of a Ren'Py project you can modify.

init python:
    def _keyquest_press(name, text=""):
        import pygame
        key = getattr(pygame, "K_" + name)
        mods = pygame.KMOD_SHIFT if text and text.isupper() else 0
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, key=key, mod=mods, unicode=text, repeat=False))
        pygame.event.post(pygame.event.Event(
            pygame.KEYUP, key=key, mod=mods, unicode=""))

    _keyquest_screens = getattr(config, "always_shown_screens", config.overlay_screens)
    if "_keyquest_launcher" not in _keyquest_screens:
        _keyquest_screens.append("_keyquest_launcher")

default persistent.keyquest_top = False
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
    button:
        align (0.98, 0.95)
        background Frame("keyquest_panel.png", 24, 24)
        hover_background Frame("keyquest_panel_mint.png", 24, 24)
        padding (8, 6)
        action ToggleScreen("_keyquest_keyboard")
        alt "Keyquest keyboard"
        alternate (ToggleScreen("_keyquest_values") if renpy.has_screen("_keyquest_values") else NullAction())
        hbox:
            spacing 7
            if renpy.loadable("keyquest_logo.png"):
                add "keyquest_logo.png" xysize (48, 48) yalign 0.5
            text "Keyboard" color "#eff8ff" size 22 yalign 0.5

screen _keyquest_keyboard():
    zorder 991
    default caps = False
    default settings_open = False
    default editing_slot = 1
    frame:
        background Frame("keyquest_panel_mint.png" if persistent.keyquest_light_accent else "keyquest_panel.png", 24, 24)
        at Transform(zoom=min(1.0, config.screen_width / 650.0) * (0.78 if persistent.keyquest_compact else 1.0))
        padding (18, 16)
        align (0.5, 0.96 if not persistent.keyquest_top else 0.12)
        vbox:
            spacing 8
            text ("Keyboard settings" if settings_open else "Keyboard") color "#eff8ff" size 26
            hbox:
                spacing 6
                for quick in (persistent.keyquest_quick_one, persistent.keyquest_quick_two):
                    textbutton quick.upper() style "keyquest_key" action Function(_keyquest_press, quick, quick, _update_screens=False)
                if renpy.has_screen("_keyquest_values"):
                    textbutton "Values" style "keyquest_key" action [Hide("_keyquest_keyboard"), ToggleScreen("_keyquest_values")]
                if renpy.has_screen("_keyquest_automation"):
                    textbutton "Macros" style "keyquest_key" action [Hide("_keyquest_keyboard"), Show("_keyquest_automation")]
                textbutton "Settings" style "keyquest_key" action ToggleScreenVariable("settings_open")
                textbutton "Close" style "keyquest_key" action Hide("_keyquest_keyboard")
            if settings_open:
                hbox:
                    spacing 6
                    textbutton ("Dock bottom" if persistent.keyquest_top else "Dock top") style "keyquest_key" action ToggleField(persistent, "keyquest_top")
                    textbutton ("Full size" if persistent.keyquest_compact else "Compact") style "keyquest_key" action ToggleField(persistent, "keyquest_compact")
                    textbutton "Theme" style "keyquest_key" action ToggleField(persistent, "keyquest_light_accent")
                hbox:
                    spacing 6
                    textbutton "Edit shortcut 1" style "keyquest_key" action SetScreenVariable("editing_slot", 1)
                    textbutton "Edit shortcut 2" style "keyquest_key" action SetScreenVariable("editing_slot", 2)
                text "Tap a letter or digit to set shortcut [editing_slot]." color "#f3fffa" size 20
            for row in ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"):
                hbox:
                    spacing 5
                    for letter in row:
                        $ caption = letter.upper() if caps else letter
                        textbutton caption:
                            style "keyquest_key"
                            action (SetField(persistent, "keyquest_quick_one" if editing_slot == 1 else "keyquest_quick_two", letter) if settings_open else Function(_keyquest_press, letter, caption, _update_screens=False))
            hbox:
                spacing 6
                textbutton "Shift" style "keyquest_key" action SetScreenVariable("caps", not caps)
                textbutton "Space" style "keyquest_key" action Function(_keyquest_press, "SPACE", " ", _update_screens=False)
                textbutton "." style "keyquest_key" action Function(_keyquest_press, "PERIOD", ".", _update_screens=False)
                textbutton "-" style "keyquest_key" action Function(_keyquest_press, "MINUS", "-", _update_screens=False)
                textbutton "_" style "keyquest_key" action Function(_keyquest_press, "MINUS", "_", _update_screens=False)
                textbutton "Backspace" style "keyquest_key" action Function(_keyquest_press, "BACKSPACE", _update_screens=False)
                textbutton "Enter" style "keyquest_key" action Function(_keyquest_press, "RETURN", _update_screens=False)
