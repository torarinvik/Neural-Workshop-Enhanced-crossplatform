#!/usr/bin/env python3
"""Compare Hold It audio windows with the Python synthesizer."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, holdit


def notes_for(ask):
    notes = []

    def note(time, duration, frequency, pan, gain, voice, seed):
        notes.append(drshape.Note(time, duration, frequency, pan, pan, gain, gain, 0.8, voice, seed, -1, 0.0))

    for k, (on, off) in enumerate(ask.lamps):
        note(on, off - on, 330 + 110 * k, -0.3 + 0.6 * k, 0.5, 0, k)
    if ask.tick:
        time = 0.3
        while time < ask.turn + holdit.WAIT + 6:
            note(time, 0.04, 1400, 0.6, 0.35, 1, int(time * 100))
            time += ask.tick
    return notes


def expected_windows():
    patches = [drshape.make_patch(name, Random(1)) for name in ("organ", "wood")]
    for scenario, rung in enumerate((1, 7, 10, 13, 25)):
        ask = holdit.deal(rung, scenario - 2)
        notes = notes_for(ask)
        for window in range(80):
            begin = window * 0.117
            yield drshape.synth(notes, begin, begin + 0.117, patches)


if __name__ == "__main__":
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    expected = list(expected_windows())
    assert len(actual) == len(expected)
    for index, (encoded, pcm) in enumerate(zip(actual, expected)):
        assert bytes.fromhex(encoded) == pcm, index
    print(f"PASS: {len(expected)} stereo PCM windows exactly match Python")
