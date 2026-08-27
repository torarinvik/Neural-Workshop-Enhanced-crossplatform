#!/usr/bin/env python3
"""Differential harness for src/scene_crossedwires.elisa against the REAL screen.

The Bench is real -- built from a real deal -- and then put into the spec's
visible state. What the deal decided about the WIRING is left alone, because
the screen never reads it; what the screen does read is overwritten.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.crossedwires import GRADES, Bench, deal       # noqa: E402
from neural_workshop.ui.crossedwires import CrossedWires           # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "playing", 2: "scored"}


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = CrossedWires()
    screen.rung = spec["rung"]
    screen.show_grid = bool(spec["show_grid"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    bench = Bench(deal(spec["rung"], seed=spec["spec"] + 1))
    bench.at = (spec["at_x"], spec["at_y"])
    bench.goal_at = spec["goal_at"]
    # `goal()` reads bout.goals, and the count of them is part of the status
    # line, so both are set rather than only the index. A Bout is immutable --
    # goals is a tuple -- so it is replaced rather than written into.
    bench.bout = bench.bout._replace(
        goals=tuple([(spec["goal_x"], spec["goal_y"])] * spec["goals_n"]),
        budget=spec["budget"])
    bench.presses = spec["budget"] - spec["presses_left"]
    screen.bench = bench
    screen.phase = PHASES[spec["phase"]]
    if spec["phase"] == 1:
        grade = GRADES[spec["rung"] - 1]
        screen.message = _('%s — %d keys, %d targets') % (
            _(grade.name), grade.keys, grade.targets)
    else:
        screen.message = _('Press Space to start')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
