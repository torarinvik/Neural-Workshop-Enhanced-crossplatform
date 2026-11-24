"""Replay Cricket Hunt's grades, rooms and tries against Python, bit for bit.

Every dealt room (each checked by the autopilot playing it through), every
step of a try -- where you stand and look, what you have caught and
missed, how the first cricket is heard and whether it is aimed at -- the
verdict, where the crickets ended up, the notes, and every sound track's
settings and phases must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import crickethunt as model

LIVE, ALL_CAUGHT, OUT_OF_TIME, GRABS_AT_NOTHING = range(4)


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
        return LIVE
    ok, text = run.result
    if ok:
        return ALL_CAUGHT
    return GRABS_AT_NOTHING if text == "Three grabs at nothing" else OUT_OF_TIME


def player(run, mode, n):
    ports = model.autopilot(run)
    auto = ports[0] if ports else -1
    if mode == 0:
        return auto
    if mode == 1:
        return -1
    if mode == 2:
        return model.GRAB if n % 30 == 0 else -1
    return (n // 40) % 6 if n < 600 else auto


def replay(rows, rung, seed, mode, dt):
    draw = Random(seed)
    room = model.deal(rung, rng=draw)
    marker, *values = next(rows).split()
    assert marker == "room"
    same(values, [mode, rung, seed, draw.getrandbits(32), *room.start, room.seconds])
    for c in room.crickets:
        marker, *values = next(rows).split()
        assert marker == "cricket"
        same(values, [*c.at, *c.hop, c.pitch, c.phase])
    marker, *values = next(rows).split()
    assert marker == "furniture"
    same(values, [float(v) for piece in room.furniture for v in piece])
    if mode < 0:
        return None, 0
    run = model.Run(room)
    n = 0
    while run.result is None:
        port = player(run, mode, n)
        if port == model.GRAB:
            model.act(run, port)
        run.step(dt, None if port in (-1, model.GRAB) else port)
        try:
            same(next(rows).split(), [port, outcome(run), run.t, run.x, run.z, run.yaw, run.pitch, run.misses,
                                      sum(run.caught), len(run.hum.t), *run.heard(0), int(run.aimed(0))])
        except AssertionError as error:
            raise AssertionError((rung, seed, mode, n, error)) from error
        n += 1
    marker, *values = next(rows).split()
    assert marker == "end"
    same(values, [outcome(run), run.t])
    for c in run.where:
        marker, *values = next(rows).split()
        assert marker == "where"
        same(values, list(c))
    for note in run.notes:
        same(next(rows).split(), [note.seed, note.voice, note.t, float(note.freq), note.dur, note.gain])
    tracks = run.tracks + [run.hum]
    for track in tracks:
        assert track.t == run.hum.t
    for k in range(len(run.hum.t)):
        expected = [run.hum.t[k]]
        for track in tracks:
            expected += [track.l[k], track.r[k], track.b[k], track.ph[k]]
        try:
            same(next(rows).split(), expected)
        except AssertionError as error:
            raise AssertionError((rung, seed, mode, "setting", k, error)) from error
    return outcome(run), n


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, float(g.room), g.crickets, float(g.low), float(g.high), float(g.every), float(g.hum),
                      int(g.hop), float(g.radius)))
    rooms = 0
    for rung in (1, 2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 16, 20, 25, 30, 40):
        for seed in range(1, 4):
            replay(rows, rung, seed, -1, 0.0)
            rooms += 1
    endings = set()
    steps = tries = 0
    for rung in (1, 2, 4, 7, 8, 10, 13):
        for mode in (0, 2, 3):
            result, n = replay(rows, rung, 17 + mode, mode, 1 / 30.0)
            endings.add(result)
            steps += n
            tries += 1
            if mode == 0:
                assert result == ALL_CAUGHT, (rung, result)
    for rung, seed, mode, dt in ((1, 5, 1, 1 / 30.0), (4, 9, 0, 1 / 120.0), (20, 3, 0, 1 / 30.0)):
        result, n = replay(rows, rung, seed, mode, dt)
        endings.add(result)
        steps += n
        tries += 1
    assert next(rows, None) is None
    assert endings == {ALL_CAUGHT, OUT_OF_TIME, GRABS_AT_NOTHING}, endings
    print(f"PASS: 41 Cricket Hunt grades, {rooms} rooms and {tries} tries ending {sorted(endings)} over {steps} steps, "
          f"with how they are heard, the notes and every track's settings and phases, bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
