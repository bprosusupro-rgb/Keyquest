init 999 python:
    import pygame
    pygame.display.init()
    pygame.event.clear()
    for sample, answer in (
            (u"25+17=?", "42"), (u"(12 − 4) × 3 = ?", "24"), (u"7 ÷ 2 = ?", "3.5"),
            (u"3.X-5?", "-15"), (u"3 X -5 ?", "-15"), (u"007 + 05", "12"), (u"9 - 9 = ?", "0"), ("1 / 3", "0.333333"), ("-1 / 1000000000", "0"),
            ("2**6", None), ("8//2", None), ("2/0", None), ("1+2\n5+7", None),
            ("4*500000000", None), ("print(1)", None)):
        assert _keyquest_math_answer(sample) == answer, (sample, _keyquest_math_answer(sample))
    assert _keyquest_math_answer("3.X-5?", True) == "-15"
    assert _keyquest_math_answer("3.X-57", True) is None
    assert _keyquest_read_key_cue(u"Press S and I rapidly!") == ("s", "i")
    assert _keyquest_read_key_cue(u"Press S and | rapidly!") == ("s", "i")
    assert _keyquest_read_key_cue(u"Alternate between [S] and [I] rapidly!") == ("s", "i")
    assert _keyquest_read_key_cue(u"Tap “S” then “I”") == ("s", "i")
    assert _keyquest_read_key_cue(u"Keys: A → Enter, A") == ("a", "RETURN", "a")
    assert _keyquest_read_key_cue(u"Press Space to continue") == ("SPACE",)
    assert _keyquest_read_key_cue(u"Press S\nPress I") is None
    assert _keyquest_read_key_cue(u"Press any key") is None
    phrase = u"Hello from Keyquest! " * 5 + u"café"
    _keyquest_insert_text(phrase)
    posted = [ev.text for ev in pygame.event.get() if ev.type == pygame.TEXTINPUT]
    assert u"".join(posted) == phrase, posted
    assert all(len(part.encode("utf-8")) <= 30 for part in posted)
    print("Keyquest math and SDL text event tests passed.")

label start:
    show screen _keyquest_keyboard
    $ renpy.pause(0.15, hard=True)
    hide screen _keyquest_keyboard
    show screen _keyquest_smart_input(initial_mode="repeat")
    $ renpy.pause(0.15, hard=True)
    hide screen _keyquest_smart_input
    show screen _keyquest_smart_input(initial_mode="math", status="Sample error.")
    $ renpy.pause(0.15, hard=True)
    hide screen _keyquest_smart_input
    python:
        _keyquest_scan_state.started = _kq_time.time()
        _keyquest_scan_state.mode = "math"
        _keyquest_scan_state.destination = "show"
        _keyquest_scan_state.response = (_keyquest_scan_state.request, "25 + 17 = ?", None)
        _keyquest_ocr_poll()
        assert not any(ev.type == pygame.TEXTINPUT for ev in pygame.event.get())
    $ renpy.pause(0.15, hard=True)
    $ assert renpy.get_screen("_keyquest_ocr_result").scope["result"] == "42"
    hide screen _keyquest_ocr_result
    python:
        _keyquest_scan_state.started = _kq_time.time()
        _keyquest_scan_state.mode = "keys"
        _keyquest_scan_state.region = "top"
        _keyquest_scan_state.repeat_settings = (("q",), 3, 0.15)
        _keyquest_scan_state.response = (_keyquest_scan_state.request, "Press S and I rapidly!", None)
        _keyquest_ocr_poll()
        assert _keyquest_repeat_job is None
    $ renpy.pause(0.15, hard=True)
    $ assert renpy.get_screen("_keyquest_smart_input").scope["sequence"] == ("s", "i")
    hide screen _keyquest_smart_input
    $ observed_keys = []
    show screen _keyquest_test_key_order
    $ _keyquest_start_repeat(("s", "i", "s"), 2, 0.1, "full")
    $ renpy.pause(2.0, hard=True)
    $ assert _keyquest_repeat_job is None
    $ assert observed_keys == ["s", "i", "s", "s", "i", "s"], observed_keys
    $ assert renpy.get_screen("_keyquest_repeat_runner") is None
    hide screen _keyquest_test_key_order
    python:
        _keyquest_scan_state.watch = "keys"
        _keyquest_watch_apply(u"Press S and I rapidly!", 1.0)
        assert _keyquest_scan_state.watch_value == ("s", "i")
        _keyquest_scan_state.watch_index = 1
        _keyquest_watch_apply(u"Press S and I rapidly!", 1.5)
        assert _keyquest_scan_state.watch_index == 1
        _keyquest_watch_apply(u"Press A then D", 2.0)
        assert _keyquest_scan_state.watch_value == ("a", "d")
        assert _keyquest_scan_state.watch_index == 0
        _keyquest_watch_apply(u"Wait for the next round", 2.5)
        assert _keyquest_scan_state.watch_value is None
        _keyquest_scan_state.watch = "math"
        _keyquest_watch_apply(u"4 * 5 = ?", 3.0)
        assert _keyquest_scan_state.watch_value == "20"
        _keyquest_watch_apply(u"5 + 1 = ?", 3.5)
        assert _keyquest_scan_state.watch_value == "6"
        _keyquest_ocr_reset()
    $ print("Keyquest Smart Input render and repeat timer tests passed.")
    show screen _keyquest_test_typing
    $ actual = renpy.input("Test in-game OCR text")
    $ assert actual == u"Keyquest café 42", actual
    $ print("Keyquest text reached the active game field.")
    $ renpy.quit()

init python:
    def _keyquest_test_type_result():
        _keyquest_scan_state.started = _kq_time.time()
        _keyquest_scan_state.mode = "text"
        _keyquest_scan_state.destination = "type"
        _keyquest_scan_state.response = (_keyquest_scan_state.request, u"Keyquest café 42", None)
        _keyquest_ocr_poll()

screen _keyquest_test_typing():
    timer 0.25 action Function(_keyquest_test_type_result, _update_screens=False)
    timer 0.75 action Function(_keyquest_press, "RETURN", _update_screens=False)

screen _keyquest_test_key_order():
    key "K_s" action Function(observed_keys.append, "s", _update_screens=False)
    key "K_i" action Function(observed_keys.append, "i", _update_screens=False)
