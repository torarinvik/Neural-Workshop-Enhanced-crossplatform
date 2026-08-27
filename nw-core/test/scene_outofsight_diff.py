#!/usr/bin/env python3
"""Differential harness for src/scene_outofsight.elisa against the REAL screen.

Three groups and the order between them is the task: dots at 0, the ring at 1,
the blinds at 2. A dot that goes behind a slab takes ITS RING WITH IT, which
is the whole point -- the question is where a thing you cannot see has got to.

The RING carries the verdict rather than the dot, so all three of its states
are swept; the dot itself only ever says whether it was cued.

This screen has no VerdictLabel of its own, so the sweep carries no verdict
knob -- the ring is where the outcome is said.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.outofsight import Blind, Dot, OutOfSight    # noqa: E402

PHASES = {0: "ready", 1: "cueing", 2: "tracking", 3: "asking",
          4: "revealing", 5: "done"}
ANSWERS = {-1: None, 0: False, 1: True}


def build(spec):
    import framerec
    geometry.set_window_size(912, 684)
    display.relayout()
    framerec.set_scale(geometry._width() / 912.0, geometry._height() / 684.0)
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = OutOfSight()
    dots = []
    for index in range(spec["dots"]):
        dot = Dot(0.07 + 0.11 * (index % 8), 0.13 + 0.13 * (index % 6),
                  0.0, 0.0, index % 3 == 0)
        dots.append(dot)
    screen.dots = dots
    screen.blinds = [Blind(0.05 + 0.17 * index,
                           0.12 + 0.13 * (index % 4), 0.14, 0.22)
                     for index in range(spec["blinds"])]
    at = spec["spec"]
    if spec["has_probe"]:
        screen.probe = Dot(0.31 + 0.04 * (at % 9), 0.27 + 0.05 * (at % 7),
                           0.0, 0.0, True)
    else:
        screen.probe = None
    screen.verdict = ANSWERS[spec["answer"]]
    screen.round = spec["round"]
    screen.total_rounds = spec["total_rounds"]
    screen.probes_done = spec["probes_done"]
    screen.probes_per_round = spec["probes_per_round"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Where did it go?'
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
