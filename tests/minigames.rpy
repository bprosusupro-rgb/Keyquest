default _test_colors = ("#d60000", "#0000c2", "#01cf00", "#d7cf00")
default _test_pressed = []
default _test_reject_color = False
default _test_hit_count = 0
default _test_dim_blank = False
default _test_tiles = (1, 2, 3, 4, 5, 6, 7, 0, 8)
default _test_timing_y = 0.5
default _test_timing_clicks = 0
default _test_paddle_motions = []

init 999 python:
    def _test_arcade_detectors():
        import pygame
        frame = pygame.Surface((480, 270))
        frame.fill((60, 87, 42))
        white = (239, 230, 202)
        frame.fill(white, (238, 43, 2, 177))
        frame.fill(white, (110, 80, 270, 1))
        frame.fill(white, (111, 94, 3, 40))
        pygame.draw.circle(frame, white, (208, 116), 4)
        bounds = (0.22, 0.16, 0.80, 0.82)
        ball = _keyquest_paddle_ball(frame, bounds)
        assert ball is not None and abs(ball[0] - 208.0 / 480) < 0.01
        target = _keyquest_paddle_target((0.32, 0.65), (0.34, 0.59), bounds, "left")
        assert abs(target[0] - 0.24) < 0.01 and 0.65 < target[1] < 0.82

    def _test_timing_press():
        renpy.store._test_timing_clicks += 1

    class _TestPaddleMotion(renpy.Displayable):
        def render(self, width, height, st, at):
            return renpy.Render(width, height)

        def event(self, ev, x, y, st):
            import pygame
            if ev.type == pygame.MOUSEMOTION:
                _test_paddle_motions.append((x, y))

    def _test_runtime_state_and_tile_crop():
        import pickle
        import threading
        import pygame

        for instance, field in ((_KeyquestScanState(), "activity"), (_KeyquestDiagnostics(), "android_activity"),
                                (_KeyquestVisionWorker(), "libraries")):
            setattr(instance, field, threading.Lock())
            restored = pickle.loads(pickle.dumps(instance, pickle.HIGHEST_PROTOCOL))
            assert not getattr(restored, field)

        sample = pygame.Surface((800, 600))
        sample.fill((0, 0, 0))
        sample.fill((205, 180, 109), (100, 132, 600, 400))
        sample.fill((0, 0, 0), (100, 132, 150, 100))
        coarse = (0.101, 0.14, 0.895, 0.9)
        bounds = _keyquest_refine_tile_bounds(sample, coarse, 4)
        assert max(abs(a - b) for a, b in zip(bounds, (0.125, 0.22, 0.875, 532.0 / 600))) < 0.004
        tiles, _, signatures = _keyquest_tile_scan(sample, bounds, 4)
        assert tiles[0] == 0 and len(signatures[0]) == 25
        sample.fill((178, 143, 104))
        positions = ((288, 90), (408, 90), (288, 225), (408, 225))
        for position, color in zip(positions, ((218, 0, 0), (0, 0, 185), (0, 218, 0), (210, 196, 0))):
            sample.fill(color, position + (96, 111))
        marked = (0.17, 0.09, 0.85, 0.85)
        assert not _keyquest_color_layout(_keyquest_color_sample(sample, marked))
        pads = _keyquest_color_centers(sample, marked)
        assert len(pads) == 4
        assert _keyquest_color_layout(_keyquest_color_sample(sample, marked, pads)) == (0, 1, 2, 3)
        idle = ((218, 0, 0), (0, 0, 185), (0, 218, 0), (210, 196, 0))
        dim_flash = ((250, 4, 3),) + idle[1:]
        assert _keyquest_flash(idle, dim_flash, None) == 0

    assert _keyquest_color_layout(((0, 0, 194), (214, 0, 0), (215, 207, 0), (1, 207, 0))) == (1, 0, 3, 2)
    dark_signatures = {0: ((0, 0, 0),) * 9, 1: ((19, 21, 25),) * 9, 2: ((220, 170, 80),) * 9}
    old_tiles, new_tiles = (1, 0, 2), (0, 1, 2)
    dark_moved = tuple(dark_signatures[tile] for tile in new_tiles)
    assert _keyquest_observe_tiles(dark_moved, dark_signatures, old_tiles, new_tiles) == new_tiles
    ambiguous = (((9, 10, 12),) * 9,) * 2 + (dark_signatures[2],)
    assert _keyquest_observe_tiles(ambiguous, dark_signatures, old_tiles, new_tiles) is None
    log_board = (2, 3, 0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
    log_expected = _keyquest_slide_tile(log_board, 6)
    log_reference = tuple(((0, 0, 0),) * 9 if not tile else
                          ((100 + tile * 4, 150, 140),) * 9 for tile in log_board)
    log_frame = list(log_reference)
    log_frame[2] = ((163, 186, 176),) * 9
    log_frame[6] = ((36, 36, 36),) * 9
    log_signatures = dict(zip(log_board, log_reference))
    assert _keyquest_observe_tiles(log_frame, log_signatures, log_board, log_expected) is None
    assert _keyquest_tile_transition(log_frame, log_reference, log_board, log_expected) == log_expected
    assert _keyquest_tile_transition(log_reference, log_reference, log_board, log_expected) == log_board
    log_frame[7] = ((15, 15, 15),) * 9
    assert _keyquest_tile_transition(log_frame, log_reference, log_board, log_expected) is None

    def _test_press_color(index):
        _test_pressed.append(index)
        if _test_reject_color:
            _keyquest_color_label("minigame_repeat_pattern_wrong_button", True)
    board = (0.30, 0.31, 0.95, 0.94)
    assert _keyquest_tile_stop_position(board, 1280, 720, 112, 48) == (1163, 5)
    assert _keyquest_tile_stop_position((0.0, 0.0, 1.0, 1.0), 1280, 720, 112, 48) is None
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

    import random as _test_random
    _test_goal4 = tuple(range(1, 16)) + (0,)
    ranked = [(str(i), i) for i in range(15, 0, -1)]
    real_example = (1, 2, 3, 4, 5, 9, 7, 8, 6, 13, 10, 11, 0, 14, 15, 12)
    assert _keyquest_numbered_goal(ranked, real_example, 4) == _test_goal4
    assert not _keyquest_numbered_goal(ranked[:-1] + [("12", 1)], real_example, 4)
    broken_order = (2, 1) + _test_goal4[2:]
    assert not _keyquest_numbered_goal(ranked, broken_order, 4)
    rng = _test_random.Random(934)
    for attempt in range(12):
        current = list(_test_goal4)
        old_blank = None
        for move_number in range(120):
            blank = current.index(0)
            next_cell = rng.choice([cell for cell in _keyquest_tile_neighbors(blank, 4) if cell != old_blank])
            current[blank], current[next_cell] = current[next_cell], 0
            old_blank = blank
        for step in _keyquest_tile_moves(tuple(current), _test_goal4, 4):
            blank = current.index(0)
            assert step in _keyquest_tile_neighbors(blank, 4)
            current[blank], current[step] = current[step], 0
        assert tuple(current) == _test_goal4
    try:
        _keyquest_tile_moves((2, 1) + _test_goal4[2:], _test_goal4, 4)
        raise AssertionError("An unreachable 4 × 4 board was accepted.")
    except ValueError:
        pass
    sample = lambda: tuple(rng.randint(40, 220) for _ in range(3))
    edges = {tile: [tuple(sample() for _ in range(12)) for direction in range(4)] for tile in range(1, 16)}
    for index in range(15):
        if index % 4 != 3 and index + 1 < 15:
            edges[index + 2][3] = edges[index + 1][1]
        if index + 4 < 15:
            edges[index + 5][0] = edges[index + 1][2]
    assert _keyquest_guess_layout(tuple(current), edges, 4)[1] == _test_goal4

    def _test_slide(index, side):
        if index not in _keyquest_tile_neighbors(_test_tiles.index(0), side):
            return
        renpy.store._test_hit_count += 1
        if side == 3 and _test_hit_count == 1:
            return
        renpy.store._test_tiles = _keyquest_slide_tile(_test_tiles, index)
        if side == 4:
            renpy.store._test_dim_blank = True

label start:
    $ _test_arcade_detectors()
    $ _test_runtime_state_and_tile_crop()
    $ persistent.keyquest_minigame_boards = {"colors": (0.17, 0.17, 0.64, 0.61), "tiles": (0.30, 0.31, 0.95, 0.94)}
    $ _keyquest_minigame.mode = "colors"
    show screen _kq_test_colors
    show screen _keyquest_minigames
    $ renpy.pause(0.25, hard=True)
    $ _keyquest_begin_minigame("watch")
    show screen _kq_test_flashes
    $ renpy.pause(2.3, hard=True)
    hide screen _kq_test_flashes
    $ assert _keyquest_minigame.sequence == (0, 2, 0), _keyquest_minigame.sequence
    $ assert _keyquest_minigame.job is None
    $ assert "3 flashes recorded" in _keyquest_minigame.message
    $ _keyquest_begin_minigame("color-play")
    $ renpy.pause(2.1, hard=True)
    $ assert _test_pressed == [0, 2, 0], _test_pressed
    $ _test_colors = ("#0000c2", "#d60000", "#d7cf00", "#01cf00")
    $ _test_pressed = []
    $ _keyquest_begin_minigame("color-play")
    $ renpy.pause(2.1, hard=True)
    $ assert _test_pressed == [1, 3, 1], _test_pressed
    $ _test_pressed = []
    $ _test_reject_color = True
    $ _keyquest_begin_minigame("color-play")
    $ renpy.pause(1.6, hard=True)
    $ assert _test_pressed == [1], _test_pressed
    $ assert "rejected" in _keyquest_minigame.message

    hide screen _kq_test_colors
    hide screen _keyquest_minigames

    $ _keyquest_minigame.mode = "tiles"
    show screen _kq_test_tiles
    $ renpy.pause(0.25, hard=True)
    python:
        tiles, edges, signatures = _keyquest_tile_scan(_keyquest_frame(), _keyquest_board())
        _keyquest_minigame.tiles = tiles
        _keyquest_minigame.signatures = signatures
        # A pointer or animation can temporarily light up two blank-slot samples.
        blank_points = ((219, 210, 211), (200, 220, 207)) + signatures[0][2:]
        samples = tuple(signatures[tile] if tile else blank_points for tile in tiles)
        assert _keyquest_observe_tiles(samples, signatures, tiles, None) == tiles
        target = list(tiles)
        target[7], target[8] = target[8], target[7]
        _keyquest_minigame.moves = _keyquest_tile_moves(tiles, tuple(target))
        _keyquest_begin_minigame("tile-play")
    $ renpy.pause(4.0, hard=True)
    $ assert _test_hit_count == 2, _test_hit_count
    $ assert _test_tiles == _test_goal, _test_tiles
    $ assert not _keyquest_minigame.moves
    $ assert "complete" in _keyquest_minigame.message, _keyquest_minigame.message
    hide screen _kq_test_tiles
    hide screen _keyquest_minigames
    $ _keyquest_set_tile_size(4)
    $ assert _keyquest_board() is None
    $ persistent.keyquest_minigame_boards["tiles-4"] = (0.15, 0.13, 0.667, 0.64)
    $ _test_tiles = _test_goal4[:14] + (0, 15)
    show screen _kq_test_tiles(side=4, actual_bounds=(0.17, 0.17, 0.64, 0.61))
    $ renpy.pause(0.25, hard=True)
    $ _keyquest_begin_minigame("tile-scan")
    python:
        for _ in range(12):
            if renpy.get_screen("_keyquest_tile_review") is not None:
                break
            renpy.pause(0.3, hard=True)
    $ assert renpy.get_screen("_keyquest_tile_review") is not None, _keyquest_minigame.message
    $ assert len(_keyquest_minigame.tile_thumbnails) == 15
    $ assert abs(_keyquest_minigame.tile_bounds[1] - 0.17) < 0.006
    $ tiles = _keyquest_minigame.tiles
    $ _keyquest_minigame.tile_goal = tiles[:14] + (tiles[15], 0)
    python:
        goal = _keyquest_minigame.tile_goal
        _keyquest_minigame.tile_number_order = ()
        _keyquest_review_tile(0)
        _keyquest_review_tile(0)
        assert _keyquest_minigame.tile_number_order == (goal[0],)
        for tile_slot in range(1, 15):
            _keyquest_review_tile(tile_slot)
        assert _keyquest_minigame.tile_number_order is None
        assert _keyquest_minigame.tile_goal == goal
    $ _keyquest_review_tile(0)
    $ _keyquest_review_tile(1)
    $ _keyquest_confirm_layout()
    $ assert renpy.get_screen("_keyquest_tile_review") is not None
    $ _keyquest_review_tile(0)
    $ _keyquest_review_tile(1)
    $ _keyquest_confirm_layout()
    $ assert _keyquest_minigame.moves
    $ _keyquest_begin_minigame("tile-play")
    $ _test_tiles = _keyquest_slide_tile(_test_tiles, 10)
    $ renpy.pause(2.25, hard=True)
    $ assert _test_hit_count == 4, _test_hit_count
    $ assert _test_tiles == _test_goal4, _test_tiles
    $ assert not _keyquest_minigame.moves
    $ assert "complete" in _keyquest_minigame.message, _keyquest_minigame.message
    hide screen _keyquest_minigames
    $ _test_dim_blank = False
    $ _test_tiles = (0,) + tuple(range(2, 17))
    $ renpy.pause(0.25, hard=True)
    python:
        tiles, _, signatures = _keyquest_tile_scan(_keyquest_frame(), _keyquest_minigame.tile_bounds, 4)
        _keyquest_minigame.tiles = tiles
        _keyquest_minigame.signatures = signatures
        _keyquest_minigame.tile_frame = None
        _keyquest_minigame.moves = (1, 2, 6)
        _keyquest_begin_minigame("tile-play")
    $ renpy.pause(3.5, hard=True)
    $ assert _test_tiles == log_expected, _test_tiles
    $ assert _test_hit_count == 7, _test_hit_count
    $ assert "complete" in _keyquest_minigame.message, _keyquest_minigame.message
    $ print("Keyquest minigame detection and verified clicks passed.")
    hide screen _keyquest_minigames
    hide screen _kq_test_tiles
    $ _keyquest_minigame.mode = "timing"
    show screen _kq_test_timing_track
    $ renpy.pause(0.2, hard=True)
    $ _keyquest_begin_minigame("timing")
    $ renpy.pause(0.55, hard=True)
    $ assert _test_timing_clicks == 0, _test_timing_clicks
    $ _test_timing_y = 0.32
    $ renpy.pause(0.6, hard=True)
    $ assert _test_timing_clicks == 1, _test_timing_clicks
    $ _test_timing_y = 0.46
    $ renpy.pause(0.35, hard=True)
    $ _test_timing_y = 0.33
    $ renpy.pause(0.45, hard=True)
    $ assert _test_timing_clicks == 2, _test_timing_clicks
    $ _keyquest_stop_minigame()
    hide screen _kq_test_timing_track
    $ _keyquest_minigame.mode = "paddle"
    show screen _kq_test_paddle_court
    $ renpy.pause(0.2, hard=True)
    $ _keyquest_begin_minigame("paddle")
    $ renpy.pause(0.55, hard=True)
    $ assert any(abs(x - config.screen_width * 0.24) <= 3 and abs(y - config.screen_height * 0.41) < 9 for x, y in _test_paddle_motions), _test_paddle_motions
    $ _keyquest_stop_minigame()
    $ print("Keyquest paddle tracking and one timing tap per pass worked.")
    $ renpy.quit()

screen _kq_test_timing_track():
    add Solid("#bba579")
    add Solid("#d81914") xpos 0.35 ypos 0.22 xysize (6, int(config.screen_height * 0.2))
    add Solid("#163fc8") xpos 0.349 ypos _test_timing_y xysize (15, 7)
    key "mouseup_1" action Function(_test_timing_press, _update_screens=False)

screen _kq_test_paddle_court():
    add Solid("#364b35")
    add Solid("#efe8ca") xpos 0.47 ypos 0.40 xysize (13, 13)
    add _TestPaddleMotion()

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
            action Function(_test_press_color, index, _update_screens=False)

screen _kq_test_flashes():
    timer 0.60 action SetVariable("_test_colors", ("#ffaaaa", "#0000c2", "#01cf00", "#d7cf00"))
    timer 0.85 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#01cf00", "#d7cf00"))
    timer 1.10 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#baffba", "#d7cf00"))
    timer 1.35 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#01cf00", "#d7cf00"))
    timer 1.60 action SetVariable("_test_colors", ("#ffaaaa", "#0000c2", "#01cf00", "#d7cf00"))
    timer 1.85 action SetVariable("_test_colors", ("#d60000", "#0000c2", "#01cf00", "#d7cf00"))
    timer 2.05 action Function(_keyquest_color_label, "minigame_repeat_pattern_interaction_phase_start", True)

screen _kq_test_tiles(side=3, actual_bounds=None):
    $ bounds = actual_bounds or _keyquest_board()
    $ palette = ("#000", "#f99", "#9f9", "#99f", "#ff9", "#f9f", "#9ff", "#aaa", "#a92", "#845", "#585", "#395", "#123", "#746", "#376", "#ac3", "#bf3")
    for index, tile in enumerate(_test_tiles):
        $ point = _keyquest_board_point(bounds, side, index)
        button:
            pos point
            anchor (0.5, 0.5)
            xysize (int(config.screen_width * (bounds[2] - bounds[0]) / side), int(config.screen_height * (bounds[3] - bounds[1]) / side))
            background Solid("#242424" if tile == 0 and _test_dim_blank else palette[tile])
            action Function(_test_slide, index, side)
