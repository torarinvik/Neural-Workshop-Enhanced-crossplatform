#!/usr/bin/env python3
"""Differential harness for src/scene_crossword.elisa against the REAL screen.

The grid goes down in four passes and the order is the picture: the page, then
the washes and the cursor box, then the blocks and letters, then the rules
LAST so they sit over everything. A letter's colour says where it came from --
vermillion for a contradiction, the ink for a given, blue for what the player
wrote -- and a given is also the only bold thing inside the grid.

The grid is built the same way on both sides rather than dealt, so the two are
looking at the same puzzle without a puzzle file between them. Slots are
contiguous runs, which is what a crossword entry is, so the port carries a
first cell and a length instead of a tuple of cells.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.crossword import Crossword                  # noqa: E402

PHASES = {0: "ready", 1: "solving", 2: "solved", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_crossword_sweep.elisa")
CLUE = re.search(r'const CLUE: cstr = "((?:[^"\\]|\\.)*)"',
                 open(SWEEP).read()).group(1)


class Slot:
    def __init__(self, number, down, cells, clue):
        self.number = number
        self.down = down
        self.cells = tuple(cells)
        self.clue = clue

    @property
    def length(self):
        return len(self.cells)


class Grid:
    """Only what the drawing reads off a Puzzle."""

    def __init__(self, size, clued):
        self.size = size
        cells = size * size
        self.solution = []
        self.filled = []
        self.givens = set()
        for cell in range(cells):
            if cell % 7 == 6:
                self.solution.append('')
                self.filled.append('')
                continue
            answer = chr(97 + cell % 26)
            self.solution.append(answer)
            if cell % 3 == 0:
                self.filled.append(chr(ord(answer) + 1)
                                   if cell % 11 == 0 else answer)
                if cell % 5 == 0:
                    self.givens.add(cell)
            else:
                self.filled.append('')
        slots = []
        for row in range(size - 2):
            clue = CLUE if clued else ''
            slots.append(Slot(row + 1, False,
                              [row * size + one for one in range(3)], clue))
            slots.append(Slot(row + 1 + size, True,
                              [row + one * size for one in range(3)], clue))
        self.slots = tuple(slots)


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
    screen = Crossword()
    grid = Grid(spec["size"], bool(spec["clued"]))
    screen.puzzle = grid if spec["has_puzzle"] else None
    screen.filled = list(grid.filled)
    screen.at = spec["at"]
    screen.down = bool(spec["down"])
    screen.hovered = None if spec["hovered"] < 0 else spec["hovered"]
    screen.show_mistakes = bool(spec["show_mistakes"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - five squares'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
