#!/usr/bin/env python3
"""Differential harness for src/scene_taskhub.elisa against the REAL screen.

The tabs and the cards both shrink their text to fit and they do it
DIFFERENTLY: a tab's size is chosen once from the longest category name and
every tab drawn at it, so the row reads as a row; a card's is chosen per card
from its own name. Both walk down a whole point at a time, which is why each
is a loop rather than one division.

The port carries the category and task tables itself, so this suite is also
what says they agree with the reference's -- a renamed task or a reordered
category fails it.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.taskhub import CATEGORIES, TaskHub          # noqa: E402


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
    screen = TaskHub(category=CATEGORIES[spec["category"]][0])
    screen.category = CATEGORIES[spec["category"]][0]
    screen.selected = spec["selected"]
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
