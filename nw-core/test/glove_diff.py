"""Replay Glove's grades, innings and their steps against Python, bit for bit.

Every pitch's flight and where it crosses the plate, the camera's cuts, and
every step of an inning -- the glove, the view, the ball in flight, the
screen's axes at the glove and where the glove is seen -- the verdict and
the notes must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import glove as model


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
    return 1 if run.result[0] else 2


def player(run, mode, n):
    if mode == 0:
        ports = model.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    if mode == 2:
        port = (n // 20) % 5 - 1
        return None if port < 0 else port
    return model.UP if (n // 90) % 2 == 0 else model.RIGHT


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, g.pitches, g.misses, float(g.speed), float(g.curve), float(g.cut), g.per_pitch, g.views,
                      float(g.glove), float(g.spread)))
    modes = [(0, rung, 17) for rung in (1, 2, 4, 7, 10, 13, 16, 20, 30)]
    modes += [(1, 1, 19), (2, 4, 19), (3, 10, 19), (2, 13, 23)]
    steps = points = cuts = 0
    endings = set()
    for mode, rung, seed in modes:
        draw = Random(seed)
        g = model.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "game"
        same(values, [mode, rung, seed, True, draw.getrandbits(32), float(g.seconds), len(g.cuts)])
        for p in g.pitches:
            marker, *values = next(rows).split()
            assert marker == "pitch"
            same(values, [float(p.at), len(p.path), *map(float, p.cross)])
            for point in p.path:
                same(next(rows).split(), [float(v) for v in point])
                points += 1
        for at, view in g.cuts:
            marker, *values = next(rows).split()
            assert marker == "cut"
            same(values, [float(at), view])
            cuts += 1
        run = model.Run(g)
        n = 0
        while run.result is None:
            port = player(run, mode, n)
            run.step(1 / 120.0, port)
            view = run.view()
            (rx, ry), (ux, uy) = model.axes(view, tuple(run.glove))
            seen = model._project(view, (run.glove[0], run.glove[1], 0.0))
            ball = run.ball()
            index = -1
            if ball is not None:
                index = next(k for k, p in enumerate(g.pitches) if 0 <= run.t - p.at <= p.cross[2])
            expected = [-1 if port is None else port, outcome(run), run.t, *map(float, run.glove), run.next, run.caught,
                        run.missed, view, index, *(map(float, ball) if ball is not None else (0.0, 0.0, 0.0)),
                        rx, ry, ux, uy, *seen, run.flash is not None,
                        0.0 if run.flash is None else run.flash[0], bool(run.flash and run.flash[1])]
            try:
                same(next(rows).split(), expected)
            except AssertionError as error:
                raise AssertionError((mode, rung, n, run.t, error)) from error
            steps += 1
            n += 1
        result = outcome(run)
        endings.add(result)
        marker, *values = next(rows).split()
        assert marker == "end"
        same(values, [result, run.caught, run.missed, len(run.notes)])
        for note in run.notes:
            same(next(rows).split(), [note.seed, note.voice, note.t, float(note.freq), note.dur, note.gain])
        if mode == 0:
            assert result == 1, (rung, run.result)
    assert next(rows, None) is None
    assert {1, 2} <= endings, endings
    print(f"PASS: {41 + len(modes)} Glove cases (41 grades, {len(modes)} innings ending {sorted(endings)}), "
          f"{points} flight points, {cuts} cuts and {steps} steps bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
