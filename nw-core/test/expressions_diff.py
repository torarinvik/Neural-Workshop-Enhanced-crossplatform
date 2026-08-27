#!/usr/bin/env python3
"""Differential harness for tasks/expressions.elisa against expressions.py.

The reference imports nothing but `re`, `fractions` and `typing`, so it is
imported and run as itself -- `Poly`, `parse`, `render`, `render_mono` and the
arithmetic under them.

The corpus is written to a file the sweep reads back, so both sides read the
same strings and there is one place they are written down. Terms are emitted in
RENDER order and again in `str(mono)` order rather than in the order the
polynomial happens to hold them: the reference says term order is not part of
the value -- everything that looks at it sorts first -- and emitting the
internal order would be testing a coincidence.
"""
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

from neural_workshop import expressions as X  # noqa: E402

CORPUS_PATH = "/tmp/nw_expressions_corpus.txt"

#: Read by both sides. Valid and invalid on purpose: a player typing `3x+` and
#: pressing return has answered wrongly, not crashed, and the port has to agree
#: about which of these are answers at all.
CORPUS = (
    "3x + 4",
    "2(x+1)",
    "(x+1)(x-1)",
    "-x^2",
    "-x**2",
    "(-x)^2",
    "x^3 - 2x^2 + x - 5",
    "1/2 + 1/3",
    "2/3 * 3/4",
    "7",
    "0",
    "-0",
    "x/2",
    "(x+1)/2",
    "x/(x+1)",
    "x^-1",
    "x^0",
    "x^2^3",
    "2^3^2",
    "3 4",
    "3x y",
    "2 x",
    "xy",
    "n + z",
    "q",
    "",
    "   ",
    "3x+",
    "(x+1",
    "x)",
    "3 +* 4",
    "12345678901234567890123456789",
    "1/0",
    "X + Y",
    "  3  x  ",
    "3**2",
    "-3x - -4",
    "x*y*z*n",
    "(x+y)^3",
    "1 + 2 + 3 + 4",
    "5 - 3 - 1",
    "2/4",
    "3 - 4 + 5 - 6",
    "(2x + 3y)(2x - 3y)",
    "n^2 + x^2",
    "z",
    "4x^2y",
    "0x + 5",
    "(x - x) + 7",
    "1 - 1",
    "-(x + 1)",
    "+x",
    "2(3(4(x+1)))",
    "x^1",
    "10x^10",
    "1/3 + 1/6",
)

AT = {"x": Fraction(1, 2), "y": Fraction(-3), "z": Fraction(2), "n": Fraction(1)}
NAMES = ("x", "y", "z", "n")


def read(text):
    """`parse`, with the three failures the callers catch folded into None."""
    try:
        return X.parse(text)
    except (X.ParseError, ArithmeticError, ZeroDivisionError):
        return None


def number(value):
    return (str(value.numerator) if value.denominator == 1 else str(value))


def powers(mono):
    held = dict(mono)
    return [held.get(name, 0) for name in NAMES]


def term_cells(poly, key):
    out = []
    for mono in sorted(poly.terms, key=key):
        out.extend(powers(mono))
        out.append(number(poly.terms[mono]))
    return out


def poly_cells(poly):
    out = [len(poly.terms), X.render(poly),
           1 if poly.is_constant() else 0,
           number(poly.constant_value()) if poly.is_constant() else "-",
           poly.degree()]
    out.extend(poly.degree_in(name) for name in NAMES)
    out.extend(term_cells(poly, X._order))
    out.append("|")
    out.extend(term_cells(poly, lambda mono: str(mono)))
    return out


def reference():
    with open(CORPUS_PATH, "w") as handle:
        for line in CORPUS:
            handle.write("%s\n" % line)

    out = []
    for spec, text in enumerate(CORPUS):
        got = read(text)
        row = ["parse", spec, 0 if got is None else 1]
        if got is not None:
            row.extend(poly_cells(got))
            try:
                row.append(number(got.evaluate(AT)))
            except ValueError:
                row.append("-")
        out.append(row)

    for one in range(len(CORPUS)):
        for two in range(len(CORPUS)):
            if (one * 7 + two * 3) % 11:
                continue
            left, right = read(CORPUS[one]), read(CORPUS[two])
            row = ["arith", one, two,
                   0 if left is None else 1, 0 if right is None else 1]
            if left is None or right is None:
                out.append(row)
                continue
            row.append(1 if left == right else 0)
            for name, op in (("add", lambda a, b: a + b),
                             ("sub", lambda a, b: a - b),
                             ("mul", lambda a, b: a * b),
                             ("div", lambda a, b: a / b)):
                try:
                    made = op(left, right)
                except (ArithmeticError, ZeroDivisionError):
                    row.append("-")
                    continue
                row.append(X.render(made))
            for exponent in range(4):
                try:
                    row.append(X.render(left ** exponent))
                except ArithmeticError:
                    row.append("-")
            out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
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
