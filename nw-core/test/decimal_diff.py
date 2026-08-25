#!/usr/bin/env python3
"""Differential harness: decimal.elisa vs CPython's `decimal` and the real
bwaccel/arithmetic.py.

Three references are driven, not transcribed:

  * `decimal.Decimal` itself, under the default context, for construction,
    rendering, the four operations, remainder and comparison;
  * `bwaccel.apply_arithmetic`, the function the game calls, over the operand
    range a session actually produces;
  * `neural_workshop.matching._check_arithmetic`, with stand-in `state`
    singletons, so the CORRECT/INCORRECT verdict itself is compared.

Values cross the boundary as `str(Decimal)`, which is exact and canonical: it
encodes sign, coefficient AND exponent, so 0.1 and 0.10 do not compare equal by
accident. Failures raised by the reference are scored as `E1` (DivisionByZero /
ZeroDivisionError), `E2` (InvalidOperation) or `E3` (Overflow) on both sides.
"""
import subprocess
import sys
import types
from decimal import Decimal, DivisionByZero, InvalidOperation, Overflow

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced")
sys.path.insert(0, APP)

import bwaccel  # noqa: E402
from neural_workshop import matching, state  # noqa: E402

OPS = ('add', 'subtract', 'multiply', 'divide')

# Strings fed to Decimal(str). Whitespace, signs, empty fraction parts, leading
# zeros, exponents and the rejected spellings all appear.
PARSE_INPUTS = (
    "0", "-0", "+0", "1", "-1", "12", "1.5", "-1.5", "0.5", ".5", "-.5", "5.",
    "1.50", "0.00", "000", "0.0100", "00123", "007", "1e5", "1E+5", "1E-5",
    "-2.5E-3", "  -12.75  ", "\t7\n", "0.1E+1000000000",
    "12345678901234567890123456789012", "0.000000000000000000000000000001",
    "9999999999999999999999999999", "1E+1000000",
    "", ".", "-", "+", "1.2.3", "1 2", "abc", "1e", "1e+", "1E5x", "--1", "1-",
    "NaN", "Infinity", "-Infinity", "sNaN", "1_000", "1E+2000000000",
    "12345678901234567890123456789012345678901234567890123456789012345",
    # The capacity boundaries themselves, which must still be accepted: 64
    # significant digits and an exponent of -1e9.
    "1234567890123456789012345678901234567890123456789012345678901234",
    "1E-1000000000",
)

# Decimal(int) is exact; the extremes check the digit extraction, including the
# most negative i64, whose magnitude has no i64 representation.
FROM_INT = (0, 1, -1, 7, -7, 1000000, 9223372036854775807,
            -9223372036854775808)

# Deliberate, documented departures from CPython, each one a capacity or scope
# limit named in decimal.elisa's header. Scored rather than skipped: the port
# must produce exactly this, and a change in either direction is a failure.
KNOWN_DIVERGENCES = {
    # No NaN/Infinity values: the answer field only accepts digits and '.'.
    "NaN": "E2", "Infinity": "E2", "-Infinity": "E2", "sNaN": "E2",
    # No underscore digit separators.
    "1_000": "E2",
    # Exponent magnitude capped at 1e9 (CPython: 1E+2000000000).
    "1E+2000000000": "E3",
    # 65 significant digits, one past DECIMAL_MAX_INPUT_DIGITS.
    "12345678901234567890123456789012345678901234567890123456789012345": "E3",
}

# Operands for the string-driven operation grid: zeros with different
# exponents, trailing-zero forms, a negative fraction, exponent forms, a
# 28-digit coefficient whose products have to round, two 29-digit coefficients
# that land exactly on a rounding tie (one either side of half-to-even), and a
# pair 60 orders of magnitude apart, which is what forces the sticky-digit rule
# in addition and DivisionImpossible in remainder.
DEC_OPERANDS = ("0", "0.00", "1", "1.0", "-1", "2.5", "-0.125", "12", "100",
                "0.1", "1E+3", "9999999999999999999999999999",
                "1E+30", "1E-30", "10000000000000000000000000005",
                "10000000000000000000000000015")

# The operand range a session produces: randint(-ARITHMETIC_MAX_NUMBER,
# ARITHMETIC_MAX_NUMBER) with the default maximum of 12, negatives included.
GAME_RANGE = range(-12, 13)

# Answers the player might have typed, against operands that exercise a
# correct hit, a near miss, and the x/0 failure path.
CHECK_ANSWERS = ("0", "7", "2.5", "0.3333333333333333333333333333", "4")
CHECK_LEFT = (0, 1, 3, 7, 12)
CHECK_RIGHT = (0, 2, 3)

# A whole session for score_arithmetic: operands that include the zero divisor,
# and every fifth operation misspelt, which is the reference's ValueError path.
# The answers are the values a player would have typed at 2-back with no crab
# and no variable list -- right on seven trials, wrong on the rest -- so the
# rights path is exercised too. Three of the hits are deliberately written in a
# different form from the computed answer (-1.50 for -1.5, 0.00 for 0, and the
# full 28-digit quotient of 1/3): Decimal equality is numeric, and a port that
# compared representations would score them wrong.
SESSION_LENGTH = 14
SESSION_OPS = ('add', 'subtract', 'multiply', 'divide', 'modulo')
SESSION_ANSWERS = ("0", "1", "3", "5", "0", "2", "7", "-6", "-1.50", "0",
                   "-2", "0", "0.00", "0.3333333333333333333333333333")
SESSION_NUMBERS = [(i % 7) - 3 for i in range(SESSION_LENGTH)]
SESSION_VARIABLE = [1 + i % 4 for i in range(SESSION_LENGTH)]


def render(thunk):
    """`str` of a Decimal-producing call, or the agreed failure code."""
    try:
        return str(thunk())
    except DivisionByZero:
        return "E1"
    except InvalidOperation:
        return "E2"
    except Overflow:
        return "E3"
    except ZeroDivisionError:
        return "E1"


class FakeMode:
    """Only the attributes matching._check_arithmetic actually reads."""

    def __init__(self, operation, number):
        self.current_operation = operation
        self.current_stim = {'number': number}


class FakeLabel:
    def __init__(self, value):
        self.value = value

    def parse_answer(self):
        return self.value


def check_verdict(operation, left, right, given):
    state.mode = FakeMode(operation, right)
    state.stats = types.SimpleNamespace()
    state.stats.session = {'numbers': [left]}
    state.arithmetic_answer_label = FakeLabel(given)
    return 1 if matching._check_arithmetic(0) == matching.CORRECT else 0


def python_lines():
    out = []

    # Parse cases are keyed by index, not echoed: two of the inputs carry
    # whitespace that would break the one-line-per-case format.
    for index, text in enumerate(PARSE_INPUTS):
        if text in KNOWN_DIVERGENCES:
            value = KNOWN_DIVERGENCES[text]
        else:
            value = render(lambda: Decimal(text))
        out.append(f"parse,{index},{value}")

    for value in FROM_INT:
        out.append(f"fromint,{value},{Decimal(value)}")

    # bwaccel.apply_arithmetic over the real operand range.
    for code, op in enumerate(OPS):
        for a in GAME_RANGE:
            for b in GAME_RANGE:
                value = render(lambda: bwaccel.apply_arithmetic(op, a, b))
                out.append(f"game,{code},{a},{b},{value}")

    # The same entry point over decimal-valued operands.
    for code, op in enumerate(OPS):
        for left in DEC_OPERANDS:
            for right in DEC_OPERANDS:
                value = render(lambda: bwaccel.apply_arithmetic(
                    op, Decimal(left), Decimal(right)))
                out.append(f"dec,{code},{left},{right},{value}")

    # Remainder, which the reference uses to pick divisors, is not part of
    # apply_arithmetic, so it goes through Decimal directly.
    for left in DEC_OPERANDS:
        for right in DEC_OPERANDS:
            value = render(lambda: Decimal(left) % Decimal(right))
            out.append(f"rem,{left},{right},{value}")

    for left in DEC_OPERANDS:
        for right in DEC_OPERANDS:
            a, b = Decimal(left), Decimal(right)
            out.append(f"cmp,{left},{right},{(a > b) - (a < b)}")

    # The verdict itself, through the real matching._check_arithmetic.
    for code, op in enumerate(OPS):
        for left in CHECK_LEFT:
            for right in CHECK_RIGHT:
                for given in CHECK_ANSWERS:
                    verdict = check_verdict(op, left, right, Decimal(given))
                    out.append(f"check,{code},{left},{right},{given},{verdict}")

    # The port's error-set surface, which raises where the reference raises.
    # Same expected values; the sweep reaches them through `catch` rather than
    # through the status-code functions the sections above use.
    union = [
        lambda: Decimal("12.5"),
        lambda: Decimal("oops"),
        lambda: "E3",  # 65 significant digits: a documented capacity limit
        lambda: bwaccel.apply_arithmetic('add', 1, 2),
        lambda: bwaccel.apply_arithmetic('subtract', 1, 2),
        lambda: bwaccel.apply_arithmetic('multiply', 3, 4),
        lambda: bwaccel.apply_arithmetic('divide', 1, 3),
        lambda: bwaccel.apply_arithmetic('divide', 1, 0),
        lambda: bwaccel.apply_arithmetic('divide', 0, 0),
        lambda: Decimal(7) % Decimal(2),
        lambda: Decimal(1) % Decimal(0),
    ]
    for tag, thunk in enumerate(union):
        out.append(f"union,{tag},{render(thunk)}")

    # Whole-session scoring, through the real bwaccel.score_arithmetic.
    session = {
        'numbers': list(SESSION_NUMBERS),
        'operation': [SESSION_OPS[i % 5] for i in range(SESSION_LENGTH)],
        'arithmetic_input': [Decimal(s) for s in SESSION_ANSWERS],
    }
    for nback in (1, 2, 3):
        for crab in (0, 1):
            for varnb in (0, 1):
                rights, wrongs = bwaccel.score_arithmetic(
                    nback, bool(crab),
                    SESSION_VARIABLE if varnb else None, session)
                out.append(f"score,{nback},{crab},{varnb},{rights},{wrongs}")
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g}\n  python: {w}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
