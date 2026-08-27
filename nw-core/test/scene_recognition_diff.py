#!/usr/bin/env python3
"""Differential harness for src/scene_recognition.elisa against the REAL screen.

The stage is not symmetric between the two media, which is the thing worth
sweeping: a sound's plate and crotchet stay up through the HIDDEN phase --
the sound is still playing, so the screen still has something to say -- while
a picture is taken down and only the buttons remain.

The image pool is a stand-in, as in Reflex: the real one draws from the
player's own photographs.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.recognition import Recognition              # noqa: E402

PHASES = {0: "ready", 1: "showing", 2: "hidden", 3: "done"}
MEDIA = {0: "picture", 1: "sound"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_recognition_sweep.elisa")
SOURCE = open(SWEEP).read()


def sizes(name):
    body = SOURCE.split("def %s(which: i64) -> i64:" % name)[1]
    body = body.split("\n\n")[0]
    return [int(one) for one in re.findall(r"return (\d+)", body)]


IMAGES = [pyglet.image.SolidColorImagePattern((0, 255, 0, 255))
          .create_image(wide, tall)
          for wide, tall in zip(sizes("image_width_of"),
                                sizes("image_height_of"))]


class Pool:
    @staticmethod
    def item(path):
        return IMAGES[int(path)]


class Round:
    """Only what `_draw_stage` reads off a Trial."""

    def __init__(self, asset):
        self.path = str(asset)


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
    screen = Recognition()
    screen.pool = Pool()
    screen.medium = MEDIA[spec["medium"]]
    screen.trials = [Round(spec["asset"]) for _ in range(spec["trials"])]
    screen.index = spec["index"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Seen it, or new?'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
