#!/usr/bin/env python3
"""Differential harness for tasks/sudoku.elisa against neural_workshop.sudoku.

Runs the SAME rungs and seeds through the real module and compares line for
line. `generate` is the whole port in one call -- fill, dig and rate -- so a
divergence in the draw order or in any of the six techniques shows up as a
different puzzle, and the first differing cell is named.

`attempts` is passed explicitly on both sides: the rung's own budget would make
the sixteens take minutes here, and rejection sampling means the count is part
of the answer rather than a speed dial.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

import random                                   # noqa: E402
from neural_workshop import sudoku              # noqa: E402


def reference():
    out = []
    for level in range(1, 14):
        g = sudoku.GRADES[max(0, min(len(sudoku.GRADES) - 1, level - 1))]
        out.append(["grd", level, g.box, g.floor, g.ceiling,
                    g.guesses, g.keep, g.tries])
    for level in range(1, 9):
        for seed in range(1, 7):
            made = sudoku.generate(level, seed=seed, attempts=3)
            row = ["gen", level, seed, made.box, made.tier, made.guesses,
                   made.blanks()]
            row.extend(made.givens)
            row.extend(made.solution)
            out.append(row)
    for seed in range(1, 3):
        made = sudoku.generate(9, seed=seed, attempts=1)
        row = ["big", seed, made.box, made.tier, made.guesses]
        row.extend(made.givens)
        out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
    binary = sys.argv[1]
    got = subprocess.run([binary], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a == b:
            continue
        print("MISMATCH line %d" % index)
        acells, bcells = a.split(","), b.split(",")
        if len(acells) != len(bcells):
            print("  elisa  %d cells" % len(acells))
            print("  python %d cells" % len(bcells))
        else:
            for at, (x, y) in enumerate(zip(acells, bcells)):
                if x != y:
                    print("  first differing cell %d: elisa %s, python %s" % (at, x, y))
                    break
        print("  elisa:  %s" % a[:160])
        print("  python: %s" % b[:160])
        return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
