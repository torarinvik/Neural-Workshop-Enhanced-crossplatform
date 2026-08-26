#!/usr/bin/env python3
"""Differential harness: tasks/crossedwires.elisa vs the real
neural_workshop/crossedwires.py.

Drives the ACTUAL module: `GRADES`, `pressure`, `gap`, `deal`, and a replayed
`Bench`.

Two stream-order traps live here and neither shows up in a single field, which
is why whole bouts are compared:

* `dead` is drawn ONLY when the rung kills a key -- `randrange(keys) if
  grade.dies else -1`. Drawing it unconditionally consumes one value too many
  and changes every wiring on rungs 1-8, all of which have dies == 0.
* the CROSSED family RETRIES: shuffle, keep only if some key moved. A rejected
  shuffle has already consumed a full Fisher-Yates pass, so filtering after the
  fact rather than retrying desynchronises everything after it.

Both produce a perfectly legal-looking bout when got wrong.
"""
import random
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/"
       "Neural-Workshop-Enhanced-crossplatform/original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import crossedwires as ref  # noqa: E402

FAMILY_ID = {ref.STEADY: 0, ref.TURNED: 1, ref.MIRRORED: 2, ref.CROSSED: 3}


def row(*values):
    return ",".join(str(v) for v in values)


def grade_lines(out):
    for level in (-3, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 40):
        g = ref.GRADES[max(0, min(len(ref.GRADES) - 1, level - 1))]
        out.append(row("grd", level, g.keys, FAMILY_ID[g.family], g.across,
                       g.down, g.targets, g.spare, g.drift, g.dies,
                       *ref.pressure(g)))


def gap_lines(out):
    for across in (11, 13, 15, 17):
        for keys in (4, 8):
            for hx in (0, 3, 7, 10):
                for tx in (0, 5, 9, 12):
                    for hy in (0, 4, 8):
                        for ty in (0, 6, 10):
                            out.append(row("gap", across, keys, hx, hy, tx, ty,
                                           ref.gap((hx, hy), (tx, ty), across,
                                                   across, keys)))


def deal_lines(out):
    for level in range(1, 13):
        for seed in (0, 1, 7, 42, 1234, 99991):
            bout = ref.deal(level, seed=seed)
            flat = []
            for spot in bout.goals:
                flat += [spot[0], spot[1]]
            flat += list(bout.wiring)
            out.append(row("deal", level, seed, bout.start[0], bout.start[1],
                           bout.turn, bout.dead, bout.budget, bout.shortest,
                           len(bout.goals), *flat))


def play_lines(out):
    for level in (1, 3, 6, 9, 11, 12):
        for seed in (1, 7, 1234):
            bout = ref.deal(level, seed=seed)
            bench = ref.Bench(bout)
            steps = []
            for press in range(60):
                keyed = (press * 3 + press // 5) % bout.grade.keys
                went = bench.press(keyed)
                # The port packs the step into one integer as dx*4 + dy + 2.
                steps.append(went[0] * 4 + went[1] + 2)
            out.append(row("play", level, seed, *steps, bench.at[0],
                           bench.at[1], bench.presses, bench.reached,
                           bench.wasted))


def python_lines():
    out = []
    grade_lines(out)
    gap_lines(out)
    deal_lines(out)
    play_lines(out)
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
