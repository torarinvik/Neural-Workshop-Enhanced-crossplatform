#!/usr/bin/env python3
"""Differential harness: tasks/ninarow.elisa vs the real
neural_workshop/ninarow.py.

The reference is pure and takes its seed as an argument, so this drives the
ACTUAL module: every row comes out of `ninarow.grade_at`, `ninarow.all_lines`,
`ninarow.lines_through` and `ninarow.generate`.

The draw order is the thing under test, and the subtle part is WHERE the float
draw sits. The reference's noise loop is:

    for cell in order:
        if cells[cell] != EMPTY or cell == target: continue
        value = OPPONENT if rng.random() < 0.62 else PLAYER

so the `random()` happens AFTER the empty/target filter and a skipped cell
consumes nothing. Drawing first and filtering after produces boards that look
entirely reasonable and are wrong from the first skipped cell onward -- which
only a whole-board comparison across several seeds catches.

Rungs 1-6 only; see the sweep's header for why. The line tables are checked
separately from the deals, so a wrong table is named directly rather than
showing up as a mysteriously different board.
"""
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/"
       "Neural-Workshop-Enhanced-crossplatform/original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import ninarow as ref  # noqa: E402


def row(*values):
    return ",".join(str(v) for v in values)


def grade_lines(out):
    for rung in (-4, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 99):
        grade = ref.grade_at(rung)
        out.append(row("grd", rung, grade.size, grade.pellets, grade.length,
                       grade.attempts))


def line_lines(out):
    for size in (5, 6, 8, 12, 16):
        for length in (3, 4, 5, 8):
            if length > size:
                continue
            lines = ref.all_lines(size, length)
            through = [len(ref.lines_through(size, length, cell))
                       for cell in range(size * size)]
            out.append(row("lines", size, length, len(lines), *through))


def deal_lines(out):
    for rung in (1, 2, 3, 4, 5, 6):
        for seed in (0, 1, 7, 42, 1234):
            puzzle = ref.generate(rung, seed=seed)
            if puzzle is None:
                out.append(row("deal", rung, seed, 0))
            else:
                out.append(row("deal", rung, seed, 1, puzzle.size,
                               puzzle.pellets, puzzle.length, puzzle.answer,
                               puzzle.rung, *puzzle.cells))


def python_lines():
    out = []
    grade_lines(out)
    line_lines(out)
    deal_lines(out)
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
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
