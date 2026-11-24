"""Replay the shared Tuner game and scene against Python's model and clock rules."""

import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import tuner


def compare(binary):
    lines = iter(subprocess.check_output([binary], text=True).splitlines())
    rng = random.Random(-17)
    now, last = 10.0, 10.0
    rung, trial, passed, best = 1, 1, 0, 0
    run = tuner.Run(tuner.deal(rung, rng=rng, bank="tune"))

    def state(phase, result=0):
        values = next(lines).split()
        assert tuple(map(int, values[:6])) == (phase, rung, trial, passed, best, result), values
        expected = (run.t, run.dial, run.replay_until) if run else (0, 0, 0)
        assert all(math.isclose(float(a), b, rel_tol=0, abs_tol=1e-10)
                   for a, b in zip(values[6:9], expected)), (values, expected)
        assert int(values[9]) == (len(run.gains) if run else 0), values

    def tick(elapsed, controls=None):
        nonlocal now, last
        now += elapsed
        dt = max(0.0, min(0.1, now - last))
        last = now
        steps = max(1, math.ceil(dt / (1 / 120)))
        for _ in range(steps):
            run.step(dt / steps, controls)
            if run.result is not None:
                break

    state(1)
    tick(0.4)
    for _ in range(12):
        tick(0.05)
    state(1)
    start = 0.0
    for expected in (8192 / tuner.RATE, run.t):
        end, pcm = next(lines).split()
        assert math.isclose(float(end), expected, rel_tol=0, abs_tol=1e-12)
        assert bytes.fromhex(pcm) == tuner.mix(run, start, expected)
        start = expected

    for result in (1, -1, -2):
        if result != -2:
            while not run.on():
                tick(0.05, [tuner.UP])
            run.dial = min(tuner.DIAL, run.dial + 0.12)
            tick(0.05, [tuner.FINE_DOWN])
            state(1)
            target = run.radio.target if result == 1 else (run.radio.target + 1) % len(run.radio.stations)
            run.dial = run.where(target)
            run.replay()
            run.press()
        tick(0.05)
        while run.result is None:
            tick(0.05)
        if result == 1:
            passed += 1
            best = max(best, rung)
            rung += 1
        else:
            rung = max(1, rung - 1)
        state(2, result)
        now += 2.5 if result == 1 else 0.05
        last = now
        if trial < 3:
            trial += 1
            run = tuner.Run(tuner.deal(rung, rng=rng, bank="tune"))
            state(1)
        else:
            run = None
            state(3)

    rung, trial, passed, best = 1, 1, 0, 0
    run = tuner.Run(tuner.deal(rung, rng=rng, bank="tune"))
    state(1)
    assert next(lines, None) is None
    print("PASS: 13 Tuner states and checks match Python across an adaptive run, PCM reads, and restart")


if __name__ == "__main__":
    compare(sys.argv[1])
