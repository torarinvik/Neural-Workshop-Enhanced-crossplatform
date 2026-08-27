#!/usr/bin/env python3
"""Differential harness for src/scene_field.elisa against the REAL screen.

The board itself is the real thing: `Field` is instantiated, so its grid, its
3D stage and its crosshair come from the module under test's own source. So do
the numbers the stimulus is placed by -- `position_pixel_center` and
`current_cell_px` are called here rather than restated, which is what makes
`centre_of` and `stimulus_size` a comparison and not a copy.

What is MIRRORED rather than instantiated is `Visual`. Its constructor makes
two labels and eight coloured-square sprites before a single one of them is
placed, and it picks an image set at random; a frame built from it would carry
nine widgets the board never shows, and would not be the same frame twice.
The three spawn branches are therefore rebuilt here with the constructor calls
`spawn` makes, in `spawn`'s order -- and the sizes and centres they are given
come off the reference's own functions, so what is restated is the pyglet
call and never the arithmetic.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
import bwaccel                                                      # noqa: E402

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.grid import (current_cell_px,                  # noqa: E402
                                  position_pixel_center)
from neural_workshop.paths import load_pyglet_image                 # noqa: E402
from neural_workshop.ui.field import Field                          # noqa: E402

GLYPHS = ["7", "12", "-3", "K"]
VARIABLES = ["2", "3", "5"]
COLOR = (19, 6, 224, 255)

#: Nothing may be garbage collected between building the frame and capturing
#: it -- the recorder holds weak references, and a shape dropped on the line
#: that made it is a shape that never happened.
KEEP = []


def build(spec):
    import framerec

    geometry.set_window_size(912, spec["tall"] // 2)
    display.relayout()
    if (geometry._width(), geometry._height()) != (1824, spec["tall"]):
        raise SystemExit("asked for 1824x%d pixels, got %dx%d"
                         % (spec["tall"], geometry._width(), geometry._height()))
    framerec.set_scale(geometry._width() / 912.0,
                       geometry._height() / (spec["tall"] / 2.0))

    cfg = state.cfg
    cfg.BLACK_BACKGROUND = bool(spec["black"])
    cfg.FIELD_EXPAND = bool(spec["expanded"])
    cfg.GRIDLINES = True
    cfg.CROSSHAIRS = bool(spec["crosshairs"])
    cfg.GRID_SIZE = spec["n"]
    cfg.GRID_SIZE_MIN = 2
    cfg.GRID_SIZE_MAX = 32
    cfg.GRID_INCLUDE_CENTER = bool(spec["include_center"])
    cfg.GRID_3D = bool(spec["grid_3d"])
    cfg.GRID_3D_CUBES = 1
    cfg.VARIABLE_NBACK = bool(spec["variable_mode"])
    state.mode.paused = bool(spec["paused"])
    state.mode.modalities[state.mode.mode] = (
        ['position1'] if spec["has_position"] else ['audio'])

    del KEEP[:]

    def lay_out():
        field = Field()
        KEEP.append(field)
        state.field = field
        _put_stimulus(spec, field)

    return _Nothing(), lay_out


class _Nothing:
    """`scenediff` closes the screen it built; this board has nothing to close."""

    def close(self):
        pass


def _put_stimulus(spec, field):
    """`Visual.spawn`'s three branches, and the variable-N label after them."""
    cell = current_cell_px()
    size = max(4, int(cell * (0.9375 if spec["shrunk"] else 1.0)))
    font = max(8, int(cell * 0.45))
    center_x, center_y = position_pixel_center(spec["position"])

    if spec["stim"] == 1:
        lx = center_x - size // 2 + 2
        rx = center_x + size // 2 - 2
        by = center_y - size // 2 + 2
        ty = center_y + size // 2 - 2
        if spec["sharp"]:
            points = [(lx, by), (rx, by), (rx, ty), (lx, ty)]
        else:
            xy = bwaccel.rounded_rect_vertices(lx, rx, by, ty, size // 5)
            points = list(zip(xy[0::2], xy[1::2]))
        KEEP.append(pyglet.shapes.Polygon(*points, color=COLOR,
                                          batch=state.batch))
    elif spec["stim"] == 2:
        from neural_workshop import resources
        image = load_pyglet_image(
            resources.resourcepaths['misc']['colored-squares'][0])
        sprite = pyglet.sprite.Sprite(image)
        if (image.width, image.height) != (256, 256):
            raise SystemExit("the coloured square is %dx%d, not the 256x256 "
                             "the sweep names" % (image.width, image.height))
        sprite.opacity = 255
        sprite.x = center_x - size // 2
        sprite.y = center_y - size // 2
        sprite.scale = 1.0 * size / image.width
        sprite.batch = state.batch
        KEEP.append(sprite)
    elif spec["stim"] == 3:
        label = pyglet.text.Label(
            GLYPHS[spec["glyph"]], font_size=font, weight='bold',
            anchor_x='center', anchor_y='center', batch=state.batch)
        label.x = center_x
        label.y = center_y + 4
        label.color = COLOR
        KEEP.append(label)

    if spec["variable"] >= 0:
        label = pyglet.text.Label(
            VARIABLES[spec["variable"]], font_size=font, weight='bold',
            anchor_x='center', anchor_y='center', batch=state.batch)
        label.x = field.center_x
        if not spec["has_position"]:
            label.y = field.center_y - int(current_cell_px()) + 4
        else:
            label.y = field.center_y + 4
        label.color = COLOR
        KEEP.append(label)


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
