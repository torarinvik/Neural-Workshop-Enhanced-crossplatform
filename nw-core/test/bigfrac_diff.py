#!/usr/bin/env python3
"""Differential harness for src/bigfrac.elisa against CPython.

The reference here is the language: `int` and `fractions.Fraction` are what
neural_workshop/algebra.py and expressions.py compute in, so they are what this
is checked against. Nothing is lifted, because nothing needs to be.

The sizes are chosen for the top of the algebra ladder -- six five-digit primes
multiplied, a box of about 10^28, a recombination running to 10^33 -- and the
signs are chosen for where the two languages part: Python's `//` floors toward
minus infinity and its `%` takes the sign of the divisor.
"""
import random
import subprocess
import sys
from fractions import Fraction

SEEDS = (0, 1, 7, 1000000007, 999999999999999989, 4294967296)


def sample(spec):
    magnitude, sign = spec // 2, spec % 2
    if magnitude < 6:
        value = SEEDS[magnitude]
    else:
        value = 99991
        for _each in range(magnitude - 5):
            value *= 99989
        value += magnitude * 37
    return -value if sign else value


def getrandbits(rng, k):
    return rng.getrandbits(k) if k > 0 else 0


def reference():
    out = []

    for a in range(24):
        for b in range(24):
            left, right = sample(a), sample(b)
            row = ["int", a, b, left, right,
                   (left > right) - (left < right),
                   left + right, left - right, left * right,
                   __import__("math").gcd(left, right),
                   left.bit_length()]
            if right == 0:
                row.append(-1)
            else:
                row.extend((0, left // right, left % right))
            for small in (1, 2, 60, 99991):
                row.append(left % small)
            out.append(row)

    for spec in range(20):
        left = sample(spec * 2)
        rng = random.Random(5000 + spec)
        row = ["draw", spec, left, left.bit_length()]
        for _each in range(3):
            row.append(getrandbits(rng, left.bit_length()))
        for _each in range(3):
            row.append(rng.randrange(left) if left > 0 else 0)
        row.append(rng.randrange(1000000))
        out.append(row)

    for a in range(14):
        for b in range(14):
            num_one, den_one = a * 5 - 30, a + 1
            num_two, den_two = b * 7 - 42, b + 2
            one = Fraction(num_one, den_one)
            two = Fraction(num_two, den_two)
            row = ["frac", num_one, den_one, num_two, den_two,
                   text(one), text(two), text(one + two), text(one - two),
                   text(one * two)]
            if two == 0:
                row.append(-1)
            else:
                row.extend((0, text(one / two)))
            row.append((one > two) - (one < two))
            row.append(1 if one == two else 0)
            row.append(1 if one.denominator == 1 else 0)
            for exponent in range(4):
                row.append(text(one ** exponent))
            out.append(row)

    for spec in range(8):
        left = sample(12 + spec)
        one = Fraction(left)
        two = Fraction(3, 7)
        out.append(["bigfrac", spec, text(one), text(one + two),
                    text(one * two), text(one / two),
                    1 if one.denominator == 1 else 0])
    return [",".join(str(one) for one in row) for row in out]


def text(value):
    """`Fraction`'s own two-way spelling, which is what both `_number`s use."""
    return (str(value.numerator) if value.denominator == 1
            else "%d/%d" % (value.numerator, value.denominator))


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
