"""Replay Steadicam's grades, parks and takes against Python, bit for bit.

Every walker's path, the trees and the cues the park deals, and every
step's camera -- its yaw, pitch and field of view and how fast they move
-- what it has framed and counted, where the subject sits in the frame,
and whom it follows, must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import steadicam as model


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
    if text == "Lost them for 3 seconds":
        assert not won
        return 3
    share = run.framed / max(1e-6, run.counted)
    assert text == "Framed %d%% of the time, %d%% needed" % (round(100 * share), round(100 * run.level.need)), text
    return 1 if won else 2


def player(run, mode, n):
    if mode == 0:
        ports = model.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    if mode == 2:
        return model.PAN_R
    if mode == 3:
        return (model.TILT_U, model.ZOOM_IN, model.TILT_D, model.ZOOM_OUT)[(n // 40) % 4]
    port = (n // 25) % 7 - 1
    return None if port < 0 else port


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, float(g.speed), float(g.wind), float(g.near), float(g.box), float(g.size[0]),
                      float(g.size[1]), g.heavy, g.moods, g.lead, g.people, float(g.cue), float(g.seconds), float(g.need)))
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(1, 1, 19), (2, 4, 19), (3, 10, 19), (4, 16, 19)]
    steps = points = 0
    endings = set()
    for mode, rung, seed in modes:
        draw = Random(seed)
        park = model.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "park"
        same(values, [mode, rung, seed, True, draw.getrandbits(32), len(park.cues), *map(float, park.start)])
        for w in park.walkers:
            assert next(rows) == f"walker {len(w.points)}"
            for (x, z), p in zip(w.points, w.pace):
                same(next(rows).split(), [x, z, float(p)])
                points += 1
        for tree in park.trees:
            marker, *values = next(rows).split()
            assert marker == "tree"
            same(values, list(tree))
        for at, who in park.cues:
            marker, *values = next(rows).split()
            assert marker == "cue"
            same(values, [float(at), who])
        run = model.Run(park)
        n = 0
        while run.result is None:
            port = player(run, mode, n)
            run.step(1 / 120.0, port)
            ux, uy, tall = run.place()
            expected = [-1 if port is None else port, outcome(run), run.t, run.yaw, run.pitch, run.fov, run.vyaw,
                        run.vpitch, run.framed, run.counted, -1.0 if run.lost_since is None else run.lost_since,
                        run.in_frame(), run.whom(), run.lost_since is not None, ux, uy, tall, run.motion()]
            try:
                same(next(rows).split(), expected)
            except AssertionError as error:
                raise AssertionError((mode, rung, n, run.t, error)) from error
            steps += 1
            n += 1
        result = outcome(run)
        endings.add(result)
        share = run.framed / max(1e-6, run.counted)
        marker, *values = next(rows).split()
        assert marker == "end"
        same(values, [result, len(run.notes), share])
        for note in run.notes:
            same(next(rows).split(), [note.seed, note.voice, note.t])
        if mode == 0:
            assert result == 1, (rung, run.result)
    assert next(rows, None) is None
    assert {1, 3} <= endings, endings
    print(f"PASS: {41 + len(modes)} Steadicam cases (41 grades, {len(modes)} parks and takes ending {sorted(endings)}), "
          f"{points} path points and {steps} steps bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
