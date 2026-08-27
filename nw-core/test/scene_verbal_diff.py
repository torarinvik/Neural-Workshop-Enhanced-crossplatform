#!/usr/bin/env python3
"""Differential harness for src/scene_verbal.elisa against the REAL screen.

The first screen whose layout is driven by MEASURED text: the answer choices
are spread down whatever room is left under the wrapped question, so the whole
lower half of the frame moves if src/textmetrics.elisa is out by a line.

The question and choice texts are read back out of the sweep rather than
retyped here. They are long, the point of the long ones is which side of a
font-size step they fall on, and a copy that drifted by one character would
change the size on one side only -- which is a mismatch about the harness and
not about the port.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.verbal import VerbalReasoning               # noqa: E402

PHASES = {0: "ready", 1: "asking", 2: "judged", 3: "done", 4: "unavailable"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_verbal_sweep.elisa")


def literals():
    """PROMPTS, CHOICES and the explanation, lifted from the sweep source."""
    source = open(SWEEP).read()

    def returns(name):
        body = source.split("def %s(which: i64) -> cstr:" % name)[1]
        body = body.split("\n\n")[0]
        return [scenediff.unescape(one)
                for one in re.findall(r'return "((?:[^"\\]|\\.)*)"', body)]

    return returns("prompt_of"), returns("choice_of"), returns("explanation_of")


PROMPTS, CHOICES, EXPLANATIONS = literals()


class Made:
    """Only what `_redraw`, `_build_options` and `_lay_out` read off a Question."""

    task_type = 'sentence_completion'

    def __init__(self, prompt, choices, answer, explanation):
        self.prompt = prompt
        self.choices = choices
        self.answer = answer
        self.answer_text = choices[answer]
        self.explanation = explanation


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
    screen = VerbalReasoning()
    choices = list(CHOICES[:spec["choices"]])
    screen.question = (Made(PROMPTS[spec["prompt"]], choices, 0,
                            EXPLANATIONS[spec["note"]])
                       if spec["has_question"] else None)
    screen.choice = spec["choice"]
    screen.answered = spec["answered"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Sentence Completion'
    screen.show_explanation = bool(spec["show_explanation"])
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
