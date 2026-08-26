#!/usr/bin/env python3
"""Differential harness: tasks/cookiethief.elisa vs the real
neural_workshop/cookiethief.py.

Drives the ACTUAL module: GRADES and their derived properties, `generate`, and
a beat-by-beat replay through `press` and `beat`.

The replay is the real test. `beat` asks the door AFTER the grab has landed, so
she arrives on the grab that opened it rather than the one after -- reorder
those two lines and the game is still perfectly playable and is a different
game. Likewise `idle` is computed BEFORE the noise is taken off, so the beat
that finishes clearing the pace counts as having done something. Neither shows
up in a summary; both show up immediately in a per-beat trace.

The decoy draw is the stream trap: `sorted(picked)` means the shuffle decides
WHICH beats and the sort decides the order the two choice() draws happen in.
Drawing in shuffled order consumes exactly as many values and assigns them to
different decoys.
"""
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/"
       "Neural-Workshop-Enhanced-crossplatform/original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import cookiethief as ref  # noqa: E402

WHO_ID = {None: 0, ref.MOTHER: 1, ref.SISTER: 2, ref.DOG: 3}
PHASE_ID = {ref.AWAY: 0, ref.COMING: 1, ref.WATCHING: 2, ref.GONE: 3}


def row(*values):
    return ",".join(str(v) for v in values)


def grade_lines(out):
    for level in (-2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 40):
        g = ref.GRADES[max(0, min(len(ref.GRADES) - 1, level - 1))]
        out.append(row("grd", level, g.quota, g.notice, g.opening, g.settling,
                       g.spread, g.warn, g.visit, g.patience, g.slack, g.gold,
                       g.decoys, g.limit, g.room, int(g.reactive),
                       ref.beats_of(g)))


def deal_lines(out):
    for level in range(1, 11):
        for seed in (0, 1, 7, 42, 1234, 99991):
            setup = ref.generate(level, seed=seed)
            flat = []
            for at, who in setup.decoys:
                flat += [at, WHO_ID[who]]
            out.append(row("deal", level, seed, setup.trigger, setup.deadline,
                           len(setup.decoys), *flat))


def play_lines(out):
    for level in (1, 3, 5, 6, 8, 9, 10):
        for seed in (1, 7, 1234):
            for style in (0, 1, 2):
                setup = ref.generate(level, seed=seed)
                grade = setup.grade
                thief = ref.Thief()
                trace = []
                step = 0
                while step < 60 and not ref.over(thief, setup):
                    if style == 0:
                        port = ref.GRAB
                    elif style == 1:
                        port = ref.GRAB if step % 2 == 0 else ref.WAIT
                    else:
                        if thief.gold_on_offer:
                            port = ref.LUNGE
                        elif ref.safe(thief, grade):
                            port = ref.GRAB
                        else:
                            port = ref.WAIT
                    ref.press(thief, port, setup)
                    took = ref.beat(thief, setup)
                    trace += [took, PHASE_ID[thief.phase],
                              ref.door(thief, grade)]
                    step += 1
                out.append(row("play", level, seed, style, *trace, thief.jar,
                               thief.eaten, thief.caught, thief.beat,
                               int(ref.cleared(thief, setup)),
                               ref.haul(thief)))


def python_lines():
    out = []
    grade_lines(out)
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
