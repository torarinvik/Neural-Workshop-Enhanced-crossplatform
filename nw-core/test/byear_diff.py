"""Replay By Ear's grades, tunes and tries against Python, bit for bit.

Every dealt tune -- each step's keys in the order Python's frozensets give
them, the shift and the lit key -- and every step of a try, the notes and
the keys pressed must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import byear as model

LIVE, PLAYED, WRONG, APART, SLOW = range(5)


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
    if run.result[0]:
        return PLAYED
    text = run.result[1]
    return WRONG if text.startswith("A wrong") else (APART if text.startswith("Both") else SLOW)


def mask(step):
    return sum(1 << k for k in step)


def player(run, mode, n):
    ports = model.autopilot(run)
    auto = ports[0] if ports else -1
    if mode == 0:
        return auto
    if mode == 1:
        return -1
    if mode == 2:
        if auto < 0 or run.done < 1:
            return -1
        want = run.tune.want[run.done]
        return next((k for k in range(model.KEYS) if k not in want), -1)
    if mode == 3:
        return -1 if auto >= 0 and run.held else auto
    return (n * 7) % 13 if n % 25 == 0 else -1


def replay(rows, rung, seed, mode, dt):
    draw = Random(seed)
    tune = model.deal(rung, rng=draw)
    marker, *values = next(rows).split()
    assert marker == "tune"
    same(values, [mode, rung, seed, 1, draw.getrandbits(32), -1 if tune.lit is None else tune.lit])
    for want, heard in zip(tune.want, tune.heard):
        assert next(rows).split() == ["want", str(len(want)), *map(str, want)], (rung, seed)
        assert next(rows).split() == ["heard", str(len(heard)), *map(str, heard)], (rung, seed)
    if mode < 0:
        return tune, None, 0
    run = model.Run(tune)
    marker, *values = next(rows).split()
    assert marker == "begin"
    same(values, [run.listen_end, run.end])
    n = 0
    while run.result is None:
        key = player(run, mode, n)
        if key >= 0:
            model.act(run, key)
        run.step(dt)
        try:
            same(next(rows).split(), [key, outcome(run), run.t, run.done, mask(run.held), len(run.notes), len(run.pressed)])
        except AssertionError as error:
            raise AssertionError((rung, seed, mode, n, error)) from error
        n += 1
    marker, *values = next(rows).split()
    assert marker == "end"
    same(values, [outcome(run), run.done])
    for note in run.notes:
        same(next(rows).split(), [note.seed, note.voice, note.t, float(note.freq), note.dur, note.gain])
    for t, key, right in run.pressed:
        marker, *values = next(rows).split()
        assert marker == "press"
        same(values, [t, key, right])
    return tune, outcome(run), n


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, len(g.keys), g.length, float(g.note), g.shift, float(g.pairs), g.patch, *g.keys))
    tunes = pairs = shifted = 0
    for rung in range(1, 41):
        for seed in range(1, 16):
            tune, _, _ = replay(rows, rung, seed, -1, 0.0)
            tunes += 1
            pairs += sum(len(s) == 2 for s in tune.want)
            shifted += tune.lit is not None
    endings = set()
    steps = tries = 0
    for rung in (1, 2, 4, 7, 10, 13, 16, 25, 40):
        for mode in range(5):
            _, result, n = replay(rows, rung, 17 + mode, mode, 1 / 120.0)
            endings.add(result)
            steps += n
            tries += 1
            if mode == 0:
                assert result == PLAYED, (rung, result)
    for rung, seed, mode in ((13, 5, 0), (30, 9, 3)):
        _, result, n = replay(rows, rung, seed, mode, 1 / 30.0)
        endings.add(result)
        steps += n
        tries += 1
    assert next(rows, None) is None
    assert endings == {PLAYED, WRONG, APART, SLOW}, endings
    print(f"PASS: 41 By Ear grades, {tunes} tunes ({pairs} pairs, {shifted} shifted) and {tries} tries ending "
          f"{sorted(endings)} over {steps} steps bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
