# -*- coding: utf-8 -*-
"""The scaffolding every scene differential shares.

A scene diff is one function: given a spec the sweep printed, build the real
pyglet screen in that state and let it draw. Everything around that -- finding
the interpreter with a GL context, building the application, keeping the
recorder in step, parsing the sweep, reporting the first command that differs
-- is the same for all forty-three, so it is here and not copied.

Use it like this:

    import scenediff

    def build(spec):
        screen = Removals()
        ...                       # put it in the spec's state
        return screen, screen._build_chrome

    if __name__ == "__main__":
        raise SystemExit(scenediff.main(build))

`build` returns the screen and the call that lays it out. The recorder is
cleared between the two, so the frame comes back in the order the screen
created it and nothing from the previous spec is left in it.

SPDX-License-Identifier: GPL-2.0-or-later
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
VENV = os.path.join(ORIGINAL, ".venv", "bin", "python")


def reexec():
    """Come back under the interpreter that has pyglet and a GL context.

    check.sh runs every diff with plain python3 and should not have to know
    which ones need a window. The sweep binary's path is made absolute first,
    because the reference has to be built with its own directory as the cwd.
    """
    if len(sys.argv) > 1:
        sys.argv[1] = os.path.abspath(sys.argv[1])
    if not os.environ.get("NW_SCENE_REEXEC") and os.path.exists(VENV):
        os.environ["NW_SCENE_REEXEC"] = "1"
        os.execv(VENV, [VENV] + sys.argv)
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(ORIGINAL, "tests"))
    os.chdir(ORIGINAL)

    # The recorder has to be in place before the application is built, and
    # uisupport builds it on import -- widgets are made once and then mutated,
    # so a recorder that arrives afterwards sees an empty frame. Building here
    # rather than in main() is also what puts `neural_workshop` on the path, so
    # a scene diff can import the screen it is about at module level.
    import framerec
    framerec.install()

    import uisupport
    if uisupport.UI_IMPORT_ERROR is not None:
        print("UI_IMPORT_ERROR: %s" % (uisupport.UI_IMPORT_ERROR,))
        raise SystemExit(2)


def parse(binary):
    """The sweep's output: a `spec|` line, its frame, and `end`.

    A spec's cells are named by the sweep's own first line, so a scene that
    needs another knob adds it in one place.
    """
    got = subprocess.run([binary], capture_output=True, text=True, check=True)
    names, specs, frames = None, [], []
    current = None
    for line in got.stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith("names|"):
            names = line.split("|")[1:]
        elif line.startswith("spec|"):
            cells = line.split("|")[1:]
            if names is None:
                raise SystemExit("sweep printed no `names|` line")
            specs.append(dict(zip(names, (int(one) for one in cells))))
            current = []
        elif line == "end":
            frames.append(current)
            current = None
        elif current is not None:
            current.append(line)
    if len(specs) != len(frames):
        raise SystemExit("sweep printed %d specs and %d frames"
                         % (len(specs), len(frames)))
    if not specs:
        # A sweep that printed nothing used to come back as "PASS: 0 frames",
        # which is what a suite says when its binary is stale or was never
        # built. Nothing checked is not the same as nothing wrong.
        raise SystemExit("sweep printed no specs at all")
    return specs, frames


def settle_positions(frame):
    """Sort each run of commands that differ only in WHERE they are.

    Some scenes draw a set of identical marks -- Go rings its target group with
    one circle a point -- and the reference gets that set out of a frozenset,
    so the order it draws them in is CPython's hash order. Reproducing that
    would mean reproducing setobject.c's probe schedule to decide which of
    several IDENTICAL circles goes down first.

    The rule applied instead is narrow and can be stated: adjacent commands
    that agree on everything except their first two numbers are the same mark
    in different places, and the order of those is unobservable UNLESS THEY
    OVERLAP. Equal-radius circles on distinct board points do not. A scene
    where they could overlap must not opt in to this, which is why it is
    opt-in and not the default.
    """
    out = []
    run = []
    shape = None
    for line in frame:
        cells = line.split("|")
        here = tuple(cells[:1] + cells[3:])
        if here == shape:
            run.append(line)
            continue
        out.extend(sorted(run))
        run = [line]
        shape = here
    out.extend(sorted(run))
    return out


def main(build, width=912, height=684, settle=None):
    reexec()

    import framerec
    from neural_workshop import display, geometry

    specs, mine = parse(sys.argv[1])

    geometry.set_window_size(width, height)
    display.relayout()
    framerec.set_scale(geometry._width() / float(width),
                       geometry._height() / float(height))
    framerec.set_bits(True)

    bad = 0
    for spec, ours in zip(specs, mine):
        for overlay in list(display.open_overlays()):
            overlay.close()
        screen, lay_out = build(spec)
        framerec.forget()
        lay_out()
        theirs = framerec.capture()
        try:
            screen.close()
        except Exception:                                  # noqa: BLE001
            pass
        if settle is not None:
            ours, theirs = settle(ours), settle(theirs)
        if ours == theirs:
            continue
        bad += 1
        if bad > 3:
            continue
        print("MISMATCH spec %s" % (
            " ".join("%s=%s" % pair for pair in sorted(spec.items())),))
        if len(ours) != len(theirs):
            print("  command count: elisa %d, pyglet %d"
                  % (len(ours), len(theirs)))
        for at, (a, b) in enumerate(zip(ours, theirs)):
            if a != b:
                print("  first differing command %d" % at)
                print("    elisa:  %s" % a[:170])
                print("    pyglet: %s" % b[:170])
                break
    if bad:
        print("FAIL: %d of %d frames differ" % (bad, len(mine)))
        return 1
    print("PASS: %d frames, %d commands identical"
          % (len(mine), sum(len(frame) for frame in mine)))
    return 0
