#!/usr/bin/env python3
"""Differential harness for src/scene_sokoban.elisa against the REAL screen.

The boxes come out of a frozenset, so the order they are drawn in is CPython's
hash order. This is NOT settled for the way Go's rings are: a box that is home
is green and one that is not is blue, so the order reaches the display list
even though it cannot reach a pixel. The port drives `tasks/pyset.elisa` for
it, and the whole point of this suite is that the two orders agree.

The room is built the same way on both sides -- a wall border with goals and
traps sprinkled by cell index -- so the sweep and the reference are looking at
the same level without a level file between them.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.sokoban import SokobanTask                  # noqa: E402

PHASES = {0: "ready", 1: "pushing", 2: "solved", 3: "lost", 4: "done"}


class Room:
    """Only what `_redraw` and `_cell_rect` read off a Level."""

    def __init__(self, wide, tall):
        self.width = wide
        self.height = tall
        walls, goals, traps, boxes = set(), set(), set(), []
        for cell in range(wide * tall):
            x, y = cell % wide, cell // wide
            edge = x == 0 or y == 0 or x == wide - 1 or y == tall - 1
            if edge:
                walls.add(cell)
                continue
            if cell % 7 == 3:
                goals.add(cell)
            if cell % 11 == 5:
                traps.add(cell)
            if cell % 5 == 2:
                boxes.append(cell)
        self.walls = frozenset(walls)
        self.goals = frozenset(goals)
        self.traps = frozenset(traps)
        # Built from a LIST in the sweep's order, so the hash order this comes
        # back in is the thing under test.
        self.boxes = frozenset(boxes)


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
    screen = SokobanTask()
    room = Room(spec["wide"], spec["tall_cells"])
    screen.level = room if spec["has_level"] else None
    screen.boxes = room.boxes
    screen.player = spec["wide"] + 1
    screen.pushes = spec["pushes"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - one room'
    screen.show_traps = bool(spec["show_traps"])
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
