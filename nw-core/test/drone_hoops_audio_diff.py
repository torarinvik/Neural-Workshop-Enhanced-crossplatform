"""Compare the seven live Drone Hoops instruments with the Python PCM mix."""
from random import Random
import subprocess
import sys

from drone_hoops_diff import dronehoops
from neural_workshop import drshape


def windows():
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(dronehoops.PATCHES)]
    for rung, guided in ((1, True), (24, True), (35, False)):
        run = dronehoops.Run(dronehoops.deal(rung, 17))
        tick = 0
        tested = set()
        while run.result is None:
            begin = run.t
            run.step(1 / 30, dronehoops.autopilot(run) if guided else dronehoops.FORWARD)
            if tick % 5 == 0:
                for note in run.notes:
                    if note.t < run.t and note.t + note.dur + patches[note.voice].release > begin:
                        tested.add(note.voice)
                yield drshape.synth(run.notes, begin, run.t, patches), tested
            tick += 1


if __name__ == "__main__":
    lines = iter(subprocess.check_output([sys.argv[1]], text=True, timeout=60).splitlines())
    voices = set()
    count = 0
    for count, (pcm, audible) in enumerate(windows(), 1):
        actual = bytes.fromhex(next(lines))
        assert actual == pcm, count
        voices |= audible
    assert next(lines, None) is None
    assert voices == set(range(7)), voices
    print(f"Drone Hoops matched {count} stereo windows byte for byte across all seven voices")
