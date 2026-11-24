"""Replay Shadow Puppets' cube turns, shapes, grades, deals, play and sound against Python.

The figure's matrix, its distance from the fit, and every clock value must
match bit for bit: the turns compound for thousands of steps, and the
reference sums with Python's compensated float sum, so a last-bit slip
would grow into a different run.
"""
from math import isclose
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, shadowpuppets as model

NAMES = sorted(model.SHAPES)
SHOWN = {"wall": 0, "card": 1, "named": 2}
SCRIPT = (12, 3, 3, 0, 14, 14, 4, 1, 15, 13, 9, 6)


def mask(cells):
    return sum(1 << ((x + 2) * 5 + (y + 2)) for x, y in cells)


def same(actual, expected):
    """Exact: floats by their bits, the rest by value."""
    actual = list(actual)
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        if isinstance(b, float):
            assert struct.pack("<d", float(a)) == struct.pack("<d", b), (a, b)
        else:
            assert int(a) == int(b), (a, b)


def flat(m):
    return [float(v) for row in m for v in row]


def player(run, mode, step):
    if mode == 0:
        ports = model.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    return SCRIPT[step % len(SCRIPT)]


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for q in model.SQUARE:
        marker, *values = next(rows).split()
        assert marker == "square"
        same(values, flat(q))
    marker, *values = next(rows).split()
    assert marker == "cells"
    same(values, [mask(model.cells(n)) for n in NAMES])
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, g.flat, g.shadows, float(g.near), SHOWN[g.shown], g.tone, g.hidden, float(g.seconds)))
    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(model.PATCHES)]
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)] + [(1, 1, 19), (2, 4, 19)]
    steps = cues = cast = 0
    for mode, rung, seed in modes:
        draw = Random(seed)
        puppet = model.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "puppet"
        expected = [mode, rung, seed, puppet.seed, True, draw.getrandbits(32), NAMES.index(puppet.front),
                    NAMES.index(puppet.side), len(puppet.wanted)] + flat(puppet.start)
        for wanted, name in zip(puppet.wanted, puppet.names):
            expected += [mask(wanted), NAMES.index(name) if name else -1]
        same(values, expected)
        run = model.Run(puppet)
        n = 0
        while run.result is None:
            port = player(run, mode, n)
            if port is not None:
                model.act(run, port)
            run.step(1 / 60)
            result = 0 if run.result is None else 1 if run.result[0] else 2
            try:
                same(next(rows).split(), [-1 if port is None else port, result, run.hand.x, run.hand.y,
                                          run.hand.down, run.t, run.at, run.stay, run.tone_at, run.off()] + flat(run.m))
            except AssertionError as error:
                raise AssertionError((mode, rung, n, run.t, error)) from error
            steps += 1
            n += 1
        assert next(rows).split() == ["end", str(result), str(run.at)]
        assert result == (1 if mode == 0 else 2), (mode, rung, run.result)
        if mode == 0:
            assert run.result[1] == "Every shadow cast"
        else:
            assert run.result[1] == "Time: %d of %d cast" % (run.at, len(run.fits)), run.result
        cast += run.at
        assert next(rows) == f"notes {len(run.notes)}"
        for note in run.notes:
            values = next(rows).split()
            assert all(isclose(float(a), b, rel_tol=0, abs_tol=0) for a, b in
                       zip(values, (note.seed, note.voice, note.t, note.dur, note.freq, note.gain, note.pan))), (values, note)
            cues += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            t = float(stamp)
            assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, t, t + 0.1, patches), (rung, mode, t)
    assert next(rows, None) is None
    print(f"PASS: {106 + len(modes)} Shadow Puppets cases (24 cube turns, the shapes, 81 grades, {len(modes)} runs), "
          f"{steps} steps bit for bit, {cast} shadows cast, {cues} cues, and {3 * len(modes)} stereo windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
