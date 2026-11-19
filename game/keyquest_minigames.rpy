# Local helpers for a four-color memory board and 3 by 3 and 4 by 4 sliding puzzles.

default persistent.keyquest_minigame_boards = {}

init python:
    import time as _kq_puzzle_time

    class _KeyquestMinigameState(object):
        mode = "colors"
        job = None
        corner = None
        message = ""
        deadline = 0.0
        sequence = ()
        baseline = None
        lit = None
        tile_result = None
        tile_busy = False
        tile_generation = 0
        tile_side = 3
        tile_goal = ()
        tile_thumbnails = {}
        tile_picked = None
        tiles = ()
        moves = ()
        signatures = {}
        pending = None
        next_tap = 0.0

    _keyquest_minigame = _KeyquestMinigameState()
    _keyquest_color_names = ("Red", "Blue", "Green", "Yellow")

    def _keyquest_stop_minigame():
        state = _keyquest_minigame
        state.job = None
        state.pending = None
        state.tile_generation += 1
        for panel in ("_keyquest_minigame_picker", "_keyquest_minigame_run", "_keyquest_minigame_delay", "_keyquest_tile_review"):
            renpy.hide_screen(panel)

    config.after_load_callbacks.append(_keyquest_stop_minigame)

    def _keyquest_show_minigame(message="", clear_moves=False):
        state = _keyquest_minigame
        _keyquest_stop_minigame()
        state.message = message
        if clear_moves:
            state.moves = ()
            state.tile_goal = ()
            state.tile_thumbnails = {}
        renpy.show_screen("_keyquest_minigames")
        renpy.restart_interaction()

    def _keyquest_minigame_mode(mode):
        _keyquest_minigame.mode = mode
        _keyquest_minigame.message = ""

    def _keyquest_set_tile_size(side):
        state = _keyquest_minigame
        if state.tile_side != side:
            _keyquest_stop_minigame()
            state.tile_side = side
            state.moves = ()
            state.tile_goal = ()
            state.tile_thumbnails = {}
            state.message = ""

    def _keyquest_board_setup():
        state = _keyquest_minigame
        state.corner = None
        state.moves = ()
        state.tile_goal = ()
        state.tile_thumbnails = {}
        renpy.hide_screen("_keyquest_minigames")
        renpy.show_screen("_keyquest_minigame_picker")

    def _keyquest_valid_board(first, second):
        return second[0] - first[0] >= 0.09 and second[1] - first[1] >= 0.09

    class _KeyquestBoardPicker(renpy.Displayable):
        def render(self, width, height, st, at):
            return renpy.Render(config.screen_width, config.screen_height)

        def event(self, ev, x, y, st):
            import pygame
            if ev.type != pygame.MOUSEBUTTONUP or getattr(ev, "button", 0) != 1:
                return
            state = _keyquest_minigame
            point = (x / float(config.screen_width), y / float(config.screen_height))
            if not (0 <= point[0] <= 1 and 0 <= point[1] <= 1):
                return
            if state.corner is None:
                state.corner = point
                renpy.restart_interaction()
            elif _keyquest_valid_board(state.corner, point):
                boards = dict(persistent.keyquest_minigame_boards)
                boards[_keyquest_board_key()] = state.corner + point
                persistent.keyquest_minigame_boards = boards
                state.sequence = () if state.mode == "colors" else state.sequence
                _keyquest_show_minigame("Board saved.")
            else:
                state.corner = None
                renpy.restart_interaction()
            raise renpy.IgnoreEvent()

    def _keyquest_board_key():
        state = _keyquest_minigame
        if state.mode == "tiles" and state.tile_side == 4:
            return "tiles-4"
        return state.mode

    def _keyquest_board():
        return persistent.keyquest_minigame_boards.get(_keyquest_board_key())

    def _keyquest_board_point(board, side, index, u=0.5, v=0.5):
        left, top, right, bottom = board
        return (left + (right - left) * (index % side + u) / side,
                top + (bottom - top) * (index // side + v) / side)

    def _keyquest_frame():
        return renpy.display.draw.screenshot(renpy.game.interface.surftree)

    def _keyquest_sample(frame, point):
        width, height = frame.get_size()
        x, y = int(point[0] * width), int(point[1] * height)
        return tuple(frame.get_at((min(width - 1, max(0, x)), min(height - 1, max(0, y)))))[:3]

    def _keyquest_cell_samples(frame, board, side, index, locations):
        return tuple(_keyquest_sample(frame, _keyquest_board_point(board, side, index, u, v)) for u, v in locations)

    def _keyquest_color_sample(frame, board):
        result = []
        locations = ((0.5, 0.5), (0.35, 0.35), (0.65, 0.35), (0.35, 0.65), (0.65, 0.65))
        for index in range(4):
            points = _keyquest_cell_samples(frame, board, 2, index, locations)
            result.append(tuple(sorted(point[c] for point in points)[2] for c in range(3)))
        return tuple(result)

    def _keyquest_color_layout(colors):
        red, blue, green, yellow = colors
        return (red[0] - max(red[1:]) >= 40 and blue[2] - max(blue[:2]) >= 40
                and green[1] - max(green[0], green[2]) >= 40
                and min(yellow[:2]) - yellow[2] >= 40)

    def _keyquest_flash(baseline, colors, current):
        changes = [sum(abs(a - b) for a, b in zip(old, new)) for old, new in zip(baseline, colors)]
        order = sorted(range(4), key=lambda index: changes[index], reverse=True)
        largest, second = order[:2]
        if changes[largest] < 32:
            return None
        if changes[largest] >= 52 and changes[second] < 45:
            return largest
        return current

    def _keyquest_append_color(index):
        state = _keyquest_minigame
        if len(state.sequence) < 32:
            state.sequence += (index,)

    def _keyquest_begin_minigame(job):
        state = _keyquest_minigame
        _keyquest_stop_minigame()
        _keyquest_ocr_reset()
        if renpy.has_screen("_keyquest_runner"):
            _keyquest_stop_task()
        state.job = job
        state.message = ""
        state.deadline = _kq_puzzle_time.time() + (22 + len(state.moves) if job == "tile-play" else 22)
        state.next_tap = 0.0
        if job == "tile-scan":
            state.moves = ()
            state.tile_goal = ()
            state.tile_thumbnails = {}
        if job == "watch":
            state.sequence = ()
            state.baseline = None
            state.lit = None
        if job == "color-play":
            state.pending = tuple(state.sequence)
        renpy.hide_screen("_keyquest_minigames")
        renpy.show_screen("_keyquest_minigame_delay")

    def _keyquest_puzzle_click(index, side):
        import pygame
        x, y = _keyquest_board_point(_keyquest_board(), side, index)
        point = tuple(map(int, renpy.display.draw.untranslate_point(int(x * config.screen_width), int(y * config.screen_height))))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point, touch=False, which=0))

    def _keyquest_tile_neighbors(index, side=3):
        return tuple(other for other in (index - side, index + side, index - 1, index + 1)
                     if 0 <= other < side * side
                     and abs(index // side - other // side) + abs(index % side - other % side) == 1)

    def _keyquest_tile_parity(board, side=3):
        tiles = [tile for tile in board if tile]
        inversions = sum(a > b for index, a in enumerate(tiles) for b in tiles[index + 1:])
        blank_row = board.index(0) // side if side % 2 == 0 else 0
        return (inversions + blank_row) % 2

    def _keyquest_tile_moves(board, target, side=3):
        import heapq

        if _keyquest_tile_parity(board, side) != _keyquest_tile_parity(target, side):
            raise ValueError("The selected tile arrangement cannot be reached.")
        if side == 4:
            return _keyquest_place_tile_groups(board, target, side)
        goals = {tile: index for index, tile in enumerate(target)}
        def distance(state):
            return sum(abs(index // 3 - goals[tile] // 3) + abs(index % 3 - goals[tile] % 3)
                       for index, tile in enumerate(state) if tile)

        queue = [(distance(board), 0, board)]
        visited = {board: (0, None, None)}
        while queue:
            _, cost, current = heapq.heappop(queue)
            if current == target:
                moves = []
                while visited[current][1] is not None:
                    _, previous, step = visited[current]
                    moves.append(step)
                    current = previous
                return tuple(reversed(moves))
            if cost != visited[current][0]:
                continue
            blank = current.index(0)
            for neighbor in _keyquest_tile_neighbors(blank):
                next_board = list(current)
                next_board[blank], next_board[neighbor] = next_board[neighbor], 0
                next_board = tuple(next_board)
                known = visited.get(next_board)
                if known is None or cost + 1 < known[0]:
                    visited[next_board] = (cost + 1, current, neighbor)
                    heapq.heappush(queue, (cost + 1 + distance(next_board), cost + 1, next_board))
        raise ValueError("Unable to plan a solution.")

    def _keyquest_place_tile_groups(board, target, side):
        from collections import deque

        # Solve each outer row and column, placing their final two tiles together.
        # Only the blank and the tiles in the current group matter to this search.
        groups = []
        for offset in range(side - 2):
            row = tuple(offset * side + column for column in range(offset, side))
            column = tuple(line * side + offset for line in range(offset + 1, side))
            groups.extend((cell,) for cell in row[:-2])
            groups.append(row[-2:])
            groups.extend((cell,) for cell in column[:-2])
            groups.append(column[-2:])
        fixed = set()
        current = list(board)
        path = []
        neighbors = tuple(_keyquest_tile_neighbors(i, side) for i in range(len(board)))

        for group in groups:
            start = (current.index(0),) + tuple(current.index(target[cell]) for cell in group)
            queue = deque([start])
            previous = {start: None}
            while queue:
                state = queue.popleft()
                if state[1:] == group:
                    steps = []
                    while previous[state] is not None:
                        steps.append(state[0])
                        state = previous[state]
                    for step in reversed(steps):
                        blank = current.index(0)
                        current[blank], current[step] = current[step], 0
                        path.append(step)
                    fixed.update(group)
                    break
                blank = state[0]
                for step in neighbors[blank]:
                    if step in fixed:
                        continue
                    new = (step,) + tuple(blank if tile == step else tile for tile in state[1:])
                    if new not in previous:
                        previous[new] = state
                        queue.append(new)
            else:
                raise ValueError("Unable to place the next tile group.")

        # Four unlocked cells remain. A full-state BFS here is tiny.
        start = tuple(current)
        queue = deque([start])
        previous = {start: None}
        while queue:
            state = queue.popleft()
            if state == target:
                steps = []
                while previous[state] is not None:
                    steps.append(state.index(0))
                    state = previous[state]
                return tuple(path) + tuple(reversed(steps))
            blank = state.index(0)
            for step in neighbors[blank]:
                if step in fixed:
                    continue
                new = list(state)
                new[blank], new[step] = new[step], 0
                new = tuple(new)
                if new not in previous:
                    previous[new] = state
                    queue.append(new)
        raise ValueError("Unable to solve the final four tiles.")

    _keyquest_tile_centers = tuple((u, v) for v in (0.25, 0.5, 0.75) for u in (0.25, 0.5, 0.75))
    _keyquest_tile_edges = (
        tuple((i / 24.0, 0.035) for i in range(2, 23)),
        tuple((0.965, i / 24.0) for i in range(2, 23)),
        tuple((i / 24.0, 0.965) for i in range(2, 23)),
        tuple((0.035, i / 24.0) for i in range(2, 23)),
    )

    def _keyquest_pixel_difference(a, b):
        return sum(abs(value - other) for p, q in zip(a, b) for value, other in zip(p, q)) / float(len(a) * 3)

    def _keyquest_tile_scan(frame, board, side=3):
        centers = tuple(_keyquest_cell_samples(frame, board, side, index, _keyquest_tile_centers)
                        for index in range(side * side))
        empty = [index for index, points in enumerate(centers) if sum(max(p) <= 31 for p in points) >= 8]
        if len(empty) != 1:
            raise ValueError("A single dark empty slot was not found. Check the board corners.")
        tiles = tuple(index + 1 if index != empty[0] else 0 for index in range(side * side))
        edges = {tile: tuple(_keyquest_cell_samples(frame, board, side, index, edge)
                             for edge in _keyquest_tile_edges)
                 for index, tile in enumerate(tiles) if tile}
        return tiles, edges, dict(zip(tiles, centers))

    def _keyquest_guess_layout(tiles, edges, side=3):
        import itertools

        right = {(a, b): _keyquest_pixel_difference(edges[a][1], edges[b][3]) for a in edges for b in edges}
        below = {(a, b): _keyquest_pixel_difference(edges[a][2], edges[b][0]) for a in edges for b in edges}
        parity = _keyquest_tile_parity(tiles, side)
        if side == 4:
            return _keyquest_beam_layout(tuple(sorted(edges)), right, below, parity, side)
        scored = []
        for a, b, c, d, e, f, g, h in itertools.permutations(sorted(edges)):
            score = (right[a, b] + right[b, c] + right[d, e] + right[e, f] + right[g, h]
                     + below[a, d] + below[b, e] + below[c, f] + below[d, g] + below[e, h])
            scored.append((score, (a, b, c, d, e, f, g, h, 0)))
        scored.sort()
        return next((score, target, scored[1][0] - score) for score, target in scored
                    if _keyquest_tile_parity(target) == parity)

    def _keyquest_beam_layout(ids, right, below, parity, side):
        import heapq

        # Retain a bounded set of the lowest-cost partial pictures. A 15! search
        # would be impractical on the headset.
        beam = [(0.0, (), ids)]
        for index in range(len(ids)):
            candidates = []
            for cost, placed, remaining in beam:
                for tile in remaining:
                    score = cost
                    if index % side:
                        score += right[placed[-1], tile]
                    if index >= side:
                        score += below[placed[index - side], tile]
                    candidates.append((score, placed + (tile,), tuple(t for t in remaining if t != tile)))
            beam = heapq.nsmallest(1024, candidates)
        score, placed, _ = beam[0]
        target = placed + (0,)
        if _keyquest_tile_parity(target, side) != parity:
            return score, target, 0
        return score, target, beam[1][0] - score

    def _keyquest_tile_thumbnails(frame, board, tiles, side, generation):
        import io

        width, height = frame.get_size()
        previews = {}
        for index, tile in enumerate(tiles):
            if not tile:
                continue
            a = _keyquest_board_point(board, side, index, 0.015, 0.015)
            b = _keyquest_board_point(board, side, index, 0.985, 0.985)
            left, top = int(a[0] * width), int(a[1] * height)
            right, bottom = int(b[0] * width), int(b[1] * height)
            piece = frame.subsurface((left, top, right - left, bottom - top))
            piece = renpy.display.scale.smoothscale(piece, (64, 46))
            with io.BytesIO() as out:
                renpy.display.module.save_png(piece, out, 0)
                previews[tile] = im.Data(out.getvalue(), "keyquest-tile-%d-%d.png" % (generation, tile))
        return previews

    def _keyquest_open_review():
        state = _keyquest_minigame
        state.tile_picked = None
        renpy.hide_screen("_keyquest_minigames")
        renpy.show_screen("_keyquest_tile_review")

    def _keyquest_review_tile(index):
        state = _keyquest_minigame
        previous = state.tile_picked
        if previous is None:
            state.tile_picked = index
        else:
            goal = list(state.tile_goal)
            goal[index], goal[previous] = goal[previous], goal[index]
            state.tile_goal = tuple(goal)
            state.tile_picked = None
            state.moves = ()
            state.message = ""

    def _keyquest_confirm_layout():
        state = _keyquest_minigame
        try:
            state.moves = _keyquest_tile_moves(state.tiles, state.tile_goal, state.tile_side)
        except ValueError as error:
            state.message = str(error) + " Adjust the picture layout."
            return
        _keyquest_show_minigame("%d tile moves ready." % len(state.moves) if state.moves else "The picture is already arranged.")

    def _keyquest_make_plan():
        import threading

        state = _keyquest_minigame
        if state.tile_busy:
            return
        side = state.tile_side
        frame, board = _keyquest_frame(), _keyquest_board()
        tiles, edges, signatures = _keyquest_tile_scan(frame, board, side)
        generation = state.tile_generation
        if side == 4:
            state.tile_thumbnails = _keyquest_tile_thumbnails(frame, board, tiles, side, generation)
        state.tile_result = None
        state.tile_busy = True

        def plan():
            try:
                _, target, confidence = _keyquest_guess_layout(tiles, edges, side)
                if side == 4:
                    result = (tiles, signatures, (), target, confidence, None)
                else:
                    if confidence < 7:
                        raise ValueError("Tile edges are ambiguous. Recheck the board corners, then scan again.")
                    result = (tiles, signatures, _keyquest_tile_moves(tiles, target, side), (), confidence, None)
            except Exception as error:
                result = (None, None, (), (), 0, str(error))
            state.tile_result = generation, result
            state.tile_busy = False

        thread = threading.Thread(target=plan)
        thread.daemon = True
        try:
            thread.start()
        except Exception:
            state.tile_busy = False
            raise

    def _keyquest_same_tiles(expected, signatures, side):
        points = _keyquest_tile_centers
        frame, board = _keyquest_frame(), _keyquest_board()
        for index, tile in enumerate(expected):
            colors = _keyquest_cell_samples(frame, board, side, index, points)
            if _keyquest_pixel_difference(colors, signatures[tile]) > 19:
                return False
        return True

    def _keyquest_step_tiles(state, now):
        if state.pending is not None:
            expected, until = state.pending
            if _keyquest_same_tiles(expected, state.signatures, state.tile_side):
                state.tiles = expected
                state.moves = state.moves[1:]
                state.pending = None
                if not state.moves:
                    _keyquest_show_minigame("The planned tile moves are complete.")
                elif state.job == "tile-step":
                    _keyquest_show_minigame("Move checked. %d remaining." % len(state.moves))
                else:
                    state.next_tap = now + 0.15
            elif now > until:
                message = "Last move sent. Check the game result." if len(state.moves) == 1 else "The board did not move as expected. Scan it again."
                _keyquest_show_minigame(message, clear_moves=True)
            return
        if not _keyquest_same_tiles(state.tiles, state.signatures, state.tile_side):
            _keyquest_show_minigame("The board changed. Scan it again.", clear_moves=True)
            return
        index = state.moves[0]
        blank = state.tiles.index(0)
        expected = list(state.tiles)
        expected[blank], expected[index] = expected[index], 0
        state.pending = tuple(expected), now + 1.4
        _keyquest_puzzle_click(index, state.tile_side)
        state.next_tap = now + 0.23

    def _keyquest_minigame_tick():
        state = _keyquest_minigame
        job = state.job
        if job is None:
            return
        now = _kq_puzzle_time.time()
        if now > state.deadline:
            _keyquest_show_minigame("Recording ended." if job == "watch" else "The minigame helper timed out.")
            return
        if now < state.next_tap:
            return
        try:
            if job == "watch":
                colors = _keyquest_color_sample(_keyquest_frame(), _keyquest_board())
                if state.baseline is None:
                    if not _keyquest_color_layout(colors):
                        _keyquest_show_minigame("Could not find red, blue, green and yellow. Check the corners and start when the colors are idle.")
                        return
                    state.baseline = colors
                    return
                hit = _keyquest_flash(state.baseline, colors, state.lit)
                if hit != state.lit:
                    state.lit = hit
                    if hit is not None:
                        _keyquest_append_color(hit)
                        renpy.restart_interaction()
            elif job == "color-play":
                if state.next_tap == 0 and not _keyquest_color_layout(_keyquest_color_sample(_keyquest_frame(), _keyquest_board())):
                    _keyquest_show_minigame("The color board is no longer visible. Check the corners before playing.")
                    return
                if not state.pending:
                    _keyquest_show_minigame("Sequence finished. Record again for the next round.")
                    return
                _keyquest_puzzle_click(state.pending[0], 2)
                state.pending = state.pending[1:]
                state.next_tap = now + 0.48
            elif job == "tile-scan":
                if state.tile_result is None:
                    if not state.tile_busy:
                        _keyquest_make_plan()
                    return
                generation, result = state.tile_result
                state.tile_result = None
                if generation != state.tile_generation:
                    return
                tiles, signatures, moves, goal, confidence, error = result
                if error:
                    _keyquest_show_minigame(error, clear_moves=True)
                else:
                    state.tiles, state.signatures, state.moves = tiles, signatures, moves
                    state.tile_goal = goal
                    if goal:
                        _keyquest_stop_minigame()
                        state.message = ("Picture match uncertain. Tap two tiles to swap them." if confidence < 7
                                         else "Check the picture. Tap two tiles to swap them if needed.")
                        _keyquest_open_review()
                        renpy.restart_interaction()
                    else:
                        _keyquest_show_minigame("%d tile moves ready." % len(moves) if moves else "The inferred picture is already arranged.")
            else:
                _keyquest_step_tiles(state, now)
        except Exception as error:
            renpy.log("Keyquest minigame: " + repr(error))
            _keyquest_show_minigame(str(error) if isinstance(error, ValueError) else "Could not read the game board.", clear_moves=job.startswith("tile"))

screen _keyquest_minigames():
    zorder 993
    $ helper = _keyquest_minigame
    $ board = _keyquest_board()
    use _keyquest_floating("minigames", "Minigame helpers", 670, 440, (0.98, 0.4)):
        hbox:
            spacing 6
            textbutton "Color memory" style "keyquest_deck_key" selected (helper.mode == "colors") action Function(_keyquest_minigame_mode, "colors")
            textbutton "Picture tiles" style "keyquest_deck_key" selected (helper.mode == "tiles") action Function(_keyquest_minigame_mode, "tiles")
            textbutton "Back to OCR" style "keyquest_deck_key" action [Hide("_keyquest_minigames"), Show("_keyquest_smart_input")]
        if helper.mode == "tiles":
            hbox:
                spacing 6
                for side in (3, 4):
                    textbutton ("%d × %d" % (side, side)) style "keyquest_deck_key" selected (helper.tile_side == side) action Function(_keyquest_set_tile_size, side)
        textbutton ("Adjust board" if board else "Set board corners") style "keyquest_deck_key" action Function(_keyquest_board_setup)
        if helper.mode == "colors":
            text "Start recording while all four colors are idle. When the game asks you to repeat, finish recording and play the sequence." color "#b9d3e8" size 19 xmaximum 618
            text (" · ".join(_keyquest_color_names[i] for i in helper.sequence) or "No colors recorded") substitute False color "#eff8ff" size 20 xmaximum 618
            hbox:
                spacing 6
                for index, name in enumerate(_keyquest_color_names):
                    textbutton name style "keyquest_deck_key" action Function(_keyquest_append_color, index)
                textbutton "Undo" style "keyquest_deck_key" sensitive bool(helper.sequence) action SetField(helper, "sequence", helper.sequence[:-1])
                textbutton "Clear" style "keyquest_deck_key" sensitive bool(helper.sequence) action SetField(helper, "sequence", ())
            hbox:
                spacing 6
                textbutton "Record flashes" style "keyquest_deck_accent" sensitive bool(board) action Function(_keyquest_begin_minigame, "watch")
                textbutton "Play sequence" style "keyquest_deck_key" sensitive bool(board and helper.sequence) action Function(_keyquest_begin_minigame, "color-play")
        else:
            text "Choose the grid size and set the corners around the entire grid, including the empty slot. Scan to match picture edges and plan legal slides." color "#b9d3e8" size 19 xmaximum 618
            hbox:
                spacing 6
                textbutton "Scan tiles" style "keyquest_deck_accent" sensitive bool(board) action Function(_keyquest_begin_minigame, "tile-scan")
                textbutton "Play one move" style "keyquest_deck_key" sensitive bool(board and helper.moves) action Function(_keyquest_begin_minigame, "tile-step")
                textbutton "Play all moves" style "keyquest_deck_key" sensitive bool(board and helper.moves) action Function(_keyquest_begin_minigame, "tile-play")
            if helper.tile_goal:
                textbutton "Review layout" style "keyquest_deck_key" action Function(_keyquest_open_review)
        if helper.message:
            text helper.message substitute False color "#d5f6e7" size 19 xmaximum 618

screen _keyquest_tile_review():
    zorder 994
    $ helper = _keyquest_minigame
    use _keyquest_floating("tile-review", "Review 4 × 4 picture", 595, 495, (0.98, 0.35)):
        text (helper.message or "Tap two tiles to swap them.") substitute False color "#b9d3e8" size 20 xmaximum 550
        if helper.tile_goal:
            grid 4 4:
                spacing 2
                for index, tile in enumerate(helper.tile_goal):
                    if tile:
                        button:
                            background Solid("#65dec1" if helper.tile_picked == index else "#1b2c42")
                            hover_background Solid("#629ccc")
                            padding (2, 2)
                            action Function(_keyquest_review_tile, index)
                            add helper.tile_thumbnails[tile]
                    else:
                        add Solid("#08131f") xysize (68, 50)
        hbox:
            spacing 6
            textbutton "Plan moves" style "keyquest_deck_accent" sensitive bool(helper.tile_goal) action Function(_keyquest_confirm_layout)
            textbutton "Back" style "keyquest_deck_key" action Function(_keyquest_show_minigame)

screen _keyquest_minigame_picker():
    zorder 997
    modal True
    add _KeyquestBoardPicker()
    $ first = _keyquest_minigame.corner
    if first is not None:
        add Solid("#6aefcb") xysize (14, 14) pos first anchor (0.5, 0.5)
    use _keyquest_floating("minigame-picker", "Mark board corners", 535, 135, (0.5, 0.04)):
        hbox:
            spacing 8
            text ("Tap the bottom-right corner." if first else "Tap the top-left corner.") color "#eff8ff" size 20 yalign 0.5
            textbutton "Cancel" style "keyquest_deck_key" action Function(_keyquest_show_minigame)

screen _keyquest_minigame_delay():
    timer 0.16 action [Hide("_keyquest_minigame_delay"), Show("_keyquest_minigame_run")]

screen _keyquest_minigame_run():
    zorder 997
    $ helper = _keyquest_minigame
    timer (0.075 if helper.job == "watch" else 0.14) repeat True action Function(_keyquest_minigame_tick, _update_screens=False)
    use _keyquest_floating("minigame-run", "Minigame helper", 420, 180, (0.97, 0.98)):
        if helper.job == "watch":
            text ("%d flashes recorded" % len(helper.sequence)) color "#eff8ff" size 21
            textbutton "Finish recording" style "keyquest_deck_accent" action Function(_keyquest_show_minigame)
        else:
            text ("Matching tiles…" if helper.job == "tile-scan" else "Playing moves…") color "#eff8ff" size 21
            textbutton "Stop" style "keyquest_deck_key" action Function(_keyquest_show_minigame, "Stopped.")
