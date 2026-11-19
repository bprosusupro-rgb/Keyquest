default _test_colors = ("#d60000", "#0000c2", "#01cf00", "#d7cf00")
default _test_pressed = []
default _test_tiles = (1, 2, 3, 4, 5, 6, 7, 0, 8)

init 999 python:
    assert _keyquest_color_layout(((214, 0, 0), (0, 0, 194), (1, 207, 0), (215, 207, 0)))
    _test_goal = (1, 2, 3, 4, 5, 6, 7, 8, 0)
    _test_hard = (8, 6, 7, 2, 5, 4, 3, 0, 1)
    steps = _keyquest_tile_moves(_test_hard, _test_goal)
    assert len(steps) == 31
    current = list(_test_hard)
    for step in steps:
        blank = current.index(0)
        assert step in _keyquest_tile_neighbors(blank)
        current[step], current[blank] = current[blank], current[step]
    assert tuple(current) == _test_goal
    try:
        _keyquest_tile_moves((2, 1, 3, 4, 5, 6, 7, 8, 0), _test_goal)
        raise AssertionError("An unreachable board was accepted.")
    except ValueError:
        pass

label start:
    $ persistent.keyquest_minigame_boards = {"colors": (0.17, 0.17, 0.64, 0.61), "tiles": (0.17, 0.17, 0.64, 0.61)}
    $ _keyquest_minigame.mode = "colors"
    show screen _kq_test_colors
    show screen _keyquest_minigames
    $ renpy.pause(0.25, hard=True)
    $ _keyquest_begin_minigame("watch")
    show screen _kq_test_flashes
    $ renpy.pause(2.3, hard=True)
    hide screen _kq_test_flashes
    $ assert _keyquest_minigame.sequence == (0, 2, 0), _keyquest_minigame.sequence
    $ _keyquest_show_minigame()
    $ _keyquest_begin_minigame("color-play")
    $ renpy.pause(2.1, hard=True)
    $ assert _test_pressed == [0, 2, 0], _test_pressed
    hide screen _kq_test_colors
    hide screen _keyquest_minigames

    $ _keyquest_minigame.mode = "tiles"
    show screen _kq_test_tiles
    $ renpy.pause(0.25, hard=True)
    python:
        tiles, edges, signatures = _keyquest_tile_scan(_keyquest_frame(), _keyquest_board())
        _keyquest_minigame.tiles = tiles
        _keyquest_minigame.signatures = signatures
        target = list(tiles)
        target[7], target[8] = target[8], target[7]
        _keyquest_minigame.moves = _keyquest_tile_moves(tiles, tuple(target))
        _keyquest_begin_minigame("tile-play")
    $ renpy.pause(1.7, hard=True)
    $ assert _test_tiles == _test_goal, _test_tiles
    $ assert not _keyquest_minigame.moves
    $ assert "complete" in _keyquest_minigame.message, _keyquest_minigame.message
    $ print("Keyquest minigame detection and verified clicks passed.")
    $ renpy.quit()

screen _kq_test_colors():
    $ bounds = persistent.keyquest_minigame_boards["colors"]
    for index, color in enumerate(_test_colors):
        $ point = _keyquest_board_point(bounds, 2, index)
        button:
            align (0.0, 0.0)
            pos point
            anchor (0.5, 0.5)
            xysize (int(config.screen_width * 0.235), int(config.screen_height * 0.22))
            background Solid(color)
            action Function(_test_pressed.append, index, _update_screens=False)

screen _kq_test_flashes():
    timer 0.60 action SetVariable("_test_colors", ("#ffaaaa", "#0000c2", "#01cf00", "#d7cf00"))
    timer 0.85 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#01cf00", "#d7cf00"))
    timer 1.10 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#baffba", "#d7cf00"))
    timer 1.35 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#01cf00", "#d7cf00"))
    timer 1.60 action SetVariable("_test_colors", ("#ffaaaa", "#0000c2", "#01cf00", "#d7cf00"))
    timer 1.85 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#01cf00", "#d7cf00"))

screen _kq_test_tiles():
    $ bounds = persistent.keyquest_minigame_boards["tiles"]
    for index, tile in enumerate(_test_tiles):
        $ point = _keyquest_board_point(bounds, 3, index)
        $ color = ("#000", "#f99", "#9f9", "#99f", "#ff9", "#f9f", "#9ff", "#aaa", "#a92")[tile]
        button:
            pos point
            anchor (0.5, 0.5)
            xysize (int(config.screen_width * 0.1567), int(config.screen_height * 0.1467))
            background Solid(color)
            action (SetVariable("_test_tiles", _test_goal) if index == 8 else NullAction())
