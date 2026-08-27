#!/usr/bin/env python3
"""Differential harness for src/scene_notice.elisa against the REAL screens.

Three screens that are one shape apiece: the modal notice, the saccadic
square, and the one-line prompt.

The prompt is the interesting one. It is drawn at FIXED PIXEL sizes and
coordinates -- font 10 and 12, a box 400 by 28, x at 250 -- and nothing about
it scales with the window, which is why it looks wrong on a large one. That is
reproduced rather than corrected. Its caret is a SPACE while the blink is off
rather than nothing at all, so the line does not shorten and the text does not
slide under the cursor.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.effects import Saccadic                     # noqa: E402
from neural_workshop.ui.message import Message                      # noqa: E402
from neural_workshop.ui.textinput import TextInputScreen            # noqa: E402

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_notice_sweep.elisa")
SOURCE = open(SWEEP).read()


def named(name):
    return re.search(r'const %s: cstr = "((?:[^"\\]|\\.)*)"'
                     % name, SOURCE).group(1)


NOTICE = named("NOTICE")
TITLE = named("TITLE")
TYPED = named("TYPED")


class Nothing:
    """A screen with no drawing of its own, for the frames that need none."""

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
    which = spec["which"]
    if which == 0:
        screen = Message(NOTICE)

        def lay_out():
            screen.build_chrome()
        return screen, lay_out
    # The other two screens draw IMMEDIATELY: they construct a shape, call
    # `.draw()` on it and drop it on the same line. The recorder holds a weak
    # reference, so by the time the frame is captured the shape is already
    # collected and nothing was seen. So those two are built here instead --
    # the same constructor calls with the same numbers, kept alive long enough
    # to be read back.
    import pyglet
    from neural_workshop.geometry import height_center, scale_to_height
    held = []
    if which == 1:
        eyes = Saccadic()
        eyes.position = 'left' if spec["left"] else 'right'

        def lay_out():
            del held[:]
            radius = eyes.radius
            y = height_center()
            x = radius if eyes.position == 'left' else state.window.width - radius
            held.append(pyglet.shapes.Rectangle(
                x - radius, y - radius, radius * 2, radius * 2,
                color=eyes.color))
        return Nothing(), lay_out

    prompt = TextInputScreen(title=TITLE)
    prompt.input_text = list(TYPED)
    prompt.cursor_pos = min(spec["cursor_at"], len(TYPED))
    prompt.cursor_visible = bool(spec["cursor_visible"])

    def lay_out():
        del held[:]
        prompt.build_chrome()
        width, height = prompt.BOX_SIZE
        held.append(pyglet.shapes.Rectangle(
            prompt.x_input, prompt.y_input, width, height,
            color=(200, 200, 200)))
        cursor = '_' if prompt.cursor_visible else ' '
        shown = (''.join(prompt.input_text[:prompt.cursor_pos]) + cursor
                 + ''.join(prompt.input_text[prompt.cursor_pos:]))
        held.append(pyglet.text.Label(
            shown, font_size=12, x=prompt.x_input + 4,
            y=prompt.y_input + 14, anchor_y='center'))
    return prompt, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
