#!/usr/bin/env python3
"""Differential harness: tasks/numberology.elisa vs the real
neural_workshop/numberology.py.

The reference is pure and takes its seed as an argument, so this drives the
ACTUAL module: every row comes out of `numberology.generate` and
`numberology.sequence_length`.

What is really under test is the DRAW ORDER, and specifically the reference's
`rng.randint(-scale, scale) or 1`. Python's `or` returns the left operand
unless it is falsey, so a zero draw becomes 1 -- but the draw still happened.
A port that instead loops until it gets a non-zero value consumes a different
number of stream values and desynchronises every later puzzle, while still
producing perfectly plausible sequences. Only comparing whole puzzles across
many seeds catches that.

The rule TEXT is compared as an id plus the numbers interpolated into it
rather than as a formatted string: the text is a pure function of those, so
this is the same check without making two languages agree on printf.
"""
from pathlib import Path
import re
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import numberology as ref  # noqa: E402

ADD_CONST, ADD_SAME, MUL_OFFSET, POLYNOMIAL, ALTERNATING, RECURRENCE = range(1, 7)


def rule_fields(rule):
    """(id, a, b, c) for a rule string, mirroring the port's rule_* fields."""
    # Exact matches FIRST: 'Add the same number each time' also matches the
    # 'Add ... each time' shape, and testing the pattern first misreads it.
    if rule == 'Add the same number each time':
        return (ADD_SAME, 0, 0, 0)
    if rule.startswith('Add ') and rule.endswith(' each time'):
        return (ADD_CONST, int(rule[4:-10]), 0, 0)
    if rule == 'Multiply, then add the offset':
        return (MUL_OFFSET, 0, 0, 0)
    if rule.startswith('Evaluate a degree-'):
        return (POLYNOMIAL, int(rule.split('-')[1].split(' ')[0]), 0, 0)
    if rule == 'Add alternating, growing steps':
        return (ALTERNATING, 0, 0, 0)
    if rule.startswith('order-'):
        # 'order-%d recurrence with degree-%d polynomial and %d periodic layers'
        # Matched rather than index-counted: positional indices into a split
        # silently pick up 'and' when the wording shifts by one word.
        m = re.fullmatch(r'order-(-?\d+) recurrence with degree-(-?\d+) '
                         r'polynomial and (-?\d+) periodic layers', rule)
        if not m:
            raise AssertionError('recurrence rule text changed: %r' % rule)
        return (RECURRENCE, int(m.group(1)), int(m.group(2)), int(m.group(3)))
    raise AssertionError('unrecognised rule text: %r' % rule)


def row(*values):
    return ",".join(str(v) for v in values)


def length_lines(out):
    for difficulty in (-5, 0, 1, 2, 39, 40, 41, 79, 80, 400, 4000):
        for requested in (0, -1, 1, 3, 4, 5, 12):
            # The port spells "no explicit length" as <= 0; the reference
            # spells it None. Everything else passes straight through.
            asked = None if requested <= 0 else requested
            out.append(row("len", difficulty, requested,
                           ref.sequence_length(difficulty, asked)))


def puzzle_row(tag, puzzle, *lead):
    rid, ra, rb, rc = rule_fields(puzzle.rule)
    return row(tag, *lead, len(puzzle.terms), puzzle.answer, rid, ra, rb, rc,
               puzzle.difficulty, puzzle.complexity, *puzzle.terms)


def generate_lines(out):
    for difficulty in (-2, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 16, 18, 20, 24, 32,
                       36, 40, 48, 60):
        for seed in (0, 1, 7, 42, 12345):
            puzzle = ref.generate(difficulty=difficulty, seed=seed)
            out.append(puzzle_row("gen", puzzle, difficulty, seed))


def length_puzzle_lines(out):
    for difficulty in (1, 3, 5, 6, 9, 20, 40):
        for length in (4, 5, 8, 12):
            for seed in (0, 3, 999):
                puzzle = ref.generate(difficulty=difficulty, seed=seed,
                                      length=length)
                rid, ra, rb, rc = rule_fields(puzzle.rule)
                out.append(row("lenpuz", difficulty, length, seed,
                               len(puzzle.terms), puzzle.answer, rid, ra, rb,
                               rc, puzzle.complexity, *puzzle.terms))


def python_lines():
    out = []
    length_lines(out)
    generate_lines(out)
    length_puzzle_lines(out)
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
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
