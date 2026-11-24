"""Check The Proofreader's seeded patches and overlapping cue tails."""
from random import Random
import subprocess
import sys

from neural_workshop import drshape, hand, proofreader


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    run = hand.HandRun(2)
    for point, duration, frequency, voice, gain, pan in (
        (0.05, 0.05, 520.0, 0, 0.2, 0.0),
        (0.125, 0.08, 660.0, 1, 0.3, 0.0),
        (0.15, 0.06, 420.0, 2, 0.3, -0.75),
        (0.17, 0.08, 660.0, 3, 0.3, 0.0),
        (0.21, 0.6, 880.0, 4, 0.5, 0.0),
        (0.55, 0.5, 90.0, 5, 0.5, 0.0),
    ):
        run.t = point
        run.note(duration, frequency, voice, gain, pan)
    patches = [drshape.make_patch(name, Random(index + 1)) for index, name in enumerate(proofreader.PATCHES)]
    for i in range(15):
        begin = i * 0.1
        assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, begin, begin + 0.1, patches), i
    assert next(rows, None) is None
    print("PASS: 15 Proofreader stereo windows matched Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
