#!/usr/bin/env python3
"""Differential harness for src/scene_jigsaw.elisa against the REAL screen.

The ORDER is the thing under test. The reference puts the tiles in a group at
order 0 and the marks in a group at order 1, and pyglet draws a batch by group
before serial -- so every tile and the preview go down first and every mark
afterwards, even though a tile and its own mark are created one after the
other. A port that emitted them interleaved would draw the same picture and be
a different display list.

A mark is drawn under five conditions and only the first that matches wins, so
the sweep carries a picked tile and a hovered one and neither, with the
already-home marking both on and off.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.jigsaw import JigsawPuzzle                  # noqa: E402

PHASES = {0: "ready", 1: "solving", 2: "solved", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_jigsaw_sweep.elisa")
SOURCE = open(SWEEP).read()


def named(name):
    return int(re.search(r"const %s: i64 = (\d+)" % name, SOURCE).group(1))


IMAGE_WIDTH = named("IMAGE_WIDTH")
IMAGE_HEIGHT = named("IMAGE_HEIGHT")
TILE_PIXELS = named("TILE_PIXELS")
SMALL_LIBRARY = re.search(r'const SMALL_LIBRARY: cstr = "((?:[^"\\]|\\.)*)"',
                          SOURCE).group(1)

PICTURE = (pyglet.image.SolidColorImagePattern((200, 120, 40, 255))
           .create_image(IMAGE_WIDTH, IMAGE_HEIGHT))
TILES = [pyglet.image.SolidColorImagePattern((30 + one, 60, 90, 255))
         .create_image(TILE_PIXELS, TILE_PIXELS) for one in range(64)]


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
    screen = JigsawPuzzle()
    side = spec["side"]
    places = side * side
    screen.trial_side = side
    screen.tiles = TILES[:places]
    screen.order = [position if position % 3 == 0 else (position + 1) % places
                    for position in range(places)]
    screen.image = PICTURE
    screen.preview = bool(spec["preview"])
    screen.picked = None if spec["picked"] < 0 else spec["picked"]
    screen.hovered = None if spec["hovered"] < 0 else spec["hovered"]
    screen.mark_placed = bool(spec["mark_placed"])
    screen.puzzle = spec["puzzle"]
    screen.total_puzzles = spec["total_puzzles"]
    screen.swaps = spec["swaps"]
    screen.par = spec["par"]
    screen.small_library = SMALL_LIBRARY if spec["small"] else ''
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Put it back together'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
