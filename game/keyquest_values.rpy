# Optional editor for existing numeric values in the current local game store.

init python:
    def _keyquest_read_value(name):
        import re
        if not re.match(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z", name):
            return None
        value = vars(renpy.store).get(name)
        return value if type(value) in (int, float) else None

    def _keyquest_write_value(name, text):
        import math
        current = _keyquest_read_value(name)
        if current is None:
            SetScreenVariable("feedback", "This name does not match a numeric game value.")()
            return
        try:
            value = type(current)(text.strip())
            if (math.isnan(value) or math.isinf(value)) or abs(value) > 1000000000000:
                raise ValueError()
        except (ValueError, OverflowError):
            SetScreenVariable("feedback", "Enter a valid number of the same type (up to 1 trillion).")()
            return
        setattr(renpy.store, name, value)
        _keyquest_trace("game_value_changed")
        SetScreenVariable("feedback", "{}: {} → {}".format(name, current, value))()

screen _keyquest_values():
    zorder 992
    default name = ""
    default amount = ""
    default feedback = "Choose a suggested value or enter its exact name."
    $ name_input = ScreenVariableInputValue("name", default=False)
    $ amount_input = ScreenVariableInputValue("amount", default=False)
    $ current = _keyquest_read_value(name.strip())
    $ suggestions = [item for item in ("money", "cash", "gold", "coins", "balance", "credits", "gems") if _keyquest_read_value(item) is not None]
    use _keyquest_floating("values", "Game values", 565, 490, (0.5, 0.16), light=True):
        hbox:
            spacing 12
            textbutton "Keys" style "keyquest_key" action Show("_keyquest_keyboard")
            textbutton "Close" style "keyquest_key" action Hide("_keyquest_values")
        if suggestions:
            hbox:
                spacing 4
                for item in suggestions[:4]:
                    textbutton item style "keyquest_key" action SetScreenVariable("name", item)
        textbutton "Edit variable name" style "keyquest_key" action name_input.Enable()
        frame:
            background Solid("#dee8f4")
            input value name_input length 64 pixel_width 480 color "#152538" size 23
        if current is not None:
            text "Current value: [current]" color "#405264" size 21
        textbutton "Edit new value" style "keyquest_key" action amount_input.Enable()
        frame:
            background Solid("#dee8f4")
            input value amount_input length 24 pixel_width 480 allow "0123456789.-" color "#152538" size 23
        textbutton "Apply value" style "keyquest_key" action Function(_keyquest_write_value, name.strip(), amount)
        text feedback color "#405264" size 19
