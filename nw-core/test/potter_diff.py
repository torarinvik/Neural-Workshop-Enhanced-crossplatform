"""Verify Potter's Wheel generation, reference play, and failure paths against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, hand, potter


def close(actual, expected):
    actual = tuple(map(float, actual))
    assert len(actual) == len(expected)
    assert all(isclose(a, b, rel_tol=2e-12, abs_tol=2e-12) for a, b in zip(actual, expected)), (actual, expected)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    ghosts = ("over", "beside", "brief")
    for rung in range(81):
        grade = list(potter.grade(rung))
        grade[5] = ghosts.index(grade[5])
        marker, *values = next(rows).split()
        assert marker == "grade"
        close(values, grade)

    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(potter.PATCHES)]
    steps = notes = 0
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 20, 35, 60)] + [(1, 1, 19), (2, 13, 19)]
    for mode, rung, seed in modes:
        draw = Random(seed)
        pot = potter.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "pot"
        close(values, (mode, rung, seed, pot.seed, draw.getrandbits(32), *pot.shape))
        run = potter.Run(pot)
        while run.result is None:
            ports = potter.autopilot(run) if mode == 0 else []
            if mode == 1 or (mode == 2 and run.t >= 10.0):
                run.hand.x = potter.AXIS
                run.hand.y = potter.band_y(pot.level.bands, 0)
                ports = [hand.PRESS]
            port = ports[0] if ports else -1
            if port >= 0:
                potter.act(run, port)
            run.step(1.0 / 60.0)
            result = 0 if run.result is None else ("A fine pot", "The pot collapsed", "The clay went hard").index(run.result[1]) + 1
            bands = tuple(value for pair in zip(run.r, run.was_near) for value in pair)
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t, run.turn,
                        run.wet, run.good_for, run.speed, -1 if run.touching is None else run.touching,
                        run.shown(), *bands)
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, steps, run.t, error)) from error
            steps += 1
        assert result == (1, 2, 3)[mode]
        assert next(rows) == f"notes {len(run.notes)}"
        for cue in run.notes:
            close(next(rows).split(), (cue.seed, cue.voice, cue.t, cue.dur, cue.freq, cue.gain))
            notes += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            start = float(stamp)
            actual = bytes.fromhex(next(rows))
            assert actual == drshape.synth(run.notes, start, start + 0.1, patches), (mode, rung, start)
    assert next(rows, None) is None
    print(f"PASS: {81 + len(modes)} cases from Potter's Wheel 81 grades, ten seeded deals, {steps} steps, {notes} cues, and 30 stereo PCM windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
