#!/usr/bin/env python3
"""Differential harness for src/scene_removals.elisa against the REAL screen.

Builds the pyglet application headless, makes a Removals screen, puts it in the
state the sweep named, asks it to redraw, and reads back the widgets it built.
See test/scenediff.py for everything around that, and test/framerec.py for how
a widget becomes a command.

The round comes from the reference's own generator, which removals_diff.py
already checks byte-for-byte against the port's -- so a disagreement here is a
disagreement about DRAWING and nothing else.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import state                                  # noqa: E402
from neural_workshop.removals import GRADES, generate              # noqa: E402
from neural_workshop.ui.removals import Removals                   # noqa: E402
from neural_workshop.i18n import _                                 # noqa: E402

PHASES = {0: "ready", 1: "moving", 2: "asking", 3: "scored"}


def build(spec):
    # The background flag decides the chrome's colour and the chrome is built
    # in the constructor, so it has to be set before the screen is made.
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = Removals()
    screen.round = generate(spec["rung"], seed=spec["seed"])
    screen.rung = spec["rung"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.cursor = spec["cursor"]
    screen.asking_at = spec["asking_at"]
    screen.phase = PHASES[spec["phase"]]
    if spec["phase"] == 1:
        screen.message = _('%s — %d vans, %d moves') % (
            _(GRADES[spec["rung"] - 1].name), screen.round.yard.vans,
            len(screen.round.moves))
    elif spec["phase"] == 2:
        screen.message = _('The doors close')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
