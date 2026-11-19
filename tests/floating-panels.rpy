init python:
    def _kq_find_drag(displayable, name):
        if getattr(displayable, "drag_name", None) == name:
            return displayable
        for child in displayable.visit():
            if child is not None:
                match = _kq_find_drag(child, name)
                if match is not None:
                    return match
        return None

    def _kq_panel(screen, name):
        drag = _kq_find_drag(renpy.get_screen(screen), "keyquest-" + name)
        assert drag is not None and drag.x is not None, name
        return drag

    def _kq_mouse(kind, x, y):
        import pygame
        physical = tuple(map(int, renpy.display.draw.untranslate_point(x, y)))
        pygame.mouse.set_pos(physical)
        if kind is not None:
            pygame.event.post(pygame.event.Event(kind, button=1, pos=physical, touch=False, which=0))

    def _kq_message_during_ocr_drag():
        assert _keyquest_panel_grabbed()
        state = _keyquest_scan_state
        _keyquest_vision.response = (state.request, "3+4=?", None)
        _keyquest_watch_tick()
        assert state.watch_value is None and state.watch_paused

label start:
    $ import pygame
    $ persistent.keyquest_panel_positions = {}
    $ renpy.pause(0.15, hard=True)
    $ launcher = _kq_panel("_keyquest_launcher", "launcher")
    $ _kq_mouse(None, launcher.x + 75, launcher.y + 25)
    $ renpy.pause(0.12, hard=True)
    $ _kq_mouse(pygame.MOUSEBUTTONDOWN, launcher.x + 75, launcher.y + 25)
    $ renpy.pause(0.12, hard=True)
    $ _kq_mouse(pygame.MOUSEBUTTONUP, launcher.x + 75, launcher.y + 25)
    $ renpy.pause(0.12, hard=True)
    $ assert renpy.get_screen("_keyquest_keyboard") is not None
    hide screen _keyquest_keyboard

    show screen _keyquest_smart_input
    $ renpy.pause(0.15, hard=True)
    $ panel = _kq_panel("_keyquest_smart_input", "ocr-setup")
    $ x, y = panel.x + 30, panel.y + 25
    show screen _kq_test_drag_stroke(x, y)
    $ renpy.pause(0.70, hard=True)
    hide screen _kq_test_drag_stroke
    $ assert "keyquest-ocr-setup" in persistent.keyquest_panel_positions
    $ panel = _kq_panel("_keyquest_smart_input", "ocr-setup")
    $ stored = (panel.x, panel.y)
    $ assert abs(stored[0] - (x + 25)) <= 1 and abs(stored[1] - (y + 15)) <= 1, stored
    hide screen _keyquest_smart_input
    $ renpy.pause(0.12, hard=True)
    show screen _keyquest_smart_input
    $ renpy.pause(0.12, hard=True)
    $ panel = _kq_panel("_keyquest_smart_input", "ocr-setup")
    $ assert (panel.x, panel.y) == stored
    python:
        # Simulate a previous screen instance still holding the pointer.
        guard = _KeyquestDragGuard()
        renpy.display.focus.set_grab(panel)
        guard.event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1), 0, 0, 0)
        assert _keyquest_panel_grabbed()
        guard.event(pygame.event.Event(pygame.MOUSEMOTION), 0, 0, 0)
        assert not _keyquest_panel_grabbed()
        renpy.display.focus.set_grab(panel)
        guard.event(pygame.event.Event(pygame.ACTIVEEVENT, gain=0, state=1), 0, 0, 0)
        assert not _keyquest_panel_grabbed()
    $ _kq_mouse(None, panel.x + 150, panel.y + 77)
    $ renpy.pause(0.12, hard=True)
    $ _kq_mouse(pygame.MOUSEBUTTONDOWN, panel.x + 150, panel.y + 77)
    $ renpy.pause(0.12, hard=True)
    $ _kq_mouse(pygame.MOUSEBUTTONUP, panel.x + 150, panel.y + 77)
    $ renpy.pause(0.12, hard=True)
    $ assert renpy.get_screen("_keyquest_smart_input").scope["mode"] == "math"
    hide screen _keyquest_smart_input

    show screen _keyquest_ocr_result(mode="math", region="full", result="42")
    $ renpy.pause(0.12, hard=True)
    $ _kq_panel("_keyquest_ocr_result", "ocr-result")
    hide screen _keyquest_ocr_result
    $ _keyquest_scan_state.started = _kq_time.time()
    show screen _keyquest_ocr_wait
    $ renpy.pause(0.12, hard=True)
    $ _kq_panel("_keyquest_ocr_wait", "ocr-wait")
    hide screen _keyquest_ocr_wait
    $ _keyquest_scan_state.next_scan = _kq_time.time() + 10
    $ _keyquest_scan_state.watch = "math"
    show screen _keyquest_live_ocr
    $ renpy.pause(0.12, hard=True)
    $ panel = _kq_panel("_keyquest_live_ocr", "ocr-live")
    $ _keyquest_vision.busy = True
    $ original_request = _keyquest_scan_state.request
    show screen _kq_test_drag_stroke(panel.x + 30, panel.y + 25, live=True)
    $ renpy.pause(0.85, hard=True)
    hide screen _kq_test_drag_stroke
    $ assert "keyquest-ocr-live" in persistent.keyquest_panel_positions
    $ assert not _keyquest_panel_grabbed() and not _keyquest_scan_state.watch_paused
    $ assert _keyquest_scan_state.request > original_request and _keyquest_scan_state.watch_value is None
    $ _keyquest_vision.response = (_keyquest_scan_state.request, "6*7=?", None)
    $ renpy.pause(0.25, hard=True)
    $ assert _keyquest_scan_state.watch_value == "42"
    $ _keyquest_vision.busy = False
    $ _keyquest_ocr_reset()
    $ _keyquest_start_repeat(("s",), 1, 10, "full")
    $ renpy.pause(0.12, hard=True)
    $ _kq_panel("_keyquest_repeat_runner", "repeat-runner")
    $ _keyquest_ocr_reset()

    show screen _keyquest_values
    $ renpy.pause(0.12, hard=True)
    $ _kq_panel("_keyquest_values", "values")
    hide screen _keyquest_values
    show screen _keyquest_automation
    $ renpy.pause(0.12, hard=True)
    $ _kq_panel("_keyquest_automation", "automation")
    hide screen _keyquest_automation
    show screen _keyquest_pick_target
    $ renpy.pause(0.12, hard=True, modal=False)
    $ _kq_panel("_keyquest_pick_target", "click-target")
    hide screen _keyquest_pick_target
    $ _keyquest_task = ("macro", ("s",), 0, 10)
    show screen _keyquest_runner
    $ renpy.pause(0.12, hard=True)
    $ _kq_panel("_keyquest_runner", "automation-runner")
    $ _keyquest_stop_task()
    $ _keyquest_reset_panels()
    $ assert not persistent.keyquest_panel_positions
    $ print("Keyquest floating panel drag, release recovery, and launcher checks passed.")
    $ renpy.quit()

screen _kq_test_drag_stroke(x, y, live=False):
    timer 0.05 action Function(_kq_mouse, None, x, y, _update_screens=False)
    timer 0.2 action Function(_kq_mouse, pygame.MOUSEBUTTONDOWN, x, y, _update_screens=False)
    if live:
        timer 0.3 action Function(_kq_message_during_ocr_drag, _update_screens=False)
    timer 0.35 action Function(_kq_mouse, None, x + 55, y + 40, _update_screens=False)
    timer 0.5 action Function(_kq_mouse, pygame.MOUSEBUTTONUP, x + 55, y + 40, _update_screens=False)
