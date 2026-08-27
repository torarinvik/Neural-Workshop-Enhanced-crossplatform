#!/usr/bin/env python3
"""Differential harness for src/scene_lookout.elisa against the REAL screen.

Two things are under test here that no earlier scene reached.

The first is the glyph family -- four forms, four different pyglet classes,
one of them a Star and one a Rectangle anchored on its own middle. A square
glyph's x and y are the point it is centred on, so the display list carries
the anchor rather than pre-subtracting it; a shell that ignored it would draw
every square up and to the right by half a side.

The second is the draw ORDER. `_build_chrome` makes the cue glyph, then the
flock, then calls `_update_status`, which makes the cue glyph AGAIN -- so the
one that survives is younger than every shape and is drawn last. Its x is
measured off the status line it sits beside, which is why it has to be built
after the text is set.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.lookout import (COLORS, Cue, Drifter,       # noqa: E402
                                        FORMS, Lookout)

PHASES = {0: "ready", 1: "watching", 2: "feedback", 3: "done"}
WATCHING = {0: "color", 1: "form", 2: "both"}


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
    screen = Lookout()
    screen.watching = WATCHING[spec["watching"]]
    screen.shapes = [
        Drifter(0.06 + 0.11 * (index % 8), 0.13 + 0.13 * (index % 6),
                0.0, 0.0, index % len(COLORS), index % len(FORMS), 0.0)
        for index in range(spec["shapes"])]
    screen.cue = Cue(spec["cue_color"], spec["cue_form"])
    screen.cue_number = spec["cue_number"]
    screen.total_cues = spec["total_cues"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Watch for it'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
