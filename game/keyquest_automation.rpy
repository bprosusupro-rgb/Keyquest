# Optional, local Ren'Py automation. Jobs run only after Start and stop on load.

default persistent.keyquest_macro = ("s", "i")
default persistent.keyquest_macro_delay = 0.2
default persistent.keyquest_macro_loops = 1
default persistent.keyquest_click_delay = 0.5
default persistent.keyquest_click_count = 10
default _keyquest_click_point = None
default _keyquest_task = None

init python:
    def _keyquest_cycle(value, options):
        return options[(options.index(value) + 1) % len(options)] if value in options else options[0]

    def _keyquest_add_step(value):
        if len(persistent.keyquest_macro) < 24:
            persistent.keyquest_macro = persistent.keyquest_macro + (value,)

    def _keyquest_stop_task():
        renpy.store._keyquest_task = None
        renpy.hide_screen("_keyquest_runner")

    config.after_load_callbacks.append(_keyquest_stop_task)

    def _keyquest_begin_task(mode):
        if mode == "macro":
            sequence = tuple(persistent.keyquest_macro) * persistent.keyquest_macro_loops
            if not sequence:
                return
            delay = persistent.keyquest_macro_delay
        else:
            if _keyquest_click_point is None:
                return
            sequence = (_keyquest_click_point,) * persistent.keyquest_click_count
            delay = persistent.keyquest_click_delay

        renpy.store._keyquest_task = (mode, sequence, 0, delay)
        renpy.hide_screen("_keyquest_automation")
        renpy.show_screen("_keyquest_runner")

    def _keyquest_click(x, y):
        import pygame
        px, py = renpy.display.draw.untranslate_point(x, y)
        position = (int(px), int(py))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=position, touch=False, which=0))

    def _keyquest_tick():
        if _keyquest_task is None:
            _keyquest_stop_task()
            return
        mode, sequence, index, delay = _keyquest_task
        step = sequence[index]
        if mode == "click":
            _keyquest_click(*step)
        elif step != "wait":
            _keyquest_press(step, " " if step == "SPACE" else step)
        if index + 1 == len(sequence):
            _keyquest_stop_task()
            renpy.restart_interaction()
        else:
            renpy.store._keyquest_task = (mode, sequence, index + 1, delay)

    class _KeyquestTarget(renpy.Displayable):
        def render(self, width, height, st, at):
            return renpy.Render(config.screen_width, config.screen_height)

        def event(self, ev, x, y, st):
            import pygame
            if ev.type == pygame.MOUSEBUTTONUP and getattr(ev, "button", 0) == 1:
                if 0 <= x < config.screen_width and 0 <= y < config.screen_height:
                    renpy.store._keyquest_click_point = (int(x), int(y))
                    renpy.hide_screen("_keyquest_pick_target")
                    renpy.show_screen("_keyquest_automation", initial_mode="click")
                    renpy.restart_interaction()
                raise renpy.IgnoreEvent()
            if ev.type == pygame.MOUSEBUTTONDOWN and getattr(ev, "button", 0) == 1:
                raise renpy.IgnoreEvent()

screen _keyquest_automation(initial_mode="macro"):
    default mode = initial_mode
    zorder 993
    use _keyquest_floating("automation", "Automation", 710, 515, (0.5, 0.4)):
        hbox:
            spacing 8
            textbutton "Macro writer" style "keyquest_key" action SetScreenVariable("mode", "macro")
            textbutton "Auto-clicker" style "keyquest_key" action SetScreenVariable("mode", "click")
            textbutton "Close" style "keyquest_key" action Hide("_keyquest_automation")
        if mode == "macro":
            $ sequence = "  ".join("Wait" if key == "wait" else key.title() for key in persistent.keyquest_macro)
            text (sequence or "No steps yet.") color "#eff8ff" size 22 xmaximum 630
            for row in ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"):
                hbox:
                    spacing 5
                    for value in row:
                        textbutton value.upper() style "keyquest_key" action Function(_keyquest_add_step, value)
            hbox:
                spacing 6
                textbutton "Space" style "keyquest_key" action Function(_keyquest_add_step, "SPACE")
                textbutton "Wait" style "keyquest_key" action Function(_keyquest_add_step, "wait")
                textbutton "Undo" style "keyquest_key" action SetField(persistent, "keyquest_macro", persistent.keyquest_macro[:-1])
                textbutton "Clear" style "keyquest_key" action SetField(persistent, "keyquest_macro", ())
            hbox:
                spacing 6
                textbutton ("%.2f s / step" % persistent.keyquest_macro_delay) style "keyquest_key" action SetField(persistent, "keyquest_macro_delay", _keyquest_cycle(persistent.keyquest_macro_delay, (0.1, 0.2, 0.5, 1.0)))
                textbutton ("%d repeats" % persistent.keyquest_macro_loops) style "keyquest_key" action SetField(persistent, "keyquest_macro_loops", _keyquest_cycle(persistent.keyquest_macro_loops, (1, 3, 10)))
                textbutton "Start" style "keyquest_key" sensitive bool(persistent.keyquest_macro) action Function(_keyquest_begin_task, "macro")
        else:
            $ target_text = "No target selected" if _keyquest_click_point is None else "Target: %d, %d" % _keyquest_click_point
            text target_text color "#eff8ff" size 22
            hbox:
                spacing 6
                textbutton "Pick target" style "keyquest_key" action [Hide("_keyquest_automation"), Show("_keyquest_pick_target")]
                textbutton ("%.2f s / click" % persistent.keyquest_click_delay) style "keyquest_key" action SetField(persistent, "keyquest_click_delay", _keyquest_cycle(persistent.keyquest_click_delay, (0.2, 0.5, 1.0, 2.0)))
                textbutton ("%d clicks" % persistent.keyquest_click_count) style "keyquest_key" action SetField(persistent, "keyquest_click_count", _keyquest_cycle(persistent.keyquest_click_count, (5, 10, 25, 50)))
            textbutton "Start" style "keyquest_key" sensitive (_keyquest_click_point is not None) action Function(_keyquest_begin_task, "click")

screen _keyquest_pick_target():
    zorder 994
    modal True
    add _KeyquestTarget()
    use _keyquest_floating("click-target", "Pick a target", 535, 140, (0.5, 0.05)):
        hbox:
            spacing 12
            text "Tap the point you want to repeat." color "#eff8ff" size 22 yalign 0.5
            textbutton "Cancel" style "keyquest_key" action [Hide("_keyquest_pick_target"), Show("_keyquest_automation", initial_mode="click")]

screen _keyquest_runner():
    zorder 995
    if _keyquest_task is not None:
        $ stop_x = 0.98 if _keyquest_click_point is None or _keyquest_click_point[0] < config.screen_width / 2 else 0.02
        use _keyquest_floating("automation-runner", "Automation running", 430, 136, (stop_x, 0.04)):
            textbutton "Stop automation" style "keyquest_key" action Function(_keyquest_stop_task)
        timer _keyquest_task[3] repeat True modal True action Function(_keyquest_tick, _update_screens=False)
