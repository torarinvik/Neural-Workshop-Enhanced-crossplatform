#!/usr/bin/env python3
"""Compare Point of View seeded scenes and distractor camera order."""
from itertools import product, zip_longest
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import nearer, pov


def polygon(tag, colour, points):
    red, green, blue = colour
    rgba = (red << 24) | (green << 16) | (blue << 8) | 255
    return (*map(str, (tag, rgba, len(points))), *(coord for point in points for coord in point))


def expected():
    cases = [*product(range(-1, 32), range(-10, 10)), (25, -(1 << 63)), (25, (1 << 63) - 1)]
    for rung, seed in cases:
        puzzle = pov.deal(rung, seed)
        yield (*map(str, (rung, seed, puzzle.rung, len(puzzle.solids), len(puzzle.views), puzzle.answer)),
               puzzle.angle, puzzle.eye)
        for solid in puzzle.solids:
            colour = nearer.COLOURS.index(solid.colour) if solid.colour in nearer.COLOURS else -1
            yield (*map(str, (nearer.KINDS.index(solid.kind), colour)), *solid.centre, solid.size, solid.yaw)
            yield polygon(-1, solid.colour, pov.footprint(solid))
        signatures = set()
        for angle, eye, mirrored in puzzle.views:
            key = 0
            for port in pov.order(puzzle.solids, angle, eye, mirrored):
                key = key * 6 + port
            assert key not in signatures
            signatures.add(key)
            yield (str(int(mirrored)), angle, eye, str(key))
            painted = pov.picture(puzzle, (angle, eye, mirrored))
            yield (str(len(painted)),)
            for shape in painted:
                yield polygon(-1 if shape.tag is None else shape.tag, shape.colour, shape.points)
    rng = Random(17)
    for event, rung in (("start", 20), ("next", 21), ("refill", 21)):
        yield (event, str(rng.randrange(1 << 30)), str(rung))


if __name__ == "__main__":
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    for row, (actual, reference) in enumerate(zip_longest(output, expected()), 1):
        assert actual is not None and reference is not None, (row, actual, reference)
        columns = actual.split()
        assert len(columns) == len(reference), (row, columns, reference)
        for field, (got, want) in enumerate(zip(columns, reference)):
            match = isclose(float(got), want, rel_tol=1e-14, abs_tol=1e-15) if isinstance(want, float) else got == want
            assert match, (row, field, got, want)
    print("PASS: 662 Python Point of View deals, signed seed limits, solids, camera views, unique distractors, projected faces, and the think-clock lifecycle")
