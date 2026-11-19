# Use as the fixture's start script.
label start:
    python:
        path = _keyquest_log_os.path.join(config.savedir, "Keyquest-log.txt")
        persistent.keyquest_diagnostics_enabled = False
        _keyquest_trace("disabled_event")
        assert not _keyquest_log_os.path.exists(path)
        _keyquest_diagnostics_toggle()
        assert persistent.keyquest_diagnostics_enabled, _keyquest_diagnostics.status
        _keyquest_press("q", "q")
        _keyquest_insert_text(u"private sample")
        _keyquest_trace("tile_tap", index=7, retry=False)
    call _keyquest_diagnostic_test_label
    show screen _keyquest_diagnostics_settings
    $ renpy.pause(1.1, hard=True)
    python:
        try:
            raise ValueError("private exception message")
        except ValueError:
            assert _keyquest_diagnostics_error(None) is False
        _keyquest_diagnostics_toggle()
        assert not persistent.keyquest_diagnostics_enabled
        with open(path, "rb") as log:
            original = log.read()
        for event in (b"session_started", b"game_label", b"_keyquest_diagnostic_test_label",
                      b"game_alive", b"keyboard_press", b"character", b"ocr_typing",
                      b"tile_tap", b"game_exception", b"ValueError", b"logging_turned_off"):
            assert event in original, (event, original)
        assert b"private sample" not in original and b"private exception message" not in original
        _keyquest_trace("disabled_event")
        _keyquest_diagnostics_flush()
        with open(path, "rb") as log:
            assert log.read() == original
        _keyquest_diagnostics_start(False)
        _keyquest_trace("after_reopen")
        _keyquest_diagnostics_quit()
        with open(path, "rb") as log:
            reopened = log.read()
        assert reopened.startswith(original) and b"after_reopen" in reopened
        persistent.keyquest_diagnostics_enabled = False
        _keyquest_diagnostics_toggle()
        _keyquest_trace("fresh_log")
        _keyquest_diagnostics_toggle()
        with open(path, "rb") as log:
            fresh = log.read()
        assert b"fresh_log" in fresh and b"after_reopen" not in fresh
        assert "Keyquest-log.txt" in _keyquest_log_os.listdir(config.savedir)
    $ print("Keyquest diagnostics opt-in, privacy, append and replacement passed.")
    $ renpy.quit()

label _keyquest_diagnostic_test_label:
    return
