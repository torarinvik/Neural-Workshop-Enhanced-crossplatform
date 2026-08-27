#!/usr/bin/env python3
"""Differential harness for src/scene_buzzwire.elisa against the REAL screen.

Only the chrome, for Marble Maze's reason: the wire, the loop and the hand go
through a GL pipeline of their own and not one of them is a pyglet drawable,
so the recorder cannot see them.

The clearance gauge is the thing worth sweeping. It is eight cells of hash and
dot, rounded half to even, and the share is CLAMPED before it is rounded --
so the sweep runs past both ends of the bar as well as through every cell of
it.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import buzzwire as buzzwire_ui              # noqa: E402
from neural_workshop.ui.buzzwire import BuzzWire                    # noqa: E402

PHASES = {0: "ready", 1: "flying", 2: "settled", 3: "done"}


class Hand:
    def __init__(self, arc, used):
        self.arc = arc
        self._used = used

    def offset(self):
        return self._used


class Wire:
    length = 100.0


class Grade:
    def __init__(self, touches):
        self.touches = touches


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
    screen = BuzzWire()
    screen.wire = Wire()
    screen.grade = Grade(spec["touches"])
    # `along` is `int(100 * arc / length)` and the clock is a countdown from
    # `deadline`, so both are solved back to the numbers the sweep named.
    screen.hand = (Hand(spec["along"], spec["used"] / 12.0)
                   if spec["flying"] else None)
    screen.clock = lambda: 0.0
    screen.deadline = spec["left"]
    screen.buzzes = spec["buzzes"]
    screen.show_meter = bool(spec["show_meter"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Steady now'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    buzzwire_ui.B.clearance = lambda _grade: 1.0

    def lay_out():
        held = screen._build_scene
        screen._build_scene = lambda: None
        try:
            screen._build_chrome()
        finally:
            screen._build_scene = held
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
