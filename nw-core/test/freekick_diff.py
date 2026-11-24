"""Replay Free Kick's grades, pitches, plans and rounds against Python, bit
for bit.

Every dealt pitch, the kick its plan finds, a grid of 225 kicks judged on
each pitch with where and when they crossed, and every step of a round --
the dials, the ball along its flight, the keeper -- the verdict and the
notes must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import freekick as model

TEXTS = {"In the ring": 1, "Into the wall": 2, "Fell short": 3, "Wide of the goal": 4, "Over the bar": 5,
         "Saved": 6, "Out of time": 8}
HOW = {"wall": 0, "short": 1, "line": 2}


def same(actual, expected):
    actual = list(actual)
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        if isinstance(b, float):
            assert struct.pack("<d", float(a)) == struct.pack("<d", b), (a, b)
        else:
            assert int(a) == int(b), (a, b)


def verdict(p, k):
    """judge() as (code, miss), the miss worked out as the reference does."""
    won, text = model.judge(p, k)
    if text.startswith("In the goal, but"):
        cross = model.fly(p, k)[0]
        import math
        miss = math.hypot(cross[0] - p.ring[0], cross[1] - p.ring[1]) - p.ring[2]
        assert text == "In the goal, but %.1f m from the ring" % miss
        return 7, miss
    return TEXTS[text], 0.0


def code(result, p, k):
    if result is None:
        return 0, 0.0
    if result[1].startswith("In the goal, but"):
        return verdict(p, k)
    return TEXTS[result[1]], 0.0


def player(run, mode, n):
    if mode == 0:
        ports = model.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    if mode == 2:
        return (n // 20) % 9
    if n == 300:
        return model.KICK
    return (n // 15) % 8


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, g.guide, float(g.ring), g.wall, float(g.jump), float(g.keeper), float(g.wind),
                      float(g.side), float(g.distance)))
    modes = [(0, rung, 17) for rung in (1, 2, 3, 4, 7, 10, 13, 16, 20, 30)]
    modes += [(1, 1, 19), (2, 4, 19), (3, 10, 19), (2, 13, 23)]
    steps = kicks = 0
    endings = set()
    verdicts = set()
    for mode, rung, seed in modes:
        draw = Random(seed)
        p = model.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "pitch"
        same(values, [mode, rung, seed, True, draw.getrandbits(32), float(p.spot[0]), float(p.spot[1]), float(p.goal_x),
                      *map(float, p.ring), *map(float, p.wall), float(p.keeper), *map(float, p.wind)])
        found = model.plan(p)
        marker, *values = next(rows).split()
        assert marker == "plan"
        if found is None:
            assert values[0] == "0"
        else:
            same(values, [True, *map(float, found)])
        for aim in (-20.0, -8.0, 0.0, 8.0, 20.0):
            for lift in (0.0, 6.0, 14.0, 25.0, 40.0):
                for curl in (-14.0, 0.0, 9.0):
                    for power in (8.0, 20.0, 34.0):
                        k = model.Kick(aim, lift, curl, power)
                        v = verdict(p, k)
                        cross, how, path = model.fly(p, k, keep=True)
                        marker, *values = next(rows).split()
                        assert marker == "kick"
                        expected = [v[0], v[1], HOW[how]]
                        expected += [0.0, 0.0, 0.0] if cross is None else [float(c) for c in cross]
                        expected.append(path[-1][0])
                        try:
                            same(values, expected)
                        except AssertionError as error:
                            raise AssertionError((mode, rung, k, error)) from error
                        verdicts.add(v[0])
                        kicks += 1
        run = model.Run(p)
        n = 0
        while run.result is None:
            port = player(run, mode, n)
            if port is not None and port in model.EVENTS:
                model.act(run, port)
                held = None
            else:
                held = port
            run.step(1 / 120.0, held)
            ball = run.ball()
            expected = [-1 if port is None else port, code(run.result, p, run.kick)[0], run.t, *map(float, run.kick),
                        run.kicked is not None, 0.0 if run.kicked is None else run.kicked, *map(float, ball),
                        float(run.keeper_x())]
            values = next(rows).split()
            try:
                same(values, expected)
            except AssertionError as error:
                raise AssertionError((mode, rung, n, run.t, error)) from error
            steps += 1
            n += 1
        result, miss = code(run.result, p, run.kick)
        endings.add(result)
        marker, *values = next(rows).split()
        assert marker == "end"
        same(values, [result, miss, len(run.path or ()), len(run.notes)])
        for note in run.notes:
            same(next(rows).split(), [note.seed, note.voice, note.t, float(note.freq), note.dur, note.gain])
        if mode == 0:
            assert result == 1, (rung, run.result)
    assert next(rows, None) is None
    assert {1, 8} <= endings, endings
    assert {1, 2, 3, 4, 5, 7} <= verdicts, verdicts
    print(f"PASS: {41 + len(modes)} Free Kick cases (41 grades, {len(modes)} pitches with their plans and rounds "
          f"ending {sorted(endings)}), {kicks} judged kicks with verdicts {sorted(verdicts)}, and {steps} steps "
          "bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
