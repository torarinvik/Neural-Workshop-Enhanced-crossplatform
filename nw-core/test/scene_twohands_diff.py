#!/usr/bin/env python3
"""Differential harness for src/scene_twohands.elisa against the REAL screen.

The only perspective in the workshop, and it is one function -- so the sweep
walks the car down the road in sub-rows, which slides the bands, swaps the
dashes onto the rows between them, and moves every hazard through the whole
depth of the view.

Hazards are drawn FAR ONES FIRST, and two of the swept ones stand the same
distance away so the sort has a tie to keep. All nine kinds appear, because
each carries its two rule-bits in shape rather than in colour and they are
nine different shapes.

The road, the ride and the sky are the model's, and the model has a suite of
its own; what is set here is what it would have returned.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state, twohands      # noqa: E402
from neural_workshop.ui import twohands as twohands_ui              # noqa: E402
from neural_workshop.ui.twohands import Twohands                    # noqa: E402

PHASES = {0: "ready", 1: "setting", 2: "running", 3: "scored", 4: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_twohands_sweep.elisa")
ASKED = re.search(r'const ASKED: cstr = "((?:[^"\\]|\\.)*)"',
                  open(SWEEP).read()).group(1)

SUB = 4
BODY = 3
CAR = 3


class Hazard:
    """Only what the drawing reads off a Hazard, with its own `body`."""

    def __init__(self, ahead, lane, kind, at):
        self.at = at
        self.lane = lane
        self.kind = kind
        self._ahead = ahead

    @property
    def body(self):
        return self.at + CAR - 1


class Target:
    def __init__(self, across, up):
        self._across = across
        self._up = up

    def aloft(self, _at):
        return True

    def where(self, _at):
        return (self._across, self._up)


class Grade:
    def __init__(self, top):
        self.top = top
        self.hang = 4
        self.swerve = 2
        self.name = 'three lanes'


class Road:
    def __init__(self, hazards, sky, top):
        self.hazards = hazards
        self.sky = sky
        self.grade = Grade(top)
        self.length = 240
        self.rows = 60
        self.clock = 90
        self.par = 40
        self.start = 0


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
    screen = Twohands()
    at = spec["at"]
    # `_in_view` measures `_rows_of(haz.body - at)`, so a hazard standing the
    # sweep's number of rows ahead has its body that many sub-rows past the
    # car -- which is what is solved for here.
    hazards = []
    for index in range(spec["hazards"]):
        body = at + 2 + index * 7
        hazards.append(Hazard(0.0, index % 3, index % 9, body - CAR + 1))
    sky = [Target(0.11 + 0.19 * index, 0.17 + 0.16 * (index % 4))
           for index in range(spec["sky"])]
    road = Road(hazards, sky, spec["top_gear"])
    screen.road = road
    screen.ride = twohands.Ride(at=at, lane=0, to=1, cross=0,
                                air=spec["air"],
                                speed=spec["gear"], ticks=spec["at"] % 91,
                                points=spec["at"] % 23)
    screen.downed = set(range(spec["downed"]))
    screen.shot = spec["downed"]
    screen.points = 0
    screen.cross_x = 0.29 + 0.07 * (spec["spec"] % 8)
    screen.cross_y = 0.23 + 0.09 * (spec["spec"] % 6)
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Drive and shoot'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    names = ('drawn_lane', 'sighted')
    stubs = {
        'drawn_lane': lambda _ride, _grade: spec["car_lane"] / 2.0,
        'sighted': lambda *rest, **kw: 0 if spec["loaded"] else None,
    }

    def lay_out():
        held = {name: getattr(twohands_ui, name) for name in names}
        for name in names:
            setattr(twohands_ui, name, stubs[name])
        try:
            screen._build_chrome()
            screen.asked.text = ASKED
        finally:
            for name, was in held.items():
                setattr(twohands_ui, name, was)
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
