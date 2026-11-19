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

    if "_keyquest_launcher" not in config.overlay_screens:
        config.overlay_screens.append("_keyquest_launcher")

style keyquest_key is button:
    background Solid("#263950")
    hover_background Solid("#406677")
    padding (14, 9)
    yminimum 44

style keyquest_key_text is button_text:
    color "#f3fffa"
    size 24

screen _keyquest_launcher():
    zorder 990
    textbutton "Keyboard":
        style "keyquest_key"
        align (0.99, 0.04)
        action ToggleScreen("_keyquest_keyboard")

screen _keyquest_keyboard():
    zorder 991
    default caps = False
    default upper = False
    frame:
        background Solid("#101e2af5")
        padding (16, 12)
        align (0.5, 0.96 if not upper else 0.06)
        vbox:
            spacing 6
            hbox:
                spacing 6
                textbutton "S" style "keyquest_key" action Function(_keyquest_press, "s", "s", _update_screens=False)
                textbutton "I" style "keyquest_key" action Function(_keyquest_press, "i", "i", _update_screens=False)
                textbutton "Move" style "keyquest_key" action SetScreenVariable("upper", not upper)
                textbutton "Close" style "keyquest_key" action Hide("_keyquest_keyboard")
            for row in ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"):
                hbox:
                    spacing 5
                    for letter in row:
                        $ caption = letter.upper() if caps else letter
                        textbutton caption:
                            style "keyquest_key"
                            action Function(_keyquest_press, letter, caption, _update_screens=False)
            hbox:
                spacing 6
                textbutton "Shift" style "keyquest_key" action SetScreenVariable("caps", not caps)
                textbutton "Space" style "keyquest_key" action Function(_keyquest_press, "SPACE", " ", _update_screens=False)
                textbutton "Backspace" style "keyquest_key" action Function(_keyquest_press, "BACKSPACE", _update_screens=False)
                textbutton "Enter" style "keyquest_key" action Function(_keyquest_press, "RETURN", _update_screens=False)
