#!/usr/bin/env python3
"""Differential harness for src/scene_go.elisa against the REAL screen.

The problem comes from the reference's own generator, which go_diff.py already
checks against the port's.

`settle_positions` is opted into here and nowhere else so far: the target group
is a frozenset, so the reference rings its points in CPython's hash order. The
rings are one colour and one radius on distinct board points, so which goes
down first cannot change a pixel -- see scenediff.settle_positions for the rule
and its limit.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.go import generate_problem                    # noqa: E402
from neural_workshop.ui.go import GoWinningMove                    # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "solving", 2: "judged"}


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = GoWinningMove()
    screen.problem = (generate_problem(spec["seed"], spec["difficulty"])
                      if spec["has_problem"] else None)
    screen.difficulty = spec["difficulty"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.cursor_x = spec["cursor_x"]
    screen.cursor_y = spec["cursor_y"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = _('Press Space to start')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build, settle=scenediff.settle_positions))
