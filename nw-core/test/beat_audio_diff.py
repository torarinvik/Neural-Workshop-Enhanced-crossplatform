"""Compare metronome PCM windows to the original instrument synthesis."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import beat, drshape


def expected_windows():
    patches = [drshape.make_patch(name, Random(1)) for name in ("glass", "wood")]
    for rung in range(15, 18):
        song = beat.deal(rung, 17)
        notes = []
        for index, (onset, heard) in enumerate(zip(song.beats, song.heard)):
            if heard:
                first = index % len(song.level.pattern) == 0
                frequency, gain, voice = (880.0, 0.9, 0) if first else (660.0, 0.7, 1)
                notes.append(drshape.Note(onset, 0.08, frequency, 0.0, 0.0,
                                          gain, gain, 0.8, voice, index, -1, 0.0))
        for onset in song.beats:
            for begin in (onset - 0.024, onset + 0.012):
                yield drshape.synth(notes, begin, begin + 0.093, patches)


if __name__ == "__main__":
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    expected = list(expected_windows())
    assert len(actual) == len(expected)
    for index, (encoded, pcm) in enumerate(zip(actual, expected)):
        assert bytes.fromhex(encoded) == pcm, index
    print(f"Keep the Beat matched {len(expected)} Python PCM windows byte for byte")
