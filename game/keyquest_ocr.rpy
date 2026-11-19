# Optional on-device screen reading and repeat keys for Ren'Py 7.8 and 8.0–8.5.

init python:
    import ast as _kq_ast
    import re as _kq_re
    import time as _kq_time

    class _KeyquestScanState(object):
        request = 0
        started = 0.0
        response = None
        bridge = None
        mode = "text"
        region = "full"
        destination = "show"
        repeat_settings = ((), 3, 0.15)
        native = False
        activity = None
        watch = None
        watch_value = None
        watch_index = 0
        watch_confirmed = 0.0
        next_scan = 0.0

    _keyquest_scan_state = _KeyquestScanState()

    def _keyquest_math_value(node):
        if isinstance(node, _kq_ast.Num):
            result = node.n
        elif isinstance(node, _kq_ast.UnaryOp) and isinstance(node.op, (_kq_ast.UAdd, _kq_ast.USub)):
            result = _keyquest_math_value(node.operand)
            if isinstance(node.op, _kq_ast.USub):
                result = -result
        elif isinstance(node, _kq_ast.BinOp):
            left = _keyquest_math_value(node.left)
            right = _keyquest_math_value(node.right)
            if isinstance(node.op, _kq_ast.Add):
                result = left + right
            elif isinstance(node.op, _kq_ast.Sub):
                result = left - right
            elif isinstance(node.op, _kq_ast.Mult):
                result = left * right
            elif isinstance(node.op, _kq_ast.Div):
                result = float(left) / right
            else:
                raise ValueError("Unsupported operator")
        else:
            raise ValueError("Unsupported expression")
        if not -1000000000 <= result <= 1000000000:
            raise ValueError("Arithmetic limit")
        return result

    def _keyquest_math_answer(text, require_prompt=False):
        replacements = ((u"×", "*"), (u"÷", "/"), (u"−", "-"), (u"–", "-"))
        for before, after in replacements:
            text = text.replace(before, after)
        candidates = set()
        for line in text.splitlines():
            line = line.strip()
            if require_prompt and not line.endswith(("?", "=")):
                continue
            line = _kq_re.sub(r"(?<=[\d.)])\s*[xX]\s*(?=[+\-\d.(])", "*", line)
            expression = _kq_re.sub(r"\s*(?:=\s*\??|\?)\s*$", "", line).strip()
            if (len(expression) <= 64 and _kq_re.match(r"^[0-9.()+*/ \t-]+\Z", expression)
                    and _kq_re.search(r"[\d.)]\s*[+*/-]", expression)):
                candidates.add(expression)
        if len(candidates) != 1:
            return None
        try:
            expression = candidates.pop()
            # Strip integer leading zeros, preserving decimal fractions and trailing zeros.
            expression = _kq_re.sub(r"(?<![\d.])0+(?=\d)", "", expression)
            result = _keyquest_math_value(_kq_ast.parse(expression, mode="eval").body)
        except (ArithmeticError, SyntaxError, ValueError):
            return None
        formatted = ("%.6f" % result).rstrip("0").rstrip(".")
        return "0" if formatted == "-0" else formatted

    def _keyquest_read_key_cue(text):
        cues = set()
        for line in text.splitlines():
            match = _kq_re.match(r"^\s*(?:(?:press|tap|alternate(?:\s+between)?)\b|keys?\s*:)\s*(.+)$", line, _kq_re.I)
            if not match:
                continue
            cue = _kq_re.split(r"\s+(?:rapidly|quickly|repeatedly|now|to)\b", match.group(1), 1, flags=_kq_re.I)[0]
            cue = cue.strip(" .!:").lower().replace(u"→", ",")
            cue = cue.replace("[", "").replace("]", "").replace('"', "").replace(u"“", "").replace(u"”", "")
            tokens = _kq_re.split(r"\s*(?:[,/+&]|\band\b|\bthen\b)\s*|\s+", cue)
            tokens = tuple({"space": "SPACE", "enter": "RETURN", "|": "i"}.get(token, token) for token in tokens if token)
            if 0 < len(tokens) <= 12 and all(
                    token in ("SPACE", "RETURN") or _kq_re.match(r"^[a-z0-9]\Z", token) for token in tokens):
                cues.add(tokens)
        return cues.pop() if len(cues) == 1 else None

    def _keyquest_ocr_reset():
        state = _keyquest_scan_state
        state.request += 1
        state.response = None
        state.bridge = None
        state.native = False
        state.activity = None
        state.watch = None
        state.watch_value = None
        renpy.store._keyquest_repeat_job = None
        for panel in ("_keyquest_ocr_capture", "_keyquest_ocr_wait", "_keyquest_ocr_result", "_keyquest_repeat_runner", "_keyquest_live_ocr"):
            renpy.hide_screen(panel)

    config.after_load_callbacks.append(_keyquest_ocr_reset)

    def _keyquest_ocr_begin(mode, region, destination="show", repeat_settings=((), 3, 0.15)):
        _keyquest_ocr_reset()
        state = _keyquest_scan_state
        state.started = _kq_time.time()
        state.mode = mode
        state.region = region
        state.destination = destination
        state.repeat_settings = repeat_settings
        renpy.hide_screen("_keyquest_smart_input")
        if not renpy.android:
            _keyquest_ocr_return("Screen scanning is available in the Android game.")
            return
        renpy.show_screen("_keyquest_ocr_capture")

    def _keyquest_ocr_return(message, keys=None):
        state = _keyquest_scan_state
        sequence, loops, interval = state.repeat_settings
        _keyquest_ocr_reset()
        renpy.show_screen("_keyquest_smart_input", initial_mode="repeat" if state.mode == "keys" else state.mode,
                          initial_region=state.region, initial_destination=state.destination,
                          initial_repeat=(sequence if keys is None else keys, loops, interval), status=message)
        renpy.restart_interaction()

    def _keyquest_submit_local(mode, region):
        from jnius import autoclass

        state = _keyquest_scan_state
        if state.activity is None:
            state.activity = autoclass("org.renpy.android.PythonSDLActivity").mActivity
        if not state.activity.hasWindowFocus() or _keyquest_vision.busy:
            return False
        detailed = region in ("race", "bottom")
        size = _keyquest_capture_size(960 if state.watch and not detailed else 1440, detailed)
        frame = renpy.screenshot_to_bytes(size)
        if not frame:
            return False
        return _keyquest_vision.start(state.request, frame, region, mode,
                                      state.activity.getCodeCacheDir().getAbsolutePath())

    def _keyquest_capture_size(maximum, allow_upscale=False):
        width, height = config.screen_width, config.screen_height
        scale = min(float(maximum) / max(width, height), (1550000.0 / (width * height)) ** 0.5)
        if not allow_upscale:
            scale = min(1.0, scale)
        return (max(1, int(width * scale)), max(1, int(height * scale)))

    def _keyquest_ocr_capture_frame():
        state = _keyquest_scan_state
        renpy.hide_screen("_keyquest_ocr_capture")
        if not _keyquest_vision.unavailable and renpy.loadable("keyquest_vision.zip"):
            try:
                state.native = _keyquest_submit_local(state.mode, state.region)
            except Exception as error:
                renpy.log("Keyquest local OCR: " + repr(error))
            if state.native:
                renpy.show_screen("_keyquest_ocr_wait")
                return
        try:
            from jnius import autoclass, PythonJavaClass, java_method

            request = state.request

            class Reply(PythonJavaClass):
                __javainterfaces__ = ["android/os/Handler$Callback"]

                @java_method("(Landroid/os/Message;)Z")
                def handleMessage(self, message):
                    data = message.getData()
                    if request == state.request:
                        state.response = (request, data.getString("text"), data.getString("error"))
                    return True

            activity = autoclass("org.renpy.android.PythonSDLActivity").mActivity
            callback = Reply()
            handler = autoclass("android.os.Handler")(autoclass("android.os.Looper").getMainLooper(), callback)
            messenger = autoclass("android.os.Messenger")(handler)
            state.bridge = (callback, handler, messenger, activity)

            frame = renpy.screenshot_to_bytes(_keyquest_capture_size(1440, state.region in ("race", "bottom")))
            if not frame:
                raise ValueError("No game frame")
            bitmap = autoclass("android.graphics.BitmapFactory").decodeByteArray(frame, 0, len(frame))
            if bitmap is None:
                raise ValueError("Frame could not be decoded")
            crop = bitmap
            try:
                width, height = bitmap.getWidth(), bitmap.getHeight()
                area = _keyquest_ocr_crop(width, height, state.region)
                if area is not None:
                    crop = autoclass("android.graphics.Bitmap").createBitmap(bitmap, *area)
                stream = autoclass("java.io.ByteArrayOutputStream")()
                formats = autoclass("android.graphics.Bitmap$CompressFormat")
                encodings = [(formats.JPEG, quality) for quality in (92, 76, 58, 40)]
                if state.region == "race":
                    encodings.insert(0, (formats.PNG, 100))
                for encoding, quality in encodings:
                    stream.reset()
                    if crop.compress(encoding, quality, stream) and stream.size() <= 400 * 1024:
                        break
                else:
                    raise ValueError("Frame is too large")

                extras = autoclass("android.os.Bundle")()
                extras.putByteArray("image", stream.toByteArray())
                extras.putParcelable("reply", messenger)
                extras.putBoolean("math", state.mode in ("math", "keys"))
                extras.putBoolean("race", state.region == "race" and state.mode == "keys")
                intent = autoclass("android.content.Intent")()
                intent.setClassName("org.keyquest.studio", "org.keyquest.studio.OcrActivity")
                intent.addFlags(0x10000)  # FLAG_ACTIVITY_NO_ANIMATION
                intent.putExtras(extras)
                activity.startActivity(intent)
            finally:
                if crop is not bitmap:
                    crop.recycle()
                bitmap.recycle()
        except Exception as error:
            renpy.log("Keyquest OCR bridge: " + repr(error))
            _keyquest_ocr_return("Could not start OCR. Update Keyquest Studio and try again.")
            return
        renpy.show_screen("_keyquest_ocr_wait")
        renpy.restart_interaction()

    def _keyquest_ocr_poll():
        state = _keyquest_scan_state
        if _kq_time.time() - state.started > 20:
            _keyquest_ocr_return("The scan timed out. Try a smaller scan area.")
            return
        response = _keyquest_vision.response if state.native else state.response
        if response is None or response[0] != state.request:
            return
        _, text, error = response
        if state.native and error:
            # Older game runtimes can still use Studio for a one-shot scan.
            renpy.log("Keyquest local OCR: " + error)
            state.native = False
            renpy.hide_screen("_keyquest_ocr_wait")
            renpy.show_screen("_keyquest_ocr_capture")
            renpy.restart_interaction()
            return
        # A result can arrive before Android restores the game's input focus.
        activity = state.activity if state.native else (state.bridge[3] if state.bridge else None)
        if (state.destination == "type" and state.mode != "keys"
                and activity is not None and not activity.hasWindowFocus()):
            return
        if error or not text:
            _keyquest_ocr_return(error or "No text found. Try a smaller scan area.")
            return
        if state.mode == "keys":
            keys = _keyquest_read_key_cue(text)
            if keys is None:
                _keyquest_ocr_return("No clear key prompt found. Try Race for the running minigame.")
            else:
                _keyquest_ocr_return("Check the detected keys, then press Start.", keys)
            return
        if state.mode == "math":
            output = _keyquest_math_answer(text, state.region == "bottom")
            if output is None:
                _keyquest_ocr_return("No single arithmetic problem found. Choose the area that contains it.")
                return
        else:
            output = u" ".join(text.split())[:160]
        _keyquest_ocr_reset()
        if state.destination == "show":
            renpy.show_screen("_keyquest_ocr_result", mode=state.mode, region=state.region, result=output)
            renpy.restart_interaction()
            return
        try:
            _keyquest_insert_text(output)
        except Exception as failure:
            renpy.log("Keyquest text input: " + repr(failure))
            _keyquest_ocr_return("The game could not accept this scan as text.")

    def _keyquest_watch_start(mode, region, repeat_settings=((), 3, 0.15)):
        _keyquest_ocr_reset()
        state = _keyquest_scan_state
        state.mode = mode
        state.region = region
        state.destination = "show"
        state.repeat_settings = repeat_settings
        if not renpy.android or not renpy.loadable("keyquest_vision.zip") or _keyquest_vision.unavailable:
            _keyquest_ocr_return("Live OCR is unavailable here. One-shot scanning is still available on Android.")
            return
        state.watch = mode
        state.started = _kq_time.time()
        state.watch_confirmed = 0.0
        state.watch_index = 0
        state.next_scan = state.started + 0.25
        renpy.hide_screen("_keyquest_smart_input")
        renpy.show_screen("_keyquest_live_ocr")

    def _keyquest_watch_apply(text, now):
        state = _keyquest_scan_state
        value = (_keyquest_read_key_cue(text) if state.watch == "keys"
                 else _keyquest_math_answer(text, state.region == "bottom"))
        state.watch_confirmed = now
        if value != state.watch_value:
            state.watch_value = value
            state.watch_index = 0
            renpy.restart_interaction()

    def _keyquest_watch_tick():
        state = _keyquest_scan_state
        if state.watch is None:
            return
        now = _kq_time.time()
        if now - state.started > 60:
            _keyquest_ocr_return("Live OCR ended after one minute.")
            return
        response = _keyquest_vision.response
        if response is not None and response[0] == state.request:
            _keyquest_vision.response = None
            _, text, error = response
            if error:
                renpy.log("Keyquest live OCR: " + error)
                _keyquest_ocr_return("Live OCR could not start on this game. Try a one-shot scan.")
                return
            _keyquest_watch_apply(text, now)
        if state.watch_value is not None and now - state.watch_confirmed > 1.5:
            _keyquest_watch_apply(u"", now)
        if now >= state.next_scan and not _keyquest_vision.busy:
            state.next_scan = now + 0.55
            try:
                _keyquest_submit_local(state.watch, state.region)
            except Exception as error:
                renpy.log("Keyquest live OCR: " + repr(error))
                _keyquest_ocr_return("Could not capture the game screen.")

    def _keyquest_watch_press():
        state = _keyquest_scan_state
        if (state.watch != "keys" or not state.watch_value or not state.activity
                or not state.activity.hasWindowFocus() or _kq_time.time() - state.watch_confirmed > 1.5):
            return
        key = state.watch_value[state.watch_index]
        state.watch_index = (state.watch_index + 1) % len(state.watch_value)
        _keyquest_press_named(key)

    def _keyquest_press_named(key):
        _keyquest_press(key, " " if key == "SPACE" else key if len(key) == 1 else "")

    def _keyquest_insert_text(text):
        import pygame
        # SDL2 text input holds at most 31 UTF-8 bytes per event.
        chunk = u""
        size = 0
        for character in text:
            length = len(character.encode("utf-8"))
            if size + length > 30:
                pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=chunk))
                chunk, size = u"", 0
            chunk += character
            size += length
        if chunk:
            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=chunk))

    def _keyquest_next_option(value, choices):
        return choices[(choices.index(value) + 1) % len(choices)]

    def _keyquest_start_repeat(sequence, loops, interval, region):
        _keyquest_ocr_reset()
        renpy.store._keyquest_repeat_job = (sequence, loops, interval, region, 0)
        renpy.hide_screen("_keyquest_smart_input")
        renpy.show_screen("_keyquest_repeat_runner")

    def _keyquest_edit_repeat():
        if _keyquest_repeat_job is None:
            return
        sequence, loops, interval, region, _ = _keyquest_repeat_job
        _keyquest_ocr_reset()
        renpy.show_screen("_keyquest_smart_input", initial_mode="repeat", initial_region=region,
                          initial_repeat=(sequence, loops, interval))

    def _keyquest_repeat_press():
        if _keyquest_repeat_job is None:
            return
        sequence, loops, interval, region, index = _keyquest_repeat_job
        key = sequence[index % len(sequence)]
        index += 1
        _keyquest_press_named(key)
        if index >= len(sequence) * loops:
            renpy.store._keyquest_repeat_job = None
            renpy.hide_screen("_keyquest_repeat_runner")
            renpy.restart_interaction()
        else:
            renpy.store._keyquest_repeat_job = (sequence, loops, interval, region, index)

    def _keyquest_sequence_label(sequence):
        return u" · ".join({"SPACE": "Space", "RETURN": "Enter"}.get(key, key.upper()) for key in sequence)

default _keyquest_repeat_job = None

screen _keyquest_smart_input(initial_mode="text", initial_region="full", initial_destination="show", initial_repeat=((), 3, 0.15), status=""):
    zorder 993
    default mode = initial_mode
    default region = initial_region
    default destination = initial_destination
    default sequence = initial_repeat[0]
    default loops = initial_repeat[1]
    default interval = initial_repeat[2]
    use _keyquest_floating("ocr-setup", "Smart Input", 610, 555, (0.5, 0.38)):
        hbox:
            spacing 6
            for choice, caption in (("text", "Copy text"), ("math", "Solve math"), ("repeat", "Repeat keys")):
                textbutton caption style "keyquest_deck_key" selected (mode == choice) action SetScreenVariable("mode", choice)
            textbutton "Keyboard" style "keyquest_deck_key" action [Hide("_keyquest_smart_input"), Show("_keyquest_keyboard")]
        if renpy.has_screen("_keyquest_minigames"):
            textbutton "Minigame helpers" style "keyquest_deck_key" action [Hide("_keyquest_smart_input"), Show("_keyquest_minigames")]
        if status and mode == initial_mode:
            text status color "#fff0c8" size 19 substitute False
        if mode == "repeat":
            text (_keyquest_sequence_label(sequence) if sequence else "Tap keys in the order you want them pressed.") color "#b9d3e8" size 19 xmaximum 565
            for row in ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"):
                hbox:
                    spacing 4
                    for letter in row:
                        textbutton letter.upper() style "keyquest_deck_key" xsize 45 sensitive (len(sequence) < 12) action SetScreenVariable("sequence", sequence + (letter,))
            hbox:
                spacing 6
                for button, value in (("Space", "SPACE"), ("Enter", "RETURN")):
                    textbutton button style "keyquest_deck_key" sensitive (len(sequence) < 12) action SetScreenVariable("sequence", sequence + (value,))
                textbutton "Undo" style "keyquest_deck_key" sensitive bool(sequence) action SetScreenVariable("sequence", sequence[:-1])
                textbutton "Clear" style "keyquest_deck_key" sensitive bool(sequence) action SetScreenVariable("sequence", ())
            hbox:
                spacing 6
                textbutton ("Area: " + region.title()) style "keyquest_deck_key" action SetScreenVariable("region", _keyquest_next_option(region, ("full", "top", "center", "bottom", "race")))
                textbutton "Read keys" style "keyquest_deck_key" action Function(_keyquest_ocr_begin, "keys", region, "show", (sequence, loops, interval))
                textbutton ("%d loops" % loops) style "keyquest_deck_key" action SetScreenVariable("loops", _keyquest_next_option(loops, (1, 3, 5, 10, 25, 50)))
                textbutton ("%.2f s" % interval) style "keyquest_deck_key" action SetScreenVariable("interval", _keyquest_next_option(interval, (0.08, 0.15, 0.30, 0.60)))
                textbutton "Start" style "keyquest_deck_accent" sensitive bool(sequence) action Function(_keyquest_start_repeat, sequence, loops, interval, region)
            textbutton "Follow key prompts" style "keyquest_deck_key" action Function(_keyquest_watch_start, "keys", region, (sequence, loops, interval))
        else:
            hbox:
                spacing 6
                for location, caption in (("full", "Full screen"), ("top", "Top"), ("center", "Center"), ("bottom", "Bottom")):
                    textbutton caption style "keyquest_deck_key" selected (region == location) action SetScreenVariable("region", location)
            hbox:
                spacing 6
                textbutton "Show result" style "keyquest_deck_key" selected (destination == "show") action SetScreenVariable("destination", "show")
                textbutton "Type in game" style "keyquest_deck_key" selected (destination == "type") action SetScreenVariable("destination", "type")
                textbutton ("Scan & show" if destination == "show" else "Scan & type") style "keyquest_deck_accent" action Function(_keyquest_ocr_begin, mode, region, destination)
            if destination == "type":
                text "Open the game's text field before scanning." color "#b9d3e8" size 19
            elif mode == "math":
                textbutton "Watch for answers" style "keyquest_deck_key" action Function(_keyquest_watch_start, "math", region)

screen _keyquest_ocr_result(mode, region, result):
    zorder 995
    use _keyquest_floating("ocr-result", "OCR result", 520, 300, (0.5, 0.12)):
        text ("Answer" if mode == "math" else "Recognized text") color "#b9d3e8" size 22
        text result.replace("{", "{{") substitute False color "#eff8ff" size (48 if mode == "math" else 24) xmaximum 480
        hbox:
            spacing 6
            textbutton "Scan again" style "keyquest_deck_accent" action Function(_keyquest_ocr_begin, mode, region, "show")
            textbutton "Close" style "keyquest_deck_key" action Hide("_keyquest_ocr_result")

screen _keyquest_ocr_capture():
    timer 0.20 action Function(_keyquest_ocr_capture_frame)

screen _keyquest_ocr_wait():
    zorder 995
    timer 0.15 repeat True action Function(_keyquest_ocr_poll, _update_screens=False)
    use _keyquest_floating("ocr-wait", "OCR scan", 385, 135, (0.98, 0.05)):
        hbox:
            spacing 10
            text "Reading screen…" color "#eff8ff" size 20 yalign 0.5
            textbutton "Cancel" style "keyquest_deck_key" action Function(_keyquest_ocr_reset)

screen _keyquest_repeat_runner():
    zorder 995
    if _keyquest_repeat_job is not None:
        $ interval = _keyquest_repeat_job[2]
        use _keyquest_floating("repeat-runner", "Repeating keys", 420, 135, (0.98, 0.04)):
            hbox:
                spacing 6
                textbutton "Edit keys" style "keyquest_deck_key" action Function(_keyquest_edit_repeat)
                textbutton "Stop repeat" style "keyquest_deck_key" action Function(_keyquest_ocr_reset)
        timer interval repeat True modal True action Function(_keyquest_repeat_press, _update_screens=False)

screen _keyquest_live_ocr():
    zorder 995
    $ live = _keyquest_scan_state
    timer 0.1 repeat True action Function(_keyquest_watch_tick, _update_screens=False)
    if live.watch == "keys":
        timer live.repeat_settings[2] repeat True action Function(_keyquest_watch_press, _update_screens=False)
    use _keyquest_floating("ocr-live", "Live OCR", 435, 160, (0.98, 0.04)):
        hbox:
            spacing 10
            if live.watch_value is not None:
                $ caption = _keyquest_sequence_label(live.watch_value) if live.watch == "keys" else "Answer  " + live.watch_value
                text caption color "#eff8ff" size 22 yalign 0.5 xmaximum 270
            else:
                text "Watching…" color "#b9d3e8" size 20 yalign 0.5
            textbutton "Stop OCR" style "keyquest_deck_key" action Function(_keyquest_ocr_reset)
