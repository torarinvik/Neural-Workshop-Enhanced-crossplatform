"""Compare every seeded Captcha glyph and mark with the original Python model."""

import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import captcha

RUNGS = (-2, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 19, 20, 23, 24, 27, 29, 30, 31, 100, 2**63 - 1)
KINDS = ("blob", "stray", "line", "arc", "strike")
FLAGS = {"colour": 1, "small": 2, "upside": 4}


def packed(colour):
    return int.from_bytes(bytes(colour), "big")


def compare_session(lines):
    rng = random.Random(17)
    first = captcha.deal(16, rng=rng)
    second = captcha.deal(17, rng=rng)
    restart = captcha.deal(16, rng=rng)

    expected = [
        (1, 1, 16, 1, 0, 0, 0, 0, 1, first.answer, ""),
        (1, 1, 16, 1, 100, 0, 0, 0, 1, first.answer, ""),
        (1, 1, 16, 1, 501, 0, 0, 0, 0, first.answer, "A"),
        (1, 1, 16, 1, 601, 0, 0, 0, 0, first.answer, ""),
        (1, 2, 17, 1, 1030, 1, 16, 3530, 1, first.answer, first.answer),
        (0, 2, 17, 1, 1030, 1, 16, 3530, 1, first.answer, first.answer),
        (1, 1, 17, 2, 3530, 1, 16, 3530, 0, second.answer, ""),
        (0, 1, 17, 2, 4000, 1, 16, 3530, 1, second.answer, captcha.ALPHABET[:12]),
        (1, 2, 16, 2, 4100, 1, 16, 6600, 1, second.answer, captcha.ALPHABET[:12]),
        (1, 3, 16, 2, 6600, 1, 16, 6600, 1, "", ""),
        (1, 1, 16, 1, 7000, 0, 0, 6600, 1, restart.answer, ""),
    ]
    for case in expected:
        *fields, answer, typed = case
        line = next(lines)
        received = line.split(" ", 9)
        assert tuple(map(int, received[:9])) == tuple(fields), (case, line)
        assert received[9] == f"{answer}|{typed}", (case, line)


def compare(binary):
    lines = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in RUNGS:
        for seed in range(-4, 9):
            puzzle = captcha.deal(rung, seed)
            level = puzzle.level
            rules, keep = captcha._rule(level, random.Random(seed))
            def numbers(expected):
                actual = next(lines).split()
                assert len(actual) == len(expected), (rung, seed, actual, expected)
                for token, value in zip(actual, expected):
                    if isinstance(value, float):
                        assert math.isclose(float(token), value, abs_tol=1e-12, rel_tol=0), (rung, seed, actual, expected)
                    else:
                        assert int(token) == value, (rung, seed, actual, expected)
            numbers((*level[:11], level.decoys, sum(FLAGS[rule] for rule in rules), keep,
                     *(packed(colour + (255,)) for colour in puzzle.paper), puzzle.stripes))
            assert next(lines) == puzzle.answer, (rung, seed, puzzle.answer)
            assert next(lines) == puzzle.rule, (rung, seed, puzzle.rule)
            preview = f"Rung {level.rung}: {level.length} characters."
            if level.decoys:
                preview += f"  {level.decoys} decoys."
            if level.clutter:
                preview += "  Clutter."
            assert next(lines) == preview, (rung, seed, preview)
            for glyph in puzzle.glyphs:
                char, *fields = next(lines).split()
                assert char == glyph.char, (rung, seed, char, glyph)
                for actual, expected in zip(fields[:4], glyph[1:5]):
                    assert math.isclose(float(actual), expected, abs_tol=1e-12, rel_tol=0), (rung, seed, fields, glyph)
                assert tuple(map(int, fields[4:])) == tuple(glyph[5:]), (rung, seed, fields, glyph)
            for mark in puzzle.marks:
                numbers((KINDS.index(mark.kind), mark.width, packed(mark.colour), ord(mark.char) if mark.char else 0,
                         mark.face, *mark.points))
    compare_session(lines)
    assert next(lines, None) is None
    print(f"PASS: {len(RUNGS) * 13 + 1} Captcha cases match Python (seeded puzzles and an adaptive typing session)")


if __name__ == "__main__":
    compare(sys.argv[1])
