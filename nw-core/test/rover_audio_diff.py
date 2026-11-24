"""Compare Rover cues, their overlap, and silence with Python's mixer."""
from random import Random
import subprocess
import sys
from unittest.mock import patch

from rover_diff import rover
from neural_workshop import drshape


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    with patch.object(rover, "play", side_effect=[(True, ""), (False, "")]):
        ground = rover.deal(13, seed=17)
    run = rover.Run(ground)
    for index, (x, z) in enumerate(ground.flags[:2]):
        run.t = 0.125 + 0.25 * index
        run.state = rover.State(x, z, 0.0, 0.0)
        run.step(0.0)
    x, z, _ = ground.rocks[0]
    run.t = 0.625
    run.state = rover.State(x, z, 0.0, 0.0)
    run.step(0.0)
    assert run.result == (False, "Hit a rock")
    assert [note.voice for note in run.notes] == [1, 1, 2]
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(rover.PATCHES)]
    for index in range(14):
        begin = index * 0.1
        pcm = drshape.synth(run.notes, begin, begin + 0.1, patches)
        assert pcm == bytes.fromhex(next(rows)), index
    assert next(rows, None) is None
    print("PASS: 14 Rover stereo windows matched Python byte for byte")


if __name__ == "__main__":
    main(sys.argv[1])
