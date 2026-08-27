#!/usr/bin/env python3
"""Differential harness for tasks/tracking.elisa against ui/tracking.py.

`bounced` is module-level, so it is LIFTED by AST and run as itself, with
SPAWN_APART. The scatter and the deal are methods on the pyglet-owning class
and are transcribed -- what stays the reference's own there is the stream:
`sample`, then a `uniform` pair per spawn attempt, then a `uniform` heading per
ball, in that order.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "tracking.py")

WANTED_FN = {"bounced"}
WANTED_CONST = {"SPAWN_APART"}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in WANTED_FN:
            keep.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in WANTED_CONST:
                keep.append(node)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if WANTED_CONST.intersection(names + tuples):
                keep.append(node)
    space = {"Tuple": tuple, "math": math}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = (WANTED_FN | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("tracking_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()


def scatter(ball_count, apart, low_x, high_x, low_y, high_y, rng):
    gap = apart
    while True:
        spots = []
        for _attempt in range(ball_count * 60):
            spot = (rng.uniform(low_x, high_x), rng.uniform(low_y, high_y))
            if all((spot[0] - x) ** 2 + (spot[1] - y) ** 2 >= gap * gap
                   for x, y in spots):
                spots.append(spot)
                if len(spots) == ball_count:
                    return spots
        gap *= 0.8


def deal_round(ball_count, targets, speed, apart, bounds, rng):
    low_x, high_x, low_y, high_y = bounds
    chosen = set(rng.sample(range(ball_count), targets))
    spots = scatter(ball_count, apart, low_x, high_x, low_y, high_y, rng)
    balls = []
    for index, (x, y) in enumerate(spots):
        heading = rng.uniform(0.0, 2 * math.pi)
        balls.append([x, y, speed * math.cos(heading), speed * math.sin(heading),
                      1 if index in chosen else 0])
    return balls


def advance(balls, dt, aspect, bounds):
    low_x, high_x, low_y, high_y = bounds
    for ball in balls:
        ball[0] += ball[2] * dt * aspect
        ball[1] += ball[3] * dt
        ball[0], ball[2] = REF["bounced"](ball[0], ball[2], low_x, high_x)
        ball[1], ball[3] = REF["bounced"](ball[1], ball[3], low_y, high_y)


def scaled(value):
    return int(round(value * 1000000.0))


BOUNDS = (0.06, 0.94, 0.10, 0.86)


def reference():
    out = []
    for step in range(0, 21):
        position = -0.5 + step * 0.1
        for sign in range(0, 2):
            velocity = 2.0 if sign == 0 else -2.0
            px, pv = REF["bounced"](position, velocity, 0.1, 0.9)
            out.append(["bounce", step, sign, scaled(px), scaled(pv)])
    for balls in range(4, 13):
        for seed in range(1, 4):
            rng = random.Random(balls * 100 + seed)
            flock = deal_round(balls, 3, 0.35, 0.09, BOUNDS, rng)
            row = ["deal", balls, seed, len(flock),
                   sum(1 for ball in flock if ball[4])]
            for ball in flock:
                row.extend((scaled(ball[0]), scaled(ball[1]),
                            scaled(ball[2]), scaled(ball[3]), ball[4]))
            out.append(row)
            for _tick in range(200):
                advance(flock, 0.05, 0.5625, BOUNDS)
            row = ["flown", balls, seed]
            for ball in flock:
                row.extend((scaled(ball[0]), scaled(ball[1]),
                            scaled(ball[2]), scaled(ball[3])))
            out.append(row)
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
