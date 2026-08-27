#!/usr/bin/env python3
"""Differential harness for src/glyphs.elisa against neural_workshop.glyphs.

`glyphs.py` imports math, os, random, struct, sys and typing -- no pyglet -- so
the reference is imported and run as itself. Nothing is lifted.

What a shell still owes the module is one function: `ui/glyphs.coverage()` asks
pyglet for a glyph bitmap. So the coverages here are BUILT, out of rectangles,
the way the reference's own tests build them (`tests/test_glyphs.py:block`).
That is not a weakening of the test -- every function below reads a Coverage as
a rectangle of bytes and none of them can tell where the bytes came from -- and
it is what keeps the suite from depending on which typefaces this machine has.

Floats cross as their IEEE bits. Nothing here is compared at a tolerance: an
`amp` that differs in the last place is a generator that drew a different
number, and rounding it away would hide exactly the bug worth finding.

The draw-count check is the last cell of every `deal` row: one more `random()`
AFTER the deal. Two implementations can agree on every knob and still have left
the generator in different places -- `_spread` returns early without drawing
when its width is zero, and the top rung has two such knobs -- and that cell is
what catches it.
"""
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

from neural_workshop import glyphs as G                            # noqa: E402

#: Letters the recogniser is given templates for, in the order it gets them.
LETTERS = "ACEGKMORTW"


def bits(value):
    """A float as the i64 its bytes spell, which is how the sweep prints one."""
    return struct.unpack("<q", struct.pack("<d", float(value)))[0]


def build_cov(spec):
    """A coverage made of rectangles. Pixels, not fonts -- and no RNG.

    Some pixels land at 90, which is below `INK`: the threshold is used by
    `bounds`, `ink`, `_mass_box` and `signature` and not by `sample`, so a
    corpus that only ever wrote 0 and 255 would let a wrong comparison through.
    """
    width = 24 + spec % 9
    height = 20 + (spec * 5) % 13
    cov = G.Coverage(width, height)
    if spec % 17 == 16:
        return cov                       # empty: the None paths
    for box in range(2 + spec % 4):
        x0 = (spec * 3 + box * 7) % (width - 4)
        y0 = (spec * 5 + box * 11) % (height - 4)
        x1 = min(width, x0 + 2 + (spec + box) % 5)
        y1 = min(height, y0 + 2 + (spec * 2 + box) % 6)
        for y in range(y0, y1):
            for x in range(x0, x1):
                cov.alpha[y * width + x] = 255 if (x + y + box) % 7 else 90
    if spec % 17 == 15:
        for index in range(len(cov.alpha)):
            cov.alpha[index] = 90        # ink-free but not empty
    return cov


def cover_rows(cov):
    """One ink count a row, so a mismatch says WHERE and not only THAT."""
    return [sum(1 for x in range(cov.width)
                if cov.alpha[y * cov.width + x] >= G.INK)
            for y in range(cov.height)]


def reference():
    out = []

    # --- the rectangle of bytes -------------------------------------------
    for spec in range(34):
        cov = build_cov(spec)
        box = cov.bounds()
        row = ["cov", spec, cov.width, cov.height, cov.ink(), cov.weight(),
               1 if box else 0]
        row.extend(box if box else (-1, -1, -1, -1))
        for step in range(9):
            x = -1.5 + step * (cov.width + 3.0) / 8.0
            y = -1.5 + step * (cov.height + 3.0) / 8.0
            row.append(cov.at(int(x), int(y)))
            row.append(cov.sample(x, y))
            row.append(cov.sample(y * 0.5, x * 0.5))
        out.append(row)

    # --- the matrix -------------------------------------------------------
    for spec in range(30):
        sx = 0.4 + (spec % 7) * 0.25
        sy = 0.4 + (spec % 5) * 0.3
        shear = -0.5 + (spec % 11) * 0.1
        turn = (-40.0 + spec * 5.0) * G.TAU / 360.0
        tilt_x = -0.35 + (spec % 9) * 0.09
        tilt_y = -0.35 + (spec % 13) * 0.06
        forward = G.homography(sx, sy, shear, turn, tilt_x, tilt_y)
        row = ["mat", spec] + [bits(one) for one in forward]
        try:
            back = G.mat_inverse(forward)
            row.append(1)
            row.extend(bits(one) for one in back)
        except ValueError:
            row.append(0)
            row.extend([0] * 9)
        product = G.mat_mul(forward, forward)
        row.extend(bits(one) for one in product)
        for step in range(5):
            u = step * 0.27
            v = 1.0 - step * 0.19
            x, y = G.mat_apply(forward, u, v)
            row.extend((bits(x), bits(y)))
        out.append(row)

    # --- one dealt appearance ---------------------------------------------
    for rung in range(0, 12):
        for seed in (0, 1, 3, 11, 97):
            rng = random.Random(seed * 31 + rung)
            dist = G.deal(rung, rng)
            grade = G.grade_of(rung)
            row = ["deal", rung, seed, grade.name, grade.waves,
                   len(dist.warp.ripple), len(dist.bars)]
            row.extend(bits(one) for one in dist.warp.inverse)
            for wave in dist.warp.ripple:
                row.extend((bits(wave.amp), bits(wave.across), bits(wave.down),
                            bits(wave.phase), wave.axis, bits(wave.slope)))
            for bar in dist.bars:
                row.extend((bits(bar.left), bits(bar.top),
                            bits(bar.width), bits(bar.height)))
            row.extend((bits(dist.thickness), bits(dist.speckle),
                        bits(dist.contrast)))
            row.extend((bits(dist.warp.slope(0)), bits(dist.warp.slope(1))))
            row.append(bits(G.fold_free(dist.warp, 8)))
            # The generator's position, which every knob above can agree on
            # and still be wrong about.
            row.append(bits(rng.random()))
            out.append(row)

    # --- wear, warp, dirt, bars -------------------------------------------
    for spec in range(40):
        rung = 1 + spec % 10
        size = 32 if spec % 4 else 24
        cov = build_cov(spec * 3 % 34)
        rng = random.Random(4000 + spec)
        dist = G.deal(rung, rng)
        worn = G.thicken(cov, dist.thickness)
        row = ["stamp", spec, rung, size, worn.ink(), worn.weight()]
        placed = G._fit(worn, 0.12)
        row.append(1 if placed else 0)
        row.extend(bits(one) for one in (placed or (0.0, 0.0, 0.0)))
        made = G.stamp(cov, dist, size, rng)
        row.extend((made.ink(), made.weight()))
        box = made.bounds()
        row.extend(box if box else (-1, -1, -1, -1))
        row.extend(cover_rows(made))
        sig = G.signature(made)
        row.extend(bits(one) for one in sig)
        row.append(bits(rng.random()))
        out.append(row)

    # --- thickening on its own, both directions ---------------------------
    for spec in range(24):
        cov = build_cov(spec)
        radius = -2.6 + spec * 0.23
        worn = G.thicken(cov, radius)
        row = ["thicken", spec, bits(radius), worn.width, worn.height,
               worn.ink(), worn.weight()]
        box = worn.bounds()
        row.extend(box if box else (-1, -1, -1, -1))
        row.extend(cover_rows(worn))
        out.append(row)

    # --- the measurement --------------------------------------------------
    templates = {}
    for index, letter in enumerate(LETTERS):
        templates[letter] = [G.signature(build_cov(index * 2 + part))
                             for part in range(2)]
    flat = [(letter, shape)
            for letter, shapes in templates.items() for shape in shapes]
    for spec in range(34):
        cov = build_cov(spec)
        sig = G.signature(cov)
        row = ["sig", spec] + [bits(one) for one in sig]
        row.append(bits(sum(sig)))
        box = G._mass_box(cov, G.TRIM)
        row.append(1 if box else 0)
        row.extend(box if box else (-1, -1, -1, -1))
        for cells in (4, 8, 12):
            other = G.signature(cov, cells)
            row.append(bits(sum(other)))
            row.append(bits(G.distance(other, other)))
        for letter, shape in flat[:4]:
            row.append(bits(G.distance(sig, shape)))
        said = G.recognise(sig, templates)
        row.append(LETTERS.index(said) if said else -1)
        out.append(row)

    return [",".join(str(one) for one in row) for row in out]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        for index, (a, b) in enumerate(zip(mine, want)):
            if a != b:
                print("  first differing line %d" % index)
                print("  elisa:  %s" % a[:200])
                print("  python: %s" % b[:200])
                break
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, python %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a[:200])
            print("  python: %s" % b[:200])
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
