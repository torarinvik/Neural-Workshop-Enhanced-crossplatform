#!/usr/bin/env python3
"""Differential harness for src/scene_removals.elisa against the REAL screen.

Not a snapshot. This builds the pyglet application headless, makes a Removals
screen, puts it in a named state, asks it to redraw, and reads back the widgets
it actually built -- then compares that against the display list the Elisa
scene emits for the same state.

The state is set rather than played into, and that is the point: a scene is a
function from state to frame, and driving forty moves to reach move forty tests
the driving. Every phase, every rung and both backgrounds are reachable in one
step this way, and the states the port is asked about are the states the sweep
prints in its `spec` lines -- so neither side chooses them.

The round itself comes from the reference's own generator, which
test/removals_diff.py already checks byte-for-byte against the port's. So a
disagreement here is a disagreement about DRAWING, which is what this is for.

Run it with plain python3; it re-execs itself under the original's own
interpreter, which is the one with pyglet and a GL context. check.sh runs every
diff the same way and should not have to know which ones need a window.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
VENV = os.path.join(ORIGINAL, ".venv", "bin", "python")

# The reference has to be built in the interpreter that has pyglet, and the
# sweep binary's path has to survive the chdir below, so it is made absolute
# before anything moves.
if len(sys.argv) > 1:
    sys.argv[1] = os.path.abspath(sys.argv[1])
if not os.environ.get("NW_SCENE_REEXEC") and os.path.exists(VENV):
    os.environ["NW_SCENE_REEXEC"] = "1"
    os.execv(VENV, [VENV] + sys.argv)

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ORIGINAL, "tests"))
os.chdir(ORIGINAL)

import framerec                                                    # noqa: E402
framerec.install()

import uisupport                                                   # noqa: E402

if uisupport.UI_IMPORT_ERROR is not None:
    print("UI_IMPORT_ERROR: %s" % (uisupport.UI_IMPORT_ERROR,), file=sys.stderr)
    raise SystemExit(2)

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.removals import generate                       # noqa: E402
from neural_workshop.ui.removals import Removals                    # noqa: E402
from neural_workshop.i18n import _                                  # noqa: E402

PHASES = {0: "ready", 1: "moving", 2: "asking", 3: "scored"}


def reference(specs):
    geometry.set_window_size(912, 684)
    display.relayout()
    physical_w, physical_h = geometry._width(), geometry._height()
    framerec.set_scale(physical_w / 912.0, physical_h / 684.0)
    framerec.set_bits(True)

    out = []
    for spec in specs:
        for overlay in list(display.open_overlays()):
            overlay.close()
        state.cfg.BLACK_BACKGROUND = bool(spec["black"])
        screen = Removals()
        screen.round = generate(spec["rung"], seed=spec["seed"])
        screen.rung = spec["rung"]
        screen.trial = spec["trial"]
        screen.total_trials = spec["total_trials"]
        screen.cursor = spec["cursor"]
        screen.asking_at = spec["asking_at"]
        screen.phase = PHASES[spec["phase"]]
        if spec["phase"] == 1:
            grade = __import__("neural_workshop.removals", fromlist=["GRADES"]).GRADES
            screen.message = _('%s — %d vans, %d moves') % (
                _(grade[spec["rung"] - 1].name), screen.round.yard.vans,
                len(screen.round.moves))
        elif spec["phase"] == 2:
            screen.message = _('The doors close')

        # The chrome is rebuilt because the background flag decides its colour,
        # and it is rebuilt BEFORE the recorder is cleared so that the frame
        # comes back in the order `_build_chrome` then `_redraw` created it.
        framerec.forget()
        screen._build_chrome()
        out.append((spec, framerec.capture()))
        screen.close()
    return out


def parse(binary):
    """The sweep's output: a spec line, its frame, and `end`."""
    got = subprocess.run([binary], capture_output=True, text=True, check=True)
    specs, frames = [], []
    current = None
    for line in got.stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith("spec|"):
            cells = line.split("|")
            specs.append({
                "spec": int(cells[1]), "rung": int(cells[2]),
                "seed": int(cells[3]), "ok": int(cells[4]),
                "black": int(cells[5]), "phase": int(cells[6]),
                "cursor": int(cells[7]), "asking_at": int(cells[8]),
                "vans": int(cells[9]), "moves": int(cells[10]),
                "asked": int(cells[11]),
                "trial": 1 + int(cells[1]) % 5, "total_trials": 5,
            })
            current = []
        elif line == "end":
            frames.append(current)
            current = None
        elif current is not None:
            current.append(line)
    return specs, frames


def main():
    specs, mine = parse(sys.argv[1])
    want = reference(specs)
    bad = 0
    for spec, (_same, theirs) in zip(specs, want):
        ours = mine[specs.index(spec)]
        if ours == theirs:
            continue
        bad += 1
        print("MISMATCH spec %d (rung %d seed %d phase %d black %d)"
              % (spec["spec"], spec["rung"], spec["seed"], spec["phase"],
                 spec["black"]))
        if len(ours) != len(theirs):
            print("  command count: elisa %d, pyglet %d" % (len(ours), len(theirs)))
        for at, (a, b) in enumerate(zip(ours, theirs)):
            if a != b:
                print("  first differing command %d" % at)
                print("    elisa:  %s" % a[:170])
                print("    pyglet: %s" % b[:170])
                break
        if bad >= 3:
            break
    if bad:
        return 1
    total = sum(len(frame) for frame in mine)
    print("PASS: %d frames, %d commands identical" % (len(mine), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
