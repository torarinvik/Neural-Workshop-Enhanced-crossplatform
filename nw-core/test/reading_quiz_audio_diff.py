"""Compare seeded quiz patches and overlapping cue tails with Python."""
from random import Random
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, feelings, hand


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    run = hand.HandRun(2)
    for time, duration, frequency, voice, gain in (
        (0.05, 0.05, 720.0, feelings.TICK, 0.2),
        (0.09, 0.3, 880.0, feelings.RIGHT, 0.4),
        (0.28, 0.35, 180.0, feelings.WRONG, 0.4),
        (0.42, 0.6, 1320.0, feelings.DONE, 0.5),
        (0.53, 0.5, 90.0, feelings.MISS, 0.5),
    ):
        run.t = time
        run.note(duration, frequency, voice, gain)
    patches = [drshape.make_patch(name, Random(index + 1)) for index, name in enumerate(feelings.PATCHES)]
    for i in range(15):
        begin = i * 0.1
        assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, begin, begin + 0.1, patches), i
    assert next(rows, None) is None
    print("PASS: 15 reading quiz stereo windows match Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
