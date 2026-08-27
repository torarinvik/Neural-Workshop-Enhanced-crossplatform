#!/usr/bin/env python3
"""Differential harness for src/scene_trialui.elisa against the REAL widgets.

The feedback labels are the player's controls, and their layout is the odd
thing worth checking: the width is ESTIMATED from the character count rather
than measured, because pyglet does not expose a laid-out label's width before
it is drawn, and the two denominators -- `total - 0.99` and `total - 0.5` --
are neither a rounding of the other. A single modality is the case `total - 1`
would divide by zero on, so the sweep runs one through six.

Each widget is built directly rather than through a live session: what they
say comes off `state.mode` and `check_match`, which have suites of their own,
and what is under test here is where each lands and what colour it takes.

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
                                      from_left_edge, from_right_edge,
                                      width_center)

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_trialui_sweep.elisa")
SOURCE = open(SWEEP).read()


def named(name):
    return scenediff.unescape(
        re.search(r'const %s: cstr = "((?:[^"\\]|\\.)*)"' % name,
                  SOURCE).group(1))


PROMPTS = [scenediff.unescape(one) for one in re.findall(
    r'return "((?:[^"\\]|\\.)*)"',
    SOURCE.split("def prompt_of(which: i64) -> cstr:")[1].split("\n\n")[0])]
ARITHMETIC = named("ARITHMETIC")
SESSION = named("SESSION")
THRESHOLDS = named("THRESHOLDS")
SPACE = named("SPACE")

CORRECT = (64, 255, 64, 255)
INCORRECT = (255, 64, 64, 255)
OOPS = (255, 255, 64, 255)


def feedback_size(total):
    if total < 4:
        return calc_fontsize(16)
    if total < 5:
        return calc_fontsize(14)
    if total < 6:
        return calc_fontsize(13)
    return calc_fontsize(11)


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
    # COLOR_TEXT, which `config` swaps for COLOR_TEXT_BLK on the dark page --
    # 240 grey and NOT white, which is what the port has to carry too.
    if spec["black"]:
        state.cfg.COLOR_TEXT = state.cfg.COLOR_TEXT_BLK
    else:
        state.cfg.COLOR_TEXT = (0, 0, 0, 255)
    ink = tuple(state.cfg.COLOR_TEXT)
    shades = {0: ink, 1: CORRECT, 2: OOPS, 3: INCORRECT}
    total = spec["total"]
    held = []

    def lay_out():
        # The batch is kept in `held` alongside the labels it owns. Letting it
        # go first takes the labels' vertex lists with it and the next frame
        # walks freed memory -- which shows up as a segfault several specs
        # later rather than as an error here.
        for one in held:
            try:
                one.delete()
            except Exception:
                pass
        del held[:]
        batch = pyglet.graphics.Batch()
        held.append(batch)
        for pos in range(total):
            text = PROMPTS[pos % len(PROMPTS)]
            size = feedback_size(total)
            width = (len(text) * size * 4) / 5
            spacing = (state.window.width - 100) / float(total - .99)
            x = 30 + int(pos * spacing - width * pos / (total - .5))
            held.append(pyglet.text.Label(
                text=text, x=x, y=from_bottom_edge(30), anchor_x='left',
                anchor_y='center', batch=batch, font_size=size,
                color=shades[(spec["answer"] + pos) % 4]))
        arith = spec["arith_answer"]
        held.append(pyglet.text.Label(
            ARITHMETIC, x=state.window.width / 2 - 40,
            y=from_bottom_edge(30), anchor_x='left', anchor_y='center',
            batch=batch, font_size=calc_fontsize(16), color=shades[arith],
            weight='bold' if arith in (1, 3) else 'normal'))
        held.append(pyglet.text.Label(
            SESSION, multiline=True, width=128, font_size=calc_fontsize(11),
            color=ink, x=from_left_edge(20), y=from_bottom_edge(145),
            anchor_x='left', anchor_y='top', batch=batch,
            weight='bold' if spec["bold"] else 'normal'))
        held.append(pyglet.text.Label(
            THRESHOLDS, multiline=True, width=128,
            font_size=calc_fontsize(11), color=ink, x=from_right_edge(20),
            y=from_bottom_edge(145), anchor_x='right', anchor_y='top',
            batch=batch))
        held.append(pyglet.text.Label(
            SPACE, font_size=calc_fontsize(16), weight='bold',
            color=(32, 32, 255, 255), x=width_center(),
            y=from_bottom_edge(62), anchor_x='center', anchor_y='center',
            batch=batch))

    class Nothing:
        def close(self):
            return None

    return Nothing(), lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
