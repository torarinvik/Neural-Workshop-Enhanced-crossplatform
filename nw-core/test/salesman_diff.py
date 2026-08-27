#!/usr/bin/env python3
"""Differential harness for tasks/salesman.elisa against ui/salesman.py.

`tour_length`, `optimal_tour` and `scatter` are module-level functions, so they
are LIFTED out of the reference by AST and run as themselves -- importing the
module would drag in pyglet. The five constants come with them, so a change to
SPREAD or to either ladder threshold is picked up here.

Only the ladder is transcribed, and only because it lives on the class.
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "salesman.py")

WANTED_FN = {"tour_length", "optimal_tour", "scatter"}
WANTED_CONST = {"FEWEST_CITIES", "MOST_CITIES", "GROW_AT", "SHRINK_AT",
                "SPREAD"}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in WANTED_FN:
            keep.append(node)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if WANTED_CONST.intersection(names + tuples):
                keep.append(node)
    import math
    import random
    space = {"math": math, "random": random, "Sequence": list, "List": list,
             "Tuple": tuple, "Dict": dict, "Point": tuple, "Optional": object}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = (WANTED_FN | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("salesman_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
import random  # noqa: E402


def clamped(count):
    return max(REF["FEWEST_CITIES"], min(REF["MOST_CITIES"], count))


def next_count(count, close):
    if close >= REF["GROW_AT"]:
        return clamped(count + 1)
    if close < REF["SHRINK_AT"]:
        return clamped(count - 1)
    return clamped(count)


def closeness(optimal, walked):
    return 0.0 if walked <= 0 else optimal / walked


def scaled(value):
    return int(round(value * 1000000.0))


def reference():
    out = []
    for count in range(0, 22):
        out.append(["clamp", count, clamped(count)])
    for count in range(5, 13):
        for seed in range(1, 4):
            rng = random.Random(count * 100 + seed)
            cities = REF["scatter"](count, rng)
            row = ["scatter", count, seed, len(cities)]
            for cx, cy in cities:
                row.extend((scaled(cx), scaled(cy)))
            out.append(row)
            order, length = REF["optimal_tour"](cities)
            row = ["tour", count, seed, scaled(length)]
            row.extend(order)
            out.append(row)
            walk = list(range(count))
            out.append(["len", count, seed,
                        scaled(REF["tour_length"](cities, walk)),
                        scaled(REF["tour_length"](cities, order))])
    for count in range(4, 20):
        for hundredth in range(0, 21):
            out.append(["ladder", count, hundredth,
                        next_count(count, hundredth * 0.05)])
    out.append(["close", scaled(closeness(1.0, 0.0)),
                scaled(closeness(2.0, 4.0))])
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
            acells, bcells = a.split(","), b.split(",")
            for at, (x, y) in enumerate(zip(acells, bcells)):
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
