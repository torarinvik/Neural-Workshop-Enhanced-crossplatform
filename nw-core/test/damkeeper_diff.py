"""Differential of accepted deals and every recorded Dam Keeper tick."""

from math import ceil, isclose
from pathlib import Path
from random import Random
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import damkeeper as source

LEVELS = (1, 3, 4, 7, 10, 13, 16, 20, 35)


def result(run):
    if run.result is None:
        return 0, -1
    passed, message = run.result
    if passed:
        return 1, -1
    if match := re.fullmatch(r"Dam (\d+) overtopped", message):
        return 2, int(match[1]) - 1
    if match := re.fullmatch(r"Reservoir (\d+) ran too low", message):
        return 3, int(match[1]) - 1
    assert message == "The town flooded", message
    return 4, -1


def check_floats(actual, expected, location):
    assert len(actual) == len(expected)
    for a, b in zip(actual, expected):
        assert isclose(float(a), b, rel_tol=1e-12, abs_tol=1e-12), (location, a, b)


def check_session(rows):
    def read(label, accepted, phase, rung, trial, passed, best, run, deadline):
        kind, stage, *fields = next(rows).split()
        assert (kind, stage) == ("game", label)
        expected = (accepted, phase, rung, trial, passed, best, result(run)[0] if run else 0)
        assert tuple(map(int, fields[:7])) == expected, (label, fields, expected)
        check_floats(fields[7:], (run.t if run else 0.0, deadline), label)

    def tick(run, now, previous):
        elapsed = max(0.0, min(0.1, now - previous))
        frames = max(1, ceil(elapsed / (1 / 30)))
        for _ in range(frames):
            run.step(elapsed / frames)
            if run.result is not None:
                break

    rng = Random(17)
    run = source.Run(source.deal(4, rng=rng))
    read("start", 1, 1, 4, 1, 0, 0, run, 0.0)
    tick(run, 7.0, 5.0)
    read("clamp", 1, 1, 4, 1, 0, 0, run, 0.0)
    previous, index = 7.0, 1
    while run.result is None:
        now = 7.0 + index / 60
        tick(run, now, previous)
        previous = now
        index += 1
    assert not run.result[0]
    deadline = previous + 3.0
    read("fail", 1, 2, 3, 1, 0, 0, run, deadline)
    read("wait", 0, 2, 3, 1, 0, 0, run, deadline)
    run = source.Run(source.deal(3, rng=rng))
    read("next", 1, 1, 3, 2, 0, 0, run, deadline)
    previous, index = deadline, 1
    while run.result is None:
        now = deadline + index / 60
        for port in source.autopilot(run):
            run.press(port)
        tick(run, now, previous)
        previous = now
        index += 1
    assert run.result[0]
    read("pilot", 1, 2, 4, 2, 1, 3, run, previous + 3.0)
    read("done", 1, 3, 4, 2, 1, 3, None, previous + 3.0)
    read("restart", 1, 1, 4, 1, 0, 0, None, previous + 3.0)


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    ticks = 0
    results = set()
    for seed, rung in enumerate(LEVELS, -4):
        valley = source.deal(rung, seed=seed)
        level = valley.level
        header = next(rows).split()
        assert header[:5] == ["valley", *map(str, (rung, seed, level.dams, level.storms))]
        check_floats(header[5:], (level.rain, level.delay, level.flood, level.stiff, level.hidden), (rung, seed))
        for storm in valley.storms:
            kind, *fields = next(rows).split()
            assert kind == "storm"
            check_floats(fields, storm, (rung, seed))
        for initial in valley.start:
            kind, field = next(rows).split()
            assert kind == "water"
            check_floats([field], [initial], (rung, seed))
        for policy in range(3):
            run = source.Run(valley)
            tick = 0
            while run.result is None:
                if policy == 0:
                    port = next(iter(source.autopilot(run)), -1)
                else:
                    port = 2 * (level.dams - 1) if policy == 2 and tick < 4 else -1
                if port >= 0:
                    run.press(port)
                dt = 1 / 30 if policy < 2 else (0.0 if tick % 23 == 0 else (0.037 if tick % 2 == 0 else 0.011))
                run.step(dt)
                row, *fields = next(rows).split()
                verdict, dam = result(run)
                expected = (policy, tick, port, verdict, dam)
                assert row == "tick" and tuple(map(int, fields[:5])) == expected, (rung, seed, fields, expected)
                check_floats(fields[5:8], (run.t, run.town, run.flood_for), (rung, seed, tick))
                for k in range(level.dams):
                    start = 8 + 6 * k
                    check_floats(fields[start:start + 6],
                                 (run.water[k], run.gate[k], run.opening[k], run.arriving[k], run.low_for[k], run.in_pipe(k)),
                                 (rung, seed, tick, k))
                tick += 1
                ticks += 1
            results.add(result(run)[0])
    assert results == {1, 2, 3, 4}, results
    check_session(rows)
    assert next(rows, None) is None
    print(f"PASS: {len(LEVELS)} Dam Keeper valleys, {ticks:,} clocked states, all four outcomes, and controller replay")


if __name__ == "__main__":
    compare(sys.argv[1])
