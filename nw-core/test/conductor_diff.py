"""Verify Conductor's timing, cue actions, verdicts, and note events against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import conductor, drshape


def close(actual, expected):
    actual = tuple(map(float, actual))
    assert len(actual) == len(expected)
    assert all(isclose(a, b, rel_tol=2e-12, abs_tol=2e-12) for a, b in zip(actual, expected)), (actual, expected)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(81):
        grade = list(conductor.grade(rung))
        del grade[5]
        grade[5] = ("all", "bars", "start").index(grade[5])
        marker, *values = next(rows).split()
        assert marker == "grade"
        close(values, grade)

    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(conductor.PATCHES)]
    steps = notes = 0
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 45, 60)] + [(1, 4, 19), (2, 20, 19)]
    for mode, rung, seed in modes:
        draw = Random(seed)
        piece = conductor.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "piece"
        close(values, (mode, rung, seed, piece.seed, piece.key, draw.getrandbits(32)))
        close(next(rows).split(), piece.times)
        for cue in piece.cues:
            close(next(rows).split(), (cue.beat, ("enter", "cut", "loud", "soft").index(cue.kind), cue.section))
        run = conductor.Run(piece)
        while run.result is None:
            ports = conductor.autopilot(run) if mode == 0 else ([conductor.SOFTER] if mode == 2 else [])
            port = ports[0] if ports else -1
            if port >= 0:
                conductor.act(run, port)
            run.step(1.0 / 60.0)
            result = 0 if run.result is None else (1 if run.result[0] else 2)
            flags = sum(1 << i for i, playing in enumerate(run.playing) if playing)
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t, run.fall,
                        run.flash, run.loud, run.slips, run.next, run.judged, flags, int(run.shown_beat() or 0))
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, run.t, error)) from error
            steps += 1
        assert result == (1 if mode == 0 else 2)
        assert next(rows) == f"notes {len(run.notes)}"
        for cue in run.notes:
            close(next(rows).split(), (cue.seed, cue.voice, cue.t, cue.dur, cue.freq, cue.gain, cue.pan))
            notes += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            start = float(stamp)
            actual = bytes.fromhex(next(rows))
            assert actual == drshape.synth(run.notes, start, start + 0.1, patches), (mode, rung, start)
    assert next(rows, None) is None
    print(f"PASS: {81 + len(modes)} cases from Conductor 81 grades, eleven pieces, {steps} steps, {notes} notes, and 33 stereo PCM windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
