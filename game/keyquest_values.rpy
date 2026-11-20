# Optional editor for numeric values already present in a local Ren'Py game.

init python:
    import math as _kq_value_math
    import re as _kq_value_re

    try:
        import __builtin__ as _kq_value_builtins
    except ImportError:
        import builtins as _kq_value_builtins

    try:
        _keyquest_number_types = (int, long, float)
    except NameError:
        _keyquest_number_types = (int, float)

    _keyquest_value_names = ("money", "cash", "gold", "coins", "balance", "credits", "gems", "wallet", "points")
    _keyquest_value_token = _kq_value_re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
    _keyquest_value_instance = _kq_value_re.compile(r"store(?:\.[A-Za-z][A-Za-z0-9_]*)*\Z")
    _keyquest_value_ignore = ("config", "persistent", "preferences", "style", "gui", "build", "renpy")

    def _keyquest_numeric(value):
        return (type(value) in _keyquest_number_types and
                (type(value) is not float or not (_kq_value_math.isnan(value) or _kq_value_math.isinf(value))))

    def _keyquest_value_entries(owner):
        if isinstance(owner, _kq_value_builtins.dict):
            return owner
        if isinstance(owner, _kq_value_builtins.list):
            return None
        if not isinstance(owner, type) and _keyquest_value_instance.match(getattr(type(owner), "__module__", "")):
            return getattr(owner, "__dict__", None)
        return None

    def _keyquest_value_stores():
        stores = renpy.python.store_dicts
        return sorted((name, values) for name, values in stores.items()
                      if _keyquest_value_instance.match(name)
                      and not set(name.split(".")[1:]).intersection(_keyquest_value_ignore))

    def _keyquest_value_slot(path):
        parts = path.strip().split(".")
        if len(parts) > 12 or any(not (_keyquest_value_token.match(part) or part.isdigit()) for part in parts):
            return None
        stores = dict(_keyquest_value_stores())
        owner = stores.get("store", vars(renpy.store))
        if parts[0] == "store":
            for size in range(len(parts) - 1, 0, -1):
                prefix = ".".join(parts[:size])
                if prefix in stores:
                    owner, parts = stores[prefix], parts[size:]
                    break
        for part in parts:
            if part in _keyquest_value_ignore:
                return None
            entries = _keyquest_value_entries(owner)
            if entries is not None and part in entries:
                key, value = part, entries[part]
            elif isinstance(owner, _kq_value_builtins.list) and part.isdigit() and len(part) < 8 and int(part) < len(owner):
                key, value = int(part), owner[int(part)]
            else:
                return None
            parent, owner = owner, value
        return parent, key, owner

    def _keyquest_read_value(path):
        found = _keyquest_value_slot(path)
        return found[2] if found and _keyquest_numeric(found[2]) else None

    def _keyquest_value_catalog():
        found, visited = [], set()
        pending = [(name if name != "store" else "", owner, 0)
                   for name, owner in _keyquest_value_stores()]
        index = 0
        while index < len(pending) and index < 700 and len(found) < 450:
            prefix, owner, depth = pending[index]
            index += 1
            if id(owner) in visited:
                continue
            visited.add(id(owner))
            entries = _keyquest_value_entries(owner)
            if entries is not None:
                keys = sorted(key for key in entries if isinstance(key, _keyquest_string_types)
                              and _keyquest_value_token.match(key) and key not in _keyquest_value_ignore)
                children = ((key, entries[key]) for key in keys[:500])
            elif isinstance(owner, _kq_value_builtins.list):
                children = ((str(i), item) for i, item in enumerate(owner[:60]))
            else:
                continue
            for key, value in children:
                path = (prefix + "." + key) if prefix else key
                if _keyquest_numeric(value):
                    found.append(path)
                elif depth < 4 and len(pending) < 700 and (
                        isinstance(value, _kq_value_builtins.list) or _keyquest_value_entries(value) is not None):
                    pending.append((path, value, depth + 1))
        return tuple(sorted(set(found), key=lambda path: (
            path.rsplit(".", 1)[-1].lower() not in _keyquest_value_names, path.lower())))

    def _keyquest_refresh_values():
        screen = renpy.get_screen("_keyquest_values")
        if screen is not None:
            screen.scope["catalog"] = _keyquest_value_catalog()

    def _keyquest_value_label(path, limit):
        return path if len(path) <= limit else u"…" + path[-(limit - 1):]

    try:
        _keyquest_string_types = (basestring,)
    except NameError:
        _keyquest_string_types = (str,)

    def _keyquest_write_value(path, text):
        path = path.strip()
        found = _keyquest_value_slot(path)
        if not found or not _keyquest_numeric(found[2]):
            message = "Select an existing numeric game value."
        else:
            parent, key, current = found
            try:
                value = type(current)(text.strip())
                if not _keyquest_numeric(value) or abs(value) > 1000000000000:
                    raise ValueError()
            except (ValueError, OverflowError):
                message = "Enter a whole number." if type(current) is not float else "Enter a number up to ±1 trillion."
            else:
                try:
                    if isinstance(parent, (_kq_value_builtins.dict, _kq_value_builtins.list)):
                        parent[key] = value
                    else:
                        setattr(parent, key, value)
                    if _keyquest_read_value(path) != value:
                        raise ValueError()
                except Exception:
                    message = "The game did not keep this change."
                else:
                    _keyquest_trace("game_value_changed")
                    message = "Applied  %s → %s" % (current, value)
        renpy.session["keyquest_value_status"] = (path, message)
        renpy.restart_interaction()

style keyquest_value_row is keyquest_deck_key:
    xfill True
    ysize 54
    padding (12, 6)

style keyquest_value_row_text is keyquest_deck_key_text:
    size 20
    xalign 0.0

style keyquest_value_pad is keyquest_deck_key:
    xsize 96
    ysize 44

style keyquest_value_pad_text is keyquest_deck_key_text:
    size 23

screen _keyquest_values():
    zorder 992
    default catalog = _keyquest_value_catalog()
    default query = ""
    default selected = ""
    default amount = ""
    default show_letters = False
    $ query_input = ScreenVariableInputValue("query", default=False)
    $ amount_input = ScreenVariableInputValue("amount", default=False)
    $ matches = [path for path in catalog if query.strip().lower() in path.lower()]
    $ typed_path = query.strip()
    $ direct = _keyquest_read_value(typed_path)
    if direct is not None and typed_path not in matches:
        $ matches.insert(0, typed_path)
    $ current = _keyquest_read_value(selected)
    $ status_path, status = renpy.session.get("keyquest_value_status", ("", ""))
    use _keyquest_floating("values", "Game values", 766, 625, (0.5, 0.16)):
        hbox:
            spacing 8
            textbutton "Refresh list" style "keyquest_deck_key" action Function(_keyquest_refresh_values)
            textbutton "Close" style "keyquest_deck_key" action Hide("_keyquest_values")
        hbox:
            spacing 20
            vbox:
                xsize 384
                spacing 6
                text "Find a value" size 24 color "#eff8ff"
                hbox:
                    spacing 6
                    frame:
                        xsize 312
                        ysize 47
                        padding (10, 6)
                        background Solid("#26384c")
                        input value query_input length 112 pixel_width 287 color "#eff8ff" size 23
                    textbutton ("List" if show_letters else "ABC") style "keyquest_deck_key" action ToggleScreenVariable("show_letters")
                hbox:
                    spacing 6
                    textbutton "Edit search" style "keyquest_deck_key" action query_input.Enable()
                    textbutton "Clear" style "keyquest_deck_key" action SetScreenVariable("query", "")
                if show_letters:
                    for letters in ("abcdefg", "hijklmn", "opqrstu", "vwxyz._"):
                        hbox:
                            spacing 3
                            for letter in letters:
                                textbutton letter style "keyquest_deck_key" xsize 50 action SetScreenVariable("query", (query + letter)[:112])
                    textbutton "Delete last" style "keyquest_deck_key" action SetScreenVariable("query", query[:-1])
                elif matches:
                    viewport:
                        xsize 384
                        ysize 224
                        mousewheel True
                        draggable True
                        scrollbars "vertical"
                        vbox:
                            spacing 4
                            for path in matches:
                                button:
                                    id ("keyquest-value-" + path)
                                    style "keyquest_value_row"
                                    selected (selected == path)
                                    action [SetScreenVariable("selected", path), SetScreenVariable("amount", "")]
                                    text _keyquest_value_label(path, 31) substitute False size 20 color "#eff8ff" xmaximum 332
                else:
                    text "No matches. Try part of the variable name, or refresh during gameplay." color "#b9d3e8" size 20 xmaximum 374
            vbox:
                xsize 316
                spacing 6
                text (_keyquest_value_label(selected, 64) or "Select a value") substitute False size 23 color "#eff8ff" xmaximum 316
                if current is not None:
                    text ("Current   %s" % current) substitute False color "#a5efd4" size 22
                    text "New value" size 19 color "#b9d3e8"
                    frame:
                        xsize 302
                        ysize 44
                        background Solid("#26384c")
                        padding (9, 4)
                        input value amount_input length 24 pixel_width 276 allow "0123456789.-" color "#eff8ff" size 25
                    for row in ("123", "456", "789", "-0."):
                        hbox:
                            spacing 7
                            for digit in row:
                                textbutton digit id ("keyquest-pad-" + digit) style "keyquest_value_pad" action SetScreenVariable("amount", (amount + digit)[:24])
                    hbox:
                        spacing 6
                        textbutton "Clear" style "keyquest_deck_key" action SetScreenVariable("amount", "")
                        textbutton "Delete" style "keyquest_deck_key" action SetScreenVariable("amount", amount[:-1])
                        textbutton "Edit" style "keyquest_deck_key" action amount_input.Enable()
                    textbutton "Apply value" id "keyquest_apply_value" style "keyquest_deck_accent" xsize 302 sensitive bool(amount.strip()) action Function(_keyquest_write_value, selected, amount)
                else:
                    text "Pick a number from the list to see and change it here." color "#b9d3e8" size 20 xmaximum 310
        if selected and selected == status_path and status:
            text status substitute False color "#a5efd4" size 20 xmaximum 700
