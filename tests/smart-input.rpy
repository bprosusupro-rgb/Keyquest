init 999 python:
    import pygame
    pygame.display.init()
    pygame.event.clear()
    for sample, answer in (
            (u"25+17=?", "42"), (u"(12 − 4) × 3 = ?", "24"), (u"7 ÷ 2 = ?", "3.5"),
            (u"007 + 05", "12"), (u"9 - 9 = ?", "0"), ("1 / 3", "0.333333"), ("-1 / 1000000000", "0"),
            ("2**6", None), ("8//2", None), ("2/0", None), ("1+2\n5+7", None),
            ("4*500000000", None), ("print(1)", None)):
        assert _keyquest_math_answer(sample) == answer, (sample, _keyquest_math_answer(sample))
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
    $ _keyquest_repeat_left = 3
    show screen _keyquest_repeat_runner(key="s", interval=0.1)
    $ renpy.pause(2.0, hard=True)
    $ assert _keyquest_repeat_left == 0
    $ assert renpy.get_screen("_keyquest_repeat_runner") is None
    $ print("Keyquest Smart Input render and repeat timer tests passed.")
    show screen _keyquest_test_typing
    $ actual = renpy.input("Test in-game OCR text")
    $ assert actual == u"Keyquest café 42", actual
    $ print("Keyquest text reached the active game field.")
    $ renpy.quit()

screen _keyquest_test_typing():
    timer 0.25 action Function(_keyquest_insert_text, u"Keyquest café 42", _update_screens=False)
    timer 0.75 action Function(_keyquest_press, "RETURN", _update_screens=False)
