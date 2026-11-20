# Local helpers for memory, sliding tiles, paddle, and timing minigames.

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
        color_event = None
        color_order = ()
        color_points = ()
        tile_result = None
        tile_busy = False
        tile_generation = 0
        tile_side = 3
        tile_goal = ()
        tile_number_order = None
        tile_thumbnails = {}
        tile_picked = None
        tiles = ()
        moves = ()
        signatures = {}
        pending = None
        tile_target = ()
        tile_frame = None
        tile_bounds = None
        tile_seen = None
        tile_seen_count = 0
        tile_wait_until = 0.0
        next_tap = 0.0
        timing_armed = True
        paddle_side = "left"
        ball = None
        ball_at = 0.0

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
        if message or clear_moves:
            _keyquest_trace("minigame_ended", cleared=bool(clear_moves), remaining=len(state.moves))
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
            state.tile_bounds = None
            state.moves = ()
            state.tile_goal = ()
            state.tile_thumbnails = {}
            state.message = ""

    def _keyquest_board_setup():
        state = _keyquest_minigame
        state.corner = None
        state.tile_bounds = None
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
            elif (_keyquest_valid_board(state.corner, point) if state.mode != "timing"
                  else point[1] - state.corner[1] >= 0.15 and abs(point[0] - state.corner[0]) <= 0.06):
                boards = dict(persistent.keyquest_minigame_boards)
                if state.mode == "timing":
                    center = (state.corner[0] + point[0]) / 2.0
                    boards[_keyquest_board_key()] = (max(0, center - 0.026), state.corner[1],
                                                     min(1, center + 0.026), point[1])
                else:
                    boards[_keyquest_board_key()] = state.corner + point
                persistent.keyquest_minigame_boards = boards
                _keyquest_trace("board_calibrated", mode=_keyquest_board_key(), bounds=boards[_keyquest_board_key()])
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
        default = {"paddle": (0.22, 0.16, 0.80, 0.82), "timing": (0.318, 0.005, 0.385, 0.59)}
        key = _keyquest_board_key()
        return persistent.keyquest_minigame_boards.get(key, default.get(key))

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

    def _keyquest_color_sample(frame, board, points=None):
        result = []
        locations = ((0.5, 0.5), (0.35, 0.35), (0.65, 0.35), (0.35, 0.65), (0.65, 0.65))
        for index in range(4):
            if points:
                x, y = points[index]
                pixels = [_keyquest_sample(frame, (x + dx, y + dy)) for dx, dy in
                          ((0, 0), (-0.01, 0), (0.01, 0), (0, -0.01), (0, 0.01))]
            else:
                pixels = _keyquest_cell_samples(frame, board, 2, index, locations)
            result.append(tuple(sorted(pixel[c] for pixel in pixels)[2] for c in range(3)))
        return tuple(result)

    def _keyquest_color_index(pixel, minimum):
        red, green, blue = pixel
        scores = (red - max(green, blue), blue - max(red, green),
                  green - max(red, blue), min(red, green) - blue)
        strongest = max(scores)
        return scores.index(strongest) if strongest >= minimum else None

    def _keyquest_color_layout(colors):
        order = tuple(_keyquest_color_index(pixel, 40) for pixel in colors)
        return order if None not in order and len(set(order)) == 4 else ()

    def _keyquest_color_centers(frame, board):
        if _keyquest_color_layout(_keyquest_color_sample(frame, board)):
            return tuple(_keyquest_board_point(board, 2, index) for index in range(4))

        columns, rows = 64, 40
        cells = {}
        for y in range(rows):
            for x in range(columns):
                point = ((x + 0.5) / columns, (y + 0.5) / rows)
                left, top, right, bottom = board
                if not (left <= point[0] <= right and top <= point[1] <= bottom):
                    continue
                color = _keyquest_color_index(_keyquest_sample(frame, point), 112)
                if color is not None:
                    cells[x, y] = color
        blocks = {}
        while cells:
            start, color = cells.popitem()
            component = [start]
            for x, y in component:
                for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if cells.get(neighbor) == color:
                        del cells[neighbor]
                        component.append(neighbor)
            if len(component) < 12:
                continue
            xs, ys = zip(*component)
            left, right = min(xs), max(xs)
            top, bottom = min(ys), max(ys)
            width, height = right - left + 1, bottom - top + 1
            if min(width, height) < 3 or len(component) < width * height * 0.8:
                continue
            if color not in blocks or len(component) > blocks[color][0]:
                blocks[color] = (len(component), ((left + right + 1) / (2.0 * columns),
                                                   (top + bottom + 1) / (2.0 * rows)))
        if len(blocks) != 4 or max(block[0] for block in blocks.values()) > 2.4 * min(block[0] for block in blocks.values()):
            return ()
        points = sorted((block[1] for block in blocks.values()), key=lambda point: point[1])
        top, bottom = sorted(points[:2]), sorted(points[2:])
        if (abs(top[0][1] - top[1][1]) > 0.06 or abs(bottom[0][1] - bottom[1][1]) > 0.06
                or any(abs(a[0] - b[0]) > 0.06 or b[1] - a[1] < 0.08 for a, b in zip(top, bottom))
                or min(top[1][0] - top[0][0], bottom[1][0] - bottom[0][0]) < 0.07):
            return ()
        return tuple(top + bottom)

    def _keyquest_flash(baseline, colors, current):
        changes = [sum(abs(a - b) for a, b in zip(old, new)) for old, new in zip(baseline, colors)]
        order = sorted(range(4), key=lambda index: changes[index], reverse=True)
        largest, second = order[:2]
        if changes[largest] < 20:
            return None
        if changes[largest] >= 30 and changes[largest] - changes[second] >= 18:
            return largest
        return current

    def _keyquest_color_label(name, abnormal):
        state = _keyquest_minigame
        if state.job == "watch" and name == "minigame_repeat_pattern_interaction_phase_start":
            state.color_event = "ready"
        elif state.job == "color-play":
            if name == "minigame_repeat_pattern_wrong_button":
                state.color_event = "wrong"
            elif name in ("minigame_repeat_pattern_got_all_right", "minigame_repeat_pattern_end",
                          "minigame_repeat_pattern_interaction_phase_preparation"):
                state.color_event = "finished"

    def _keyquest_append_color(index):
        state = _keyquest_minigame
        if len(state.sequence) < 32:
            state.sequence += (index,)

    def _keyquest_tile_stop_position(board, screen_width, screen_height, width, height):
        left, top, right, bottom = board
        gap = 5
        if screen_height * (1 - bottom) >= height + 2 * gap:
            return (screen_width - width - gap, screen_height - height - gap)
        if screen_height * top >= height + 2 * gap:
            return (screen_width - width - gap, gap)
        if screen_width * (1 - right) >= width + 2 * gap:
            return (screen_width - width - gap, screen_height - height - gap)
        if screen_width * left >= width + 2 * gap:
            return (gap, screen_height - height - gap)
        return None

    def _keyquest_begin_minigame(job):
        state = _keyquest_minigame
        _keyquest_stop_minigame()
        _keyquest_ocr_reset()
        if renpy.has_screen("_keyquest_runner"):
            _keyquest_stop_task()
        state.job = job
        _keyquest_trace("minigame_started", job=job, side=state.tile_side, remaining=len(state.moves))
        state.message = ""
        duration = 120 if job in ("paddle", "timing") else 22
        state.deadline = _kq_puzzle_time.time() + duration + (len(state.moves) if job == "tile-play" else 0)
        if job in ("paddle", "timing"):
            state.ball = None
            state.timing_armed = True
        state.next_tap = 0.0
        state.color_event = None
        state.tile_seen = None
        state.tile_seen_count = 0
        state.tile_wait_until = 0.0
        if job in ("tile-play", "tile-step"):
            target = state.tiles
            for step in state.moves:
                target = _keyquest_slide_tile(target, step)
            state.tile_target = target
        if job.startswith("tile-") or job in ("watch", "color-play", "paddle", "timing"):
            for panel in ("_keyquest_keyboard", "_keyquest_values", "_keyquest_automation", "_keyquest_pick_target"):
                renpy.hide_screen(panel)
        if job == "tile-scan":
            state.tile_bounds = None
            state.tile_frame = None
            state.moves = ()
            state.tile_goal = ()
            state.tile_thumbnails = {}
        if job == "watch":
            state.sequence = ()
            state.baseline = None
            state.color_order = ()
            state.color_points = ()
            state.lit = None
        if job == "color-play":
            state.pending = tuple(state.sequence)
        renpy.hide_screen("_keyquest_minigames")
        renpy.show_screen("_keyquest_minigame_delay")

    def _keyquest_puzzle_click(index, side):
        board = _keyquest_minigame.tile_bounds if side in (3, 4) else None
        points = _keyquest_minigame.color_points if side == 2 else ()
        point = points[index] if points else _keyquest_board_point(board or _keyquest_board(), side, index)
        _keyquest_puzzle_pointer(point, click=True)

    def _keyquest_puzzle_pointer(position, click=False):
        import pygame
        x, y = position
        point = tuple(map(int, renpy.display.draw.untranslate_point(int(x * config.screen_width), int(y * config.screen_height))))
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION,
                         pos=point, rel=(0, 0), buttons=(0, 0, 0), touch=False, which=0))
        if click:
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                pygame.event.post(pygame.event.Event(kind, button=1, pos=point, touch=False, which=0))

    def _keyquest_arcade_rect(frame, bounds):
        width, height = frame.get_size()
        left, top, right, bottom = bounds
        return (int(left * width), int(top * height), int(right * width), int(bottom * height))

    def _keyquest_timing_marker(frame, bounds):
        left, top, right, bottom = _keyquest_arcade_rect(frame, bounds)
        best = ()
        rail = None
        for x in range(left, right):
            red = []
            for y in range(top, bottom):
                r, g, b = tuple(frame.get_at((x, y)))[:3]
                if r >= 145 and r - g >= 72 and r - b >= 60:
                    red.append(y)
            if not red:
                continue
            span = red[-1] - red[0] + 1
            if len(red) >= (bottom - top) * 0.05 and span <= (bottom - top) * 0.7 and len(red) >= span * 0.76:
                if len(red) > len(best):
                    best, rail = red, x
        if rail is None:
            return None
        blue = []
        for y in range(top, bottom):
            for x in range(max(left, rail - 4), min(right, rail + 5)):
                r, g, b = tuple(frame.get_at((x, y)))[:3]
                if b >= 100 and b - r >= 45 and b - g >= 30:
                    blue.append(y)
                    break
        if not blue or blue[-1] - blue[0] + 1 > max(3, (bottom - top) * 0.07):
            return None
        return (rail / float(frame.get_width()), (blue[0] + blue[-1]) / 2.0, best[0], best[-1])

    def _keyquest_timing_step(state, marker):
        if marker is None:
            return False
        _, y, top, bottom = marker
        if not top <= y <= bottom:
            state.timing_armed = True
            return False
        margin = max(1, min(3, (bottom - top) * 0.15))
        if state.timing_armed and top + margin <= y <= bottom - margin:
            state.timing_armed = False
            return True
        return False

    def _keyquest_paddle_ball(frame, bounds, previous=None):
        left, top, right, bottom = _keyquest_arcade_rect(frame, bounds)
        width, height = frame.get_size()
        diameter = max(4, int(width * 0.024))
        pixel = frame.get_at
        bright = set()
        for y in range(top + 2, bottom - 2):
            start = None
            for x in range(left + 2, right - 1):
                color = pixel((x, y))
                r, g, b = color[0], color[1], color[2]
                white = r >= 158 and g >= 158 and b >= 158 and max(r, g, b) - min(r, g, b) <= 76
                if white and x < right - 2:
                    if start is None:
                        start = x
                elif start is not None:
                    if 1 <= x - start <= diameter:
                        bright.update((i, y) for i in range(start, x))
                    start = None
        candidates = []
        while bright:
            blob = [bright.pop()]
            for x, y in blob:
                for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if point in bright:
                        bright.remove(point)
                        blob.append(point)
            if len(blob) < 5:
                continue
            xs, ys = zip(*blob)
            w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if not (3 <= w <= diameter and 3 <= h <= diameter and 0.6 <= w / float(h) <= 1.65):
                continue
            candidates.append(((min(xs) + max(xs)) / (2.0 * width),
                               (min(ys) + max(ys)) / (2.0 * height)))
        if len(candidates) == 1:
            return candidates[0]
        if candidates and previous is not None:
            ranked = sorted((abs(point[0] - previous[0]) + abs(point[1] - previous[1]), point) for point in candidates)
            if ranked[0][0] <= 0.18 and ranked[1][0] - ranked[0][0] > 0.025:
                return ranked[0][1]
        return None

    def _keyquest_paddle_target(ball, previous, bounds, side):
        left, top, right, bottom = bounds
        target_x = left if side == "left" else right
        y = ball[1]
        if previous is not None:
            dx = ball[0] - previous[0]
            if abs(dx) >= 0.004 and (target_x - ball[0]) * dx > 0:
                y += (ball[1] - previous[1]) * min(9, (target_x - ball[0]) / dx)
                height = bottom - top
                reflected = (y - top) % (height * 2)
                y = top + min(reflected, height * 2 - reflected)
        return (target_x + (0.02 if side == "left" else -0.02), min(bottom - 0.025, max(top + 0.025, y)))

    def _keyquest_arcade_tick(state, now):
        if not _keyquest_game_has_focus():
            state.ball = None
            state.timing_armed = False
            return
        size = (640, 360) if state.job == "timing" else (480, 270)
        frame = renpy.display.scale.smoothscale(_keyquest_frame(), size)
        board = _keyquest_board()
        if state.job == "timing":
            marker = _keyquest_timing_marker(frame, board)
            if _keyquest_timing_step(state, marker):
                _keyquest_puzzle_pointer((max(0.07, marker[0] - 0.06), (board[1] + board[3]) / 2.0), click=True)
                _keyquest_trace("timing_tap")
                state.next_tap = now + 0.08
        else:
            previous = state.ball if now - state.ball_at < 0.28 else None
            ball = _keyquest_paddle_ball(frame, board, previous)
            if ball is not None:
                _keyquest_puzzle_pointer(_keyquest_paddle_target(ball, previous, board, state.paddle_side))
                if previous is None:
                    _keyquest_trace("paddle_ball_found")
                state.ball, state.ball_at = ball, now


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

    def _keyquest_snap_tile_edge(frame, axis, edge, inward, span, cross_start, cross_end, side):
        width, height = frame.get_size()
        size, cross_size = (width, height) if axis == 0 else (height, width)
        origin = int(edge * size)
        radius = max(3, int(span * size / side * 0.46))
        cross = tuple(int(cross_size * (cross_start + (cross_end - cross_start) * i / 26.0))
                      for i in range(3, 24))
        best = None
        for point in range(max(3, origin - radius), min(size - 3, origin + radius + 1)):
            transitions = 0
            dark_outside = 0
            for cross_pixel in cross:
                outside = point - 2 * inward
                inside = point + 2 * inward
                before = max(frame.get_at((outside, cross_pixel) if axis == 0 else (cross_pixel, outside))[:3])
                after = max(frame.get_at((inside, cross_pixel) if axis == 0 else (cross_pixel, inside))[:3])
                if before <= 34:
                    dark_outside += 1
                    if after >= 74 and after - before >= 48:
                        transitions += 1
            if transitions * 2 >= len(cross) and dark_outside * 3 >= len(cross) * 2:
                candidate = (transitions, -abs(point - origin), point)
                if best is None or candidate > best:
                    best = candidate
        return best[2] / float(size) if best else edge

    def _keyquest_refine_tile_bounds(frame, board, side):
        left, top, right, bottom = board
        width, height = right - left, bottom - top
        bounds = (
            _keyquest_snap_tile_edge(frame, 0, left, 1, width, top, bottom, side),
            _keyquest_snap_tile_edge(frame, 1, top, 1, height, left, right, side),
            _keyquest_snap_tile_edge(frame, 0, right, -1, width, top, bottom, side),
            _keyquest_snap_tile_edge(frame, 1, bottom, -1, height, left, right, side),
        )
        return bounds if _keyquest_valid_board(bounds[:2], bounds[2:]) else board

    def _keyquest_dark_tile(pixels, level, numerator, denominator):
        return sum(max(pixel) <= level for pixel in pixels) * denominator >= len(pixels) * numerator

    _keyquest_tile_centers = tuple((u, v) for v in (0.18, 0.34, 0.5, 0.66, 0.82) for u in (0.18, 0.34, 0.5, 0.66, 0.82))
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
        empty = [index for index, points in enumerate(centers) if _keyquest_dark_tile(points, 31, 8, 9)]
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
            piece = renpy.display.scale.smoothscale(piece, (120, 72))
            with io.BytesIO() as out:
                renpy.display.module.save_png(piece, out, 0)
                previews[tile] = im.Data(out.getvalue(), "keyquest-tile-%d-%d.png" % (generation, tile))
        return previews

    def _keyquest_open_review():
        state = _keyquest_minigame
        state.tile_picked = None
        state.tile_number_order = None
        renpy.hide_screen("_keyquest_minigames")
        renpy.show_screen("_keyquest_tile_review")

    def _keyquest_review_tile(index):
        state = _keyquest_minigame
        if state.tile_number_order is not None:
            tile = state.tile_goal[index]
            if tile not in state.tile_number_order:
                state.tile_number_order += (tile,)
                if len(state.tile_number_order) == len(state.tile_goal) - 1:
                    state.tile_goal = state.tile_number_order + (0,)
                    state.tile_number_order = None
                    state.moves = ()
                    state.message = "Number order set. Plan moves when ready."
            return
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

    def _keyquest_numbered_goal(labels, tiles, side):
        ordered = []
        for value, tile in labels:
            value = value.strip()
            if not value or len(value) > 2 or any(c not in "0123456789" for c in value):
                return ()
            ordered.append((int(value), tile))
        ordered.sort()
        if [value for value, tile in ordered] != list(range(1, side * side)):
            return ()
        target = tuple(tile for value, tile in ordered) + (0,)
        return target if _keyquest_tile_parity(tiles, side) == _keyquest_tile_parity(target, side) else ()

    def _keyquest_tile_number_images(frame, board, tiles, side):
        import io

        width, height = frame.get_size()
        images = []
        for index, tile in enumerate(tiles):
            if tile:
                a = _keyquest_board_point(board, side, index, 0.27, 0.22)
                b = _keyquest_board_point(board, side, index, 0.73, 0.78)
                left, top = int(a[0] * width), int(a[1] * height)
                piece = frame.subsurface((left, top, int(b[0] * width) - left, int(b[1] * height) - top))
                piece_width, piece_height = piece.get_size()
                scale = 160.0 / max(piece_width, piece_height)
                piece = renpy.display.scale.smoothscale(piece, (max(1, int(piece_width * scale)), max(1, int(piece_height * scale))))
                with io.BytesIO() as out:
                    renpy.display.module.save_png(piece, out, 0)
                    images.append((out.getvalue(), tile))
        return images

    def _keyquest_make_plan():
        import threading

        state = _keyquest_minigame
        if state.tile_busy or (renpy.android and _keyquest_vision.busy):
            return
        side = state.tile_side
        frame, original = _keyquest_frame(), _keyquest_board()
        board = _keyquest_refine_tile_bounds(frame, original, side)
        state.tile_bounds = board
        _keyquest_trace("tile_crop", original=original, bounds=board, frame=frame.get_size())
        tiles, edges, signatures = _keyquest_tile_scan(frame, board, side)
        generation = state.tile_generation
        if side == 4:
            state.tile_thumbnails = _keyquest_tile_thumbnails(frame, board, tiles, side, generation)
        images, model_root = (), None
        if renpy.android and not _keyquest_vision.unavailable:
            try:
                from jnius import autoclass
                activity = autoclass("org.renpy.android.PythonSDLActivity").mActivity
                model_root = activity.getCodeCacheDir().getAbsolutePath()
                images = _keyquest_tile_number_images(frame, board, tiles, side)
            except Exception as error:
                _keyquest_trace("tile_number_capture_failed", kind=type(error).__name__)
        state.tile_result = None
        state.tile_busy = True
        if images:
            _keyquest_vision.busy = True

        def plan():
            try:
                numbered = ()
                if images:
                    try:
                        if _keyquest_vision.engine is None:
                            _keyquest_vision.prepare(model_root)
                        labels = []
                        for image, tile in images:
                            value = ""
                            for scan_mode in ("digits-light", "digits-light-word", "digits"):
                                value = _keyquest_vision.engine.recognize(image, "full", scan_mode)
                                if value.isdigit() and 1 <= int(value) < side * side:
                                    break
                            labels.append((value, tile))
                        numbered = _keyquest_numbered_goal(labels, tiles, side)
                        recognized = [int(value) for value, _ in labels if value.isdigit() and 1 <= int(value) < side * side]
                        _keyquest_trace("tile_labels", read=len(recognized), unique=len(set(recognized)), total=len(labels))
                    except Exception as error:
                        _keyquest_trace("tile_number_scan_failed", kind=type(error).__name__)
                    finally:
                        _keyquest_vision.busy = False
                if numbered:
                    target, confidence = numbered, 100
                else:
                    _, target, confidence = _keyquest_guess_layout(tiles, edges, side)
                if side == 4:
                    result = (tiles, signatures, (), target, confidence, bool(numbered), None)
                else:
                    if confidence < 7:
                        raise ValueError("Tile edges are ambiguous. Recheck the board corners, then scan again.")
                    result = (tiles, signatures, _keyquest_tile_moves(tiles, target, side), (), confidence, bool(numbered), None)
            except Exception as error:
                result = (None, None, (), (), 0, False, str(error))
            state.tile_result = generation, result
            state.tile_busy = False

        thread = threading.Thread(target=plan)
        thread.daemon = True
        try:
            thread.start()
        except Exception:
            state.tile_busy = False
            if images:
                _keyquest_vision.busy = False
            raise

    def _keyquest_slide_tile(tiles, index):
        moved = list(tiles)
        blank = tiles.index(0)
        moved[blank], moved[index] = moved[index], 0
        return tuple(moved)

    def _keyquest_tile_appearance(colors, reference):
        # Ignore the largest local changes, such as the pointer or a tile label.
        distances = sorted(sum(abs(a - b) for a, b in zip(pixel, original)) / 3.0
                           for pixel, original in zip(colors, reference))
        kept = len(distances) - len(distances) * 2 // 9
        return sum(distances[:kept]) / float(kept)

    def _keyquest_tile_transition(samples, previous, current, expected):
        if previous is None:
            return None
        changes = [_keyquest_tile_appearance(pixels, old) for pixels, old in zip(samples, previous)]
        if max(changes) <= 10:
            return current
        if expected is None:
            return None
        destination = current.index(0)
        source = expected.index(0)
        if any(change > 24 for index, change in enumerate(changes) if index not in (source, destination)):
            return None
        # A legal slide changes two cells. Compare with the frame immediately
        # before the tap, since calibration can sample a moved tile differently.
        moved = _keyquest_tile_appearance(samples[destination], previous[source])
        blank = _keyquest_tile_appearance(samples[source], previous[destination])
        dark = _keyquest_dark_tile(samples[source], 42, 5, 9)
        if (changes[source] >= 10 and moved <= 48 and moved + 8 <= changes[destination]
                and (dark or blank + 8 <= changes[source]
                     or (moved <= 18 and changes[source] >= 52))):
            return expected
        return None

    def _keyquest_observe_tiles(samples, signatures, current, expected):
        empty = [index for index, pixels in enumerate(samples) if _keyquest_dark_tile(pixels, 31, 7, 9)]
        matching = []
        for board in (expected, current):
            if board is None or board.index(0) not in empty:
                continue
            distances = [_keyquest_tile_appearance(samples[i], signatures[tile])
                         for i, tile in enumerate(board)]
            if max(distances) <= 28:
                matching.append((sum(distances), board))
        if len(matching) == 1:
            return matching[0][1]
        if len(matching) == 2:
            matching.sort()
            return matching[0][1] if matching[1][0] - matching[0][0] >= 8 else None
        if len(empty) != 1:
            return None
        blank = empty[0]

        # Replan only when each tile has an unambiguous visual identity.
        identified = []
        for i, pixels in enumerate(samples):
            if i == blank:
                identified.append(0)
                continue
            ranking = sorted((_keyquest_tile_appearance(pixels, signature), tile)
                             for tile, signature in signatures.items() if tile)
            best, tile = ranking[0]
            if best > 24 or ranking[1][0] - best < 4:
                return None
            identified.append(tile)
        return tuple(identified) if len(set(identified)) == len(samples) else None

    def _keyquest_send_tile_move(state, now, retry=False):
        index = state.moves[0]
        _keyquest_trace("tile_tap", index=index, blank=state.tiles.index(0), retry=retry, remaining=len(state.moves))
        state.pending = (_keyquest_slide_tile(state.tiles, index), now + (3.2 if retry else 2.2), retry)
        state.tile_seen = None
        state.tile_seen_count = 0
        state.next_tap = now + 0.23
        _keyquest_puzzle_click(index, state.tile_side)

    def _keyquest_accept_tile_board(state, observed, expected, now, samples):
        state.pending = None
        state.tile_wait_until = 0.0
        state.next_tap = now + 0.16
        _keyquest_trace("tile_board_accepted", expected=observed == expected, board=observed)
        if observed == expected:
            state.moves = state.moves[1:]
        else:
            try:
                state.moves = _keyquest_tile_moves(observed, state.tile_target, state.tile_side)
            except ValueError:
                _keyquest_show_minigame("Could not match the changed board. Scan it again.", clear_moves=True)
                return
        state.tiles = observed
        state.tile_frame = samples
        if not state.moves:
            _keyquest_show_minigame("The planned tile moves are complete.")
        elif state.job == "tile-step":
            message = "Move checked." if observed == expected else "Board changed. Plan updated."
            _keyquest_show_minigame("%s %d remaining." % (message, len(state.moves)))

    def _keyquest_step_tiles(state, now):
        expected, until, retried = state.pending or (None, 0.0, False)
        frame, board, side = _keyquest_frame(), state.tile_bounds or _keyquest_board(), state.tile_side
        samples = tuple(_keyquest_cell_samples(frame, board, side, i, _keyquest_tile_centers)
                        for i in range(side * side))
        # Play can also resume after an interrupted verification. Check the
        # planned slide against the last confirmed frame before sending it again.
        planned = expected or _keyquest_slide_tile(state.tiles, state.moves[0])
        observed = _keyquest_tile_transition(samples, state.tile_frame, state.tiles, planned)
        match = "frame" if observed is not None else "scan"
        if observed is None:
            observed = _keyquest_observe_tiles(samples, state.signatures, state.tiles, planned)
        if state.tile_seen_count == 0 or observed != state.tile_seen:
            _keyquest_trace("tile_observed", board=observed, waiting_for=expected,
                            match=match if observed is not None else "unreadable")
            state.tile_seen = observed
            state.tile_seen_count = 0
        state.tile_seen_count += 1
        stable = observed is not None and state.tile_seen_count >= 2

        if stable and observed != state.tiles:
            _keyquest_accept_tile_board(state, observed, planned, now, samples)
        elif state.pending:
            if now < until:
                return
            if stable and not retried:
                _keyquest_send_tile_move(state, now, retry=True)
            elif stable:
                _keyquest_trace("tile_wait_expired", reason="tap_ignored")
                _keyquest_show_minigame("The tile did not respond. Tap Play to retry.")
            elif now >= until + 2.0:
                source, destination = expected.index(0), state.tiles.index(0)
                _keyquest_trace("tile_wait_expired", reason="move_unconfirmed",
                                source=source, destination=destination,
                                dark_samples=sum(max(pixel) <= 42 for pixel in samples[source]),
                                tile_difference=int(_keyquest_tile_appearance(
                                    samples[destination], state.tile_frame[source])))
                final_move = len(state.moves) == 1
                message = ("Last move sent. If the board is still open, tap Play to check it again." if final_move
                           else "The board could not be confirmed. Tap Play to check it again, or scan a new board.")
                _keyquest_show_minigame(message)
        elif stable:
            state.tile_wait_until = 0.0
            state.tile_frame = samples
            _keyquest_send_tile_move(state, now)
        elif not state.tile_wait_until:
            state.tile_wait_until = now + 3.0
        elif now >= state.tile_wait_until:
            _keyquest_trace("tile_wait_expired", reason="board_unreadable")
            _keyquest_show_minigame("The board is hard to read. Check the board corners or tap Play to retry.")

    def _keyquest_minigame_tick():
        state = _keyquest_minigame
        job = state.job
        if job is None or _keyquest_panel_grabbed():
            return
        now = _kq_puzzle_time.time()
        if now > state.deadline:
            _keyquest_show_minigame("Recording ended." if job == "watch" else "The minigame helper timed out.")
            return
        if now < state.next_tap:
            return
        try:
            if job in ("paddle", "timing"):
                _keyquest_arcade_tick(state, now)
            elif job == "watch":
                if state.color_event == "ready":
                    message = ("%d flashes recorded. Check the sequence, then press Play." % len(state.sequence)
                               if state.sequence else "No flashes captured. Start recording before the next pattern.")
                    _keyquest_show_minigame(message)
                    return
                frame = _keyquest_frame()
                board = _keyquest_board()
                if state.baseline is None:
                    state.color_points = _keyquest_color_centers(frame, board)
                    if not state.color_points:
                        state.next_tap = now + 0.25
                        return
                    colors = _keyquest_color_sample(frame, board, state.color_points)
                    order = _keyquest_color_layout(colors)
                    if order:
                        state.baseline = colors
                        state.color_order = order
                        _keyquest_trace("color_pads_found", centers=state.color_points)
                    return
                colors = _keyquest_color_sample(frame, board, state.color_points)
                hit = _keyquest_flash(state.baseline, colors, state.lit)
                if hit is None:
                    state.lit = None
                else:
                    if hit != state.lit:
                        state.lit = hit
                        _keyquest_append_color(state.color_order[hit])
                        _keyquest_trace("color_flash", index=hit, count=len(state.sequence))
                        renpy.restart_interaction()
            elif job == "color-play":
                if state.color_event == "wrong":
                    _keyquest_show_minigame("The game rejected a color. Record the next full pattern before playing again.")
                    return
                if state.color_event == "finished" or not state.pending:
                    _keyquest_show_minigame("Sequence finished. Record again for the next round.")
                    return
                if state.next_tap == 0:
                    frame, board = _keyquest_frame(), _keyquest_board()
                    state.color_points = _keyquest_color_centers(frame, board)
                    state.color_order = (_keyquest_color_layout(_keyquest_color_sample(frame, board, state.color_points))
                                         if state.color_points else ())
                    if not state.color_order:
                        _keyquest_show_minigame("Could not find all four colors. Check the corners and wait for the board.")
                        return
                index = state.color_order.index(state.pending[0])
                _keyquest_trace("color_tap", index=index, remaining=len(state.pending))
                _keyquest_puzzle_click(index, 2)
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
                tiles, signatures, moves, goal, confidence, numbered, error = result
                if error:
                    _keyquest_show_minigame(error, clear_moves=True)
                else:
                    _keyquest_trace("tiles_scanned", board=tiles, moves=len(moves), review=bool(goal))
                    state.tiles, state.signatures, state.moves = tiles, signatures, moves
                    state.tile_frame = tuple(signatures[tile] for tile in tiles)
                    state.tile_goal = goal
                    _keyquest_trace("tile_goal_source", source="numbers" if numbered else "picture")
                    if goal:
                        _keyquest_stop_minigame()
                        state.message = ("Picture match uncertain. Tap two tiles to swap them." if confidence < 7
                                         else "Check the picture. Tap two tiles to swap them if needed.")
                        if numbered:
                            state.message = "Read all tile numbers. Check the order, then plan moves."
                        _keyquest_open_review()
                        renpy.restart_interaction()
                    else:
                        _keyquest_show_minigame("%d tile moves ready." % len(moves) if moves else "The inferred picture is already arranged.")
            else:
                _keyquest_step_tiles(state, now)
        except Exception as error:
            _keyquest_trace("minigame_error", job=job, kind=type(error).__name__)
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
            textbutton "Paddle" style "keyquest_deck_key" selected (helper.mode == "paddle") action Function(_keyquest_minigame_mode, "paddle")
            textbutton "Timing" style "keyquest_deck_key" selected (helper.mode == "timing") action Function(_keyquest_minigame_mode, "timing")
            textbutton "OCR" style "keyquest_deck_key" action [Hide("_keyquest_minigames"), Show("_keyquest_smart_input")]
        if helper.mode == "tiles":
            hbox:
                spacing 6
                for side in (3, 4):
                    textbutton ("%d × %d" % (side, side)) style "keyquest_deck_key" selected (helper.tile_side == side) action Function(_keyquest_set_tile_size, side)
        textbutton ("Mark timing line" if helper.mode == "timing" else ("Adjust board" if board else "Set board corners")) style "keyquest_deck_key" action Function(_keyquest_board_setup)
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
        elif helper.mode == "tiles":
            text "Choose the grid size and set the corners around the entire grid, including the empty slot. Scan to match picture edges and plan legal slides." color "#b9d3e8" size 19 xmaximum 618
            hbox:
                spacing 6
                textbutton "Scan tiles" style "keyquest_deck_accent" sensitive bool(board) action Function(_keyquest_begin_minigame, "tile-scan")
                textbutton "Play one move" style "keyquest_deck_key" sensitive bool(board and helper.moves) action Function(_keyquest_begin_minigame, "tile-step")
                textbutton "Play all moves" style "keyquest_deck_key" sensitive bool(board and helper.moves) action Function(_keyquest_begin_minigame, "tile-play")
            if helper.tile_goal:
                textbutton "Review layout" style "keyquest_deck_key" action Function(_keyquest_open_review)
        elif helper.mode == "paddle":
            text "Choose your side. Start the helper, then click the game to begin the rally." color "#b9d3e8" size 20 xmaximum 618
            hbox:
                spacing 6
                for side in ("left", "right"):
                    textbutton side.title() style "keyquest_deck_key" selected (helper.paddle_side == side) action SetField(helper, "paddle_side", side)
                textbutton "Track ball" style "keyquest_deck_accent" action Function(_keyquest_begin_minigame, "paddle")
        else:
            text "Tap only while the blue marker is inside the red zone. Mark the timing line if the default position misses it." color "#b9d3e8" size 20 xmaximum 618
            textbutton "Start timing" style "keyquest_deck_accent" action Function(_keyquest_begin_minigame, "timing")
        if helper.message:
            text helper.message substitute False color "#d5f6e7" size 19 xmaximum 618

screen _keyquest_tile_review():
    zorder 994
    $ helper = _keyquest_minigame
    use _keyquest_floating("tile-review", "Review 4 × 4 picture", 595, 495, (0.98, 0.35)):
        text (("Tap the tile labeled %d." % (len(helper.tile_number_order) + 1)) if helper.tile_number_order is not None else (helper.message or "Tap two tiles to swap them.")) substitute False color "#b9d3e8" size 20 xmaximum 550
        if helper.tile_goal:
            grid 4 4:
                spacing 2
                for index, tile in enumerate(helper.tile_goal):
                    if tile:
                        button:
                            background Solid("#65dec1" if helper.tile_picked == index else "#1b2c42")
                            hover_background Solid("#629ccc")
                            padding (2, 2)
                            sensitive (helper.tile_number_order is None or tile not in helper.tile_number_order)
                            action Function(_keyquest_review_tile, index)
                            add helper.tile_thumbnails[tile]
                    else:
                        add Solid("#08131f") xysize (124, 76)
        hbox:
            spacing 6
            textbutton "Plan moves" style "keyquest_deck_accent" sensitive (bool(helper.tile_goal) and helper.tile_number_order is None) action Function(_keyquest_confirm_layout)
            textbutton ("Cancel order" if helper.tile_number_order is not None else "Set number order") style "keyquest_deck_key" action SetField(helper, "tile_number_order", () if helper.tile_number_order is None else None)
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
            $ timing = _keyquest_minigame.mode == "timing"
            text (("Tap the bottom of the line." if first else "Tap the top of the line.") if timing else ("Tap the bottom-right corner." if first else "Tap the top-left corner.")) color "#eff8ff" size 20 yalign 0.5
            textbutton "Cancel" style "keyquest_deck_key" action Function(_keyquest_show_minigame)

screen _keyquest_minigame_delay():
    timer 0.16 action [Hide("_keyquest_minigame_delay"), Show("_keyquest_minigame_run")]

screen _keyquest_minigame_run():
    zorder 997
    $ helper = _keyquest_minigame
    timer (0.035 if helper.job == "timing" else (0.06 if helper.job == "paddle" else (0.05 if helper.job == "watch" else 0.14))) repeat True action Function(_keyquest_minigame_tick, _update_screens=False)
    if helper.job != "watch":
        $ size = (112, 48)
        $ position = _keyquest_tile_stop_position((helper.tile_bounds if helper.job.startswith("tile-") else None) or _keyquest_board(), config.screen_width, config.screen_height, *size)
        key "game_menu" action Function(_keyquest_show_minigame, "Stopped.")
        if position is not None and (helper.job != "tile-scan" or helper.tile_busy):
            textbutton "Stop" style "keyquest_deck_key" pos position xysize size action Function(_keyquest_show_minigame, "Stopped.")
    else:
        $ size = (284, 48)
        $ position = _keyquest_tile_stop_position(_keyquest_board(), config.screen_width, config.screen_height, *size)
        key "game_menu" action Function(_keyquest_show_minigame)
        if position is not None:
            textbutton ("Finish · %d flashes" % len(helper.sequence)) style "keyquest_deck_key" pos position xysize size action Function(_keyquest_show_minigame)

init 999 python:
    if hasattr(renpy.config, "label_callbacks"):
        config.label_callbacks.append(_keyquest_color_label)
    else:
        _keyquest_before_color_label = config.label_callback

        def _keyquest_color_legacy_label(name, abnormal):
            _keyquest_color_label(name, abnormal)
            if _keyquest_before_color_label is not None:
                return _keyquest_before_color_label(name, abnormal)

        config.label_callback = _keyquest_color_legacy_label
