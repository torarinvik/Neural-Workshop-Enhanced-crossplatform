#!/usr/bin/env python3
"""Differential harness for src/scene_mrtime.elisa against the REAL screen.

Six outlines, five of them one closed run of points around a random turn and
the sixth an Arc closed on itself. The turn is not a multiple of a right
angle, so a square is drawn as a diamond rather than as a square that happens
to line up -- which is what makes an off-by-one in the corner arithmetic
visible.

The quantity line steps at ten of the rung's own unit, from two decimals to a
grouped integer, so the targets straddle that at every rung.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.mrtime import KINDS, Mark, MrTime           # noqa: E402

PHASES = {0: "ready", 1: "showing", 2: "counting", 3: "watching",
          4: "asking", 5: "settled", 6: "done"}
TYPED = {0: '', 1: '1.5', 2: '12.75'}


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
    screen = MrTime()
    at = spec["spec"]
    screen.mark = Mark(kind=KINDS[spec["kind"]],
                       x=0.18 + 0.05 * (at % 9),
                       y=0.22 + 0.04 * (at % 7),
                       radius=0.10 + 0.011 * (at % 10),
                       turn=0.37 + 0.29 * (at % 11))
    screen.rung = spec["rung"]
    screen.target = spec["target"] / 7.0
    screen.answer_text = TYPED[spec["typed"]]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.correct = spec["right"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Time it'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
