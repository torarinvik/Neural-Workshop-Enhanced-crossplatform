"""Compare Unicycle finish and fall cues and silent timeout with the original mixer."""
from random import Random
import subprocess
import sys

from unicycle_diff import unicycle
from neural_workshop import drshape


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(unicycle.PATCHES)]
    for mode in range(3):
        track = unicycle.deal(1, seed=17)
        run = unicycle.Run(track)
        run.t = 0.125
        if mode == 0:
            run.body = run.body._replace(px=track.finish, qx=track.finish)
        elif mode == 1:
            run.body = run.body._replace(qy=0.1)
        else:
            run.t = track.seconds + 0.125
        run.step(0)
        assert len(run.notes) == (mode != 2)
        for index in range(10):
            begin = index * 0.1
            expected = drshape.synth(run.notes, begin, begin + 0.1, patches)
            actual = bytes.fromhex(next(rows))
            assert actual == expected, (mode, index, len(actual), len(expected))
    assert next(rows, None) is None
    print("PASS: 30 Unicycle stereo windows matched Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
