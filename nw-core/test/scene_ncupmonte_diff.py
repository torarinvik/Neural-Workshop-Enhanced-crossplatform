#!/usr/bin/env python3
"""Differential harness for src/scene_ncupmonte.elisa against the REAL screen.

`xs` is a screen fact, not a game fact: during a shuffle the cups are between
slots and the animation owns those numbers. Half the specs are settled and half
are nudged off, so a mid-swap frame is covered as well as a resting one.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import random
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.ui.ncupmonte import NCupMonte                 # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "hide", 2: "shuffle", 3: "guess", 4: "reveal",
          5: "result"}


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = NCupMonte()
    cups = spec["cups"]
    screen.cups = cups
    screen.show_numbers = bool(spec["show_numbers"])
    order = list(range(cups))
    random.Random(spec["seed"]).shuffle(order)
    screen.order = order
    screen.ball = spec["ball"]
    screen.guess = spec["guess"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = _('Press Space to hide the ball')

    def lay_out():
        # `_build_chrome` calls `_resize_slots`, which puts every cup back on
        # its slot -- deliberately, so a resize mid-shuffle does not hand the
        # player the answer. So the off-slot positions go on AFTER it, and the
        # cups are redrawn. The chrome keeps its lower serials either way, so
        # the frame comes back in the same order.
        screen._build_chrome()
        screen.xs = screen._slot_positions(cups)
        if spec["nudged"]:
            screen.xs = [x + 17.5 if index % 2 == 0 else x
                         for index, x in enumerate(screen.xs)]
        screen._redraw()

    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
