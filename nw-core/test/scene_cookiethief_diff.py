#!/usr/bin/env python3
"""Differential harness for src/scene_cookiethief.elisa against the REAL screen.

The door is the whole of the risk and every term in it is on the screen: a
solid part for the cookies already gone, which never closes, and a faint part
on top for the noise a quick hand made, which does. The sweep varies both so
each is drawn on its own and together.

The figure in the doorway is told apart by HEIGHT rather than by colour, so all
three are swept, in both the coming and the watching states -- a watcher steps
left, goes opaque, and gains two eyes punched out in the background colour.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.cookiethief import (AWAY, COMING, DOG, MOTHER,  # noqa: E402
                                         SISTER, WATCHING)
from neural_workshop.ui.cookiethief import CookieThief              # noqa: E402

PHASES = {0: "ready", 1: "setting", 2: "running", 3: "scored", 4: "done"}
AT_DOOR = {0: AWAY, 1: COMING, 2: WATCHING}
WHO = {0: MOTHER, 1: SISTER, 2: DOG}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_cookiethief_sweep.elisa")
ASKED = re.search(r'const ASKED: cstr = "((?:[^"\\]|\\.)*)"',
                  open(SWEEP).read()).group(1)


class Grade:
    name = 'quick hands'
    reactive = True
    warn = 2
    decoys = True

    def __init__(self, room, quota, notice, opening, limit, gold):
        self.room = room
        self.quota = quota
        self.notice = notice
        self.opening = opening
        self.limit = limit
        self.gold = gold


class Setup:
    def __init__(self, grade):
        self.grade = grade


class Boy:
    """Only what the drawing reads off a Thief."""

    def __init__(self, spec):
        self.jar = spec["jar"]
        self.eaten = spec["eaten"]
        self.pace = spec["pace"]
        self.beat = spec["beat"]
        self.reaching = spec["reaching"]
        self.gold_from = spec["gold_from"]
        self.gold_taken = bool(spec["gold_taken"])
        self.phase = AT_DOOR[spec["at_door"]]
        self.who = WHO[spec["who"]]

    @property
    def gold_on_offer(self):
        return (self.gold_from >= 0 and not self.gold_taken
                and self.beat < self.gold_from + 6)

    @property
    def committed(self):
        return self.reaching > 0


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
    screen = CookieThief()
    grade = Grade(spec["room"], spec["quota"], spec["notice"],
                  spec["opening"], spec["limit"], 3)
    screen.setup = Setup(grade)
    screen.thief = Boy(spec)
    screen.grabbing = bool(spec["grabbing"])
    screen.rung = 3
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Take six and go'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    def lay_out():
        screen._build_chrome()
        screen.asked.text = ASKED
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
