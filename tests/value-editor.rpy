default money = 75
default player = _TestPlayer()
default wallets = [{'credits': 25}]
default can_purchase = True
default economy.balance = 3.5

init python:
    class _TestPlayer(object):
        def __init__(self):
            self.coins = 20

    def _test_value_button(widget):
        screen = renpy.get_screen("_keyquest_values")
        button = renpy.get_displayable("_keyquest_values", widget)
        if button is None:
            raise AssertionError("Missing value editor control: " + widget)
        action = _test_find_button_action(screen, button)
        if action is None:
            raise AssertionError("Missing value editor action: " + widget)
        renpy.display.screen.push_current_screen(screen)
        try:
            renpy.run(action)
        finally:
            renpy.display.screen.pop_current_screen()

    def _test_find_button_action(item, target, action=None):
        action = getattr(item, "action", None) or action
        if item is target:
            return action
        for child in item.visit():
            if child is not None:
                found = _test_find_button_action(child, target, action)
                if found is not None:
                    return found
        return None

    def _test_find_value_panel(item):
        if getattr(item, "drag_name", None) == "keyquest-values":
            return item
        for child in item.visit():
            if child is not None:
                panel = _test_find_value_panel(child)
                if panel is not None:
                    return panel
        return None

label start:
    $ assert sorted(path for path in _keyquest_value_catalog() if path in ("money", "player.coins", "wallets.0.credits", "store.economy.balance")) == ["money", "player.coins", "store.economy.balance", "wallets.0.credits"]
    $ assert _keyquest_read_value("can_purchase") is None
    $ assert _keyquest_read_value("player.__dict__.coins") is None
    $ _keyquest_write_value("store.economy.balance", "-21.75")
    $ assert economy.balance == -21.75
    $ _keyquest_write_value("wallets.0.credits", "150")
    $ assert wallets[0]["credits"] == 150
    $ _keyquest_write_value("money", "2.5")
    $ assert money == 75
    $ _keyquest_write_value("player.coins", "1000000000001")
    $ assert player.coins == 20

    show screen _keyquest_values
    $ renpy.pause(0.2, hard=True)
    $ _test_value_button("keyquest-value-player.coins")
    $ renpy.pause(0.15, hard=True)
    $ _test_value_button("keyquest-pad-4")
    $ renpy.pause(0.15, hard=True)
    $ _test_value_button("keyquest-pad-2")
    $ renpy.pause(0.15, hard=True)
    $ _test_value_button("keyquest_apply_value")
    $ renpy.pause(0.15, hard=True)
    $ assert player.coins == 42
    $ value_panel = _test_find_value_panel(renpy.get_screen("_keyquest_values"))
    $ assert value_panel is not None and 0 <= value_panel.x and 0 <= value_panel.y
    $ assert value_panel.x + value_panel.w <= config.screen_width and value_panel.y + value_panel.h <= config.screen_height
    $ print("Keyquest value editor found nested values, applied 42 with the keypad, and fit inside the panel.")
    $ renpy.quit()
