"""Compare rendered Potter's Wheel shapes with the Python scene without a window."""
from math import ceil, isclose
from pathlib import Path
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import hand, potter
from neural_workshop.ui.potter import PottersWheel


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2
BOTTOM = 179


class Scene(PottersWheel):
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
        self.shapes.append((6, rgba(color), *self.point(*start), *self.point(*end)))

    def poly(self, points, color, group):
        points = list(points)
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
    assert ("wanted" in labels) == (run.level.ghost != "over" and run.shown())


def advance(run, now, previous):
    dt = min(0.1, now - previous)
    steps = max(1, ceil(dt / (1 / 120.0)))
    for _ in range(steps):
        run.step(dt / steps)


def check(binary):
    output = subprocess.check_output([binary], text=True)
    rows = iter(output.splitlines())
    names = ("ready", "over", "touch", "released", "lost", "hold", "next", "won", "done", "brief", "hidden")
    frames = dict((name, frame(rows, name)) for name in names)
    assert next(rows, None) is None
    assert "Press Space or click to start" in frames["ready"][3]
    draw = Random(17)
    run = potter.Run(potter.deal(4, rng=draw))
    compare("over", run, frames["over"])
    run.hand.x, run.hand.y = potter.AXIS, potter.band_y(6, 0)
    run.press()
    run.key(potter.FASTER)
    advance(run, 0.1, 0.0)
    compare("touch", run, frames["touch"])
    run.release()
    run.key(potter.WET)
    compare("released", run, frames["released"])
    run.press()
    now = 0.1
    while run.result is None:
        after = now + 0.025
        advance(run, after, now)
        now = after
    assert run.result[1] in frames["lost"][3]
    assert frames["hold"] == frames["lost"]
    compare("lost", run, frames["lost"])
    run = potter.Run(potter.deal(3, rng=draw))
    compare("next", run, frames["next"])
    now += 2.5
    while run.result is None:
        for port in potter.autopilot(run):
            hand.act(run, port)
        after = now + 1 / 60.0
        advance(run, after, now)
        now = after
    compare("won", run, frames["won"])
    assert run.result[1] in frames["won"][3]
    assert frames["lost"][0][:4] == (2, 3, 1, 0)
    assert frames["next"][0][:4] == (1, 3, 2, 0)
    assert frames["won"][0][:4] == (2, 4, 2, 1)
    assert frames["done"][0][:4] == (3, 4, 2, 1)
    assert "1 of 2 passed   highest rung passed 3" in frames["done"][3]

    run = potter.Run(potter.deal(13, rng=draw))
    compare("brief", run, frames["brief"])
    started = now + 2.5 + 3
    previous = started
    for j in range(1, 61):
        tick = started + 0.1 * j
        advance(run, tick, previous)
        previous = tick
    compare("hidden", run, frames["hidden"])
    print(f"PASS: {len(names)} Potter's Wheel frames covering shapes, target visibility, mouse controls, feedback timing, and adaptation match Python")


if __name__ == "__main__":
    check(sys.argv[1])
