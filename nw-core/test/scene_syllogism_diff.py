#!/usr/bin/env python3
"""Differential harness for src/scene_syllogism.elisa against the REAL screen.

Everything on this page is measured from the block above it, so the sweep
carries premise blocks of 2, 7 and 13 lines -- one in each band of the size
step -- and answer counts of 3, 5, 9, 12 and 27, which is one column, the edge
of one column, the last numbered count, the last unshortened count, and the
four-column shortened set the abbreviations were written for.

The texts are read back out of the sweep rather than retyped, because what
matters about the long ones is which side of a step they fall on.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.syllogism import Syllogism                  # noqa: E402

PHASES = {0: "ready", 1: "asking", 2: "judged", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_syllogism_sweep.elisa")
SOURCE = open(SWEEP).read()


def returns(name):
    body = SOURCE.split("def %s(which: i64) -> cstr:" % name)[1]
    body = body.split("\n\n")[0]
    return [scenediff.unescape(one)
            for one in re.findall(r'return "((?:[^"\\]|\\.)*)"', body)]


BLOCKS = returns("block_of")
ANSWERS = returns("answer_of")
HINT = scenediff.unescape(re.search(r'const HINT: cstr = "((?:[^"\\]|\\.)*)"',
                                    SOURCE).group(1))


class Grade:
    family = 'order'


class Made:
    """Only what `_redraw`, `_build_options` and `_premise_size` read."""

    grade = Grade()
    asked = 'Who is the tallest?'

    def __init__(self, lines, options):
        self.lines = lines
        self.working = lines
        self.options = options


def build(spec):
    import framerec
    from neural_workshop.ui import syllogism as syllogism_ui
    geometry.set_window_size(912, spec["tall"] // 2)
    display.relayout()
    if (geometry._width(), geometry._height()) != (1824, spec["tall"]):
        raise SystemExit("asked for 1824x%d pixels, got %dx%d"
                         % (spec["tall"], geometry._width(), geometry._height()))
    framerec.set_scale(geometry._width() / 912.0,
                       geometry._height() / (spec["tall"] / 2.0))
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    syllogism_ui.HINTS = {'order': HINT}
    screen = Syllogism()
    lines = BLOCKS[spec["block"]].split('\n')
    options = [ANSWERS[one % 9] for one in range(spec["answers"])]
    screen.question = Made(lines, options) if spec["has_question"] else None
    screen.choice = spec["choice"]
    screen.answered = spec["answered"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - order'
    # `working` is the same block as `lines` here, so the judged frame draws
    # the premises either way and the sweep does not have to carry a second
    # block that would only ever differ by its text.
    screen.show_working = False
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
