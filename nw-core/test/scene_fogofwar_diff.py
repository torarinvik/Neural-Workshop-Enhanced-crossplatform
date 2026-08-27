#!/usr/bin/env python3
"""Differential harness for src/scene_fogofwar.elisa against the REAL screen.

The frame is a pure function of where the walker is and what has been
revealed, and the module's whole design rests on that -- so what this checks
is that the port draws exactly the revealed cells, in CELL order, over one
rectangle of dark, and nothing else at all.

The status line is REPLACED while exploring rather than joined to, which is
the same rule: the message would change on a move and a move must not change
the screen.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.fogofwar import FogOfWar                    # noqa: E402

PHASES = {0: "ready", 1: "exploring", 2: "finished", 3: "done"}


class World:
    """Only what the drawing reads off a World."""

    def __init__(self, wide, tall):
        self.width = wide
        self.height = tall
        walls = set()
        for cell in range(wide * tall):
            x, y = cell % wide, cell // wide
            if (x == 0 or y == 0 or x == wide - 1 or y == tall - 1
                    or (x % 3 == 0 and y % 3 == 0)):
                walls.add(cell)
        self.walls = frozenset(walls)
        self.start = 0


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
    screen = FogOfWar()
    wide, tall = spec["wide"], spec["tall_cells"]
    screen.world = World(wide, tall)
    seen = spec["seen"]
    screen.revealed = {cell for cell in range(wide * tall)
                       if seen == 4 or (seen > 0 and cell % (6 - seen) == 0)}
    screen.at = spec["at"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Press Space to start'
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
