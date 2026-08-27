#!/usr/bin/env python3
"""Differential harness for src/scene_custody.elisa against the REAL screen.

The slot numbering is the layout's whole trick: the first `width` slots run
left to right along the top and the rest run right to LEFT along the bottom,
so slot and slot+1 are neighbours on screen as well as on the belt. The claw
is swept across both runs, because the arm reaches up on one and down on the
other and a held box lifts the same way.

Two of the round's requirements can be OFF -- no charge asked for, and no heat
limit -- and each turns a whole piece of the box off with it, so both are
swept.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.custody import CHARGER, COOLER, PAINTER        # noqa: E402
from neural_workshop.ui.custody import ChainOfCustody               # noqa: E402

PHASES = {0: "ready", 1: "marking", 2: "running", 3: "scored", 4: "done"}
KINDS = (CHARGER, COOLER, PAINTER)

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_custody_sweep.elisa")
ASKED = re.search(r'const ASKED: cstr = "((?:[^"\\]|\\.)*)"',
                  open(SWEEP).read()).group(1)


class Machine:
    def __init__(self, slot, kind):
        self.slot = slot
        self.kind = kind


class Box:
    def __init__(self, index, slots):
        self.slot = (2 + index * 2) % slots
        self.held = index == 1
        self.delivered = index == 3
        self.look = index
        self.charge = 0 if index % 4 == 0 else 25 * (index % 4)
        self.heat = 0 if index % 3 == 0 else 30 * (index % 3)
        self.latent = index


class Plan:
    """Only what the drawing reads off a Layout."""

    def __init__(self, span, machines, need_charge, max_heat, budget):
        self.width = span
        self.slots = span * 2
        self.bay = span * 2 - 1
        self.machines = [Machine((1 + index * 3) % (span * 2),
                                 KINDS[index % 3])
                         for index in range(machines)]
        self.need_charge = need_charge
        self.max_heat = max_heat
        self.budget = budget
        self.core = 0


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
    screen = ChainOfCustody()
    plan = Plan(spec["span"], spec["machines"], spec["need_charge"],
                spec["max_heat"], spec["budget"])
    screen.layout = plan
    screen.boxes = [Box(index, plan.slots) for index in range(spec["boxes"])]
    screen.claw = spec["claw"]
    screen.spent = spec["spent"]
    screen.rung = 3
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Follow the Core'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    # `_update_asked` builds the line from the rung's grade; the sweep names
    # the result, so the two sides are looking at the same sentence.
    def lay_out():
        screen._build_chrome()
        screen.asked.text = ASKED
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
