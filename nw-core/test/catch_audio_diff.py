"""Check Catch's panned pop, whistle and thud against the Python synthesizer."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import catch, drshape


def windows():
    patches = [drshape.make_patch(name, Random(index + 1)) for index, name in enumerate(catch.PATCHES)]
    for rung in range(1, 26, 6):
        notes = catch.sounds(catch.deal(rung, 17))
        for index in range(160):
            begin = index * 0.117
            yield drshape.synth(notes, begin, begin + 0.093, patches)


if __name__ == "__main__":
    encoded = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    expected = list(windows())
    assert len(encoded) == len(expected)
    for index, (line, pcm) in enumerate(zip(encoded, expected)):
        assert bytes.fromhex(line) == pcm, index
    print(f"Catch matched {len(expected)} Python stereo PCM windows byte for byte")
