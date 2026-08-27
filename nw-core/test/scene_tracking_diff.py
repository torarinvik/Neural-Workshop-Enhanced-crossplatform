#!/usr/bin/env python3
"""Differential harness for src/scene_tracking.elisa against the REAL screen.

The balls carry the trial's state in their colour and the meaning of that
colour changes with the phase -- orange is a ball to follow while cueing and a
ball you picked while picking -- so the sweep walks all six phases over a
flock that holds every combination of target and picked.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.tracking import Ball, MovingTargets         # noqa: E402

PHASES = {0: "ready", 1: "cueing", 2: "tracking", 3: "picking",
          4: "revealing", 5: "done"}


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
    screen = MovingTargets()
    balls = []
    for index in range(spec["balls"]):
        ball = Ball(0.07 + (index % 7) * 0.13, 0.13 + (index % 5) * 0.17,
                    0.0, 0.0, index % 2 == 0)
        ball.picked = index % 3 == 0
        balls.append(ball)
    screen.balls = balls
    screen.round = spec["round"]
    screen.total_rounds = spec["total_rounds"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Follow the orange balls'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
