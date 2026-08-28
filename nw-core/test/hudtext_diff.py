#!/usr/bin/env python3
"""Differential harness for src/hudtext.elisa against the REAL HUD widgets.

The `update()` methods in neural_workshop/ui/hud.py are called here, on the
real widget objects the application built, and what the two sides compare is
the text those methods put in their labels. Nothing restates the wording: a
port that agreed with a transliteration of the reference and disagreed with the
reference would pass such a test, and the wording is most of what is under
test.

Two of the seven are not `update()` calls, for reasons that belong to the
reference:

  * The Jaeggi warning has no update. Its text is set by `show()` and cleared
    three seconds later by a clock callback, so `show()` is what is called.
  * The three-strikes indicator is rebuilt per spec rather than updated,
    because how many circles it has is read once in its constructor -- a
    changed THRESHOLD_FALLBACK_SESSIONS does not reach an existing one.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

import bwaccel                                                      # noqa: E402
from neural_workshop import geometry, state                         # noqa: E402
from neural_workshop.ui import hud                                  # noqa: E402

BANNERS = {0: "", 1: "native: C", 2: "native: Python"}


def escape(text):
    """The sweep's own escaping, so the two sides are one line apiece."""
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def rgba(color):
    """A pyglet colour as the u32 the display list packs it into."""
    parts = tuple(color)
    if len(parts) == 3:
        parts = parts + (255,)
    red, green, blue, alpha = parts
    return (red << 24) | (green << 16) | (blue << 8) | alpha


def install(spec):
    cfg, mode = state.cfg, state.mode

    mode.started = bool(spec["started"])
    mode.hide_text = bool(spec["hide_text"])
    mode.manual = bool(spec["manual"])
    mode.paused = bool(spec["paused"])
    mode.progress = spec["progress"]
    mode.mode = spec["mode"]
    mode.back = spec["back"]
    mode.num_trials_total = spec["trials"]

    cfg.JAEGGI_MODE = bool(spec["jaeggi"])
    cfg.GRID_3D = bool(spec["grid3d"])
    cfg.VARIABLE_NBACK = bool(spec["varnback"])
    cfg.WINDOW_FULLSCREEN = bool(spec["fullscreen"])
    cfg.BLACK_BACKGROUND = bool(spec["black"])
    cfg.USE_SESSION_FEEDBACK = bool(spec["feedback"])
    cfg.THRESHOLD_FALLBACK_SESSIONS = spec["threshold"]
    # The key list asks only whether either set IS the morse set.
    cfg.AUDIO1_SETS = ["morse"] if spec["morse"] else ["letters"]
    cfg.AUDIO2_SETS = ["letters"]
    # Wide enough that the sweep's grid sizes reach grid.py unclamped; the
    # clamp itself is not what this suite is about.
    cfg.GRID_SIZE_MIN, cfg.GRID_SIZE_MAX = 2, 32
    cfg.GRID_SIZE = spec["gridsize"]
    cfg.GRID_INCLUDE_CENTER = bool(spec["include_center"])
    cfg.GRID_3D_CUBES = spec["cubes"]
    cfg.ACTIVE_POSITION_CELLS = spec["limit"]
    cfg.POSITION_CELL_COUNT = 0

    # A module-level `from ..constants import CLINICAL_MODE`, so this is the
    # name the widgets read.
    hud.CLINICAL_MODE = bool(spec["clinical"])

    state.update_available = bool(spec["update_avail"])
    state.update_version = "5.1"

    # The accelerator the runtime loaded is not something a spec can arrange,
    # and the tag is the only place its name appears.
    bwaccel.banner = lambda: BANNERS[spec["banner"]]


def frame(spec):
    install(spec)

    state.update_label.update()
    state.game_mode_label.update()
    state.jaeggi_warning_label.show()
    state.keys_list_label.update()
    state.native_backend_label.update()
    state.paused_label.update()
    state.congrats_label.update(show=bool(spec["show"]),
                                advance=bool(spec["advance"]),
                                fallback=bool(spec["fallback"]),
                                awesome=bool(spec["awesome"]),
                                great=bool(spec["great"]),
                                good=bool(spec["good"]),
                                perfect=bool(spec["perfect"]))

    rows = ["[%s]" % escape(label.label.text) for label in (
        state.update_label, state.game_mode_label, state.jaeggi_warning_label,
        state.keys_list_label, state.native_backend_label, state.paused_label,
        state.congrats_label)]

    lifted = state.keys_list_label.label.y == geometry.from_top_edge(30)
    rows.append("lifted|%d" % (1 if lifted else 0))

    circles = hud.Circles()
    cells = [str(len(circles.circle))]
    cells.extend(str(rgba(circle.color)) for circle in circles.circle)
    rows.append("circles|" + "|".join(cells))
    return rows


def main():
    specs, mine = scenediff.parse(sys.argv[1])
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
        for at, (a, b) in enumerate(zip(ours, theirs)):
            if a != b:
                print("  first differing row %d" % at)
                print("    elisa:  %s" % a)
                print("    python: %s" % b)
                break
        if len(ours) != len(theirs):
            print("  row count: elisa %d, python %d" % (len(ours), len(theirs)))
    if bad:
        print("FAIL: %d differences" % bad)
        return 1
    print("PASS: %d states identical" % len(mine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
