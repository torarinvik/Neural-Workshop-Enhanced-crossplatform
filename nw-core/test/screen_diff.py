#!/usr/bin/env python3
"""Differential harness for src/screen.elisa against the REAL `on_draw`.

`neural_workshop.events.on_draw` is called here, not a transliteration of it,
so the branch order and every condition in it are the module's own.

What is replaced is the nine things it DRAWS. `on_draw` is the one place in the
reference that decides which surface reaches the screen, and it decides it by
calling `.draw()` -- so the observable behaviour of this function is exactly
the sequence of draw calls it makes. Each drawable becomes a recorder that
notes its layer and draws nothing, and what the two sides compare is that
sequence. Nothing in `on_draw`'s own body is touched.

Note what is NOT under test here: what any of those surfaces contains. The
batch holds the board, the HUD, the readouts and the trial UI at once, and each
of those has a suite of its own. This says which of them is submitted.

`display.ensure_laid_out` and `window.clear` are stubbed for the same reason
they are not ported: the first rebuilds widgets for a window size and the
second is a GL call, and neither puts anything in the frame.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, events, state                  # noqa: E402

LAYER_GRAPH = 1
LAYER_SACCADIC = 2
LAYER_TITLE_SPLASH = 3
LAYER_TITLE_MESSAGE = 4
LAYER_TITLE_KEYS = 5
LAYER_BATCH = 6
LAYER_BRAIN_ICON = 7
LAYER_LOGO_UPPER = 8
LAYER_LOGO_LOWER = 9
LAYER_INPUT_LABEL = 10

#: Layers drawn during the `on_draw` being recorded, in call order.
DRAWN = []


class _Drawable:
    """Stands in for one thing `on_draw` draws, and records that it did."""

    def __init__(self, layer):
        self.layer = layer

    def draw(self):
        DRAWN.append(self.layer)


class _Window:
    """The window `on_draw` clears. Clearing puts nothing in a frame."""

    def clear(self):
        pass


def install(spec):
    """Put the reference in the spec's state and give it recorders to draw."""
    mode = state.mode
    mode.draw_graph = bool(spec["draw_graph"])
    mode.saccadic = bool(spec["saccadic"])
    mode.title_screen = bool(spec["title_screen"])
    mode.started = bool(spec["started"])

    # A module-level `from .constants import CLINICAL_MODE`, so the name
    # `on_draw` reads is this one and setting it is how a clinical build is
    # tested without one.
    events.CLINICAL_MODE = bool(spec["clinical"])

    state.window = _Window()
    state.graph = _Drawable(LAYER_GRAPH)
    state.saccadic = _Drawable(LAYER_SACCADIC)
    state.brain_graphic = _Drawable(LAYER_TITLE_SPLASH)
    state.title_message_label = _Drawable(LAYER_TITLE_MESSAGE)
    state.title_keys_label = _Drawable(LAYER_TITLE_KEYS)
    state.batch = _Drawable(LAYER_BATCH)
    state.brain_icon = _Drawable(LAYER_BRAIN_ICON)
    state.logo_upper_label = _Drawable(LAYER_LOGO_UPPER)
    state.logo_lower_label = _Drawable(LAYER_LOGO_LOWER)
    state.input_labels = [_Drawable(LAYER_INPUT_LABEL)
                          for _ in range(spec["labels"])]


def frame(spec):
    """The layers the reference draws for this spec, in order, plus its own
    answer to whether the batch was among them."""
    install(spec)
    DRAWN.clear()
    events.on_draw()
    rows = [str(layer) for layer in DRAWN]
    rows.append("batch|%d" % (1 if LAYER_BATCH in DRAWN else 0))
    return rows


def main():
    specs, mine = scenediff.parse(sys.argv[1])
    # `ensure_laid_out` rebuilds every widget for the window's size. The
    # recorders have replaced the widgets it would rebuild, so it has to go --
    # and it draws nothing either way.
    display.ensure_laid_out = lambda: None

    bad = 0
    for spec, ours in zip(specs, mine):
        theirs = frame(spec)
        if ours == theirs:
            continue
        bad += 1
        if bad > 3:
            continue
        print("MISMATCH spec %s" % (
            " ".join("%s=%s" % pair for pair in sorted(spec.items())),))
        print("    elisa:  %s" % " ".join(ours))
        print("    python: %s" % " ".join(theirs))
    if bad:
        print("FAIL: %d differences" % bad)
        return 1
    print("PASS: %d frames identical" % len(mine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
