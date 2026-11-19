# Optional, on-device diagnostics for patched games.
default persistent.keyquest_diagnostics_enabled = False

init python:
    import json as _keyquest_log_json
    import os as _keyquest_log_os
    import sys as _keyquest_log_sys
    import time as _keyquest_log_time
    import traceback as _keyquest_log_traceback

    class _KeyquestDiagnostics(object):
        stream = None
        java_string = None
        name = "Keyquest-log.txt"
        status = ""
        queue = None
        size = 0
        last_heartbeat = 0.0
        last_tick = 0.0
        last_focus = None
        android_activity = None

    _keyquest_diagnostics = _KeyquestDiagnostics()
    _keyquest_log_limit = 2 * 1024 * 1024

    def _keyquest_open_diagnostic_output(reset):
        diag = _keyquest_diagnostics
        if not renpy.android:
            path = _keyquest_log_os.path.join(config.savedir, diag.name)
            size = 0 if reset or not _keyquest_log_os.path.isfile(path) else _keyquest_log_os.path.getsize(path)
            reset = reset or size >= _keyquest_log_limit
            return open(path, "wb" if reset else "ab"), 0 if reset else size

        from jnius import autoclass

        diag.android_activity = autoclass("org.renpy.android.PythonSDLActivity").mActivity
        diag.java_string = autoclass("java.lang.String")
        package = diag.android_activity.getPackageName()
        diag.name = "Keyquest-" + package + ".log.txt"
        downloads = autoclass("android.provider.MediaStore$Downloads").EXTERNAL_CONTENT_URI
        resolver = diag.android_activity.getContentResolver()
        cursor = resolver.query(downloads, ["_id", "_size"], "_display_name=? AND relative_path=?",
                                [diag.name, "Download/"], None)
        uri = None
        size = 0
        if cursor is not None:
            try:
                if cursor.moveToFirst():
                    uri = autoclass("android.content.ContentUris").withAppendedId(downloads, cursor.getLong(0))
                    size = cursor.getLong(1)
            finally:
                cursor.close()
        if uri is None:
            values = autoclass("android.content.ContentValues")()
            values.put("_display_name", diag.name)
            values.put("mime_type", "text/plain")
            values.put("relative_path", "Download/")
            uri = resolver.insert(downloads, values)
            if uri is None:
                raise IOError("Could not create the diagnostic log")
            reset = True
        reset = reset or size >= _keyquest_log_limit
        stream = resolver.openOutputStream(uri, "rwt" if reset else "wa")
        if stream is None:
            raise IOError("Could not open the diagnostic log")
        return stream, 0 if reset else size

    def _keyquest_diagnostic_line(event, fields):
        now = _keyquest_log_time.time()
        seconds = _keyquest_log_time.strftime("%Y-%m-%dT%H:%M:%S", _keyquest_log_time.gmtime(now))
        record = dict(fields, event=event, time="%s.%03dZ" % (seconds, int(now * 1000) % 1000))
        return _keyquest_log_json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n"

    def _keyquest_trace_record(event, **fields):
        diag = _keyquest_diagnostics
        if diag.stream is not None and len(diag.queue) < 256:
            diag.queue.append(_keyquest_diagnostic_line(event, fields))

    def _keyquest_diagnostics_close():
        diag = _keyquest_diagnostics
        if diag.stream is not None:
            stream, diag.stream = diag.stream, None
            try:
                stream.close()
            except Exception:
                pass

    def _keyquest_diagnostics_failed(error):
        _keyquest_diagnostics_close()
        _keyquest_diagnostics.status = "Couldn't write the log (%s)." % type(error).__name__
        persistent.keyquest_diagnostics_enabled = False

    def _keyquest_diagnostics_flush():
        diag = _keyquest_diagnostics
        if diag.stream is None or not diag.queue:
            return
        try:
            payload = "".join(diag.queue)
            if diag.size + len(payload) > _keyquest_log_limit:
                _keyquest_diagnostics_close()
                diag.stream, diag.size = _keyquest_open_diagnostic_output(True)
                payload = _keyquest_diagnostic_line("log_rotated", {}) + payload
            if diag.java_string is not None:
                diag.stream.write(diag.java_string(payload).getBytes("UTF-8"))
            else:
                diag.stream.write(payload.encode("ascii"))
            diag.stream.flush()
            diag.size += len(payload)
            diag.queue = []
        except Exception as error:
            _keyquest_diagnostics_failed(error)

    def _keyquest_diagnostics_start(reset):
        diag = _keyquest_diagnostics
        try:
            diag.stream, diag.size = _keyquest_open_diagnostic_output(reset)
            diag.queue = []
            diag.last_heartbeat = 0.0
            diag.last_tick = 0.0
            diag.last_focus = None
            diag.status = ""
            persistent.keyquest_diagnostics_enabled = True
            _keyquest_trace_record("session_started", renpy=renpy.version_string, android=bool(renpy.android),
                                  screen=(config.screen_width, config.screen_height))
            _keyquest_diagnostics_flush()
        except Exception as error:
            _keyquest_diagnostics_failed(error)

    def _keyquest_diagnostics_toggle():
        if persistent.keyquest_diagnostics_enabled:
            _keyquest_trace_record("logging_turned_off")
            _keyquest_diagnostics_flush()
            _keyquest_diagnostics_close()
            persistent.keyquest_diagnostics_enabled = False
        else:
            _keyquest_diagnostics_start(True)
        renpy.save_persistent()

    def _keyquest_diagnostics_tick():
        diag = _keyquest_diagnostics
        if not persistent.keyquest_diagnostics_enabled or _keyquest_panel_grabbed():
            return
        if diag.stream is None:
            _keyquest_diagnostics_start(False)
        if diag.stream is None:
            return
        now = _keyquest_log_time.time()
        if now - diag.last_tick < 0.75:
            return
        diag.last_tick = now
        if diag.android_activity is not None:
            try:
                focused = diag.android_activity.hasWindowFocus()
                if focused != diag.last_focus:
                    _keyquest_trace_record("window_focus", focused=focused)
                    diag.last_focus = focused
            except Exception:
                pass
        if now - diag.last_heartbeat >= 15:
            diag.last_heartbeat = now
            _keyquest_trace_record("game_alive", context=renpy.context_nesting_level())
        _keyquest_diagnostics_flush()

    def _keyquest_diagnostics_label(name, abnormal):
        if persistent.keyquest_diagnostics_enabled and _keyquest_diagnostics.stream is None:
            _keyquest_diagnostics_start(False)
        _keyquest_trace_record("game_label", label=name, jump=bool(abnormal))

    def _keyquest_diagnostics_legacy_label(name, abnormal):
        _keyquest_diagnostics_label(name, abnormal)
        if _keyquest_previous_label_callback is not None:
            return _keyquest_previous_label_callback(name, abnormal)

    def _keyquest_diagnostics_load():
        _keyquest_trace_record("save_loaded")
        _keyquest_diagnostics_flush()

    def _keyquest_diagnostics_quit():
        _keyquest_trace_record("game_quit")
        _keyquest_diagnostics_flush()
        _keyquest_diagnostics_close()

    def _keyquest_diagnostics_error(*args):
        if _keyquest_diagnostics.stream is not None:
            try:
                _, error, trace = _keyquest_log_sys.exc_info()
                frames = _keyquest_log_traceback.extract_tb(trace)[-16:] if trace else []
                _keyquest_trace_record("game_exception", kind=type(error).__name__,
                                       frames=[(_keyquest_log_os.path.basename(f[0]), f[1], f[2]) for f in frames])
                _keyquest_diagnostics_flush()
            except Exception:
                pass
        if _keyquest_previous_exception_handler is not None:
            if len(args) == 1:
                import inspect
                try:
                    inspect.signature(_keyquest_previous_exception_handler).bind(*args)
                except TypeError:
                    return _keyquest_previous_exception_handler(*tuple(args[0]))
                except ValueError:
                    pass
            return _keyquest_previous_exception_handler(*args)
        return False

init 999 python:
    _keyquest_trace = _keyquest_trace_record
    _keyquest_screens.append("_keyquest_diagnostics_clock")
    if hasattr(renpy.config, "label_callbacks"):
        config.label_callbacks.append(_keyquest_diagnostics_label)
    else:
        _keyquest_previous_label_callback = config.label_callback
        config.label_callback = _keyquest_diagnostics_legacy_label
    config.interact_callbacks.append(_keyquest_diagnostics_tick)
    config.after_load_callbacks.append(_keyquest_diagnostics_load)
    config.quit_callbacks.append(_keyquest_diagnostics_quit)
    _keyquest_previous_exception_handler = config.exception_handler
    config.exception_handler = _keyquest_diagnostics_error

screen _keyquest_diagnostics_clock():
    if persistent.keyquest_diagnostics_enabled:
        timer 0.8 repeat True action Function(_keyquest_diagnostics_tick, _update_screens=False)

screen _keyquest_diagnostics_settings():
    zorder 993
    $ logger = _keyquest_diagnostics
    use _keyquest_floating("diagnostics", "Diagnostics", 615, 290, (0.55, 0.32)):
        text ("Logging is on" if persistent.keyquest_diagnostics_enabled else "Logging is off") color "#eff8ff" size 24
        text (("Downloads" if renpy.android else "Game saves") + " · " + logger.name) substitute False color "#b9d3e8" size 19 xmaximum 560
        text "Logs include scene labels and error locations. Typed text and screenshots stay out of the file." color "#b9d3e8" size 19 xmaximum 560
        if logger.status:
            text logger.status color "#ffc2a9" size 19 xmaximum 560
        hbox:
            spacing 7
            textbutton ("Turn off logging" if persistent.keyquest_diagnostics_enabled else "Start fresh log") style "keyquest_deck_accent" action Function(_keyquest_diagnostics_toggle)
            textbutton "Back to keyboard" style "keyquest_deck_key" action [Hide("_keyquest_diagnostics_settings"), Show("_keyquest_keyboard")]
