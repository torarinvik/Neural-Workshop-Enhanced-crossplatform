#!/usr/bin/env python3
"""Differential harness for src/scene_hud.elisa against the REAL widgets.

The furniture that stays on screen: the three-strikes circles, the mode
caption, the key list, the title screen's own labels, the logo's caption, the
pause notice and the end-of-session line.

Two things this checks that reading would not settle. The circles do not hide
by leaving -- when there is nothing to show they are recoloured to the
background at ZERO alpha and still drawn, so the row keeps its place, and the
recorder has to agree that a fully transparent circle is a command. And
several of these are placed off the FIELD rather than the window, two of them
off `field.center_x` where the reading is plainly `center_y`, which is
reproduced because it is where the labels are.

The widgets are built here rather than through a live session: what each says
comes off `state.mode`, which has suites of its own.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.geometry import (calc_fontsize, from_bottom_edge,  # noqa: E402
                                      from_height_center, from_left_edge,
                                      from_top_edge, from_width_center,
                                      scale_to_height, scale_to_width,
                                      width_center)

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_hud_sweep.elisa")
SOURCE = open(SWEEP).read()


def named(name):
    return scenediff.unescape(
        re.search(r'const %s: cstr = "((?:[^"\\]|\\.)*)"' % name,
                  SOURCE).group(1))


UPDATE = named("UPDATE")
GAME_MODE = named("GAME_MODE")
JAEGGI = named("JAEGGI")
KEYS = named("KEYS")
VERSION = named("VERSION")
NATIVE = named("NATIVE")
TITLE_KEYS = named("TITLE_KEYS")
CONGRATS = named("CONGRATS")


class Nothing:
    def close(self):
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
    if spec["black"]:
        state.cfg.COLOR_TEXT = state.cfg.COLOR_TEXT_BLK
    else:
        state.cfg.COLOR_TEXT = (0, 0, 0, 255)
    ink = tuple(state.cfg.COLOR_TEXT)
    held = []

    def lay_out():
        del held[:]
        batch = pyglet.graphics.Batch()
        held.append(batch)
        field_size = int(state.window.height * 0.625)
        field_x = width_center()
        field_y = from_height_center(20)

        dim = 64 if spec["black"] else 192
        back = 0 if spec["black"] else 255
        y = from_top_edge(20)
        start_x = from_left_edge(30)
        radius = scale_to_width(8)
        step = scale_to_width(20)
        for index in range(spec["circles"]):
            if spec["showing"]:
                shade = ((64, 64, 255, 255) if index < spec["progress"]
                         else (dim, dim, dim, 255))
            else:
                shade = (back, back, back, 0)
            held.append(pyglet.shapes.Circle(
                start_x + step * index, y, radius, color=shade, batch=batch))

        held.append(pyglet.text.Label(
            UPDATE, multiline=True, width=field_size // 3 - 4, align='middle',
            font_size=calc_fontsize(11), weight='bold', color=(0, 128, 0, 255),
            x=width_center(), y=field_x + field_size // 6,
            anchor_x='center', anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            GAME_MODE, font_size=calc_fontsize(16),
            color=(255, 0, 255, 255) if spec["flashing"] else ink,
            x=width_center(), y=from_top_edge(20), anchor_x='center',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            JAEGGI, font_size=calc_fontsize(12), weight='bold',
            color=(255, 0, 255, 255), x=width_center(),
            y=field_x + field_size // 3 + 8, anchor_x='center',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            KEYS, multiline=True, width=scale_to_width(300), weight='normal',
            font_size=calc_fontsize(9), color=ink, x=scale_to_width(10),
            y=from_top_edge(30 if spec["lifted"] else 40), anchor_x='left',
            anchor_y='top', batch=batch))
        held.append(pyglet.text.Label(
            'Neural Workshop', font_size=calc_fontsize(32), weight='bold',
            color=ink, x=width_center(), y=from_top_edge(25),
            anchor_x='center', anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            VERSION, font_size=calc_fontsize(14), weight='normal', color=ink,
            x=width_center(), y=from_top_edge(55), anchor_x='center',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            NATIVE, font_size=calc_fontsize(10), weight='normal', color=ink,
            x=width_center(), y=from_top_edge(78), anchor_x='center',
            anchor_y='center', batch=batch))
        # The title screen's prompt is drawn BEFORE its key list.
        held.append(pyglet.text.Label(
            'Press SPACE to enter the Workshop', font_size=calc_fontsize(20),
            weight='bold', color=(32, 32, 255, 255), x=width_center(),
            y=from_bottom_edge(35), anchor_x='center', anchor_y='center',
            batch=batch))
        held.append(pyglet.text.Label(
            TITLE_KEYS, multiline=True, width=scale_to_width(260),
            font_size=calc_fontsize(12), weight='bold', color=ink,
            x=from_width_center(65), y=from_bottom_edge(260),
            anchor_x='center', anchor_y='top', batch=batch))
        held.append(pyglet.text.Label(
            NATIVE, font_size=calc_fontsize(9), color=ink,
            x=from_left_edge(10), y=from_bottom_edge(14), anchor_x='left',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            'Brain', font_size=calc_fontsize(11), weight='bold', color=ink,
            x=field_x, y=field_y + scale_to_height(30), anchor_x='center',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            'Workshop', font_size=calc_fontsize(11), weight='bold', color=ink,
            x=field_x, y=field_y - scale_to_height(27), anchor_x='center',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            'Paused' if spec["paused"] else '', font_size=calc_fontsize(14),
            color=(64, 64, 255, 255), x=field_x, y=field_y,
            anchor_x='center', anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            CONGRATS, font_size=calc_fontsize(14), color=(255, 32, 32, 255),
            x=field_x, y=from_top_edge(47), anchor_x='center',
            anchor_y='center', batch=batch))

    return Nothing(), lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
