"""Replay Night Watch's grades, deals, play and sound against Python, bit for bit.

Every float the run keeps -- the view, the latches, each walker's place on
the floor and the time of their next step -- must match exactly, and so must
who is under the torch and who is lit.
"""
from math import hypot
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, nightwatch as model
from neural_workshop import hand as H

COLOURS = model.COLOURS + ("grey",)
KINDS = (model.THIEF, model.GUARD, model.CAT)


def same(actual, expected):
    actual = list(actual)
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        if isinstance(b, float):
            assert struct.pack("<d", float(a)) == struct.pack("<d", b), (a, b)
        elif isinstance(b, str):
            assert a == b, (a, b)
        else:
            assert int(a) == int(b), (a, b)


def outcome(run):
    if run.result is None:
        return 0
    won, text = run.result
    if won:
        return 1
    if text == "No whistle left":
        return 2
    if text.startswith("That was the "):
        return 3
    if text == "The safe is robbed":
        return 4
    assert text == "Dawn: %d of %d caught" % (run.caught, run.level.thieves), text
    return 5


def wrong(run):
    if run.result is not None:
        return None
    if run.hand.down:
        return H.RELEASE
    best = None
    for k, w in enumerate(run.night.walkers):
        if w.kind == model.THIEF:
            continue
        q = run.spot(k)
        if q is None:
            continue
        d = hypot(q[0] - run.hand.x, q[1] - run.hand.y)
        if best is None or d < best[0]:
            best = (d, k, q)
    if best is None:
        return None
    if run.under() == best[1]:
        return H.PRESS
    return H.toward(run.hand, best[2][0], best[2][1], tol=6.0)


def player(run, mode, n):
    if mode == 0:
        ports = model.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    if mode == 2:
        return (0, 0, 0, 0, 12, 13)[n % 6]
    if mode == 3:
        return wrong(run)
    if n % 3:
        return None
    return model.LEFT if (n // 30) % 2 == 0 else model.RIGHT


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, g.thieves, g.others, float(g.half), float(g.cross), float(g.beam), g.fixed, g.telling,
                      float(g.weave), g.strikes, float(g.seconds)))
    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(model.PATCHES)]
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(1, 1, 19), (2, 1, 19), (3, 4, 19), (4, 7, 19)]
    steps = cues = caught = 0
    endings = set()
    for mode, rung, seed in modes:
        draw = Random(seed)
        night = model.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "night"
        same(values, [mode, rung, seed, night.seed, True, draw.getrandbits(32), COLOURS.index(night.thief),
                      COLOURS.index(night.guard), len(night.walkers)])
        for w in night.walkers:
            marker, *values = next(rows).split()
            assert marker == "walker"
            same(values, [KINDS.index(w.kind), COLOURS.index(w.colour), w.enters, *map(float, w.start),
                          *map(float, w.goal), w.speed, w.phase])
        run = model.Run(night)
        kind = 1
        n = 0
        while run.result is None:
            port = player(run, mode, n)
            control = None
            if port is not None:
                if port in model.EVENTS:
                    model.act(run, port)
                else:
                    control = port
            run.step(1 / 60, control)
            if run.result is not None and run.result[1].startswith("That was the "):
                kind = KINDS.index(run.result[1][len("That was the "):])
            under = run.under()
            expected = [-1 if port is None else port, outcome(run), run.hand.x, run.hand.y, run.hand.down, run.t,
                        float(run.cam), run.caught, run.strikes, run.blasts, float(run.held.get(model.LEFT, -1.0)),
                        float(run.held.get(model.RIGHT, -1.0)), -1 if under is None else under, kind]
            for k in range(len(night.walkers)):
                at = run.where(k)
                expected += ["n", "n"] if at is None else [float(at[0]), float(at[1])]
                expected += [run.gone[k], float(run.step_at[k]), run.lit(k)]
            try:
                same(next(rows).split(), expected)
            except AssertionError as error:
                raise AssertionError((mode, rung, n, run.t, error)) from error
            steps += 1
            n += 1
        result = outcome(run)
        endings.add(result)
        assert next(rows).split() == ["end", str(result), str(run.caught), str(kind)]
        if mode == 0:
            assert result == 1, (rung, run.result)
        caught += run.caught
        assert next(rows) == f"notes {len(run.notes)}"
        for note in run.notes:
            same(next(rows).split(), (note.seed, note.voice, note.t, note.dur, note.freq, note.gain, note.pan))
            cues += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            t = float(stamp)
            assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, t, t + 0.1, patches), (rung, mode, t)
    assert next(rows, None) is None
    assert {1, 2, 3, 4} <= endings, endings
    print(f"PASS: {81 + len(modes)} Night Watch cases (81 grades, {len(modes)} runs ending {sorted(endings)}), "
          f"{steps} steps bit for bit, {caught} thieves caught, {cues} cues, and {3 * len(modes)} stereo windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
