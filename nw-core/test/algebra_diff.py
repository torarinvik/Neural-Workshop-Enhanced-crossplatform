#!/usr/bin/env python3
"""Differential harness for tasks/algebra.elisa against algebra.py.

algebra.py imports only `math`, `random`, `re`, `fractions` and its own
expressions module, so it is imported and run as itself -- every builder, the
forward check, the marking and `crack`.

The typed answers a rung is marked against are written to a file the sweep
reads back, so both sides read the same strings.

`Problem.candidates` is `log10(max(1, space))`, a display value, so `space`
itself is what is compared here and the logarithm is left to the shell.
`algebra_working_test.mjs` separately compares the generated derivation with
original Python fixtures and checks that the complete label reaches the display list.
"""
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

from neural_workshop import algebra as A  # noqa: E402
from neural_workshop.expressions import Poly, render  # noqa: E402

TYPED_PATH = "/tmp/nw_algebra_typed.txt"

WANTS = {"": 0, "x = ?": 1, "smallest x >= 0": 2, "smallest n >= 0": 3,
         "expand and collect": 4}
WALKS = {"coefficients": 0, "upward": 1, "fractions": 2, "outward": 3}

#: What a player might type. Read by both sides; deliberately includes the
#: question copied back, which normal form accepts and `collected` must not.
TYPED = (
    "0",
    "1",
    "-1",
    "7",
    "13",
    "1/2",
    "-3/4",
    "x",
    "3x + 4",
    "4 + 3x",
    "x - 9",
    "-x + 9",
    "2x^2 - 3x + 1",
    "y + y + 3",
    "2y + 3",
    "(x+1)(x-1)",
    "3 * x + 4",
    "1 + -11x",
    "-2x - 1",
    "",
    "   ",
    "3x+",
    "61578876179867505446099134483",
    "34189",
    "x^2 - 1",
)


def number(value):
    value = Fraction(value)
    return (str(value.numerator) if value.denominator == 1
            else "%d/%d" % (value.numerator, value.denominator))


def shown(problem):
    return (render(problem.answer) if isinstance(problem.answer, Poly)
            else number(problem.answer))


def problem_cells(problem):
    out = [problem.asked, shown(problem), problem.space, problem.steps,
           WANTS[problem.wants],
           1 if isinstance(problem.answer, Poly) else 0,
           1 if A.checks_out(problem) else 0,
           1 if A.guessable(problem) else 0,
           WALKS[A.walk_of(problem.grade)]]
    cracked = A.crack(problem)
    out.append(-1 if cracked is None else cracked)
    if isinstance(problem.answer, Poly):
        out.append(len(problem.answer.terms))
    else:
        out.append(-1)
    return out


def reference():
    with open(TYPED_PATH, "w") as handle:
        for line in TYPED:
            handle.write("%s\n" % line)

    out = []
    for rung in range(0, 15):
        grade = A.grade_of(rung)
        out.append(["grade", rung, list(A.BUILDERS).index(grade.family),
                    0 if grade.kind == A.NUMBER else 1,
                    grade.dials.get("digits", -1), grade.dials.get("high", -1),
                    grade.dials.get("degree", -1), grade.dials.get("letters", -1),
                    grade.dials.get("band", -1), grade.dials.get("modulus", -1),
                    grade.dials.get("moduli", -1),
                    A.fraction_grid(grade)[0], A.fraction_grid(grade)[1]])

    for number_at in range(1, 200):
        out.append(["prime", number_at, 1 if A.is_prime(number_at) else 0])

    for level in range(1, 13):
        for seed in range(1, 9):
            problem = A.generate(level, seed=level * 1000 + seed)
            row = ["deal", level, seed, 0 if problem is None else 1]
            if problem is not None:
                row.extend(problem_cells(problem))
                for spec, typed in enumerate(TYPED):
                    row.append(1 if A.correct(problem, typed) else 0)
            out.append(row)

    # The moduli a CRT rung is built on, which is what its derivation is made
    # of -- and the one place a five-digit prime has to be found rather than
    # picked off a list.
    for level in (10, 12):
        for seed in range(1, 5):
            problem = A.generate(level, seed=level * 77 + seed)
            row = ["crt", level, seed, 0 if problem is None else 1]
            if problem is not None:
                row.append(problem.space)
                row.append(number(problem.answer))
                for part in problem.asked.split(",  "):
                    row.append(int(part.split(" (mod ")[1].rstrip(")")))
            out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
    # The Elisa sweep reads typed answers from TYPED_PATH at startup. Generate
    # them before running the binary, or the run emits only the ungraded base
    # columns from an absent/stale fixture.
    want = reference()
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        for index, (a, b) in enumerate(zip(mine, want)):
            if a != b:
                print("  first differing line %d" % index)
                print("  elisa:  %s" % a[:170])
                print("  python: %s" % b[:170])
                break
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, python %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a[:170])
            print("  python: %s" % b[:170])
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
