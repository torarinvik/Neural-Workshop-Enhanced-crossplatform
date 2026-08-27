#!/usr/bin/env python3
"""Differential harness for src/scene_hanoi.elisa against the REAL screen.

The board is walked into position by applying the same random legal moves the
sweep applies, rather than by being assembled: a peg layout no sequence of
legal moves reaches is a layout the screen never draws.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import random
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
# Hanoi has no separate logic module: the rules live in the UI file beside the
# drawing, which is why the port splits them into tasks/hanoi.elisa and
# scene_hanoi.elisa and this imports both halves from one place.
from neural_workshop.ui.hanoi import (TowerOfHanoi, can_move, fresh_pegs,   # noqa: E402
                                      minimum_moves)
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "solving", 2: "solved", 3: "done"}


def walked(disks, seed, steps):
    pegs = fresh_pegs(disks)
    rng = random.Random(seed)
    moves = 0
    for _step in range(steps):
        source = rng.randrange(0, 3)
        target = rng.randrange(0, 3)
        if source != target and can_move(pegs, source, target):
            pegs[target].append(pegs[source].pop())
            moves += 1
    return pegs, moves


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = TowerOfHanoi()
    disks = spec["disks"]
    screen.trial_disks = disks
    screen.disks = disks
    screen.pegs, moves = walked(disks, spec["seed"], spec["walk"])
    screen.moves = moves
    screen.par = minimum_moves(disks)
    screen.round = spec["round"]
    screen.total_rounds = spec["total_rounds"]
    screen.picked = None if spec["picked"] < 0 else spec["picked"]
    screen.phase = PHASES[spec["phase"]]
    if spec["phase"] == 1:
        screen.message = _('Rebuild the tower on another peg')
    elif spec["phase"] == 2:
        screen.message = _('Solved')
    else:
        screen.message = _('Press Space to start')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
