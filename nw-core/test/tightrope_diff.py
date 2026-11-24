"""Verify the Tightrope balances, weather, reference play, and sound cues against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, tightrope


def close(actual, expected):
    actual = tuple(map(float, actual))
    assert len(actual) == len(expected)
    assert all(isclose(a, b, rel_tol=2e-12, abs_tol=2e-12) for a, b in zip(actual, expected)), (actual, expected)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        close(values, tightrope.grade(rung))

    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(tightrope.PATCHES)]
    steps = notes = 0
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(mode, 1, 19) for mode in range(1, 5)]
    verdicts = ("Across", "You fell", "You fell forward", "You fell backward", "Out of time on the wire")
    for mode, rung, seed in modes:
        draw = Random(seed)
        walk = tightrope.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "walk"
        close(values, (mode, rung, seed, walk.seed, 1, draw.getrandbits(32)))
        for event in (*walk.gusts, *walk.birds):
            close(next(rows).split(), event)
        run = tightrope.Run(walk)
        if mode:
            run.hand.x = 0.0 if mode == 1 else 500.0
            run.hand.y = {2: 0.0, 3: 640.0}.get(mode, 250.0)
        while run.result is None:
            ports = tightrope.autopilot(run) if mode == 0 else []
            port = ports[0] if ports and ports[0] is not None else -1
            if port >= 0:
                tightrope.act(run, port)
            run.step(1.0 / 60.0)
            result = 0 if run.result is None else verdicts.index(run.result[1]) + 1
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t, run.lean,
                        run.rate, run.taken, run.held, run.held_f, run.pitch, run.prate,
                        run.swing, run.swing_v, run.boing, run.boing_v, run.bird_no, *run.perched)
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, run.t, error)) from error
            steps += 1
        assert result == mode + 1
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
    print(f"PASS: {81 + len(modes)} Tightrope cases across 81 grades, 13 walks, {steps} steps, {notes} notes, and 39 stereo PCM windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
