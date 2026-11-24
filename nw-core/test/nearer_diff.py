#!/usr/bin/env python3
"""Compare the seeded Which Is Nearer? deals with the Python reference."""
from itertools import product, zip_longest
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import nearer


def expected():
    cases = [*product(range(-1, 34), range(-16, 16)), (20, -(1 << 63)), (20, (1 << 63) - 1)]
    for rung, seed in cases:
        puzzle = nearer.deal(rung, seed)
        level = nearer.grade(rung)
        cue = ("size", "floor", "shadow", "hiding", "motion").index(level.cue)
        yield (*map(str, (rung, seed, level.rung, len(puzzle.solids), cue, int(level.order))), level.ratio,
               nearer.camera(level.cue, 0.6).eye[0], nearer.camera(level.cue, 0.9).eye[0])
        for solid, order in zip(puzzle.solids, puzzle.order):
            yield (*map(str, (nearer.KINDS.index(solid.kind), nearer.COLOURS.index(solid.colour), order)),
                   *solid.centre, solid.size, solid.yaw)
        painted = nearer.scene(puzzle, 0.9)
        boxes = nearer.boxes(painted)
        yield (str(len(painted)), str(len(boxes)))
        for shape in painted:
            port = shape.tag if shape.tag is not None else -1
            red, green, blue = shape.colour
            colour = (red << 24) | (green << 16) | (blue << 8) | 255
            yield (*map(str, (port, colour, len(shape.points))), *(coord for point in shape.points for coord in point))
        for port, bounds in boxes:
            left, bottom, right, top = bounds
            x, y = (left + right) / 2, (bottom + top) / 2
            hit = next(tag for tag, (l, b, r, t) in boxes if l <= x <= r and b <= y <= t)
            yield (str(port), *bounds, str(hit))
    rng = Random(17)
    yield ("start", str(rng.randrange(1 << 30)), "20")
    yield ("next", str(rng.randrange(1 << 30)), "21")


if __name__ == "__main__":
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    for row, (actual, reference) in enumerate(zip_longest(output, expected()), 1):
        assert actual is not None and reference is not None, (row, actual, reference)
        columns = actual.split()
        assert len(columns) == len(reference), (row, columns, reference)
        for field, (got, want) in enumerate(zip(columns, reference)):
            match = isclose(float(got), want, rel_tol=1e-14, abs_tol=1e-15) if isinstance(want, float) else got == want
            assert match, (row, field, got, want)
    print("PASS: 1122 Python Which Is Nearer? deals, signed seed limits, solid order, clipped scenes, hit boxes, eye sway, and ordered scoring")
