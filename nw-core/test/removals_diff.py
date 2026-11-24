#!/usr/bin/env python3
"""Differential harness: tasks/removals.elisa vs the real
neural_workshop/removals.py.

Drives the ACTUAL module: GRADES, `generate` and `remembering`.

Whole rounds are compared, not summaries. `generate` deals up to 200 times off
ONE stream, so a single misplaced draw desynchronises every later attempt as
well as its own -- and the round that finally comes back can still look
plausible. Only the moves themselves, the start map and the answers pin it.

The ordering traps this module hides:

  * `loose` is a SET that is iterated (`list(loose)` then shuffle, and two
    comprehensions feeding `choice`). Its ids are `range(vans, size)`, never
    above 22, while CPython's table for that many entries is 8 or 128 slots --
    so `key & mask` is the key and the order is plain ascending. The port walks
    ascending for that reason; this harness is what proves the reasoning.
  * `level` is a DICT that is iterated, and `kin` -- built from that walk --
    feeds `choice`. Insertion order is therefore observable, and the port keeps
    an insertion-ordered key list beside the dense lookup.
  * `_spines` short-circuits: `if kin and (len(free) < want or rng.random() <
    SHARE)`. When `kin` is empty, or when `len(free) < want` is already true,
    `rng.random()` is NEVER CALLED. Drawing unconditionally spends a value that
    the reference does not and desynchronises everything after it.
  * `_spots` takes the FIRST early-enough slot out of the shuffled list and
    `remove`s it (order preserved), then `pop()`s from the END for the rest.
"""
from pathlib import Path
import random
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import removals as ref  # noqa: E402

KIND = {ref.PACK: 0, ref.SWAP: 1}


def row(*values):
    return ",".join(str(v) for v in values)


def grade_lines(out):
    for rung in (-3, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 99):
        g = ref.GRADES[max(0, min(len(ref.GRADES) - 1, rung - 1))]
        out.append(row("grd", rung, g.vans, g.boxes, g.items, g.depth,
                       g.asks, g.nest, g.floor, g.churn))


def round_lines(out):
    for level in range(1, 13):
        for seed in (0, 1, 7, 42, 1234):
            for attempts in (1, 5, 200):
                try:
                    got = ref.generate(level, seed, attempts)
                except RuntimeError:
                    out.append(row("rnd", level, seed, attempts, 0))
                    continue
                cells = ["rnd", level, seed, attempts, 1,
                         got.needed, got.nest, got.churn, len(got.moves)]
                for move in got.moves:
                    cells += [KIND[move.kind], move.thing, move.other]
                cells += list(got.start)
                for item, answer in zip(got.asked, got.answers):
                    cells += [item, answer]
                out.append(row(*cells))


def recall_lines(out):
    for level in (2, 5, 8, 11):
        for seed in (3, 99):
            try:
                got = ref.generate(level, seed, 200)
            except RuntimeError:
                continue
            for window in (0, 1, 3, 6, 12, 40):
                sure, _asked = ref.remembering(got, window)
                out.append(row("rcl", level, seed, window, sure))


def python_lines():
    out = []
    grade_lines(out)
    round_lines(out)
    recall_lines(out)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g[:200]}\n  python: {w[:200]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:260]}\n  python: {w[:260]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
