"""Compare Time It shots, analytic motion, and verdicts with Python."""
import math
import random
import struct
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, timeit  # noqa: E402


def equal(actual, expected, context):
    assert len(actual) == len(expected), context
    for got, want in zip(actual, expected):
        assert math.isclose(got, want, rel_tol=1e-13, abs_tol=1e-13), (context, got, want)


def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    count = 781
    for _ in range(count):
        rung, seed, kind, *values = next(records).split()
        context = int(rung), int(seed)
        shot = timeit.deal(*context)
        assert ("roll", "slow", "bounce", "throw")[int(kind)] == shot.kind, context
        equal(list(map(float, values)), [shot.level.window, shot.x0, shot.v,
              shot.decel, shot.wall, shot.vy, *shot.screen, shot.mark, shot.when], context)
        for _ in range(7):
            t, x, y = map(float, next(records).split())
            equal((x, y), timeit.where(shot, t), context)
        for offset in (-0.2, 0.0017, 0.2, 0.9):
            trial = timeit.Run(shot)
            trial.step(shot.when + offset)
            if offset < 0.9:
                trial.press()
            actual = next(records)
            assert actual == trial.result[1], (context, actual, trial.result)
    tested = 0
    for row in records:
        rung, seed, begin, end, data = row.split()
        shot = timeit.deal(int(rung), int(seed))
        notes = []
        t = 0.0
        while t <= shot.when:
            x, _ = timeit.where(shot, t)
            if x >= shot.screen[0]:
                break
            pan = x / timeit.W * 2 - 1
            notes.append(drshape.Note(t, 0.1, 110.0, pan, pan, 0.35, 0.35, 0.8, 0, int(t * 100), -1))
            t += 0.1
        expected = drshape.synth(notes, float(begin), float(end), [drshape.make_patch("pad", random.Random(1))])
        pcm = bytes.fromhex(data)
        assert len(pcm) == len(expected)
        for (got,), (want,) in zip(struct.iter_unpack("<h", pcm), struct.iter_unpack("<h", expected)):
            assert abs(got - want) <= 1, (rung, begin, got, want)
        tested += 1
    assert tested == 6, tested
    print(f"Time It matched {count} seeded Python shots, motion, and verdicts, plus {tested} stereo PCM windows")


if __name__ == "__main__":
    main()
