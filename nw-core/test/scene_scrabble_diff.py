#!/usr/bin/env python3
"""Differential harness for src/scene_scrabble.elisa against the REAL screen.

The board's passes have to go down in the reference's order and two of them
are easy to get wrong. The pointer's wash is painted AFTER the letters, so it
tints them; and the cursor's box is last of all with a fully transparent fill,
so it is a frame and not a lid -- a recorder that read opacity alone would drop
that command entirely, which is why framerec does not.

A premium is only painted where the square is empty and nothing has been laid
on it this turn, so the sweep lays tiles onto premium squares.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.scrabble import Scrabble                    # noqa: E402

PHASES = {0: "ready", 1: "playing", 2: "scored", 3: "done"}
PREMIUMS = ('', 'DL', 'TL', 'DW', 'TW')

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_scrabble_sweep.elisa")
RACK_LETTERS = re.search(r'const RACK_LETTERS: cstr = "((?:[^"\\]|\\.)*)"',
                         open(SWEEP).read()).group(1)


class Board:
    def __init__(self, size):
        self.size = size
        cells = size * size
        self.premiums = tuple(PREMIUMS[cell % 5] for cell in range(cells))
        self.letters = tuple('' if cell % 4 != 3 else chr(97 + cell % 26)
                             for cell in range(cells))

    def empty(self, cell):
        return not self.letters[cell]


class Deal:
    def __init__(self, size, rack):
        self.board = Board(size)
        self.rack = [RACK_LETTERS[slot % 8] for slot in range(rack)]


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
    screen = Scrabble()
    size = spec["size"]
    cells = size * size
    screen.deal = Deal(size, spec["rack"])
    screen.laid = [(cell, chr(97 + cell % 26)) for cell in range(cells)
                   if cell % 9 == 1 and cell // 9 < spec["laid"]]
    screen.spent = list(range(spec["spent"]))
    screen.show_premiums = bool(spec["show_premiums"])
    screen.at = spec["at"]
    screen.hovered = None if spec["hovered"] < 0 else spec["hovered"]
    screen.hovered_tile = (None if spec["hovered_tile"] < 0
                           else spec["hovered_tile"])
    screen.hovered_play = bool(spec["hovered_play"])
    screen.down = bool(spec["down"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - seven tiles'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
