#!/usr/bin/env python3
"""Differential harness for src/scene_ninarow.elisa against the REAL screen.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.ninarow import generate                       # noqa: E402
from neural_workshop.ui.ninarow import NInARow                     # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "asking", 2: "judged", 3: "done"}


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = NInARow()
    puzzle = generate(spec["rung"], spec["seed"]) if spec["has_puzzle"] else None
    screen.puzzle = puzzle
    screen.rung = spec["rung"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.choice = spec["choice"]
    screen.show_answer = bool(spec["show_answer"])
    screen.phase = PHASES[spec["phase"]]
    if spec["phase"] == 1 and puzzle is not None:
        screen.message = _('Find the move that completes %d in a row') % (
            puzzle.length,)
    else:
        screen.message = _('Press Space to start')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
