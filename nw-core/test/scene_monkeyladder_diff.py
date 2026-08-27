#!/usr/bin/env python3
"""Differential harness for src/scene_monkeyladder.elisa against the REAL screen.

The sequence is `rng.sample(cells, count)` over the grid's cells in row-major
order, so the port samples the same range with the same generator and a cell
index is `row * grid + col` on both sides.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import random
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.ui.monkeyladder import MonkeyLadder           # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "show", 2: "input", 3: "result"}


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = MonkeyLadder()
    grid = spec["grid"]
    screen.grid = grid
    screen.level = spec["level"]
    screen.reveal_answer = bool(spec["reveal"])
    cells = [(row, col) for row in range(grid) for col in range(grid)]
    picked = random.Random(spec["seed"]).sample(cells, spec["count"])
    screen.sequence = picked
    screen.clicked = picked[:spec["clicked_upto"]]
    screen.wrong = (None if spec["wrong"] < 0
                    else (spec["wrong"] // grid, spec["wrong"] % grid))
    screen.cursor_cell = (spec["cursor_cell"] // grid, spec["cursor_cell"] % grid)
    screen.cursor_enabled = bool(spec["cursor_enabled"])
    screen.phase = PHASES[spec["phase"]]
    if spec["phase"] == 1:
        screen.message = _('Remember the order')
    elif spec["phase"] == 2:
        screen.message = _('Click 1 through %d') % spec["count"]
    else:
        screen.message = _('Press Space to watch the numbers')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
