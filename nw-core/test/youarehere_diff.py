#!/usr/bin/env python3
"""Differential harness for tasks/youarehere.elisa against neural_workshop.youarehere.

The maze itself is the 2D ladder's, already covered by maze_diff, so what this
checks is everything the 3D task adds: the starting facing, the breadth-first
par over pose AND keys, the route it unwinds, the wall-hugging walk, the
slipping walk's draw order, and the view -- rays and motes both.

Floats are compared as scaled integers, so no printed decimal ever has to agree
between two languages. The scaling is round-half-even at 1e6, which is what
`py_round_half_even` is.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

import random                                     # noqa: E402
from neural_workshop import maze as mazemod       # noqa: E402
from neural_workshop import youarehere as yah     # noqa: E402

MOVES = {"ahead": 0, "back": 1, "left": 2, "right": 3}


def scaled(value):
    # Python's round() is round-half-even, which is what the port emits.
    return int(round(value * 1000000.0))


def reference():
    out = []
    for level in range(1, 16):
        for seed in range(1, 4):
            # One attempt, and the reference RAISES when none survives where
            # the port returns a Layout with ok=false. Skipping here is the
            # same skip the sweep makes on `not maze.ok`.
            try:
                maze = mazemod.generate(level, seed=seed, attempts=1)
            except ValueError:
                continue
            facing = yah.facing_at(maze)
            steps, route = yah._sweep(maze)
            row = ["par", level, seed, maze.width, facing, steps, len(route)]
            row.extend(MOVES[one] for one in route)
            out.append(row)

            out.append(["route", level, seed, len(route),
                        *(MOVES[one] for one in route)])
            out.append(["perfect", level, seed, yah.walk_perfect(maze)])

            pose = yah.Pose(maze.start, (facing + 2) % 4)
            held = yah.picked_up(maze, maze.start, 0)
            believed = yah.route_from(maze, pose, held)
            row = ["from", level, seed, len(believed)]
            row.extend(MOVES[one] for one in believed)
            out.append(row)

            out.append(["hug", level, seed, yah.walk_hugging(maze, cap=20000)])

            # Low rungs only, and a short cap -- see the sweep: this walk
            # re-plans a full breadth-first sweep after every step, and one
            # level-fifteen walk costs twenty-five seconds against about one
            # for the whole rest of the suite.
            if level <= 7:
                for rate, slip in enumerate((0.02, 0.1, 0.25)):
                    rng = random.Random(seed * 1000 + rate)
                    out.append(["slip", level, seed, rate,
                                yah.walk_slipping(maze, slip, rng, cap=1500)])

            for turn in range(4):
                pose = yah.Pose(maze.start, (facing + turn) % 4)
                seen = yah.look(maze, pose, columns=yah.COLUMNS, fov=yah.FOV)
                row = ["see", level, seed, turn]
                for one in seen:
                    row.extend((scaled(one.distance), one.cell, one.side))
                out.append(row)

                held = yah.picked_up(maze, maze.start, 0)
                marks = yah.motes(maze, pose, held, fov=yah.FOV)
                row = ["mote", level, seed, turn, len(marks)]
                for one in marks:
                    row.extend((0 if one.what == "key" else 1, one.which,
                                one.cell, scaled(one.across),
                                scaled(one.distance)))
                out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
    binary = sys.argv[1]
    got = subprocess.run([binary], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        for index in range(min(len(mine), len(want))):
            if mine[index] != want[index]:
                print("  first differing line %d" % index)
                print("  elisa:  %s" % mine[index][:120])
                print("  python: %s" % want[index][:120])
                break
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a == b:
            continue
        print("MISMATCH line %d" % index)
        acells, bcells = a.split(","), b.split(",")
        for at, (x, y) in enumerate(zip(acells, bcells)):
            if x != y:
                print("  first differing cell %d: elisa %s, python %s" % (at, x, y))
                break
        print("  elisa:  %s" % a[:150])
        print("  python: %s" % b[:150])
        return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
