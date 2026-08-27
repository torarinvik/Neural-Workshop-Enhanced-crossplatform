#!/usr/bin/env python3
"""Differential harness for src/scene_overrun.elisa against the REAL screen.

One label a letter on an 88-cell grid, and three things about it are easy to
get wrong: a space gets no label at all, the line is drawn from the original
offsets LESS whatever the cleared words took away, and an already-typed letter
is drawn as what was TYPED rather than what was wanted -- blue if they agree
and vermillion if they do not. The swept prefixes carry a mistake at index 2
so both colours are drawn.

The letter size is measured off an 'm' at 24 points, which is textmetrics
again: a letter wider than its cell would put the drawing and the arithmetic
into disagreement about where the end of the line is.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import overrun as overrun_ui                # noqa: E402
from neural_workshop.ui.overrun import Overrun                      # noqa: E402

PHASES = {0: "ready", 1: "typing", 2: "settled", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_overrun_sweep.elisa")
SOURCE = open(SWEEP).read()


def returns(name):
    body = SOURCE.split("def %s(which: i64) -> cstr:" % name)[1]
    body = body.split("\n\n")[0]
    return [scenediff.unescape(one)
            for one in re.findall(r'return "((?:[^"\\]|\\.)*)"', body)]


WORDS = returns("word_of")
TYPED = returns("typed_of")
MISSING = re.search(r'const MISSING: cstr = "((?:[^"\\]|\\.)*)"',
                    SOURCE).group(1)


class Swell:
    """Only what the drawing reads off a Wave, with its own arithmetic."""

    def __init__(self, words):
        self.words = tuple(words)
        starts, at = [], 0
        for word in self.words:
            starts.append(at)
            at += len(word) + 1
        self.starts = tuple(starts)

    @property
    def line(self):
        return ' '.join(self.words)

    @property
    def length(self):
        return len(self.line)

    @property
    def letters(self):
        return sum(len(word) for word in self.words)

    @property
    def start_cell(self):
        return overrun_ui.CELLS - 2 * self.length

    @property
    def seconds(self):
        return self.length / 6.5


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
    overrun_ui.missing_message = lambda: MISSING
    screen = Overrun()
    screen.stocked = staticmethod(lambda: bool(spec["stocked"]))
    screen.wave = Swell(WORDS[:spec["words"]]) if spec["has_wave"] else None
    screen.cleared = spec["cleared"]
    screen.typed = TYPED[spec["typed"]]
    screen.drift = spec["drift"] * 0.5
    screen.lives = spec["lives"]
    screen.trial = spec["trial"]
    screen.total_waves = spec["total_waves"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - plain words'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
