"""Compare rendered Sign Painter shapes with the Python scene without a window."""
from math import cos, isclose, pi, sin
from pathlib import Path
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import signpainter
from neural_workshop.ui.signpainter import SignPainter
from neural_workshop.ui.handtask import SCREEN, clip_poly, clip_line


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2
BOTTOM = 179


class Scene(SignPainter):
    def __init__(self):
        self.labels = []
        self.shapes = []
        self.polygons = []

    def g(self):
        return None

    def point(self, x, y):
        return LEFT + x * SCALE, BOTTOM + y * SCALE

    def rect(self, x, y, w, h, color, group):
        w, h = min(1000, x + w) - x, min(640, y + h) - y
        if w > 0 and h > 0:
            self.shapes.append((1, rgba(color), *self.point(x, y), w * SCALE, h * SCALE))

    def disc(self, at, radius, color, group):
        if radius <= at[0] <= 1000 - radius and radius <= at[1] <= 640 - radius:
            self.shapes.append((4, rgba(color), *self.point(*at[:2]), max(1, radius * SCALE), 0))
        elif -radius <= at[0] <= 1000 + radius and -radius <= at[1] <= 640 + radius:
            self.oval(at, radius, radius, color, group, n=16)

    def line(self, start, end, width, color, group):
        if start is None or end is None:
            return
        clipped = clip_line(start[:2], end[:2], SCREEN)
        if clipped:
            self.shapes.append((6, rgba(color), *self.point(*clipped[0]), *self.point(*clipped[1])))

    def poly(self, points, color, group):
        if any(point is None for point in points):
            return
        points = clip_poly([point[:2] for point in points], SCREEN)
        if len(points) < 3:
            return
        self.polygons.append((8, rgba(color), len(points), *self.point(*points[0])))
        self.polygons.extend((9, 0, 0, *self.point(*point)) for point in points[1:])

    def oval(self, point, rx, ry, color, group, n=20):
        self.poly([
            (point[0] + rx * cos(2 * pi * k / n), point[1] + ry * sin(2 * pi * k / n))
            for k in range(n)
        ], color, group)

    def words(self, text, *args, **kwargs):
        self.labels.append(text)


def rgba(color):
    return int.from_bytes(bytes((*color, 255) if len(color) == 3 else color), "big")


def frame(rows, expected):
    marker, name, *state = next(rows).split()
    assert (marker, name) == ("frame", expected)
    shapes, polygons, labels = [], [], []
    for line in rows:
        if line == "end":
            break
        kind, *values = line.split()
        if kind == "shape":
            shapes.append(tuple(map(float, values)))
        elif kind == "poly":
            polygons.append(tuple(map(float, values)))
        else:
            labels.append(line)
    return tuple(map(int, state)), shapes, polygons, labels


def matches(actual, expected):
    return len(actual) == len(expected) and all(isclose(a, b, rel_tol=0, abs_tol=0.00015) for a, b in zip(actual, expected))


def subsequence(actual, expected, name):
    available = iter(actual)
    for wanted in expected:
        assert any(matches(item, wanted) for item in available), (name, wanted)


def compare(name, run, painted):
    sketch = Scene()
    sketch._scene(run, run.t)
    _, shapes, polygons, labels = painted
    # The host also draws the card, pointer, and session labels.
    subsequence(shapes, sketch.shapes, name)
    subsequence(polygons, sketch.polygons, name)
    assert all(text in labels for text in sketch.labels), (name, labels, sketch.labels)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    assert "Press Space or click to start" in frame(rows, "ready")[3]
    run = signpainter.Run(signpainter.deal(1, rng=Random(17)))
    compare("start", run, frame(rows, "start"))
    run.stroke, run.point = 1, 3
    compare("outline", run, frame(rows, "outline"))

    run = signpainter.Run(signpainter.deal(10, rng=Random(17)))
    run.t, run.stroke, run.point, run.paint, run.smudges = 3.25, 1, 3, 2, 1
    run.key(signpainter.RED + run.sign.colour)
    run.hand.to(*run.see(*run.sign.strokes[1][0])[:2])
    run.press()
    compare("corners", run, frame(rows, "corners"))
    run.release()
    run.key(signpainter.DIP)
    compare("dipped", run, frame(rows, "dipped"))

    run = signpainter.Run(signpainter.deal(16, rng=Random(17)))
    run.t = 1.8
    compare("unguided", run, frame(rows, "unguided"))
    won = frame(rows, "won")
    assert won[0][:4] == (2, 2, 1, 1), won[0]
    assert "A handsome sign" in won[3]
    assert frame(rows, "hold") == won
    assert "1 of 1 passed   highest rung passed 1" in frame(rows, "done")[3]
    assert next(rows, None) is None
    print("PASS: Sign Painter board, chains, three guide modes, brush, palette, paint, and smudge display match Python")
    print("PASS: 9 Sign Painter frames covering session pointer, dip, adaptive result, feedback timing, and final score")


if __name__ == "__main__":
    check(sys.argv[1])
