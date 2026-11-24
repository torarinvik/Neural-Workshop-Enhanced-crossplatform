"""Compare Sign Painter boards, simulation events, and stereo PCM with Python."""
from itertools import accumulate
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, hand, signpainter


def close(actual, expected):
    actual, expected = tuple(map(float, actual)), tuple(expected)
    assert len(actual) == len(expected), (actual, expected)
    assert all(isclose(a, b, rel_tol=2e-12, abs_tol=2e-12) for a, b in zip(actual, expected)), (actual, expected)


def layout(rows, sign):
    word, *values = next(rows).split()
    assert word == sign.word, (word, sign.word)
    lengths = [len(stroke) for stroke in sign.strokes]
    close(values, (sign.colour, sign.seconds, sign.seed, sum(lengths), len(lengths), len(sign.corners)))
    close(next(rows).split(), accumulate(lengths))
    for stroke in sign.strokes:
        for point in stroke:
            close(next(rows).split(), point)
    for corner in sign.corners:
        close(next(rows).split(), corner)


def control(run, mode, tick):
    if mode == 1:
        if tick == 0:
            return signpainter.RED + (run.sign.colour + 1) % 4
        return hand.PRESS if tick % 2 else hand.RELEASE
    if mode == 2:
        run.hand.to(*run.see(*run.sign.strokes[0][0])[:2] if tick == 0 else (480.0, 285.0))
        return hand.PRESS if tick % 2 == 0 else hand.RELEASE
    if mode == 3:
        return hand.PRESS if tick == 0 else -1
    ports = signpainter.autopilot(run)
    return ports[0] if ports and ports[0] is not None else -1


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    guides = ("outline", "corners", "none")
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = signpainter.grade(rung)
        close(values, (*g[:4], guides.index(g.guide), *g[5:]))

    words = set()
    for rung in (1, 10, 16):
        for seed in range(64):
            sign = signpainter.build(signpainter.grade(rung), Random(seed))
            layout(rows, sign)
            words.add(sign.word)
    assert words == set().union(*signpainter.WORDS)

    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(signpainter.PATCHES)]
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(1, 4, 17), (2, 1, 17), (3, 7, 17)]
    verdicts = ("A handsome sign", "The sign is a mess", "That was the wrong colour", "The paint dried on the brush")
    outcomes = (1, 3, 2, 4)
    steps = notes = 0
    for mode, rung, seed in modes:
        draw = Random(seed)
        sign = signpainter.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "sign"
        close(values, (mode, rung, seed, 1, draw.getrandbits(32)))
        layout(rows, sign)
        run = signpainter.Run(sign)
        tick = 0
        while run.result is None:
            port = control(run, mode, tick)
            if port >= 0:
                signpainter.act(run, port)
            run.step(1.0 / 60.0)
            result = 0 if run.result is None else verdicts.index(run.result[1]) + 1
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t, run.stroke,
                        run.point, run.colour, run.paint, run.smudges, run.smudged_now,
                        run.brush is not None, *(run.brush or ()))
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, tick, error)) from error
            tick += 1
        steps += tick
        assert result == outcomes[mode], (mode, run.result)
        assert next(rows) == f"notes {len(run.notes)}"
        for cue in run.notes:
            close(next(rows).split(), (cue.seed, cue.voice, cue.t, cue.dur, cue.freq, cue.gain, cue.pan))
            notes += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            start = float(stamp)
            assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, start, start + 0.1, patches), (mode, rung, start)
    assert next(rows, None) is None
    print(f"PASS: {81 + 3 * 64 + len(modes)} Sign Painter cases across 81 grades, {len(words)} words, {steps} steps, {notes} cues, and 36 stereo PCM windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
