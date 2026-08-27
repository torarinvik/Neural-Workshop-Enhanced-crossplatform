#!/usr/bin/env python3
"""Differential harness for src/scene_sudoku.elisa against the REAL screen.

The board is named rather than solved: the sweep chooses every cell's value,
given-ness and pencil mask by arithmetic, so clashing digits and pencilled
cells are reachable without playing to them. `peers` is sorted in the
reference, so the wash goes down in cell order and there is no hash order here.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.ui.sudoku import Sudoku                       # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "solving", 2: "solved", 3: "done"}


class Board:
    """Just enough of a Puzzle for the screen: it only reads `box`."""

    def __init__(self, box):
        self.box = box
        self.size = box * box


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = Sudoku()
    box, size = spec["box"], spec["box"] ** 2
    cells = size * size
    screen.puzzle = Board(box) if spec["has_puzzle"] else None
    filled, givens, marks = [], set(), {}
    for cell in range(cells):
        value = 1 + (cell // size + spec["spec"]) % size if (cell + spec["spec"]) % 3 == 0 else 0
        filled.append(value)
        if value and (cell + spec["spec"]) % 6 == 0:
            givens.add(cell)
        if not value:
            marks[cell] = (cell * 37 + spec["spec"]) % 512
    screen.filled = filled
    screen.marks = marks
    # `given(cell)` is what the screen asks; the puzzle's own givens list is
    # never read by the drawing, so the set is what has to be right.
    screen.given = lambda cell, held=givens: cell in held
    screen.at = spec["at"]
    screen.show_clashes = bool(spec["show_clashes"])
    screen.pencil = bool(spec["pencil"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = _('Press Space to start')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
