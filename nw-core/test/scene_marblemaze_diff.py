#!/usr/bin/env python3
"""Differential harness for src/scene_marblemaze.elisa against the REAL screen.

Only the chrome is compared, and that is the whole point of the module: the
tray, the marbles and the walls are drawn by a GL pipeline of their own, none
of it through a pyglet drawable, so the recorder cannot see any of it and this
harness could not check it if the port had written it.

The tilt is swept through both signs, because it reads as `-3°/7°` and a port
that dropped the sign would look right on half the frames.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import math
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.marblemaze import MarbleMaze                # noqa: E402

PHASES = {0: "ready", 1: "rolling", 2: "settled", 3: "done"}


class Sim:
    """Only what `_update_status` reads off a running tray."""

    def __init__(self, home, marbles, elapsed, roll, pitch):
        self.home = home
        self.marbles = [None] * marbles
        self.elapsed = elapsed
        self.roll = math.radians(roll)
        self.pitch = math.radians(pitch)


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
    screen = MarbleMaze()
    screen.seconds = spec["left"]
    screen.sim = (Sim(spec["home"], spec["marbles"], 0.0,
                      spec["roll"], spec["pitch"])
                  if spec["rolling"] else None)
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Tip it home'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
