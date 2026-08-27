#!/usr/bin/env python3
"""Differential harness for src/scene_pursuit.elisa against the REAL screen.

The same glyph family Lookout deals from, drawn one at a time -- which is why
that family is its own module on both sides rather than two copies of four
shapes.

The quarry's radius is its OWN and not a constant, so the sweep carries one
small enough to hit the six-pixel floor on a short window and several above
it. The adaptive multiplier is printed as `x%.2f`, so it is swept across
values whose third decimal place is a five.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.pursuit import Pursuit, Quarry              # noqa: E402

PHASES = {0: "ready", 1: "chasing", 2: "feedback", 3: "done"}


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
    screen = Pursuit()
    if spec["has_quarry"]:
        screen.quarry = Quarry(0.17 + 0.06 * (spec["spec"] % 9),
                               0.21 + 0.05 * (spec["spec"] % 7),
                               0.0, spec["radius"], spec["form"],
                               spec["color"])
    else:
        screen.quarry = None
    screen.adaptive = bool(spec["adaptive"])
    screen.multiplier = spec["multiplier"] / 100.0
    screen.round = spec["round"]
    screen.total_rounds = spec["total_rounds"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Stay on it'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
