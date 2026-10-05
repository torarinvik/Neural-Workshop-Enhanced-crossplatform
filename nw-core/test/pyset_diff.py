#!/usr/bin/env python3
"""Differential harness: tasks/pyset.elisa vs a real CPython `set`.

The set emulation exists for ONE observable property -- iteration order -- so
that is all this compares, over a deterministic grid of add/discard sequences.

It is a suite in its own right because the rules are not guessable. The one that
matters most: a discarded slot becomes a DUMMY, and a later add remembers the
most recent DUMMY while continuing to probe for an existing key or the first
EMPTY slot. CPython overwrites its ``freeslot`` for every later DUMMY in the
hybrid probe. If the key is new, that DUMMY is reused without increasing
``fill``; only an EMPTY insertion increases ``fill``. Minimal witness:

    add 8; discard 8; add 24; add 11; add 28; add 23

A real set reuses the tombstone and yields the CPython iteration order; a model
that skips the DUMMY and inserts at the first EMPTY slot increases `fill`, takes
a different resize path, and yields a different order.

The sequences mirror sweep_trial's LCG exactly, so both sides see the same ops.
"""
import subprocess
import sys


def lcg(state):
    return (state * 1103515245 + 12345) & 2147483647


def trial_line(trial, span, ops):
    got = set()
    state = trial * 7919 + 13
    for _step in range(ops):
        state = lcg(state)
        key = state % span
        state = lcg(state)
        if state % 100 < 65:
            got.add(key)
        else:
            got.discard(key)
    cells = ["set", trial, span, ops, len(got)] + list(got)
    return ",".join(str(v) for v in cells)


def point_trial_line(trial, size, ops):
    """The 2-tuple keyed variant: the slot comes from CPython's TUPLE hash, so
    this exercises a different probe sequence over the same table."""
    got = set()
    state = trial * 6271 + 5
    for _step in range(ops):
        state = lcg(state); x = state % size
        state = lcg(state); y = state % size
        state = lcg(state)
        if state % 100 < 70:
            got.add((x, y))
        else:
            got.discard((x, y))
    cells = ["pt", trial, size, ops, len(got)]
    for x, y in got:
        cells += [x, y]
    return ",".join(str(v) for v in cells)


def python_lines():
    out = []
    for span in (8, 32, 256, 1024):
        for ops in (1, 2, 5, 13, 40, 90):
            for trial in range(25):
                out.append(trial_line(trial, span, ops))
    for size in (5, 7, 9, 13):
        for ops in (1, 3, 8, 20, 50):
            for trial in range(20):
                out.append(point_trial_line(trial, size, ops))
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:220]}\n  python: {w[:220]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
