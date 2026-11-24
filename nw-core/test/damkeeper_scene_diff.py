"""Compare Dam Keeper's projection and scene commands to the Python UI."""

from importlib import import_module
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import damkeeper as model, state
from neural_workshop.ui.damkeeper import DamKeeper

RECT, CIRCLE, ARC, LINE, TRIANGLE, POLYGON = 1, 4, 5, 6, 7, 8


def rgba(colour):
    r, g, b, *alpha = colour
    return (r << 24) | (g << 16) | (b << 8) | (alpha[0] if alpha else 255)


class Recorder(DamKeeper):
    def __init__(self, run, dark):
        self.run, self.dark = run, dark
        self.scenery, self.drawn = [], []
        self.batch = self.card_group = self.body_group = self.text_group = self.top_group = None
        self.shapes, self.labels, self.ports = [], [], []

    def _scenery_fresh(self, *_):
        self._build_scenery()

    def _text(self, words, x, y, size, **fields):
        self.labels.append((rgba(fields["colour"]), x, y, size, words))

    def steer(self, port):
        self.ports.append(port)

    def primitive(self, kind, *coordinates, color, **fields):
        self.shapes.append((kind, rgba(color), *coordinates))

    def polygon(self, *points, **fields):
        self.primitive(POLYGON, *(value for point in points for value in point), **fields)

    def arc(self, x, y, radius, *, angle, start_angle, **fields):
        self.primitive(ARC, x, y, radius, start_angle, angle, **fields)

    def line(self, a, b, c, d, *, thickness, **fields):
        self.primitive(LINE, a, b, c, d, thickness, **fields)

    def capture(self):
        with patch.multiple(
            import_module("pyglet.shapes"),
            Rectangle=lambda *args, **kw: self.primitive(RECT, *args, **kw),
            RoundedRectangle=lambda *args, **kw: self.primitive("rounded", *args, **kw),
            Triangle=lambda *args, **kw: self.primitive(TRIANGLE, *args, **kw),
            Polygon=self.polygon,
            Circle=lambda *args, **kw: self.primitive(CIRCLE, *args, **kw),
            Line=self.line,
            Arc=self.arc,
        ):
            self._draw(*self._area())


def equal(actual, expected):
    return len(actual) == len(expected) and all(
        isclose(a, b, abs_tol=0.00012) if isinstance(a, float) else a == b
        for a, b in zip(actual, expected)
    )


def remove_match(commands, expected):
    for i, cmd in enumerate(commands):
        if equal(cmd, expected):
            del commands[i]
            return
    raise AssertionError(f"Missing draw command {expected}")


def decode(rows):
    shapes, labels = [], []
    while (line := next(rows)) != "end":
        if line.startswith("text "):
            _, colour, x, y, size, content = line.split(maxsplit=5)
            labels.append((int(colour), float(x), float(y), float(size), content))
        elif line.startswith("poly "):
            _, colour, count = line.split()
            colour, count = int(colour), int(count)
            points = [tuple(map(float, next(rows).split()[3:5])) for _ in range(count)]
            if count == 24:
                left, top = min(x for x, _ in points), max(y for _, y in points)
                right, bottom = max(x for x, _ in points), min(y for _, y in points)
                shapes.append(("rounded", colour, left, bottom, right - left, top - bottom, top - points[0][1]))
            else:
                shapes.append((POLYGON, colour, *(value for point in points for value in point)))
        else:
            _, kind, colour, *coords = line.split()
            kind, colour, coords = int(kind), int(colour), tuple(map(float, coords))
            positions = {RECT: (0, 1, 2, 3), CIRCLE: (0, 1, 2), ARC: (0, 1, 2, 4, 5),
                         LINE: (0, 1, 2, 3, 4), TRIANGLE: (0, 1, 2, 3, 4, 5)}
            shapes.append((kind, colour, *(coords[i] for i in positions[kind])))
    return shapes, labels


def check_scene(rows, rung, mode, dark):
    assert next(rows) == f"frame {rung} {mode} {dark}"
    level = model.grade(rung)
    run = model.Run(model._build(level, Random(17)))
    run.t = run.valley.storms[0].start + (-2.5 if mode == 0 else 4.0)
    if mode:
        for _ in range(3):
            run.press(0)
        for _ in range(30):
            run.step(1 / 30)
    source = Recorder(run, dark)
    for k in range(level.dams):
        gx, gy = source._at(source._dam_x(k), source._floor(k) + 8)
        source._click(gx, gy + 1, 1)
        source._click(gx, gy, 1)
        a, b = source.ports[-2:]
        assert next(rows) == f"hit {a} {b}"
    assert next(rows) == "miss -1"
    if mode == 2:
        run.town = 6
        run.result = (False, "The town flooded")
    source.capture()
    shapes, labels = decode(rows)
    for expected in source.shapes:
        remove_match(shapes, expected)
    assert not shapes, (rung, mode, dark, shapes)
    for expected in source.labels:
        remove_match(labels, expected)
    assert any(label[-1] == "Dam Keeper" for label in labels)
    if mode == 2:
        assert any(label[0] == 0xFF4040FF and label[-1] == "The town flooded" for label in labels)


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    previous_window = state.window
    state.window = SimpleNamespace(width=912, height=684)
    try:
        for rung in (1, 16, 30):
            for mode in range(3):
                for dark in (0, 1):
                    check_scene(rows, rung, mode, dark)
        assert next(rows, None) is None
    finally:
        state.window = previous_window
    print("PASS: 18 Dam Keeper scenes matched Python terrain, weather, water, gates, clock, and gate hit regions")


if __name__ == "__main__":
    compare(sys.argv[1])
