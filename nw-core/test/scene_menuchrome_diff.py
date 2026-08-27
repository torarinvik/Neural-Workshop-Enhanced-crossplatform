#!/usr/bin/env python3
"""Differential harness for scene_menu.elisa's two extra captions.

`GameSelect` and `TaskOptions` each add one label to the menu chrome, and
neither can be instantiated for a frame: GameSelect resolves a mode out of
the live config and TaskOptions needs an option spec and a callback. The two
constructor calls are therefore rebuilt here -- but the numbers they are given
come off the reference's own `calc_fontsize`, `width_center` and
`from_bottom_edge`, and off `Menu`'s own `textcolor` rule, so what is restated
is the pyglet call and never the arithmetic.

The mode caption's FLAT BLACK is the point of the first half: it is not the
menu's ink, so on the dark page it is invisible. Both sides say so.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

import pyglet                                                       # noqa: E402

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.geometry import (calc_fontsize,                # noqa: E402
                                      from_bottom_edge, width_center)

MODES = ["Dual N-Back", "3D Position V. N-Back",
         "An invalid mode has been selected.", "Quad Combination N-Back"]
NOTES = ["Three modalities on a 4x4 board.",
         "Nothing is selected, so nothing will be played; pick at least one "
         "modality before you start.",
         "Variable N-Back draws a fresh level each trial."]

KEEP = []


class _Nothing:
    def close(self):
        pass


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

    del KEEP[:]

    def lay_out():
        batch = pyglet.graphics.Batch()
        KEEP.append(batch)
        # Menu.build_chrome's own rule, restated because Menu is not built.
        textcolor = (255 * int(state.cfg.BLACK_BACKGROUND),) * 3 + (255,)
        if spec["which"] != 1:
            # GameSelect._build_modelabel
            KEEP.append(pyglet.text.Label(
                MODES[spec["text"]], font_size=calc_fontsize(18),
                weight='normal', color=(0, 0, 0, 255), batch=batch,
                x=width_center(), y=(state.window.height * 1) / 10,
                anchor_x='center', anchor_y='center'))
        if spec["which"] != 0:
            # TaskOptions.build_chrome
            KEEP.append(pyglet.text.Label(
                NOTES[spec["text"] % 3], font_size=calc_fontsize(11),
                color=textcolor, batch=batch, x=width_center(),
                y=from_bottom_edge(92),
                width=int(state.window.width * 0.74), multiline=True,
                align='center', anchor_x='center', anchor_y='center'))

    return _Nothing(), lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
