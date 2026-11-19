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

    def _keyquest_math_answer(text):
        replacements = ((u"×", "*"), (u"÷", "/"), (u"−", "-"), (u"–", "-"))
        for before, after in replacements:
            text = text.replace(before, after)
        candidates = set()
        for line in text.splitlines():
            line = line.strip()
            line = _kq_re.sub(r"(?<=\d)\s*[xX]\s*(?=[\d.(])", "*", line)
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

    def _keyquest_ocr_reset():
        state = _keyquest_scan_state
        state.request += 1
        state.response = None
        state.bridge = None
        for panel in ("_keyquest_ocr_capture", "_keyquest_ocr_wait", "_keyquest_repeat_runner"):
            renpy.hide_screen(panel)

    config.after_load_callbacks.append(_keyquest_ocr_reset)

    def _keyquest_ocr_begin(mode, region):
        _keyquest_ocr_reset()
        state = _keyquest_scan_state
        state.started = _kq_time.time()
        state.mode = mode
        state.region = region
        renpy.hide_screen("_keyquest_smart_input")
        if not renpy.android:
            _keyquest_ocr_error("Screen scanning is available in the Android game.")
            return
        renpy.show_screen("_keyquest_ocr_capture")

    def _keyquest_ocr_error(message):
        state = _keyquest_scan_state
        mode, region = state.mode, state.region
        _keyquest_ocr_reset()
        renpy.show_screen("_keyquest_smart_input", initial_mode=mode, initial_region=region, status=message)
        renpy.restart_interaction()

    def _keyquest_ocr_capture_frame():
        state = _keyquest_scan_state
        renpy.hide_screen("_keyquest_ocr_capture")
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

            scale = min(1.0, 1440.0 / max(config.screen_width, config.screen_height),
                        (1550000.0 / (config.screen_width * config.screen_height)) ** 0.5)
            size = (max(1, int(config.screen_width * scale)), max(1, int(config.screen_height * scale)))
            frame = renpy.screenshot_to_bytes(size)
            if not frame:
                raise ValueError("No game frame")
            bitmap = autoclass("android.graphics.BitmapFactory").decodeByteArray(frame, 0, len(frame))
            if bitmap is None:
                raise ValueError("Frame could not be decoded")
            crop = bitmap
            try:
                width, height = bitmap.getWidth(), bitmap.getHeight()
                if state.region == "top" and height >= 3:
                    crop = autoclass("android.graphics.Bitmap").createBitmap(bitmap, 0, 0, width, height // 3)
                elif state.region == "center" and width >= 5 and height >= 5:
                    crop = autoclass("android.graphics.Bitmap").createBitmap(
                        bitmap, width // 10, height // 4, width * 4 // 5, height // 2)
                stream = autoclass("java.io.ByteArrayOutputStream")()
                jpeg = autoclass("android.graphics.Bitmap$CompressFormat").JPEG
                for quality in (92, 76, 58, 40):
                    stream.reset()
                    if crop.compress(jpeg, quality, stream) and stream.size() <= 400 * 1024:
                        break
                else:
                    raise ValueError("Frame is too large")

                extras = autoclass("android.os.Bundle")()
                extras.putByteArray("image", stream.toByteArray())
                extras.putParcelable("reply", messenger)
                extras.putBoolean("math", state.mode == "math")
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
            _keyquest_ocr_error("Could not start OCR. Update Keyquest Studio and try again.")
            return
        renpy.show_screen("_keyquest_ocr_wait")
        renpy.restart_interaction()

    def _keyquest_ocr_poll():
        state = _keyquest_scan_state
        if _kq_time.time() - state.started > 20:
            _keyquest_ocr_error("The scan timed out. Try a smaller scan area.")
            return
        response = state.response
        if response is None or response[0] != state.request:
            return
        # Android can deliver the result before the game's own window is active again.
        if state.bridge is not None and not state.bridge[3].hasWindowFocus():
            return
        _, text, error = response
        if error or not text:
            _keyquest_ocr_error(error or "No text found. Try a smaller scan area.")
            return
        if state.mode == "math":
            output = _keyquest_math_answer(text)
            if output is None:
                _keyquest_ocr_error("No single arithmetic problem found. Try Top or Center.")
                return
        else:
            output = u" ".join(text.split())[:160]
        _keyquest_ocr_reset()
        try:
            _keyquest_insert_text(output)
        except Exception as failure:
            renpy.log("Keyquest text input: " + repr(failure))
            _keyquest_ocr_error("The game could not accept this scan as text.")

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

    def _keyquest_repeat_press(key):
        renpy.store._keyquest_repeat_left -= 1
        if _keyquest_repeat_left <= 0:
            renpy.hide_screen("_keyquest_repeat_runner")
        _keyquest_press(key, " " if key == "SPACE" else key if len(key) == 1 else "")

default _keyquest_repeat_left = 0

screen _keyquest_smart_input(initial_mode="text", initial_region="full", status=""):
    zorder 993
    default mode = initial_mode
    default region = initial_region
    default selected_key = "s"
    default count = 10
    default interval = 0.15
    frame:
        align (0.5, 0.38)
        at Transform(zoom=min(1.0, config.screen_width / 620.0, config.screen_height / 390.0))
        background Frame("keyquest_panel.png", 24, 24)
        padding (18, 16)
        xsize 610
        vbox:
            spacing 8
            hbox:
                spacing 12
                add "keyquest_logo.png" xysize (38, 38)
                text "Smart Input" color "#eff8ff" size 28 yalign 0.5
            hbox:
                spacing 6
                for choice, caption in (("text", "Copy text"), ("math", "Solve math"), ("repeat", "Repeat key")):
                    textbutton caption style "keyquest_deck_key" selected (mode == choice) action SetScreenVariable("mode", choice)
                textbutton "Keyboard" style "keyquest_deck_key" action [Hide("_keyquest_smart_input"), Show("_keyquest_keyboard")]
            if mode == "repeat":
                for row in ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"):
                    hbox:
                        spacing 4
                        for letter in row:
                            textbutton letter.upper() style "keyquest_deck_key" xsize 45 selected (selected_key == letter) action SetScreenVariable("selected_key", letter)
                hbox:
                    spacing 6
                    textbutton "Space" style "keyquest_deck_key" selected (selected_key == "SPACE") action SetScreenVariable("selected_key", "SPACE")
                    textbutton "Enter" style "keyquest_deck_key" selected (selected_key == "RETURN") action SetScreenVariable("selected_key", "RETURN")
                    textbutton ("%d presses" % count) style "keyquest_deck_key" action SetScreenVariable("count", _keyquest_next_option(count, (5, 10, 25, 50)))
                    textbutton ("%.2f s" % interval) style "keyquest_deck_key" action SetScreenVariable("interval", _keyquest_next_option(interval, (0.08, 0.15, 0.30, 0.60)))
                    textbutton "Start" style "keyquest_deck_accent" action [Function(_keyquest_ocr_reset), SetVariable("_keyquest_repeat_left", count), Hide("_keyquest_smart_input"), Show("_keyquest_repeat_runner", key=selected_key, interval=interval)]
            else:
                $ hint = "Type English text into the active game field." if mode == "text" else "Type one answer for visible arithmetic (+, −, ×, ÷)."
                text hint color "#b9d3e8" size 19
                if status and mode == initial_mode:
                    text status color "#fff0c8" size 19 substitute False
                hbox:
                    spacing 6
                    for location, caption in (("full", "Full screen"), ("top", "Top"), ("center", "Center")):
                        textbutton caption style "keyquest_deck_key" selected (region == location) action SetScreenVariable("region", location)
                    textbutton "Scan & type" style "keyquest_deck_accent" action Function(_keyquest_ocr_begin, mode, region)

screen _keyquest_ocr_capture():
    timer 0.20 action Function(_keyquest_ocr_capture_frame)

screen _keyquest_ocr_wait():
    zorder 995
    timer 0.15 repeat True action Function(_keyquest_ocr_poll, _update_screens=False)
    frame:
        align (0.98, 0.05)
        background Frame("keyquest_panel.png", 24, 24)
        padding (12, 8)
        hbox:
            spacing 10
            text "Reading screen…" color "#eff8ff" size 20 yalign 0.5
            textbutton "Cancel" style "keyquest_deck_key" action Function(_keyquest_ocr_reset)

screen _keyquest_repeat_runner(key, interval):
    zorder 995
    textbutton "Stop repeat" style "keyquest_deck_key" align (0.98, 0.04) action Function(_keyquest_ocr_reset)
    timer interval repeat True modal True action Function(_keyquest_repeat_press, key, _update_screens=False)
