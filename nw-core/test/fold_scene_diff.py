"""Compare the display commands for Fold It to Python's layout and projection."""

from math import ceil, cos, hypot, isclose, pi, sin, sqrt
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import fold, space

WIDTH, HEIGHT = 857.28, 389.0
LEFT, BOTTOM = 27.36, 179.0
RIM = 0x22242AFF


def cards(puzzle):
    count = len(puzzle.choices)
    gap = WIDTH * 0.012
    if puzzle.kind == "opposite":
        bw = min(WIDTH * 0.3, (WIDTH - gap * (count - 1)) / count)
        left = LEFT + (WIDTH - bw * count - gap * (count - 1)) / 2
        return [(left + i * (bw + gap), BOTTOM, bw, HEIGHT * 0.13) for i in range(count)]
    cols = 2 if count <= 4 else 3
    net_width = WIDTH * 0.38
    rows = ceil(count / cols)
    cw = (WIDTH - net_width - gap * 2 - gap * (cols - 1)) / cols
    ch = (HEIGHT - gap * (rows - 1)) / rows
    side = min(cw, ch)
    return [(LEFT + net_width + 2 * gap + col * (cw + gap) + (cw - side) / 2,
             BOTTOM + HEIGHT - (row + 1) * ch - row * gap + (ch - side) / 2,
             side, side) for row, col in (divmod(i, cols) for i in range(count))]


def expected_net(puzzle):
    opposite = puzzle.kind == "opposite"
    width = WIDTH if opposite else WIDTH * 0.38
    height = HEIGHT * 0.84 if opposite else HEIGHT
    bottom = BOTTOM + HEIGHT * 0.16 if opposite else BOTTOM
    cols = max(x for x, _ in puzzle.net) + 1
    rows = max(y for _, y in puzzle.net) + 1
    cell = min(width / (cols + 0.4), height / (rows + 0.4))
    x0 = LEFT + (width - cols * cell) / 2
    y0 = bottom + (height - rows * cell) / 2
    inset = max(1.5, cell * 0.02) / sqrt(2)
    ink = packed(fold.INK)
    rects, marks = [], []
    for (col, row), (name, colour, quarter) in zip(puzzle.net, puzzle.marks):
        x, y = x0 + col * cell, y0 + row * cell
        rects.append((RIM, (x, y, cell, cell)))
        rects.append((packed(colour), (x + inset, y + inset, cell - 2 * inset, cell - 2 * inset)))
        ca, sa = cos(pi / 2 * quarter), sin(pi / 2 * quarter)
        for part in fold.GLYPHS[name].parts:
            points = tuple((x + cell / 2 + cell * 0.36 * (a * ca - b * sa),
                            y + cell / 2 + cell * 0.36 * (a * sa + b * ca))
                           for a, b in part)
            marks.append((ink, points))
    return rects, marks


def packed(colour):
    r, g, b = colour
    return (r << 24) | (g << 16) | (b << 8) | 255


def near(actual, expected):
    return len(actual) == len(expected) and all(isclose(a, b, abs_tol=0.0001)
                                               for a, b in zip(actual, expected))


def near_polygon(actual, expected):
    return len(actual) == len(expected) and all(near(a, b) for a, b in zip(actual, expected))


def expected_polygons(puzzle, boxes):
    for (cube, turn), (x, y, side, _) in zip(puzzle.cubes, boxes):
        # The six base faces come first. Raised glyphs follow with a depth bias.
        faces = fold.cube_faces(dict(cube), turn)
        # Face marks also receive a rim in the Python renderer.
        for painted in space.render(faces, fold.camera()):
            points = tuple((x + side / 2 + a * side * 0.4, y + side / 2 + b * side * 0.4)
                           for a, b in painted.points)
            colour = packed(painted.colour)
            cx = sum(a for a, _ in points) / len(points)
            cy = sum(b for _, b in points) / len(points)
            rim = max(1.5, side * 0.008)
            inner = []
            for a, b in points:
                length = hypot(a - cx, b - cy)
                fraction = max(0.0, (length - rim) / length) if length else 0.0
                inner.append((cx + (a - cx) * fraction, cy + (b - cy) * fraction))
            yield RIM, points
            yield colour, tuple(inner)


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in (1, 4, 11, 17, 26):
        puzzle = fold.deal(rung, rng=Random(17))
        boxes = cards(puzzle)
        net_rects, net_marks = expected_net(puzzle)
        for dark in (0, 1):
            for wrong in (0, 1):
                assert next(rows) == f"frame {rung} {dark} {wrong} 6"
                assert [next(rows) for _ in boxes] == [f"hit {i}" for i in range(len(boxes))]
                labels, outlines, rectangles, polygons = [], [], [], []
                while (row := next(rows)) != "end":
                    kind, *fields = row.split(maxsplit=2)
                    if kind == "text":
                        labels.append((int(fields[0]), fields[1]))
                    elif kind == "box":
                        outlines.append((int(fields[0]), tuple(map(float, fields[1].split()))))
                    elif kind == "rect":
                        rectangles.append((int(fields[0]), tuple(map(float, fields[1].split()))))
                    else:
                        assert kind == "poly"
                        polygons.append((int(fields[0]), tuple(tuple(map(float, next(rows).split()[1:]))
                                                              for _ in range(int(fields[1])))))
                assert len(rectangles) == len(net_rects) + len(boxes)
                for (colour, dimensions), (expected, target) in zip(rectangles, net_rects):
                    assert colour == expected and near(dimensions, target)
                expected_shapes = [*net_marks, *expected_polygons(puzzle, boxes)]
                assert len(polygons) == len(expected_shapes)
                for (colour, actual), (expected, target) in zip(polygons, expected_shapes):
                    assert colour == expected and near_polygon(actual, target), (rung, actual, target)
                assert len(outlines) == len(boxes)
                for i, ((colour, (*dimensions, thickness)), box) in enumerate(zip(outlines, boxes)):
                    assert near(dimensions, box)
                    marked = wrong and i in (puzzle.answer, (puzzle.answer + 1) % len(boxes))
                    assert thickness == (5 if marked else 2)
                    expected = (0x3CAA5AFF if i == puzzle.answer else 0xD6403AFF) if marked else (
                        0xFFFFFFFF if dark else 0xFF)
                    assert colour == expected
                texts = {value for _, value in labels}
                assert "Fold It" in texts
                assert (f"No: {puzzle.choices[puzzle.answer]}" if wrong else puzzle.question) in texts
                if wrong:
                    assert (0xFF4040FF, f"No: {puzzle.choices[puzzle.answer]}") in labels
                if puzzle.kind == "opposite":
                    assert set(fold.LETTERS) <= texts
                else:
                    assert {str(i + 1) for i in range(len(boxes))} <= texts
    assert next(rows, None) is None
    print("PASS: 20 Fold It scene frames with Python net and card layout, cube and glyph projection, answer hit tests, and verdicts")


if __name__ == "__main__":
    compare(sys.argv[1])
