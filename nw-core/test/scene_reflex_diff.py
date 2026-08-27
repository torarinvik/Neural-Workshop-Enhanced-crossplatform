#!/usr/bin/env python3
"""Differential harness for src/scene_reflex.elisa against the REAL screen.

The first scene whose drawing depends on the IMAGE. A target's scale is
`side / image.width`, so the core has to be told the width -- the shell
decodes the file and hands over its size, and the arithmetic stays on the
core's side. The stand-in library here is three solid images of different
shapes, so a scale taken from the width is not the same number as one taken
from the height.

The image pool is replaced rather than read: the real one draws from the
player's own photographs, and a differential that depended on which pictures
were on the machine would not be one.

A target with no life left is still DRAWN, at the scale floor of 0.001, so one
in five of the swept targets is spent.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui import reflex as reflex_ui                  # noqa: E402
from neural_workshop.ui.reflex import Reflex, Target                # noqa: E402

PHASES = {0: "ready", 1: "running", 2: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_reflex_sweep.elisa")
SOURCE = open(SWEEP).read()


def sizes(name):
    body = SOURCE.split("def %s(which: i64) -> i64:" % name)[1]
    body = body.split("\n\n")[0]
    return [int(one) for one in re.findall(r"return (\d+)", body)]


WIDTHS = sizes("image_width_of")
HEIGHTS = sizes("image_height_of")
IMAGES = [pyglet.image.SolidColorImagePattern((255, 0, 0, 255))
          .create_image(wide, tall)
          for wide, tall in zip(WIDTHS, HEIGHTS)]


class Pool:
    """The stand-in library: `item` is all the drawing ever asks of it."""

    @staticmethod
    def item(path):
        return IMAGES[int(path)]

    @staticmethod
    def reload():
        return None

    @staticmethod
    def ready(_count):
        return True

    @staticmethod
    def take():
        return None


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
    reflex_ui.media.image_pool = lambda _rng: Pool()
    screen = Reflex()
    screen.pool = Pool()
    # `remaining` is `1 - (now - born) / lifetime`, so with the clock at 1 and
    # a lifetime of 1 it comes out as `born` exactly -- which is how the wanted
    # fraction is set here.
    screen.clock = lambda: 1.0
    screen.targets = [
        Target(str(index % len(IMAGES)),
               0.12 + 0.14 * (index % 6), 0.22 + 0.12 * (index % 5),
               1.0, 0.0 if index % 5 == 4 else 1.0 - 0.17 * (index % 5))
        for index in range(spec["targets"])]
    screen.start_size = spec["start_size"]
    screen.spawned = spec["spawned"]
    screen.total_targets = spec["total_targets"]
    screen.hits = spec["hits"]
    screen.misses = spec["misses"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Click them before they go'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
