#!/usr/bin/env python3
"""Differential harness for tasks/counting.elisa against ui/counting.py.

The shape generators are METHODS on a class whose constructor reaches for
pyglet, so they are transcribed here. The five constants are LIFTED by AST, so
a change to MIN_LINE_SPAN or to either shape bound is picked up rather than
quietly compared against a copy.

What stays the reference's own is the stream -- `uniform`, `randrange` and
`choice` in exactly the order the generators call them, which is the whole
content of a tangle.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "counting.py")

WANTED = {"MAX_SHAPES", "MIN_SHAPES", "MIN_LINE_SPAN", "MIXED_KINDS",
          "LINES", "CIRCLES", "TRIANGLES", "RECTANGLES", "MIXED"}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        # AnnAssign as well as Assign: MIXED_KINDS carries a Sequence[str]
        # annotation, and lifting only bare assignments silently missed it.
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in WANTED:
                keep.append(node)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if WANTED.intersection(names + tuples):
                keep.append(node)
    space = {"Sequence": list}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = WANTED - set(space)
    if missing:
        raise SystemExit("counting_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
KIND_INDEX = {REF["LINES"]: 0, REF["CIRCLES"]: 1, REF["TRIANGLES"]: 2,
              REF["RECTANGLES"]: 3, REF["MIXED"]: 4}
BY_INDEX = [REF["LINES"], REF["CIRCLES"], REF["TRIANGLES"], REF["RECTANGLES"],
            REF["MIXED"]]


def perimeter(side, along):
    return ((along, 0.0), (1.0, along), (along, 1.0), (0.0, along))[side]


def random_line(rng):
    for _attempt in range(20):
        first = rng.randrange(4)
        second = (first + 1 + rng.randrange(3)) % 4
        start = perimeter(first, rng.uniform(0.0, 1.0))
        end = perimeter(second, rng.uniform(0.0, 1.0))
        head = rng.uniform(0.02, 0.16)
        tail = 1.0 - rng.uniform(0.02, 0.16)
        span = (end[0] - start[0], end[1] - start[1])
        points = ((start[0] + span[0] * head, start[1] + span[1] * head),
                  (start[0] + span[0] * tail, start[1] + span[1] * tail))
        if math.dist(points[0], points[1]) >= REF["MIN_LINE_SPAN"]:
            return (0, points, 0.0)
    return (0, ((0.05, 0.5), (0.95, 0.5)), 0.0)


def random_circle(rng):
    radius = rng.uniform(0.06, 0.18)
    return (1, ((rng.uniform(radius, 1 - radius),
                 rng.uniform(radius, 1 - radius)),), radius)


def random_triangle(rng):
    size = rng.uniform(0.07, 0.17)
    centre = (rng.uniform(size, 1 - size), rng.uniform(size, 1 - size))
    turn = rng.uniform(0, math.tau)
    points = tuple((centre[0] + size * math.cos(turn + i * math.tau / 3),
                    centre[1] + size * math.sin(turn + i * math.tau / 3))
                   for i in range(3))
    return (2, points, 0.0)


def random_rectangle(rng):
    width = rng.uniform(0.08, 0.26)
    height = rng.uniform(0.08, 0.26)
    left = rng.uniform(0, 1 - width)
    bottom = rng.uniform(0, 1 - height)
    return (3, ((left, bottom), (left + width, bottom + height)), 0.0)


def random_shape(index, rng):
    return (random_circle(rng) if index == 1 else
            random_triangle(rng) if index == 2 else
            random_rectangle(rng) if index == 3 else
            random_line(rng))


def generate(kind_index, count, rng):
    out = []
    for _index in range(count):
        drawn = (KIND_INDEX[rng.choice(REF["MIXED_KINDS"])]
                 if kind_index == 4 else kind_index)
        out.append(random_shape(drawn, rng))
    return out


def clamp_shapes(count):
    return max(REF["MIN_SHAPES"], min(REF["MAX_SHAPES"], count))


def scaled(value):
    return int(round(value * 1000000.0))


def shape_cells(shape):
    kind, points, radius = shape
    row = [kind, len(points), scaled(radius)]
    for px, py in points:
        row.extend((scaled(px), scaled(py)))
    return row


def reference():
    out = []
    for count in range(0, 70):
        out.append(["clamp", count, clamp_shapes(count)])
    for kind in range(0, 5):
        for seed in range(1, 5):
            rng = random.Random(kind * 1000 + seed)
            shapes = generate(kind, 12, rng)
            row = ["gen", kind, seed, len(shapes)]
            for shape in shapes:
                row.extend(shape_cells(shape))
            out.append(row)
    for seed in range(1, 4):
        rng = random.Random(7000 + seed)
        shapes = generate(4, REF["MAX_SHAPES"], rng)
        row = ["long", seed, len(shapes)]
        for shape in shapes:
            row.extend(shape_cells(shape))
        out.append(row)
    for side in range(0, 4):
        for step in range(0, 5):
            px, py = perimeter(side, step * 0.25)
            out.append(["edge", side, step, scaled(px), scaled(py)])
    return [",".join(str(one) for one in row) for row in out]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, python %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a[:140])
            print("  python: %s" % b[:140])
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
