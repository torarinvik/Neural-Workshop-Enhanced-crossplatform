#!/usr/bin/env python3
"""Differential harness: tasks/inthedark.elisa vs the real
neural_workshop/inthedark.py.

The reference is pure and takes its seed as an argument, so this drives the
ACTUAL module: `grade_at` via GRADES, `vocabulary`, `_weights`, `generate`,
`trace` and `belief`.

The new machinery under test is `random.choices` with weights, which the port
had to reproduce exactly. CPython accumulates the weights into a running total
IN LIST ORDER, takes one random() draw, scales it by the total, and
bisect_RIGHT's for the slot with hi = n - 1. All three details matter: summing
in a different order changes the floating-point rounding and therefore the pick
near a boundary; a left bisect sends an exact hit to the wrong slot; and hi of
n rather than n-1 changes what a draw past the last boundary returns.

`belief` is compared alongside `trace` for the reason the reference keeps both:
trace derives in one backwards pass what belief recomputes by brute force. If
only the fast one were checked, the derivation would be unverified on both
sides at once.
"""
from pathlib import Path
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import inthedark as ref  # noqa: E402

KIND_ID = {ref.PAINT: 0, ref.TURN: 1, ref.SWAP: 2, ref.COPY: 3}


def row(*values):
    return ",".join(str(v) for v in values)


def grade_lines(out):
    for level in (-3, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 40):
        grade = ref.GRADES[max(0, min(len(ref.GRADES) - 1, level - 1))]
        out.append(row("grd", level, grade.lamps, grade.colours, grade.depth,
                       grade.asks, grade.floor, round(grade.work * 1000.0)))


def vocab_lines(out):
    for lamps in (2, 3, 4, 5, 6):
        for colours in (2, 3, 4, 5):
            rooms = ref.vocabulary(lamps, colours)
            weights = ref._weights(rooms)
            flat = []
            for room, weight in zip(rooms, weights):
                flat += [KIND_ID[room.kind], room.lamp, room.other,
                         round(weight * 1000000.0)]
            out.append(row("vocab", lamps, colours, len(rooms), *flat))


def round_lines(out):
    for level in (1, 2, 3, 4, 5, 6, 7, 8):
        for seed in (0, 1, 7, 42, 1234):
            got = ref.generate(level, seed=seed, attempts=80)
            flat = []
            for lamp, answer in zip(got.asked, got.answers):
                flat += [lamp, answer]
            flat += list(got.start)
            for room in got.rooms:
                flat += [KIND_ID[room.kind], room.lamp, room.other]
            out.append(row("round", level, seed, got.lamps, got.colours,
                           len(got.rooms), got.needed,
                           round(got.work * 1000.0), len(got.asked), *flat))


def belief_lines(out):
    for level in (1, 2, 3, 4):
        for seed in (0, 3, 11):
            got = ref.generate(level, seed=seed, attempts=80)
            for lamp in range(got.lamps):
                back, work = ref.trace(got.rooms, lamp)
                mask = 0
                for colour in ref.belief(got.rooms, lamp, got.lamps,
                                         got.colours):
                    mask |= 1 << colour
                out.append(row("belief", level, seed, lamp, back, work, mask))


def python_lines():
    out = []
    grade_lines(out)
    vocab_lines(out)
    round_lines(out)
    belief_lines(out)
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
