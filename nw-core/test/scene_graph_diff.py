#!/usr/bin/env python3
"""Differential harness for src/scene_graph.elisa against the REAL chart.

The chart is one drawing built in one pass and its ORDER is the picture: the
two axes, the four fixed captions, then either the insufficient-data line or
the x axis drawn AS THE POINTS ARE GATHERED, the y axis, the two series, and
the legend.

The pieces the sweep is built around: fewer than two days is its own arm; past
ten days the date's hyphens become newlines so the parts stack; the label
thinning is `int(20 // xinterval)`, so how many labels appear depends on how
many days there are; and the y axis walks in quarter points from a snapped low
to a snapped high.

The chart's own statistics -- how a day's sessions fold into a score -- are
`stats`, which has a suite of its own, so the days arrive already folded.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402
from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.geometry import (calc_fontsize, from_height_center,  # noqa: E402
                                      from_left_edge, from_top_edge,
                                      scale_to_height, scale_to_width,
                                      width_center)
from neural_workshop.ui.graph import Line                           # noqa: E402

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_graph_sweep.elisa")
SOURCE = open(SWEEP).read()


def named(name):
    return scenediff.unescape(
        re.search(r'const %s: cstr = "((?:[^"\\]|\\.)*)"' % name,
                  SOURCE).group(1))


KEYS = named("KEYS")
TITLE = named("TITLE")
LEGEND = named("LEGEND")

AVERAGE = (0, 0, 255)
MAXIMUM = (255, 0, 0)


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
        axis, minor = (96, 96, 96), (64, 64, 64)
    else:
        state.cfg.COLOR_TEXT = (0, 0, 0, 255)
        axis, minor = (160, 160, 160), (224, 224, 224)
    ink = tuple(state.cfg.COLOR_TEXT)
    days = spec["days"]
    held = []

    def lay_out():
        del held[:]
        batch = pyglet.graphics.Batch()
        held.append(batch)

        def label(text, **kwargs):
            held.append(pyglet.text.Label(text, batch=batch, **kwargs))

        def line(x1, y1, x2, y2, color):
            held.append(Line(x1, y1, x2, y2, color=color, batch=batch))

        height = int(state.window.height * 0.625)
        width = int(state.window.width * 0.625)
        centre_x = width_center()
        centre_y = from_height_center(20)
        left = centre_x - width // 2
        right = centre_x + width // 2
        top = centre_y + height // 2
        bottom = centre_y - height // 2

        line(left, top, left, bottom, axis)
        line(left, bottom, right, bottom, axis)
        label(KEYS, multiline=True, width=scale_to_width(300),
              font_size=calc_fontsize(9), color=ink, x=from_left_edge(10),
              y=from_top_edge(10), anchor_x='left', anchor_y='top')
        label(TITLE, font_size=calc_fontsize(18), weight='bold', color=ink,
              x=centre_x, y=top + scale_to_height(60), anchor_x='center',
              anchor_y='center')
        label('Date', font_size=calc_fontsize(12), weight='bold', color=ink,
              x=centre_x, y=bottom - scale_to_height(80), anchor_x='center',
              anchor_y='center')
        for text, color, offset in (('Maximum', MAXIMUM + (255,), 50),
                                    ('Average', AVERAGE + (255,), 25),
                                    ('Score', ink, 0)):
            label(text, width=scale_to_width(1), font_size=calc_fontsize(12),
                  weight='bold', color=color,
                  x=left - scale_to_width(60),
                  y=centre_y + scale_to_height(offset), anchor_x='right',
                  anchor_y='center')

        if days < 2:
            label('Insufficient data: two days needed',
                  font_size=calc_fontsize(12), weight='bold',
                  color=axis + (255,), x=centre_x, y=centre_y,
                  anchor_x='center', anchor_y='center')
            return

        low = spec["low"] / 4.0
        high = spec["high"] / 4.0
        xinterval = width / float(days - 1)
        skip = int(20 // xinterval)
        avg, mx = [], []
        for index in range(days):
            x = int(xinterval * index + left)
            for series, share in ((avg, (index % 5) / 4.0),
                                  (mx, (index % 3) / 2.0)):
                value = low + (high - low) * share
                series.extend([x, int((value - low) / (high - low)
                                      * height + bottom)])
            if index % (skip + 1):
                continue
            stamp = '26-08-%02d' % (index + 1)
            if days > 10:
                stamp = stamp.replace('-', '\n')
            label(stamp, multiline=True, width=scale_to_width(12),
                  font_size=calc_fontsize(8), weight='bold', color=ink, x=x,
                  y=bottom - scale_to_height(15), anchor_x='center',
                  anchor_y='top')
            line(x, bottom, x, top, minor)
            line(x, bottom - scale_to_height(10), x, bottom, minor)

        marking = low
        while marking <= high:
            y = int((marking - low) / (high - low) * height + bottom)
            label('%.2f' % marking, font_size=calc_fontsize(10),
                  weight='normal', color=ink, x=left - scale_to_width(30),
                  y=y + scale_to_width(1), anchor_x='center',
                  anchor_y='center')
            line(left, y, right, y, minor)
            line(left - scale_to_width(10), y, left, y, minor)
            marking += 0.25

        for points, color in ((avg, AVERAGE), (mx, MAXIMUM)):
            for at in range(0, len(points) - 2, 2):
                line(points[at], points[at + 1],
                     points[at + 2], points[at + 3], color)

        label(LEGEND, font_size=calc_fontsize(11), weight='normal', color=ink,
              x=width_center(), y=scale_to_width(20), anchor_x='center',
              anchor_y='center')

    return Nothing(), lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
