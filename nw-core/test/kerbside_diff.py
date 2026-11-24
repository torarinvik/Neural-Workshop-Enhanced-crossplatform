"""Replay Kerbside's grades, streets, crossings and live sound against Python, bit for bit.

Every car the street deals, the reference's own checks on it (both
autopilot crossings and the thirteen walkers who do not listen), every
step's time and place, and windows of the run's sound -- each car's
engine, the wind, and the two notes -- must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import kerbside as model

RESULTS = {None: 0}


def same(actual, expected):
    actual = list(actual)
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        if isinstance(b, float):
            assert struct.pack("<d", float(a)) == struct.pack("<d", b), (a, b)
        else:
            assert int(a) == int(b), (a, b)


def outcome(run):
    if run.result is None:
        return 0
    won, text = run.result
    if won:
        assert text == "Across in %.1f s" % run.t, text
        return 1
    if text.startswith("Hit in lane "):
        return 2
    assert text == "Still on the street", text
    return 3


def player(run, mode, n):
    if mode == 0:
        ports = model.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    if mode == 2:
        return model.FORWARD if run.t >= 3.0 else None
    return model.FORWARD if n % 60 < 40 else model.BACK


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, g.lanes, float(g.speed), float(g.gap), float(g.electric), g.vans, float(g.wind)))
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(1, 1, 19), (2, 4, 19), (3, 10, 19)]
    steps = windows = 0
    endings = set()
    for mode, rung, seed in modes:
        draw = Random(seed)
        street = model.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "street"
        vans = list(street.vans) or [(0.0, 0.0), (0.0, 0.0)]
        same(values, [mode, rung, seed, int(values[3]), True, draw.getrandbits(32), len(street.cars), street.seconds,
                      *map(float, vans[0]), *map(float, vans[1])])
        # The street's seed is the one the reference built it from.
        again = Random(seed)
        for _ in range(200):
            fresh = again.getrandbits(32)
            if fresh == int(values[3]):
                break
        assert model._build(street.level, Random(fresh)) == street
        for car in street.cars:
            marker, *values = next(rows).split()
            assert marker == "car"
            same(values, [car.lane, car.dir, car.speed, car.at, car.electric, car.pitch])
        marker, *values = next(rows).split()
        assert marker == "checks"
        same(values, [model.play(street)[0], model.play(street, dt=1 / 60.0, sub=2)[0], model.blind(street)])
        run = model.Run(street)
        n = 0
        while run.result is None:
            port = player(run, mode, n)
            run.step(1 / 120.0, port)
            lane = int(run.result[1].split()[-1]) - 1 if run.result and run.result[1].startswith("Hit in lane ") else 0
            try:
                same(next(rows).split(), [-1 if port is None else port, outcome(run), run.t, run.y, lane])
            except AssertionError as error:
                raise AssertionError((mode, rung, n, run.t, error)) from error
            steps += 1
            n += 1
        result = outcome(run)
        endings.add(result)
        assert next(rows).split() == ["end", str(result), str(len(run.notes))]
        if mode == 0:
            assert result == 1, (rung, run.result)
        for _ in range(4):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            t = float(stamp)
            assert bytes.fromhex(next(rows)) == model.mix(run, t, t + 0.1), (mode, rung, t)
            windows += 1
    assert next(rows, None) is None
    assert endings == {1, 2, 3}, endings
    print(f"PASS: {41 + len(modes)} Kerbside cases (41 grades, {len(modes)} streets with their checks, runs ending "
          f"{sorted(endings)}), {steps} steps bit for bit, and {windows} stereo windows of live sound match Python")


if __name__ == "__main__":
    check(sys.argv[1])
