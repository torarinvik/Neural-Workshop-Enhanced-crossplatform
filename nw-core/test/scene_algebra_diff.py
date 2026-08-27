#!/usr/bin/env python3
"""Differential harness for src/scene_algebra.elisa against the REAL screen.

The Problem is a stub carrying only the four fields the screen reads. The real
generator is checked by algebra_diff.py; what is under test here is where the
lines sit and how `search_line` says a number.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.ui.algebra import Algebra                     # noqa: E402

PHASES = {0: "ready", 1: "working", 2: "judged", 3: "done"}


class Asked:
    """Only what `_redraw` reads off a Problem."""

    def __init__(self, candidates):
        self.asked = '3x + 7 = 22'
        self.wants = 'solve for x'
        self.working = ['3x = 15', 'x = 5']
        self.candidates = candidates


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = Algebra()
    screen.problem = Asked(spec["tenths"] / 10.0) if spec["has_problem"] else None
    screen.typed = '5'
    screen.show_working = bool(spec["show_working"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Press Space to start'
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
