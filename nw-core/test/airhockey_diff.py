"""Replay Air Hockey physics, camera, keeper controls, and sound against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import airhockey, drshape


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
        close(values, airhockey.grade(rung))
    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(airhockey.PATCHES)]
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(mode, 1, 19) for mode in range(1, 4)]
    steps = cues = 0
    for mode, rung, seed in modes:
        draw = Random(seed)
        game = airhockey.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "game"
        close(values, (mode, rung, seed, game.seed, True, draw.getrandbits(32), game.serve, len(game.flips)))
        for span in game.flips:
            close(next(rows).split(), span)
        run = airhockey.Run(game)
        if mode:
            run.wait = 0.0
            if mode == 3:
                run.t = game.level.seconds - 0.01
            run.puck = (0.0, 1.96) if mode == 1 else (0.25, 0.04)
            run.v = (0.0, 0.5) if mode == 1 else (0.0, -0.5)
            if mode == 1:
                run.score[0] = game.level.need - 1
            if mode == 2:
                run.score[1] = game.level.allow - 1
        while run.result is None:
            ports = airhockey.autopilot(run) if mode == 0 else []
            port = ports[0] if ports and ports[0] is not None else -1
            if 0 <= port < airhockey.LEFT:
                airhockey.act(run, port)
            run.step(1 / 60, port if port >= airhockey.LEFT else None)
            result = 0 if run.result is None else 1 if run.result[0] else 3 if run.result[1] == "Time: no winner" else 2
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t, *run.mine, *run.mine_v,
                        *run.theirs, *run.theirs_v, run.keeper, *run.score, run.wait, *run.puck, *run.v,
                        run.angle, run.clack_at, run.far_end())
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, run.t, error)) from error
            steps += 1
        assert result == (mode or 1), (mode, run.result)
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
    print(f"PASS: {81 + len(modes)} Air Hockey cases, {steps} steps, {cues} cues, and {3 * len(modes)} stereo windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
