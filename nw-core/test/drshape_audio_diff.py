"""Verify Dr Shape's seeded instruments and stereo PCM against Python."""
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape

NAMES = drshape.ALL + ("hiss",)
WINDOWS = ((0.0, 0.18, 22050), (0.18, 0.32, 22050), (0.32, 0.53, 16000))
NOTES = (
    drshape.Note(0.045, 0.19, 371.0, -0.63, 0.37, 0.58, 0.9, 0.71, 0, 19, 1, 0.8),
    drshape.Note(0.09, 0.14, 1800.0, 0.7, 0.27, 0.71, 0.12, 0.41, 1, 867, 2),
)


def floats(row, expected, where, tolerance=1e-14):
    assert len(row) == len(expected) and all(
        math.isclose(float(a), b, rel_tol=0, abs_tol=tolerance)
        for a, b in zip(row, expected)
    ), (where, row, expected)


def check_patch(lines, patch, where):
    row = next(lines).split()
    assert tuple(map(int, row[:3])) == (NAMES.index(patch.name), len(patch.partials), len(patch.taps)), where
    floats(row[3:], (patch.attack, patch.decay, patch.sustain, patch.release,
        *patch.fm, *patch.vibrato, *patch.tremolo, *patch.glide,
        patch.noise, patch.drive, patch.fold, *patch.ring), where)
    for values in (*patch.partials, *patch.taps):
        floats(next(lines).split(), values, where)


def compare(binary):
    with subprocess.Popen([binary], stdout=subprocess.PIPE, text=True) as process:
        lines = iter(process.stdout)
        for index, name in enumerate(NAMES):
            for variant in range(3):
                rng = random.Random(17 + variant * 111 + index)
                wild = variant * 0.5
                patches = [
                    drshape.make_patch(name, rng, wild),
                    drshape.make_patch(NAMES[(index + 5) % 18], rng, wild),
                ]
                where = (name, variant)
                for patch in patches:
                    check_patch(lines, patch, where)
                for begin, end, rate in WINDOWS:
                    actual = bytes.fromhex(next(lines))
                    expected = drshape.synth(NOTES, begin, end, patches, rate)
                    first_error = next((i for i, pair in enumerate(zip(actual, expected))
                                        if pair[0] != pair[1]), None)
                    assert actual == expected, (where, begin, end, rate, len(actual), len(expected), first_error)
        for rung in range(1, 33):
            rng = random.Random(rung * 17)
            level = drshape.grade(rung)
            patches = drshape._patches(level, rng)
            if level.overload:
                drshape._noise_for(level, rng, patches, 0.0)
            assert int(next(lines)) == len(patches), rung
            for patch in patches:
                check_patch(lines, patch, rung)
        cases = [(rung, rung * 13, None) for rung in range(1, 34)]
        cases.extend((30, 17, mode) for mode in drshape.MODES)
        cases.extend(((30, -(2**63), None), (30, 2**63 - 1, None)))
        for rung, seed, mode in cases:
            where = (rung, seed, mode)
            puzzle = drshape.deal(rung, seed, mode=mode)
            spans = puzzle.parts if puzzle.scene else puzzle.spans
            row = next(lines).split()
            assert tuple(map(int, row[:3])) == (
                drshape.MODES.index(puzzle.mode), len(puzzle.candidates), puzzle.answer
            ), where
            floats(row[3:5], (puzzle.show_end, puzzle.choose), where, 1e-12)
            assert tuple(map(int, row[5:])) == (len(spans), len(puzzle.notes)), where
            assert tuple(map(int, next(lines).split())) == puzzle.hues, where
            floats(next(lines).split(), puzzle.drawn_by, where, 1e-12)
            for span in spans:
                floats(next(lines).split(), span, where, 1e-12)
            for patch in puzzle.patches:
                check_patch(lines, patch, where)
            for note in puzzle.notes:
                floats(next(lines).split(), note, where, 1e-12)
            if rung == 30:
                actual = bytes.fromhex(next(lines))
                expected = drshape.synth(puzzle.notes, 0.4, 0.49, puzzle.patches)
                assert actual == expected, where
        assert next(lines, None) is None
        assert process.wait() == 0
    print("PASS: all 18 instruments, 32 instrument banks, 41 assembled puzzles, and 171 byte-exact Dr Shape stereo windows")


if __name__ == "__main__":
    compare(sys.argv[1])
