#!/usr/bin/env python3
"""Check every dealt field and the adaptive session's trial-seed stream."""
from itertools import zip_longest
from math import isclose
from pathlib import Path
import subprocess
import sys
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import rooms


def expected():
    for rung in range(-1, 33):
        for seed in range(-12, 12):
            puzzle = rooms.deal(rung, seed)
            answer = (*puzzle.answer, -1)[:2]
            yield (*map(str, (rung, seed, puzzle.rung, puzzle.cols, puzzle.rows, len(puzzle.rooms),
                              puzzle.tested, ("moved", "gone", "swapped", "recoloured").index(puzzle.change),
                              len(puzzle.answer), *answer)), puzzle.angle)
            for room in (*puzzle.rooms, puzzle.changed):
                yield tuple(map(str, (rooms.NAMES.index(room.name), rooms.TINTS.index(room.tint), len(room.things))))
                for thing in room.things:
                    yield (*map(str, (thing.cell, rooms.KINDS.index(thing.kind), rooms.COLOURS.index(thing.colour))),
                           thing.size, thing.yaw)
            polygons = rooms.scene(puzzle.cols, puzzle.rows, puzzle.changed, puzzle.angle)
            yield (str(len(polygons)), *rooms.bounds(puzzle.cols, puzzle.rows, puzzle.angle))
            for poly in polygons:
                tag = poly.tag[1] if isinstance(poly.tag, tuple) else poly.tag
                red, green, blue = poly.colour
                rgba = (red << 24) | (green << 16) | (blue << 8) | 255
                count = len(poly.points)
                x = sum(p[0] for p in poly.points) / count
                y = sum(p[1] for p in poly.points) / count
                yield (str(tag), str(rgba), str(count), *(coord for p in poly.points for coord in p),
                       str(rooms.pick(polygons, x, y)))
    rng = Random(-17)
    for event, rung in (("start", 16), ("next", 17), ("refill", 17)):
        yield (event, str(rng.randrange(1 << 30)), str(rung))


if __name__ == "__main__":
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    for row, (actual, reference) in enumerate(zip_longest(output, expected()), 1):
        assert actual is not None and reference is not None, (row, actual, reference)
        columns = actual.split()
        assert len(columns) == len(reference), (row, columns, reference)
        for field, (got, want) in enumerate(zip(columns, reference)):
            match = isclose(float(got), want, rel_tol=0, abs_tol=1e-14) if isinstance(want, float) else got == want
            assert match, (row, field, got, want)
    print("PASS: 816 Python Where Was It? deals, projected polygons and hit tests, and adaptive/think-clock session")
