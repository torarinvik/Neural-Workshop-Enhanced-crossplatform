#!/usr/bin/env python3
"""Differential harness for src/textmetrics.elisa against pyglet itself.

Nothing is lifted here: the thing being checked IS the toolkit's measurement,
so the reference is a real Label at each size with its content_width and
content_height read back.

This is what six task screens are waiting on. Ten places across seven of the
reference's UI modules lay out against a measured label -- where a thing goes
depends on how big it turned out -- and a core that cannot measure text cannot
place those.

The rules only hold because FONTLIST resolves to Courier New here and Courier
New is monospace. That is the caveat in src/textmetrics.elisa, and it is why
the numbers are a supplied default rather than a fact about text.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

import pyglet                                                      # noqa: E402
import subprocess                                                  # noqa: E402
from neural_workshop.constants import FONTLIST                     # noqa: E402

CHARACTERS = (1, 2, 7, 10, 64)
LINES = (1, 2, 3, 5, 8)


def reference():
    out = []
    for tenths in range(50, 601):
        size = tenths / 10.0
        one = pyglet.text.Label('M', font_size=size, font_name=FONTLIST)
        advance = one.content_width
        tall = pyglet.text.Label('M\nM', font_size=size, font_name=FONTLIST,
                                 multiline=True, width=4000)
        line_height = tall.content_height // 2
        row = ["m", tenths, advance, line_height]
        for count in CHARACTERS:
            label = pyglet.text.Label('M' * count, font_size=size,
                                      font_name=FONTLIST)
            row.append(label.content_width)
        for count in LINES:
            label = pyglet.text.Label('\n'.join(['M'] * count), font_size=size,
                                      font_name=FONTLIST, multiline=True,
                                      width=4000)
            row.append(label.content_height)
        out.append(",".join(str(cell) for cell in row))
    return out


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True,
                         check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, pyglet %d" % (len(mine), len(want)))
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, pyglet %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a)
            print("  pyglet: %s" % b)
            return 1
    print("PASS: %d sizes identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
