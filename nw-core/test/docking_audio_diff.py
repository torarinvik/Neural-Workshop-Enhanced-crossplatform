"""Compare Docking contact sounds and silent drift with the original mixer."""
from random import Random
import subprocess
import sys

from docking_diff import build
from neural_workshop import docking, drshape


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(docking.PATCHES)]
    for mode in range(3):
        run = docking.Run(build(docking.grade(1), Random(17)))
        run.pos[:] = [1.0 if mode == 1 else 0.0, 0.0, -100.0 if mode == 2 else 0.0]
        run.step(0.125)
        assert len(run.notes) == (mode != 2)
        for index in range(10):
            begin = index * 0.1
            expected = drshape.synth(run.notes, begin, begin + 0.1, patches)
            actual = bytes.fromhex(next(rows))
            assert actual == expected, (mode, index, len(actual), len(expected))
    assert next(rows, None) is None
    print("PASS: 30 Docking stereo windows matched Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
