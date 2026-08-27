#!/usr/bin/env python3
"""Differential harness for src/scene_trivia.elisa against the REAL screen.

The whole column of options hangs off how tall the wrapped question turned
out, so the questions in the sweep are one that does not wrap, one that wraps
to two lines and one that wraps to several -- and the option count varies
separately, because the step down the page is the room left over divided by
how many there are.

`fetched()`, `bank()` and `missing_message()` are about the installation
rather than the game, so they are replaced here with what the spec names.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import trivia as trivia_ui                   # noqa: E402
from neural_workshop.ui.trivia import Trivia                         # noqa: E402

PHASES = {0: "ready", 1: "asking", 2: "judged", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_trivia_sweep.elisa")
SOURCE = open(SWEEP).read()


def returns(name):
    body = SOURCE.split("def %s(which: i64) -> cstr:" % name)[1]
    body = body.split("\n\n")[0]
    return [one.encode().decode("unicode_escape")
            for one in re.findall(r'return "((?:[^"\\]|\\.)*)"', body)]


QUESTIONS = returns("question_of")
OPTIONS = returns("option_of")
MISSING = re.search(r'const MISSING: cstr = "((?:[^"\\]|\\.)*)"',
                    SOURCE).group(1)


class Made:
    """Only what `_redraw`, `_build_options` and `_colour_options` read."""

    def __init__(self, asked, options, answer):
        self.asked = asked
        self.options = options
        self.answer = answer
        self.shown_answer = options[answer]


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
    trivia_ui.fetched = lambda: bool(spec["fetched"])
    trivia_ui.missing_message = lambda: MISSING
    trivia_ui.bank = lambda: [None] * spec["pool"]
    screen = Trivia()
    screen.round = (Made(QUESTIONS[spec["question"]],
                         list(OPTIONS[:spec["options"]]), spec["answer"])
                    if spec["has_round"] else None)
    screen.choice = spec["choice"]
    screen.answered = spec["answered"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - general'
    screen.show_answer = bool(spec["show_answer"])
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
