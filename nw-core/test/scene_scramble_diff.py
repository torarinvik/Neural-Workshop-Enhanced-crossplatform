#!/usr/bin/env python3
"""Differential harness for src/scene_scramble.elisa against the REAL screen.

The readings line is the reason this sweep has eight ambiguity values in it:
it branches at 0.05 and at 5.0, hedges to "at least" once the grade moves
spaces, and rounds half to EVEN on both sides of the second branch.

`missing_message()` depends on what is installed rather than on the game, so
the port takes it as text and the sweep names one. What is checked here is
that it is joined on when the run has not started and the text is only the
seed sentences, and not otherwise.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import scramble as scramble_ui              # noqa: E402
from neural_workshop.ui.scramble import Scramble                    # noqa: E402

PHASES = {0: "ready", 1: "reading", 2: "judged", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_scramble_sweep.elisa")
SOURCE = open(SWEEP).read()
AMBIGUITY = [float(one) for one in
             re.findall(r"return (-?\d+\.\d+)", SOURCE.split(
                 "def ambiguity_of(which: i64) -> f64:")[1].split("\n\n")[0])]
MISSING = re.search(r'const MISSING: cstr = "((?:[^"\\]|\\.)*)"',
                    SOURCE).group(1)


class Grade:
    def __init__(self, spaces):
        self.spaces = spaces
        self.name = 'Rung 3 - letters only'


class Deal:
    """Only what `_redraw`, `_update_status` and `readings` read off a Deal."""

    shown = 'thec atsa tont hema t'
    answer = 'the cat sat on the mat'

    def __init__(self, ambiguity, spaces, words):
        self.ambiguity = ambiguity
        self.grade = Grade(spaces)
        self.words = ['x'] * words


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
    screen = Scramble()
    screen.deal = (Deal(AMBIGUITY[spec["ambiguity"]], spec["moves_spaces"],
                        spec["words"]) if spec["has_deal"] else None)
    screen.typed = 'the cat sat on the ma'
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - letters only'
    screen.show_count = bool(spec["show_count"])
    # `stocked` and the text it joins on are both about the installation and
    # not the game, so they are set here rather than being looked up.
    screen.stocked = staticmethod(lambda: bool(spec["stocked"]))
    scramble_ui.missing_message = lambda: MISSING
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
