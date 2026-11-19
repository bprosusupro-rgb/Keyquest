init 999 python:
    import pygame
    pygame.display.init()
    pygame.event.clear()
    for keyquest_name, keyquest_text in (("s", "s"), ("i", "i"), ("RETURN", ""), ("BACKSPACE", "")):
        _keyquest_press(keyquest_name, keyquest_text)
        keyquest_events = [ev for ev in pygame.event.get()
                           if ev.type in (pygame.KEYDOWN, pygame.KEYUP)]
        assert len(keyquest_events) == 2
        assert renpy.map_event(keyquest_events[0], "K_" + keyquest_name)
        assert renpy.map_event(keyquest_events[1], "keyup_K_" + keyquest_name)
        assert keyquest_events[0].unicode == keyquest_text
        assert keyquest_events[1].unicode == ""
    print("Keyquest key-down and key-up regression passed.")

label start:
    return
