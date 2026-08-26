#!/usr/bin/env python3
"""Differential harness: tasks/fogworld.elisa vs the real
neural_workshop/fogworld.py.

The reference imports cleanly and takes its randomness as an argument, so this
drives the ACTUAL module: every row below comes out of `fogworld.carve`,
`fogworld.visible`, `fogworld.generate` and `fogworld.coverage`, seeded the
same way the Elisa side seeds MT19937.

Two things are checked at once. The obvious one is the algorithm. The subtle
one is the ORDER the random stream is consumed in -- and underneath that,
CPython's set iteration order, which `braid` walks and which the port
reimplements slot for slot in maze.elisa. fogworld is where that shows up
hardest, because it braids at 0.85: almost every dead end is opened, so almost
every set-order decision is taken, and one wrong slot changes the whole world.

The rectangle is the other trap. `carve` draws `randrange(rooms_x)` before
`randrange(rooms_y)`, and on a non-square lattice those bounds differ, so
swapping them consumes a different number of bits and desynchronises
everything after. A square-only test would never catch it, which is why every
grid below is deliberately non-square.
"""
import random
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/"
       "Neural-Workshop-Enhanced-crossplatform/original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import fogworld as ref  # noqa: E402
from neural_workshop import maze as refmaze  # noqa: E402

# Keyed by hundredths so both sides name the same float literal rather than
# parsing one.
OPENNESS = {0: 0.0, 25: 0.25, 50: 0.5, 85: 0.85, 100: 1.0}


def row(*values):
    return ",".join(str(v) for v in values)


def carve_lines(out):
    for rx in (2, 3, 5, 8, 12):
        for ry in (2, 3, 7):
            for seed in (0, 1, 7, 12345):
                rng = random.Random(seed)
                width, height, open_set = ref.carve(rx, ry, rng)
                cells = sorted(open_set)
                out.append(row("carve", rx, ry, seed, len(cells), *cells))


def visible_lines(out):
    for width in (5, 11, 25):
        for height in (5, 15):
            for at in (0, 1, 7, 12, 37, 60, 124, -1, 9999):
                for radius in (0, 1, 2, 3, -1):
                    world = ref.World(width=width, height=height,
                                      walls=frozenset(), start=0)
                    seen = sorted(ref.visible(world, at, radius))
                    out.append(row("vis", width, height, at, radius,
                                   len(seen), *seen))


def generate_lines(out):
    for rx in (3, 5, 12):
        for ry in (2, 7):
            for hundredths in (0, 25, 50, 85):
                for seed in (0, 1, 7, 12345, 99991):
                    world = ref.generate(seed=seed, rooms_x=rx, rooms_y=ry,
                                         openness=OPENNESS[hundredths])
                    floor = sorted(world.open_cells())
                    out.append(row("gen", rx, ry, hundredths, seed,
                                   world.width, world.height, world.start,
                                   len(floor), *floor))


def coverage_lines(out):
    for rx in (3, 5):
        for ry in (2, 7):
            for seed in (1, 7, 12345):
                world = ref.generate(seed=seed, rooms_x=rx, rooms_y=ry,
                                     openness=ref.OPENNESS)
                for radius in (0, 1, 2, 4):
                    seen = ref.visible(world, world.start, radius)
                    share = ref.coverage(world, seen)
                    # parts-per-million, so the comparison is on integers and
                    # no float formatting has to agree across languages.
                    ppm = round(share * 1000000.0)
                    out.append(row("cov", rx, ry, seed, radius,
                                   len(seen), ppm))


def python_lines():
    out = []
    carve_lines(out)
    visible_lines(out)
    generate_lines(out)
    coverage_lines(out)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g[:180]}\n  python: {w[:180]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
