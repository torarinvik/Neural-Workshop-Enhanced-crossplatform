#!/usr/bin/env python3
"""Differential harness for src/scene_sokoban3d.elisa against the REAL screen.

The same three batches the 3D Maze has, told to the recorder the same way. The
plan is the one place in the workshop where a set is SORTED before it is drawn
-- `sorted(level.boxes)` -- so the boxes go down in cell order rather than in
the frozenset's, and that is reproduced rather than run through pyset.

A wall face is grey and a box face keeps the box's own colour, green if it is
already home and blue if it is not, so the sweep puts some of each in front of
the rays.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop import sokoban3d as model                      # noqa: E402
from neural_workshop.ui import sokoban3d as sokoban3d_ui           # noqa: E402
from neural_workshop.ui.sokoban3d import Sokoban3D                  # noqa: E402
from neural_workshop.youarehere import Sight                        # noqa: E402

PHASES = {0: "ready", 1: "pushing", 2: "solved", 3: "lost", 4: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_sokoban3d_sweep.elisa")
COLUMNS = int(re.search(r"const COLUMNS: i64 = (\d+)",
                        open(SWEEP).read()).group(1))
FAR = 1e4


class Mark:
    def __init__(self, across, distance):
        self.across = across
        self.distance = distance


class Warehouse:
    """Only what the plan and the view read off a Level."""

    def __init__(self, wide, tall):
        self.width = wide
        self.height = tall
        cells = wide * tall
        walls, goals, traps, boxes = set(), set(), set(), set()
        for cell in range(cells):
            x, y = cell % wide, cell // wide
            if x == 0 or y == 0 or x == wide - 1 or y == tall - 1:
                walls.add(cell)
                continue
            if cell % 7 == 3:
                goals.add(cell)
            if cell % 11 == 5:
                traps.add(cell)
            if cell % 5 == 2:
                boxes.add(cell)
        self.walls = frozenset(walls)
        self.goals = frozenset(goals)
        self.traps = frozenset(traps)
        self.boxes = frozenset(boxes)
        self.player = wide + 1


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
    screen = Sokoban3D()
    level = Warehouse(spec["wide"], spec["tall_cells"])
    screen.level = level
    screen.boxes = level.boxes
    screen.show_traps = bool(spec["show_traps"])
    screen.show_marks = bool(spec["show_marks"])
    screen.steps = spec["steps"]
    screen.pushes = spec["pushes"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - minimum 12 pushes'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    cells = level.width * level.height
    seen = tuple(Sight(FAR if column % 37 == 0
                       else 0.2 + 0.09 * (column % 61),
                       (column * 7) % cells, column % 2)
                 for column in range(COLUMNS))
    spots = [Mark(0.07 + 0.23 * one, 0.3 + 2.5 * one)
             for one in range(spec["marks"])]
    # The ray caster has a suite of its own; what is under test here is what
    # the screen does with what it returns.
    model.look_around = lambda _level, _boxes, _pose: seen
    model.marks = lambda _level, _boxes, _pose: spots
    sokoban3d_ui.S3 = model

    def lay_out():
        screen._build_chrome()
        framerec.set_batches([screen.plan_batch, screen.view_batch,
                              screen.batch])
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
