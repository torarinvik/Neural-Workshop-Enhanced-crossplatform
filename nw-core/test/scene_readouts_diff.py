#!/usr/bin/env python3
"""Differential harness for src/scene_readouts.elisa against the REAL widgets.

The chart is the piece worth checking. Twenty rows and three columns, all
sixty labels made up front and BLANKED when there is nothing to show -- so a
short history does not move the rows that remain, and the frame is the same
length whether the chart holds nothing or twenty sessions. The columns are
laid out as offsets from the first, which is why the third is thirty plus
seventy rather than a hundred of anything.

A blank row keeps whatever colour it was last given, and a fresh chart's rows
are pyglet's own white rather than the page's ink -- which is a thing a port
gets wrong by being sensible.

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
                                      from_right_edge, from_top_edge,
                                      scale_to_width, width_center)

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_readouts_sweep.elisa")
SOURCE = open(SWEEP).read()


def named(name):
    return scenediff.unescape(
        re.search(r'const %s: cstr = "((?:[^"\\]|\\.)*)"' % name,
                  SOURCE).group(1))


ANALYSIS = named("ANALYSIS")
CHART_TITLE = named("CHART_TITLE")
AVERAGE = named("AVERAGE")
TODAY = named("TODAY")
REMAINING = named("REMAINING")

SHADES = {0: (128, 128, 128, 255), 1: (0, 160, 0, 255), 2: (160, 0, 0, 255)}
ROWS = 20


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
    rows = spec["rows"]
    held = []

    def cells(row):
        number = 'M' if row % 5 == 4 else '#%d' % (100 + row)
        return (number, 'D%dB' % (2 + row % 3), '%d%%' % (40 + row * 3))

    def kind(row):
        if row % 5 == 4:
            return 0
        return 1 if row % 3 == 0 else (2 if row % 3 == 1 else 0)

    def lay_out():
        del held[:]
        batch = pyglet.graphics.Batch()
        held.append(batch)
        held.append(pyglet.text.Label(
            ANALYSIS, font_size=calc_fontsize(14), color=ink,
            x=width_center(), y=from_bottom_edge(92), anchor_x='center',
            anchor_y='center', batch=batch))
        held.append(pyglet.text.Label(
            CHART_TITLE, font_size=calc_fontsize(10), weight='bold',
            color=ink, x=from_right_edge(30), y=from_top_edge(85),
            anchor_x='right', anchor_y='top', batch=batch))

        start_x = from_right_edge(140)
        start_y = from_top_edge(105)
        line = calc_fontsize(15)
        twelve = calc_fontsize(30)
        offsets = (0, twelve, twelve + calc_fontsize(70))
        for column, offset in enumerate(offsets):
            for row in range(ROWS):
                text = cells(row)[column] if row < rows else ''
                shade = SHADES[kind(row)] if row < rows else (255,) * 4
                held.append(pyglet.text.Label(
                    text, font_size=calc_fontsize(10), x=start_x + offset,
                    y=start_y - row * line, anchor_x='left', anchor_y='top',
                    batch=batch, color=shade))

        held.append(pyglet.text.Label(
            AVERAGE, font_size=calc_fontsize(10), weight='normal', color=ink,
            x=from_right_edge(30), y=from_top_edge(70), anchor_x='right',
            anchor_y='top', batch=batch))
        held.append(pyglet.text.Label(
            TODAY, font_size=calc_fontsize(9), color=ink,
            x=state.window.width, y=from_top_edge(5), anchor_x='right',
            anchor_y='top', width=scale_to_width(280), multiline=True,
            batch=batch))
        held.append(pyglet.text.Label(
            REMAINING, font_size=calc_fontsize(12), weight='bold', color=ink,
            x=from_right_edge(10), y=from_top_edge(5), anchor_x='right',
            anchor_y='top', batch=batch))

    return Nothing(), lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
