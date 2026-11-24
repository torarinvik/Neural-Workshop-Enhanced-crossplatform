"""Compare rendered Conductor shapes with the Python scene without a window."""
from math import ceil, isclose
from pathlib import Path
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import conductor, hand
from neural_workshop.ui.conductor import Conductor
from neural_workshop.ui.handtask import SCREEN, clip_poly, clip_line


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2
BOTTOM = 179


class Scene(Conductor):
    def __init__(self):
        self.labels = []
        self.shapes = []
        self.polygons = []

    def g(self):
        return None

    def point(self, x, y):
        return LEFT + x * SCALE, BOTTOM + y * SCALE

    def rect(self, x, y, w, h, color, group):
        if w > 0 and h > 0:
            self.shapes.append((1, rgba(color), *self.point(x, y), w * SCALE, h * SCALE))

    def disc(self, at, radius, color, group):
        self.shapes.append((4, rgba(color), *self.point(*at), radius * SCALE, 0))

    def line(self, start, end, width, color, group):
        clipped = clip_line(start, end, SCREEN)
        if clipped:
            self.shapes.append((6, rgba(color), *self.point(*clipped[0]), *self.point(*clipped[1])))

    def poly(self, points, color, group):
        points = clip_poly([point[:2] for point in points], SCREEN)
        if len(points) < 3:
            return
        self.polygons.append((8, rgba(color), len(points), *self.point(*points[0])))
        self.polygons.extend((9, 0, 0, *self.point(*point)) for point in points[1:])

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
    subsequence(shapes, sketch.shapes, name)
    # Card shadows and pointer are shared workshop chrome.
    subsequence(polygons, sketch.polygons, name)
    assert all(text in labels for text in sketch.labels), (name, labels, sketch.labels)
    assert [text for text in labels if text.startswith("Beat ") and text[5:6].isdigit()] == [
        text for text in sketch.labels if text.startswith("Beat ") and text[5:6].isdigit()
    ]


def advance(run, now, previous):
    dt = min(0.1, now - previous)
    steps = max(1, ceil(dt / (1 / 120.0)))
    for _ in range(steps):
        run.step(dt / steps)


def check(binary):
    lines = subprocess.check_output([binary], text=True).splitlines()
    rows = iter(lines)
    assert "Press Space or click to start" in frame(rows, "ready")[3]
    run = conductor.Run(conductor.deal(1, rng=Random(17)))
    compare("start", run, frame(rows, "start"))
    now = 0.0
    while run.result is None:
        ports = conductor.autopilot(run)
        if ports:
            conductor.act(run, ports[0])
        after = now + 1 / 60.0
        advance(run, after, now)
        now = after
        if run.next == 1 and run.t - 2.0 < 1 / 60.0:
            compare("first", run, frame(rows, "first"))
        if ports == [hand.PRESS]:
            compare("cue", run, frame(rows, "cue"))
    won = frame(rows, "won")
    compare("won", run, won)
    assert won[0][:4] == (2, 2, 1, 1)
    assert "Bravo" in won[3]
    assert frame(rows, "hold") == won
    assert "1 of 1 passed   highest rung passed 1" in frame(rows, "done")[3]
    assert next(rows, None) is None
    frames = sum(line.startswith("frame ") for line in lines)
    print(f"PASS: {frames} Conductor frames covering stage, score, baton, cue visibility, feedback timing, and adaptation match Python")


if __name__ == "__main__":
    check(sys.argv[1])
