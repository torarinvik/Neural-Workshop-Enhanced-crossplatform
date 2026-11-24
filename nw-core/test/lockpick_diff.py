"""Replay Lock Pick generation, controls, and audio against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, lockpick

def close(actual, expected):
    actual = tuple(map(float, actual))
    assert len(actual) == len(expected) and all(
        isclose(a, b, abs_tol=2e-12, rel_tol=2e-12) for a, b in zip(actual, expected)
    ), (actual, expected)

def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = lockpick.grade(rung)
        close(values, (*g[:3], *g.band, *g[4:]))
    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(lockpick.PATCHES)]
    verdicts = ("", "The lock turned", "The wrench slipped once too often", "Someone is coming")
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30, 80)]
    modes += [(mode, 10 if mode == 4 else 1, 19) for mode in range(1, 5)]
    steps = cues = 0
    for mode, rung, seed in modes:
        draw = Random(seed)
        deal = lockpick.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "lock"
        close(values, (mode, rung, seed, deal.seed, True, draw.getrandbits(32)))
        for height, binding in zip(deal.heights, deal.order):
            close(next(rows).split(), (height, binding))
        run = lockpick.Run(deal)
        if mode == 3:
            run.set = 1
            run.tension = 0.55
            run.hand.down = True
            run.hand.to(lockpick.pin_x(deal.order[1]), lockpick.FLOOR + lockpick.LIFT)
        elif mode == 4:
            pin = deal.order[1]
            run.hand.down = True
            run.hand.to(lockpick.pin_x(pin), lockpick.FLOOR + lockpick.LIFT * (1 - deal.heights[pin]))
        while run.result is None:
            ports = lockpick.autopilot(run) if mode == 0 else [lockpick.TENSION] if mode == 1 else []
            port = ports[0] if ports else -1
            if 0 <= port < lockpick.TENSION:
                lockpick.act(run, port)
            run.step(1 / 60, port if port == lockpick.TENSION else None)
            result = verdicts.index(run.result[1]) if run.result else 0
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t,
                        run.tension, run.held.get(lockpick.TENSION, -1), run.set, run.slips, run.at_height,
                        -1 if run.under is None else run.under,
                        *(value for i, lift in enumerate(run.lift) for value in (lift, i in run.fooled)))
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, run.t, error)) from error
            steps += 1
        assert result == (1 if mode == 0 else 2 if mode == 1 else 3)
        if mode == 3:
            assert any(note.voice == lockpick.JAM for note in run.notes)
        if mode == 4:
            assert any(note.voice == lockpick.CLICK and note.freq == 420.0 for note in run.notes)
        assert next(rows) == f"notes {len(run.notes)}"
        for note in run.notes:
            close(next(rows).split(), (note.seed, note.voice, note.t, note.dur, note.freq, note.gain, note.pan))
            cues += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            t = float(stamp)
            assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, t, t + 0.1, patches), (rung, mode, t)
    assert next(rows, None) is None
    print(f"PASS: {81 + len(modes)} Lock Pick cases, {steps} steps, {cues} cues, and {3 * len(modes)} stereo windows match Python")

if __name__ == "__main__":
    check(sys.argv[1])
