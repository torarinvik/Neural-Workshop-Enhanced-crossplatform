"""Compare Heavier's three seeded patches and overlapping cues."""
from random import Random
import subprocess
import sys

from heavier_diff import model
from neural_workshop import drshape


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    run = model.Run(model.deal(4, seed=17))
    for voice in range(3):
        run.t = 0.125 + voice * 0.2
        run._note(0.225, 110.0 + 150.0 * voice, voice, 0.37)
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(model.PATCHES)]
    for i in range(13):
        begin = i * 0.1
        assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, begin, begin + 0.1, patches), i
    assert next(rows, None) is None
    print("PASS: 13 Heavier stereo windows matched Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
