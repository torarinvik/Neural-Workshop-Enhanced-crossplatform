#!/usr/bin/env python3
"""Differential harness for src/scene_numberology.elisa against the REAL screen.

Two window heights per run, because the typed line's y is a MAX -- a short
window pushes it UP off the verdict band rather than letting it slide down --
and one height only ever exercises one arm of that.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.numberology import Numberology              # noqa: E402

PHASES = {0: "ready", 1: "working", 2: "judged", 3: "done"}


class Sequence:
    """Only what `_redraw` reads off a SequencePuzzle."""

    asked = '2, 4, 8, 16, ?'
    rule = 'each term doubles'


def build(spec):
    import framerec
    # The sweep names the window height, so the reference is laid out at that
    # height too. Check it landed there: geometry clamps a request below
    # MIN_WINDOW_HEIGHT points, and a window manager may hand back something
    # smaller still -- either way the reference would be drawing at a height
    # the sweep never named, and every y would differ for a reason that has
    # nothing to do with the port.
    geometry.set_window_size(912, spec["tall"] // 2)
    display.relayout()
    if (geometry._width(), geometry._height()) != (1824, spec["tall"]):
        raise SystemExit("asked for 1824x%d pixels, got %dx%d"
                         % (spec["tall"], geometry._width(), geometry._height()))
    framerec.set_scale(geometry._width() / 912.0,
                       geometry._height() / (spec["tall"] / 2.0))
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = Numberology()
    screen.puzzle = Sequence() if spec["has_puzzle"] else None
    screen.typed = '32'
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Difficulty 3'
    # `verdict_shown` and not `verdict.show(...)`: _build_chrome makes a fresh
    # VerdictLabel every relayout and replays this, so setting the widget would
    # be undone by the very call the harness is about to make.
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
