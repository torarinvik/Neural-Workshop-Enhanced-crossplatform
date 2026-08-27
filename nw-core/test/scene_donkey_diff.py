#!/usr/bin/env python3
"""Differential harness for src/scene_donkey.elisa against the REAL screen.

The order is the thing the reference states outright: road, donkeys, car, and
then every donkey the car is INSIDE again, over the bonnet -- so a hit reads
as a donkey on top of a car rather than a donkey that vanished. The sweep
walks the car through the donkeys in sub-rows so that overlap happens.

Everything is placed against the car's tail at offset zero and drawn at its
own length in sub-rows, which is why the frame a round ends on is the frame
the two boxes meet.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.donkey import SPAN                             # noqa: E402
from neural_workshop.ui.donkey import Donkey                        # noqa: E402

PHASES = {0: "ready", 1: "setting", 2: "running", 3: "scored", 4: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_donkey_sweep.elisa")
ASKED = re.search(r'const ASKED: cstr = "((?:[^"\\]|\\.)*)"',
                  open(SWEEP).read()).group(1)


class Grade:
    name = 'two-row swerve'
    rows = 40
    swerve = 2


class Stretch:
    """Only what the drawing reads off a Road."""

    grade = Grade()

    def __init__(self, donkeys):
        self.beasts = tuple((8 + index * 11, index % 2)
                            for index in range(donkeys))
        self.blocked = (None,) * (8 + donkeys * 11 + 6)
        self.start = 0

    @property
    def donkeys(self):
        return len(self.beasts)

    @property
    def length(self):
        return len(self.blocked)

    @property
    def rows(self):
        return self.grade.rows


class Motor:
    """Only what the drawing reads off a Car."""

    def __init__(self, at, lane, crossing, span, passed):
        self.at = at
        self.lane = lane
        self.crossing = crossing
        self.span = span
        self.passed = passed
        self.hit = False

    @property
    def rows_done(self):
        return self.at // 4

    @property
    def share(self):
        if not self.crossing:
            return 0.0
        return (self.span - self.crossing + 1) / float(self.span + 1)


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
    screen = Donkey()
    screen.road = Stretch(spec["donkeys"]) if spec["has_road"] else None
    screen.car = Motor(spec["car_at"], spec["car_lane"], spec["car_crossing"],
                       spec["car_span"], spec["car_passed"])
    screen.rung = 3
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Swerve in time'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    # `_update_asked` builds the line from the grade; the sweep names the
    # result, so the two sides are looking at the same sentence. With no road
    # there is no line at all, and that arm is left alone.
    def lay_out():
        screen._build_chrome()
        if screen.road is not None:
            screen.asked.text = ASKED
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
