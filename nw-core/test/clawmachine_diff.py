"""Replay Claw Machine's grades, cabinets and tries against Python, bit for bit.

Every dealt cabinet (each checked by the autopilot playing it through),
every step of a try -- the trolley and its speed, the claw's swing, how far
it has come down, how far the floor has moved and where the gold prize is
-- the verdict, the drop and the notes must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import clawmachine as model

LIVE = 0
TEXTS = ["Got it", "That is not the gold one", "Missed: too far in", "Missed: not far enough in", "Missed: to the right",
         "Missed: to the left", "Out of time"]


def rgba(colour):
    r, g, b = colour
    return (r << 24) | (g << 16) | (b << 8) | 255


def same(actual, expected):
    actual = list(actual)
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        if isinstance(b, float):
            assert struct.pack("<d", float(a)) == struct.pack("<d", b), (a, b)
        else:
            assert int(a) == int(b), (a, b)


def outcome(run):
    return LIVE if run.result is None else 1 + TEXTS.index(run.result[1])


def player(run, mode, n):
    ports = model.autopilot(run)
    auto = ports[0] if ports else -1
    if mode == 0:
        return auto
    if mode == 1:
        return -1
    if mode == 2:
        return model.DROP if n == 0 else -1
    if mode == 3:
        return (n // 30) % 4 if n < 240 else auto
    which = 0 if mode == 5 else 1
    dx = run.prize_at(run.cab.prizes[which])[0] - run.x
    dz = 0.0 if mode == 5 else run.cab.prizes[which].z - run.z
    if mode == 5 and abs(dx) <= 0.02 and run.z < model.DEEP:
        return model.IN
    if abs(dx) > 0.02:
        return model.RIGHT if dx > 0 else model.LEFT
    if abs(dz) > 0.02:
        return model.IN if dz > 0 else model.OUT
    return model.DROP


def replay(rows, rung, seed, mode, dt):
    draw = Random(seed)
    cab = model.deal(rung, rng=draw)
    marker, *values = next(rows).split()
    assert marker == "cabinet"
    same(values, [mode, rung, seed, draw.getrandbits(32), float(cab.start[0]), float(cab.start[1])])
    for p in cab.prizes:
        marker, *values = next(rows).split()
        assert marker == "prize"
        same(values, [p.x, p.z, float(p.r), rgba(p.colour)])
    if mode < 0:
        return None, 0
    run = model.Run(cab)
    n = 0
    while run.result is None:
        port = player(run, mode, n)
        if port == model.DROP:
            model.act(run, port)
        run.step(dt, None if port in (-1, model.DROP) else port)
        try:
            same(next(rows).split(), [port, outcome(run), run.t, float(run.x), float(run.z), run.vx, run.vz, run.ox, run.oz,
                                      run.wx, run.wz, run.depth, run.belt, run.prize_at(cab.prizes[0])[0]])
        except AssertionError as error:
            raise AssertionError((rung, seed, mode, n, error)) from error
        n += 1
    marker, *values = next(rows).split()
    assert marker == "end"
    same(values, [outcome(run), run.t, int(run.drop is not None), run.drop if run.drop is not None else 0.0])
    for note in run.notes:
        same(next(rows).split(), [note.seed, note.voice, note.t, float(note.freq), note.dur, note.gain])
    return outcome(run), n


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, int(g.side), int(g.shadow), float(g.swing), int(g.low), int(g.sizes), float(g.belt),
                      float(g.tol), g.prizes))
    cabinets = 0
    for rung in range(1, 21):
        for seed in range(1, 4):
            replay(rows, rung, seed, -1, 0.0)
            cabinets += 1
    for rung in (25, 30, 40):
        replay(rows, rung, 5, -1, 0.0)
        cabinets += 1
    endings = set()
    steps = tries = 0
    for rung in (1, 2, 4, 7, 8, 10, 13, 16, 20):
        for mode in (0, 2, 3):
            result, n = replay(rows, rung, 17 + mode, mode, 1 / 30.0)
            endings.add(result)
            steps += n
            tries += 1
            if mode == 0:
                assert result == 1, (rung, result)
    extra = [(1, 5, 1, 1 / 30.0)] + [(1, seed, 2, 1 / 30.0) for seed in range(1, 13)] + \
        [(1, 4, 4, 1 / 30.0), (4, 6, 4, 1 / 30.0), (1, 7, 5, 1 / 30.0), (8, 9, 0, 1 / 120.0), (14, 3, 3, 1 / 120.0)]
    for rung, seed, mode, dt in extra:
        result, n = replay(rows, rung, seed, mode, dt)
        endings.add(result)
        steps += n
        tries += 1
    assert next(rows, None) is None
    assert endings == set(range(1, 8)), endings
    print(f"PASS: 41 Claw Machine grades, {cabinets} cabinets and {tries} tries ending {sorted(endings)} over {steps} "
          f"steps, with the trolley, the swing, the drop, the belt and the notes, bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
