#!/usr/bin/env python3
"""Differential harness for src/scene_ravens.elisa against the REAL screen.

What is under test is the PLACEMENT: where the matrix and each candidate are
blitted, at what scale, which one is outlined and in what colour, and where
its number goes.

What is NOT under test, and not in the port, is the inside of a card. Those
figures go into one raw vertex list per card rather than into drawables, and a
raw vertex list is not something the recorder wraps -- so it cannot be seen
here and could not be checked. The port stops at that seam rather than
shipping geometry nothing verifies.

The two blocks are sized together, so the sweep runs four candidates (a block
SHORTER than the grid, which is the arm that once pushed the grid up through
the title) as well as eight, and the explanation on and off, which takes its
room out of the puzzle and moves the whole board.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import ravens as ravens_ui                  # noqa: E402
from neural_workshop.ui.ravens import MatrixReasoning               # noqa: E402

PHASES = {0: "ready", 1: "asking", 2: "hidden", 3: "feedback", 4: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_ravens_sweep.elisa")
NOTES = re.search(r'const NOTES: cstr = "((?:[^"\\]|\\.)*)"',
                  open(SWEEP).read()).group(1)

MATRIX_PIXELS = 512
CHOICE_PIXELS = 128


class Card:
    """A stand-in for the offscreen card: only its texture is ever read."""

    def __init__(self, pixels):
        self.texture = (pyglet.image.SolidColorImagePattern((9, 9, 9, 255))
                        .create_image(pixels, pixels))

    def delete(self):
        return None


class Puzzle:
    def __init__(self, across, choices, answer):
        self.across = across
        self.choices = [None] * choices
        self.answer = answer
        self.explanation = NOTES.split('   ·   ')


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
    screen = MatrixReasoning()
    screen.puzzle = Puzzle(spec["across"], spec["choices"], spec["answer"])
    screen.picked = None if spec["picked"] < 0 else spec["picked"]
    screen.hovered = None if spec["hovered"] < 0 else spec["hovered"]
    screen.explain = bool(spec["explain"])
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.correct = spec["right"]
    screen.trial_level = spec["trial_level"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Which one finishes it?'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    def lay_out():
        # The cards are replaced with plain textures of a known size. Making
        # the real ones needs a framebuffer per card and paints geometry
        # nothing here can see; what the placement needs off them is their
        # pixel width, and that is all this hands over.
        screen._delete_cards()
        screen.matrix_card = Card(MATRIX_PIXELS)
        screen.choice_cards = [Card(CHOICE_PIXELS)
                               for _ in range(spec["choices"])]
        held = screen._build_cards
        screen._build_cards = lambda: None
        try:
            screen._build_chrome()
        finally:
            screen._build_cards = held
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
