"""Compare Captcha's shared scene geometry and text with the Python source."""

import itertools
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import captcha

AREA_WIDTH, AREA_HEIGHT, AREA_TOP = 912 * 0.94, 389, 568
SCALE = min(AREA_WIDTH * 0.94 / captcha.W, AREA_HEIGHT * 0.66 / captcha.H)
X0 = (912 - captcha.W * SCALE) / 2
Y0 = AREA_TOP - captcha.H * SCALE - AREA_HEIGHT * 0.04


def packed(colour, alpha=255):
    return int.from_bytes(bytes((*colour, alpha)), "big")


def close(actual, expected):
    assert len(actual) == len(expected) and all(
        math.isclose(a, b, rel_tol=0, abs_tol=6e-5) for a, b in zip(actual, expected)
    ), (actual, expected)


def compare(binary):
    lines = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in (1, 7, 13, 20, 30):
        puzzle = captcha.deal(rung, rng=random.Random(17))
        for phase in range(4):
            frame = list(itertools.takewhile(lambda line: line != "end", lines))
            text = [line.split(" ", 8) for line in frame if line.startswith("text ")]
            assert text[0][-1] == "Captcha"
            if phase in (0, 3):
                assert [row[-1] for row in text[2:]] == [
                    "Press Space or click to start" if phase == 0 else "0 of 1 passed   highest rung passed 0"
                ]
                assert len(frame) == 3
                continue
            judged = phase == 2
            assert text[2][-1] == (captcha.check(puzzle, "A")[1] if judged else puzzle.rule)
            assert text[3][-1] == f"rung {rung}  1/1"
            glyphs = [row for row in text if float(row[7]) > 0.0]
            expected = [
                (mark.char, packed(mark.colour[:3], mark.colour[3]), mark.points[0], mark.points[1],
                 max(5, mark.points[2] * SCALE * 1.05), mark.points[3], mark.face)
                for mark in puzzle.marks if mark.kind == "stray"
            ]
            for layer in range(3):
                expected.extend(
                    (glyph.char, packed(captcha.COLOURS[glyph.colour][1]), glyph.x, glyph.y,
                     max(6, glyph.size * SCALE * 1.05), glyph.angle, glyph.face)
                    for glyph in puzzle.glyphs[layer::3]
                )
            assert len(glyphs) == len(expected)
            for row, (char, colour, x, y, size, angle, face) in zip(glyphs, expected):
                assert row[-1] == char
                assert int(row[1]) == colour
                close(list(map(float, row[2:8])), [X0 + x * SCALE, Y0 + y * SCALE, size, 0, angle, face + 1])
            bands = [line.split() for line in frame if line.startswith("paper ")]
            assert len(bands) == 16
            for index, (_, colour, *points) in enumerate(bands):
                blend = (index + 0.5) / 16
                rgb = [round(a + (b - a) * blend) for a, b in zip(*puzzle.paper)]
                assert int(colour) == packed(rgb)
                step = captcha.H * SCALE / 16
                close(list(map(float, points)), [X0, Y0 + index * step, captcha.W * SCALE, step + 1])
            rings = [list(map(float, line.split()[1:])) for line in frame if line.startswith("ring ")]
            targets = [glyph for glyph in puzzle.glyphs if glyph.real] if judged else []
            assert len(rings) == len(targets)
            for points, glyph in zip(rings, targets):
                close(points, [X0 + (glyph.x + glyph.size * 0.7) * SCALE, Y0 + glyph.y * SCALE, 3])
            assert text[-2 if judged else -1][-1] == ("A  " if judged else "A _")
            if judged:
                assert text[-1][-1] == captcha.check(puzzle, "A")[1]
                assert int(text[-1][1]) == 0xff4040ff
    assert next(lines, None) is None
    print("PASS: 20 Captcha scenes match source glyph transforms, typefaces, paper, answer rings, and lifecycle text")


if __name__ == "__main__":
    compare(sys.argv[1])
