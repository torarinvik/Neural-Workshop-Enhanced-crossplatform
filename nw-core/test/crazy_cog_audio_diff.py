"""Compare seeded Crazy Cog patches and overlapping cue tails with Python."""
from random import Random
import subprocess
import sys

from neural_workshop import crazycog, drshape, hand


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    run = hand.HandRun(2)
    for time, duration, frequency, voice, gain, pan in (
        (0.05, 0.05, 900.0, crazycog.TICK, 0.3, 0.6),
        (0.09, 0.15, 90.0, crazycog.CLUNK, 0.4, 0.0),
        (0.28, 0.45, 140.0, crazycog.HUM, 0.3, -0.6),
        (0.42, 0.3, 55.0, crazycog.GRIND, 0.45, -0.6),
        (0.53, 0.6, 880.0, crazycog.DONE, 0.5, 0.0),
        (0.6, 0.45, 280.0, crazycog.MISS, 0.2, 0.4),
    ):
        run.t = time
        run.note(duration, frequency, voice, gain, pan)
    patches = [drshape.make_patch(name, Random(index + 1)) for index, name in enumerate(crazycog.PATCHES)]
    for i in range(15):
        begin = i * 0.1
        assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, begin, begin + 0.1, patches), i
    assert next(rows, None) is None
    print("PASS: 15 Crazy Cog stereo windows match Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
