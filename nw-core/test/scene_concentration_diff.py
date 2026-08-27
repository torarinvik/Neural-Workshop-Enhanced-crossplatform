#!/usr/bin/env python3
"""Differential harness for src/scene_concentration.elisa against the REAL screen.

The board's SHAPE is the thing under test: the column count is the square root
of the card count times the room's aspect, rounded half to even, then walked
down while a whole row would be left empty. A board of the wrong shape lays
every card somewhere else, so the sweep runs every size from two pairs to
fifteen at both window heights.

Each board carries all three card fills at once -- matched, face up, face down
-- because the fill is what says what a card is.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.concentration import Concentration          # noqa: E402

MEDIA = {0: "picture", 1: "sound"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_concentration_sweep.elisa")
SOURCE = open(SWEEP).read()


def sizes(name):
    body = SOURCE.split("def %s(which: i64) -> i64:" % name)[1]
    body = body.split("\n\n")[0]
    return [int(one) for one in re.findall(r"return (\d+)", body)]


IMAGES = [pyglet.image.SolidColorImagePattern((0, 0, 255, 255))
          .create_image(wide, tall)
          for wide, tall in zip(sizes("image_width_of"),
                                sizes("image_height_of"))]


class Pool:
    @staticmethod
    def item(path):
        return IMAGES[int(path)]


class Card:
    """Only what `_layout_board` and `_redraw` read off a Card."""

    def __init__(self, position):
        self.face_up = position % 3 == 1
        self.matched = position % 3 == 2
        self.index = position // 2
        self.path = str(position % len(IMAGES))
        self.rect = (0.0, 0.0, 0.0, 0.0)


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
    screen = Concentration()
    screen.pool = Pool()
    screen.medium = MEDIA[spec["medium"]]
    screen.pairs = spec["pairs"]
    screen.cards = [Card(position) for position in range(spec["pairs"] * 2)]
    screen.turns = spec["turns"]
    screen.show_turns = bool(spec["show_turns"])
    screen.message = 'Find the pairs'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
