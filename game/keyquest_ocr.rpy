# Optional on-device screen reading and repeat keys for Ren'Py 7.5, 7.8, and 8.0–8.5.

init python:
    import ast as _kq_ast
    import re as _kq_re
    import time as _kq_time

    class _KeyquestScanState(object):
        request = 0
        started = 0.0
        response = None
        bridge = None
        frame = None
        pass_region = None
        first_text = None
        mode = "text"
        region = "full"
        destination = "show"
        repeat_settings = ((), 3, 0.15)
        native = False
        activity = None
        watch = None
        watch_paused = False
        watch_value = None
        watch_index = 0
        watch_confirmed = 0.0
        watch_misses = 0
        next_scan = 0.0

        def __getstate__(self):
            # Android handles and the live OCR/log session belong to this process.
            return {}


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
        for before, after in ((u"×", "*"), (u"·", "*"), (u"⋅", "*"), (u"✕", "*"),
                              (u"÷", "/"), (u"−", "-"), (u"–", "-"), (u"＝", "="), (u"？", "?")):
            text = text.replace(before, after)
        text = _kq_re.sub(r"(?<=[\d.)])\s*(?:x|mal)\s*(?=[+\-\d.(])", "*", text, flags=_kq_re.I)
        text = _kq_re.sub(r"([+*/=])[^\S\n]*\n[ \t]*(?=[+\-\d.(?])", r"\1 ", text)
        marked, unmarked = set(), set()
        for line in text.splitlines():
            line = _kq_re.sub(r"^\s*(?:solve|calculate|what\s+is|rechne|berechne)(?:\s*:\s*|\s+)", "", line, flags=_kq_re.I).strip()
            ending = _kq_re.search(r"\s*(?:=\s*\??|\?)\s*$", line)
            expression = line[:ending.start()].strip() if ending else line
            if (len(expression) <= 64 and _kq_re.match(r"^[0-9.()+*/ \t-]+\Z", expression)
                    and _kq_re.search(r"[\d.)]\s*[+*/-]", expression)):
                expression = _kq_re.sub(r"\s*([()+*/-])\s*", r"\1", expression)
                if ending:
                    marked.add(expression)
                elif not require_prompt or _kq_re.search(r"\d\*\d", expression):
                    unmarked.add(expression)
        candidates = marked or unmarked
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

    def _keyquest_read_typing_prompt(text):
        instruction = _kq_re.search(r"\(?[ \t]*type\s+the\s+(?:line|sentence)\s+above\b", text, _kq_re.I)
        if instruction is None:
            return None
        preceding = text[:instruction.start()].rstrip().splitlines()
        if not preceding:
            return None
        lines = [preceding.pop().strip()]
        while preceding:
            previous = preceding.pop().strip()
            if not previous and lines[0][:1].islower() and preceding and preceding[-1].strip():
                continue
            if (not _kq_re.search(r"[^\W\d_]", previous, _kq_re.UNICODE)
                    or previous.rstrip(u'"”’').endswith((".", "!", "?"))):
                break
            lines.insert(0, previous)
        prompt = u" ".join(lines)
        # The outlined text box can be read as an isolated 4 at either end.
        border_noise = _kq_re.search(r"(?<=[.!?])\s+4$", prompt)
        if border_noise:
            prompt = prompt[:border_noise.start()]
        if border_noise and _kq_re.match(r"^4\s+[a-z]", prompt):
            prompt = _kq_re.sub(r"^4\s+", "", prompt)
            prompt = prompt[0].upper() + prompt[1:]
        if not _kq_re.search(r"[^\W\d_]", prompt, _kq_re.UNICODE):
            return None
        return prompt

    def _keyquest_read_key_cue(text):
        cues = set()
        for line in text.splitlines():
            match = _kq_re.match(r"^\s*[|!:.]*\s*(?:(?:press|tap|mash|alternate(?:\s+between)?)\b|keys?\s*:)\s*(.+)$", line, _kq_re.I)
            if not match:
                continue
            cue = _kq_re.split(r"\s+(?:rapidly|quickly|repeatedly|fast|now|to)\b", match.group(1), 1, flags=_kq_re.I)[0]
            cue = cue.strip(" .!:").lower().replace(u"→", ",")
            cue = cue.replace("[", "").replace("]", "").replace('"', "").replace(u"“", "").replace(u"”", "")
            if _kq_re.search(r"(?:\band|\bthen|[,/+&])$", cue):
                continue
            # OCR can join "and m" or split a lower-case m into "rn".
            cue = _kq_re.sub(r"^([a-z0-9])\s*and\s*([a-z0-9]|rn)$", r"\1 and \2", cue)
            if _kq_re.match(r"^[a-z0-9] and rn$", cue):
                cue = cue[:-2] + "m"
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
        state.frame = None
        state.pass_region = None
        state.first_text = None
        state.native = False
        state.activity = None
        state.watch = None
        state.watch_value = None
        renpy.store._keyquest_repeat_job = None
        for panel in ("_keyquest_ocr_capture", "_keyquest_ocr_wait", "_keyquest_ocr_result", "_keyquest_repeat_runner", "_keyquest_live_ocr"):
            renpy.hide_screen(panel)

    config.after_load_callbacks.append(_keyquest_ocr_reset)

    def _keyquest_ocr_begin(mode, region, destination="show", repeat_settings=((), 3, 0.15)):
        _keyquest_trace("ocr_started", mode=mode, region=region, destination=destination)
        _keyquest_ocr_reset()
        state = _keyquest_scan_state
        state.started = _kq_time.time()
        state.mode = mode
        state.region = region
        state.pass_region = region
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

    def _keyquest_submit_local(mode, region, frame=None):
        from jnius import autoclass

        state = _keyquest_scan_state
        if state.activity is None:
            state.activity = autoclass("org.renpy.android.PythonSDLActivity").mActivity
        if not state.activity.hasWindowFocus() or _keyquest_vision.busy:
            return False
        detailed = region in ("race", "bottom", "typing")
        limit = 1440 if region == "race" else (1920 if mode == "math" else (960 if state.watch and not detailed else 1440))
        size = _keyquest_capture_size(limit, detailed or mode == "math")
        if frame is None:
            frame = renpy.screenshot_to_bytes(size)
        if not frame:
            return False
        validate = None
        if mode == "keys" and region == "race":
            def validate(text):
                keys = _keyquest_read_key_cue(text)
                return keys and (len(keys) > 1 or _kq_re.search(r"\b(?:rapidly|quickly|repeatedly|fast)\b", text, _kq_re.I))
        if mode == "math":
            validate = lambda text: _keyquest_math_answer(text, region == "bottom") is not None
        return _keyquest_vision.start(state.request, frame, region, mode,
                                      state.activity.getCodeCacheDir().getAbsolutePath(), validate)

    def _keyquest_capture_size(maximum, allow_upscale=False):
        width, height = config.screen_width, config.screen_height
        scale = min(float(maximum) / max(width, height), (2100000.0 / (width * height)) ** 0.5)
        if not allow_upscale:
            scale = min(1.0, scale)
        return (max(1, int(width * scale)), max(1, int(height * scale)))

    def _keyquest_ocr_capture_frame():
        state = _keyquest_scan_state
        renpy.hide_screen("_keyquest_ocr_capture")
        region = state.pass_region or state.region
        if state.frame is None:
            large_text_scan = state.mode == "math" or (state.mode == "text" and state.region in ("full", "typing"))
            detailed = large_text_scan or region in ("race", "bottom")
            try:
                state.frame = renpy.screenshot_to_bytes(_keyquest_capture_size(1920 if large_text_scan else 1440, detailed))
            except Exception as error:
                _keyquest_trace("ocr_error", stage="capture")
                renpy.log("Keyquest screen capture: " + repr(error))
        if not state.frame:
            _keyquest_ocr_return("Could not capture the game screen.")
            return
        if not _keyquest_vision.unavailable and renpy.loadable("keyquest_vision.zip"):
            try:
                state.native = _keyquest_submit_local(state.mode, region, state.frame)
            except Exception as error:
                _keyquest_trace("ocr_error", stage="local_engine")
                renpy.log("Keyquest local OCR: " + repr(error))
            if state.native:
                if renpy.get_screen("_keyquest_ocr_wait") is None:
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

            frame = state.frame
            bitmap = autoclass("android.graphics.BitmapFactory").decodeByteArray(frame, 0, len(frame))
            if bitmap is None:
                raise ValueError("Frame could not be decoded")
            crop = bitmap
            try:
                width, height = bitmap.getWidth(), bitmap.getHeight()
                area = _keyquest_ocr_crop(width, height, region)
                if area is not None:
                    crop = autoclass("android.graphics.Bitmap").createBitmap(bitmap, *area)
                stream = autoclass("java.io.ByteArrayOutputStream")()
                formats = autoclass("android.graphics.Bitmap$CompressFormat")
                encodings = [(formats.JPEG, quality) for quality in (92, 76, 58, 40)]
                if region == "race":
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
                extras.putBoolean("race", region == "race" and state.mode == "keys")
                extras.putBoolean("typing", region == "typing")
                extras.putBoolean("fullText", region == "full" and state.mode == "text")
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
            _keyquest_trace("ocr_error", stage="android_bridge")
            renpy.log("Keyquest OCR bridge: " + repr(error))
            _keyquest_ocr_return("Could not start OCR. Update Keyquest Studio and try again.")
            return
        renpy.show_screen("_keyquest_ocr_wait")
        renpy.restart_interaction()

    def _keyquest_ocr_poll():
        if _keyquest_panel_grabbed():
            return
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
            _keyquest_trace("ocr_error", stage="local_engine")
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
        _keyquest_trace("ocr_result", mode=state.mode, region=state.pass_region or state.region,
                        received=bool(text), failed=bool(error))
        prompt = _keyquest_read_typing_prompt(text) if state.mode == "text" and text and not error else None
        answer = (_keyquest_math_answer(text, (state.pass_region or state.region) == "bottom")
                  if state.mode == "math" and text and not error else None)
        retry_region = None
        if state.mode == "text" and prompt is None and state.region in ("typing", "full"):
            retry_region = "typing" if state.region == "full" else "full"
        if state.mode == "math" and answer is None and state.region == "full":
            retry_region = "bottom"
        if retry_region and state.frame is not None and state.first_text is None:
            state.first_text = text if text and not error else u""
            state.pass_region = retry_region
            state.request += 1
            state.response = None
            state.bridge = None
            _keyquest_trace("ocr_retry", region=state.pass_region)
            _keyquest_ocr_capture_frame()
            return
        if state.mode == "text" and state.region == "full" and prompt is None and state.first_text:
            text, error = state.first_text, None
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
            output = answer
            if output is None:
                _keyquest_ocr_return("No single arithmetic problem found. Choose the area that contains it.")
                return
        else:
            output = prompt
            if output is None:
                if state.region == "typing":
                    _keyquest_ocr_return("Could not isolate the typing prompt. Keep the entire box visible and scan again.")
                    return
                output = text.strip() if state.destination == "show" else u" ".join(text.split())
        _keyquest_ocr_reset()
        if state.destination == "show":
            renpy.show_screen("_keyquest_ocr_result", mode=state.mode, region=state.region, result=output)
            renpy.restart_interaction()
            return
        try:
            _keyquest_insert_text(output)
        except Exception as failure:
            _keyquest_trace("ocr_error", stage="text_input")
            renpy.log("Keyquest text input: " + repr(failure))
            _keyquest_ocr_return("The game could not accept this scan as text.")

    def _keyquest_race_start(interval):
        _keyquest_watch_start("keys", "race", ((), 3, min(0.08, interval)))

    def _keyquest_watch_start(mode, region, repeat_settings=((), 3, 0.15)):
        _keyquest_trace("ocr_watch_started", mode=mode, region=region)
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
        state.watch_paused = False
        state.started = _kq_time.time()
        state.watch_confirmed = 0.0
        state.watch_misses = 0
        state.watch_index = 0
        state.next_scan = state.started + 0.25
        renpy.hide_screen("_keyquest_smart_input")
        renpy.show_screen("_keyquest_live_ocr")

    def _keyquest_watch_apply(text, now):
        state = _keyquest_scan_state
        value = (_keyquest_read_key_cue(text) if state.watch == "keys"
                 else _keyquest_math_answer(text, state.region == "bottom"))
        if state.watch == "keys" and state.region == "race":
            if value is None:
                state.watch_misses += 1
                # Keep the most recent cue through one missed sample, briefly.
                if state.watch_misses == 1 and now - state.watch_confirmed <= 0.8:
                    return
            else:
                state.watch_misses = 0
        if value is not None:
            state.watch_confirmed = now
        if value != state.watch_value:
            _keyquest_trace("ocr_watch_changed", mode=state.watch, recognized=value is not None)
            state.watch_value = value
            state.watch_index = 0
            renpy.restart_interaction()

    def _keyquest_watch_tick():
        state = _keyquest_scan_state
        if state.watch is None:
            return
        if _keyquest_panel_grabbed():
            state.watch_paused = True
            return
        now = _kq_time.time()
        if state.watch_paused:
            state.watch_paused = False
            _keyquest_trace("ocr_watch_resumed")
            state.request += 1
            state.watch_confirmed = 0.0
            state.watch_misses = 0
            state.next_scan = now
        if now - state.started > 60:
            _keyquest_ocr_return("Live OCR ended after one minute.")
            return
        response = _keyquest_vision.response
        if response is not None and response[0] == state.request:
            _keyquest_vision.response = None
            _, text, error = response
            if error:
                _keyquest_trace("ocr_error", stage="live_capture")
                renpy.log("Keyquest live OCR: " + error)
                _keyquest_ocr_return("Live OCR could not start on this game. Try a one-shot scan.")
                return
            _keyquest_watch_apply(text, now)
        if state.watch_value is not None and now - state.watch_confirmed > _keyquest_watch_expiry():
            _keyquest_watch_apply(u"", now)
        if now >= state.next_scan and not _keyquest_vision.busy:
            state.next_scan = now + (0.34 if state.region == "race" else 0.55)
            try:
                _keyquest_submit_local(state.watch, state.region)
            except Exception as error:
                _keyquest_trace("ocr_error", stage="live_capture")
                renpy.log("Keyquest live OCR: " + repr(error))
                _keyquest_ocr_return("Could not capture the game screen.")

    def _keyquest_watch_expiry():
        return 0.8 if _keyquest_scan_state.region == "race" else 1.5

    def _keyquest_watch_press():
        state = _keyquest_scan_state
        if (_keyquest_panel_grabbed() or state.watch_paused or state.watch != "keys"
                or not state.watch_value or not state.activity
                or not state.activity.hasWindowFocus() or _kq_time.time() - state.watch_confirmed > _keyquest_watch_expiry()):
            return
        key = state.watch_value[state.watch_index]
        state.watch_index = (state.watch_index + 1) % len(state.watch_value)
        _keyquest_press_named(key)

    def _keyquest_press_named(key):
        _keyquest_press(key, " " if key == "SPACE" else key if len(key) == 1 else "")

    def _keyquest_insert_text(text):
        _keyquest_trace("ocr_typing", length=len(text))
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
        return choices[(choices.index(value) + 1) % len(choices)] if value in choices else choices[0]

    def _keyquest_start_repeat(sequence, loops, interval, region):
        _keyquest_trace("repeat_started", keys=len(sequence), loops=loops, interval=interval)
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
            hbox:
                spacing 6
                textbutton "Race assist" style "keyquest_deck_accent" action Function(_keyquest_race_start, interval)
                textbutton "Follow key prompts" style "keyquest_deck_key" action Function(_keyquest_watch_start, "keys", region, (sequence, loops, interval))
        else:
            hbox:
                spacing 6
                for location, caption in (("full", "Full screen"), ("top", "Top"), ("center", "Center"), ("bottom", "Bottom")):
                    textbutton caption style "keyquest_deck_key" selected (region == location) action SetScreenVariable("region", location)
            if mode == "text":
                textbutton "Typing challenge" style "keyquest_deck_key" selected (region == "typing") action SetScreenVariable("region", "typing")
            hbox:
                spacing 6
                textbutton "Show result" style "keyquest_deck_key" selected (destination == "show") action SetScreenVariable("destination", "show")
                textbutton "Type in game" style "keyquest_deck_key" selected (destination == "type") action SetScreenVariable("destination", "type")
                textbutton ("Scan & show" if destination == "show" else "Scan & type") style "keyquest_deck_accent" action Function(_keyquest_ocr_begin, mode, "bottom" if region == "typing" and mode != "text" else region, destination)
            if destination == "type":
                text "Open the game's text field before scanning." color "#b9d3e8" size 19
            elif mode == "math":
                textbutton "Watch for answers" style "keyquest_deck_key" action Function(_keyquest_watch_start, "math", "bottom" if region == "typing" else region)

screen _keyquest_ocr_result(mode, region, result):
    zorder 995
    use _keyquest_floating("ocr-result", "OCR result", 810 if mode == "text" else 520, 420 if mode == "text" else 300, (0.5, 0.12)):
        text ("Answer" if mode == "math" else "Recognized text") color "#b9d3e8" size 22
        if mode == "text":
            viewport:
                xsize 772
                ysize 270
                mousewheel True
                draggable True
                scrollbars "vertical"
                text result.replace("{", "{{") substitute False color "#eff8ff" size 25 xmaximum 738
        else:
            text result.replace("{", "{{") substitute False color "#eff8ff" size 48 xmaximum 480
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
