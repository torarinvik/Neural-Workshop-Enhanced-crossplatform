#!/usr/bin/env python3
"""Replay seeded Same or Mirror? figures and their view matrices."""
from itertools import product, zip_longest
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import mirror, space


def figure(shape, lit):
    for cube in shape.cubes:
        yield tuple(map(str, cube))
    yield tuple(value for row in shape.turn for value in row)

    colour = (214, 176, 112) if lit else (226, 214, 190)
    face_list = space.render(mirror.faces(shape, lit, colour), mirror.camera())
    yield (str(len(face_list)), space.radius(shape.cubes))
    for polygon in face_list:
        r, g, b = polygon.colour
        yield (str((r << 24) | (g << 16) | (b << 8) | 255), polygon.depth,
               *(value for point in polygon.points for value in point))


def expected():
    cases = [*product(range(-1, 34), range(-8, 8)), (26, -(1 << 63)), (26, (1 << 63) - 1)]
    for rung, seed in cases:
        puzzle = mirror.deal(rung, seed)
        level = mirror.grade(rung)
        assert mirror.truth(puzzle)
        yield tuple(map(str, (rung, seed, level.rung, level.cubes, level.options,
                             level.nudged, int(level.lit), len(puzzle.others), puzzle.answer)))
        yield from figure(puzzle.reference, puzzle.lit)
        for shape, angle in zip(puzzle.others, puzzle.angles):
            yield (angle,)
            yield from figure(shape, puzzle.lit)
    rng = Random(17)
    for event, rung in (("start", 12), ("next", 13), ("refill", 13)):
        yield (event, str(rng.randrange(1 << 30)), str(rung))


if __name__ == "__main__":
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    for row, (actual, reference) in enumerate(zip_longest(output, expected()), 1):
        assert actual is not None and reference is not None, (row, actual, reference)
        columns = actual.split()
        assert len(columns) == len(reference), (row, columns, reference)
        for field, (got, want) in enumerate(zip(columns, reference)):
            match = isclose(float(got), want, rel_tol=1e-13, abs_tol=1e-12) if isinstance(want, float) else got == want
            assert match, (row, field, got, want)
    print("PASS: 562 Python Same or Mirror? deals, chiral figures, distractors, seeded turns, projected faces, answer order, and think-clock lifecycle")
