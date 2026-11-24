#!/usr/bin/env python3
"""Compare seeded Hold It deals and clocked sessions against Python."""
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import holdit


def deals():
    for rung in range(1, 36):
        for seed in range(-100, 100):
            ask = holdit.deal(rung, seed)
            kind = ("copy", "scale", "sum").index(ask.kind)
            floats = (*ask.level.span, ask.level.margin, ask.factor, ask.target, ask.tick, ask.turn,
                      *(time for lamp in ask.lamps for time in lamp))
            yield f"{rung} {seed} {kind} {len(ask.lamps)} " + " ".join(f"{x:.9f}" for x in floats)


def sessions():
    for scenario, start_rung in enumerate((1, 7, 10, 25)):
        rng = random.Random(17)
        rung, trial, phase = start_rung, 1, 1
        passed_rungs = []
        run = holdit.Run(holdit.deal(rung, rng=rng))
        last_tick = 0.0
        for tick in range(1, 2200):
            now = tick / 32
            if phase == 2 and now >= deadline:
                if trial == 2:
                    yield f"done {len(passed_rungs)} {max(passed_rungs, default=0)}"
                    break
                trial += 1
                run = holdit.Run(holdit.deal(rung, rng=rng))
                phase, last_tick = 1, now
            elif phase == 1:
                scale = (1, 0.3, 1.5, 1)[scenario]
                pressed = (scenario != 3 and run.your_turn()
                           and (run.down is None or run.t - run.down < run.ask.target * scale - 1e-9))
                dt = max(0.0, min(0.1, now - last_tick))
                last_tick = now
                steps = max(1, math.ceil(dt / (1 / 240)))
                for _ in range(steps):
                    run.step(dt / steps, holdit.HOLD if pressed else None)
                    if run.result is not None:
                        break
                if run.result is not None:
                    if run.result[0]:
                        passed_rungs.append(rung)
                        rung += 1
                    else:
                        rung = max(1, rung - 1)
                    phase, deadline = 2, now + 3.0
            text = run.result[1] if run.result else ""
            verdict = (0 if not run.result else 1 if run.result[0] else
                       2 if text.endswith("short") else 3 if text.endswith("long") else 4)
            lamps = [int(run.holding or a <= run.t < b) for a, b in run.ask.lamps]
            lamps += [0] * (2 - len(lamps))
            yield (f"{phase} {trial} {rung} {run.t:.9f} {int(run.down is not None)} "
                   f"{int(run.holding)} {run.held or 0:.9f} {verdict} {lamps[0]} {lamps[1]}{text}")


if __name__ == "__main__":
    expected_deals = list(deals())
    expected_sessions = list(sessions())
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    assert len(actual) == len(expected_deals) + len(expected_sessions)
    for index, (got, expected) in enumerate(zip(actual, expected_deals + expected_sessions)):
        assert got == expected, (index, got, expected)
    print(f"PASS: {len(expected_deals)} Hold It deals and {len(expected_sessions)} clocked states match Python")
