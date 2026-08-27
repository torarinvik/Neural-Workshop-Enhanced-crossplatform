#!/usr/bin/env python3
"""Differential harness for src/scene_youarehere.elisa against the REAL screen.

Three batches, drawn in an order nothing but `on_draw` knows: the map, then
the corridor, then the chrome. The recorder is TOLD that order -- it cannot
work it out, because pyglet orders within a batch and not between them -- and
the chrome, which is created first, therefore comes out last.

The view is supplied rather than cast. Ray casting has its own suite; what is
under test here is the drawing, so the sweep hands over a set of sights chosen
to sit on the decisions: walls at every distance, some of them door cells so a
doorway keeps its colour, some beyond FAR so the strip is not drawn at all, and
both sides so the edge-on dimming is exercised.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import youarehere as youarehere_ui         # noqa: E402
from neural_workshop.ui.youarehere import YouAreHere                # noqa: E402
from neural_workshop.youarehere import Sight                        # noqa: E402

PHASES = {0: "ready", 1: "walking", 2: "solved", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_youarehere_sweep.elisa")
COLUMNS = int(re.search(r"const COLUMNS: i64 = (\d+)",
                        open(SWEEP).read()).group(1))
FAR = 1e4


class Mote:
    def __init__(self, what, which, across, distance):
        self.what = what
        self.which = which
        self.across = across
        self.distance = distance


class Warren:
    """Only what the map and the view read off a Maze."""

    def __init__(self, wide, tall, doors):
        self.width = wide
        self.height = tall
        cells = wide * tall
        walls = []
        for cell in range(cells):
            x, y = cell % wide, cell // wide
            if (x == 0 or y == 0 or x == wide - 1 or y == tall - 1
                    or (x % 2 == 0 and y % 2 == 0)):
                walls.append(cell)
        self.walls = frozenset(walls)
        self.doors = tuple((wide + 1 + one * 5) % cells for one in range(doors))
        self.keys = tuple((wide + 3 + one * 7) % cells for one in range(doors))
        self.start = wide + 1
        self.way_out = cells - wide - 2


def sights_of(maze, doors):
    cells = maze.width * maze.height
    made = []
    for column in range(COLUMNS):
        beyond = column % 37 == 0
        if doors and column % 5 == 0:
            cell = maze.doors[column % doors]
        else:
            cell = (column * 7) % cells
        made.append(Sight(FAR if beyond else 0.2 + 0.09 * (column % 61),
                          cell, column % 2))
    return tuple(made)


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
    screen = YouAreHere()
    maze = Warren(spec["wide"], spec["tall_cells"], spec["doors"])
    screen.maze = maze
    screen.held = spec["held"]
    screen.show_marks = bool(spec["show_marks"])
    screen.steps = spec["steps"]
    screen.par = spec["par"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - two doors'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    seen = sights_of(maze, spec["doors"])
    marks = [Mote('key' if one % 2 == 0 else 'way out', one,
                  0.07 + 0.23 * one, 0.3 + 2.5 * one)
             for one in range(spec["motes"])]
    # The ray caster and the mark finder have suites of their own; what is
    # under test here is what the screen does with what they return.
    youarehere_ui.look = lambda _maze, _pose, columns=COLUMNS: seen
    youarehere_ui.motes = lambda _maze, _pose, _held: marks
    import neural_workshop.youarehere as model
    model.look = youarehere_ui.look
    model.motes = youarehere_ui.motes

    def lay_out():
        screen._build_chrome()
        framerec.set_batches([screen.map_batch, screen.view_batch,
                              screen.batch])
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
