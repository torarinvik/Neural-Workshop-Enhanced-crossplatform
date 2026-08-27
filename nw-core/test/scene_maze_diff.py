#!/usr/bin/env python3
"""Differential harness for src/scene_maze.elisa against the REAL screen.

Two of the warren's five passes come out of SETS -- the walls and the trail --
so their order is CPython's hash order, and the port drives tasks/pyset.elisa
for it the way Sokoban does. The walls alone could have been settled for,
being identical squares; the trail could not, because it is drawn at 70 alpha
over whatever is under it.

`held` is swept across a five-bit range so every door is drawn both locked and
opened and every key both present and taken, and the door count runs past six
so `colour % len(KEY_COLORS)` wraps and two doors share a colour.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.maze import MazeTask                        # noqa: E402

PHASES = {0: "ready", 1: "walking", 2: "solved", 3: "done"}


class Warren:
    """Only what `_draw_maze`, `_cell_rect` and `keys_left` read off a Maze."""

    def __init__(self, wide, tall, doors):
        self.width = wide
        self.height = tall
        cells = wide * tall
        walls, walked = [], []
        for cell in range(cells):
            x, y = cell % wide, cell // wide
            if (x == 0 or y == 0 or x == wide - 1 or y == tall - 1
                    or (x % 2 == 0 and y % 2 == 0)):
                walls.append(cell)
            elif cell % 3 == 1:
                walked.append(cell)
        self.walls = frozenset(walls)
        self.walked = set(walked)
        self.way_out = cells - wide - 2
        self.doors = tuple((wide + 1 + one * 5) % cells for one in range(doors))
        self.keys = tuple((wide + 3 + one * 7) % cells for one in range(doors))


def build(spec):
    import framerec
    geometry.set_window_size(912, spec["tall"] // 2)
    display.relayout()
    if (geometry._width(), geometry._height()) != (1824, spec["tall"]):
        raise SystemExit("asked for 1824x%d pixels, got %dx%d"
                         % (spec["tall"], geometry._width(), geometry._height()))
    framerec.set_scale(geometry._width() / 912.0,
                       geometry._height() / (spec["tall"] / 2.0))
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = MazeTask()
    warren = Warren(spec["wide"], spec["tall_cells"], spec["doors"])
    screen.maze = warren if spec["has_maze"] else None
    screen.walked = warren.walked
    screen.show_trail = bool(spec["show_trail"])
    screen.held = spec["held"]
    screen.walker = spec["wide"] + 1
    screen.steps = spec["steps"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - two keys'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
