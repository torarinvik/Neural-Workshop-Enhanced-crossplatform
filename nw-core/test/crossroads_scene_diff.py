"""Compare Crossroads's windowless Python scene with the Elisa display list."""
from collections import defaultdict
from importlib import import_module
from math import isclose
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, CIRCLE, LINE, RECT, Label, compare_commands, rgba, state

from neural_workshop.ui import crossroads, taskoptions

TRIANGLE, POINT = 7, 9
SHAPE_FIELDS = {
    RECT: ("x", "y", "width", "height"),
    BOX: ("x", "y", "width", "height", "thickness"),
    CIRCLE: ("x", "y", "radius"),
    LINE: ("x", "y", "x2", "y2", "thickness"),
    TRIANGLE: ("x", "y", "x2", "y2", "x3", "y3"),
    "rounded": ("x", "y", "width", "height", "radius"),
    "polygon": tuple(f"p{i}" for i in range(8)),
    "arc": ("x", "y", "radius", "thickness", "angle", "start_angle"),
}


class Screen(crossroads.Crossroads):
    def __init__(self, rung):
        self.rng = Random(17)
        self.rung = self.start_rung = rung
        self.total_trials = 1
        self.adaptive = False
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.drawn, self.scenery, self.overlay = [], [], {}
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self._reset()

    def _redraw(self):
        if self.record:
            super()._redraw()


def scenario(rung, mode, dark):
    screen = Screen(rung)
    if mode:
        screen.start_run()
    if mode >= 2:
        screen.steer(0)
        stop = 700 if mode == 2 else 2000 if mode == 3 else 120000
        while screen.phase == "playing" and screen.now < stop:
            screen.now += 100
            screen.update(0)
    if mode == 5:
        screen.now += 3000
        screen.update(0)
    shapes, labels = [], []

    def shape(kind, *args, color, **fields):
        if kind == "polygon":
            args = tuple(value for point in args for value in point)
        names = SHAPE_FIELDS[kind]
        props = dict(zip(names, args))
        props.update((name, fields[name]) for name in names[len(args):])
        obj = Label(kind=kind, color=color, **props)
        shapes.append(obj)
        return obj

    def label(text, **fields):
        obj = Label(text=text, visible=True, **fields)
        obj.content_width = len(text) * int(fields["font_size"] * 0.8 + 0.5)
        labels.append(obj)
        return obj

    factories = {
        name: (lambda *args, kind=kind, **kwargs: shape(kind, *args, **kwargs))
        for name, kind in zip(("Rectangle", "Box", "Circle", "Line", "Triangle", "RoundedRectangle", "Polygon", "Arc"),
                              SHAPE_FIELDS)
    }
    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    expected = defaultdict(list)
    for obj in shapes:
        color = rgba(obj.color)
        if hasattr(obj, "opacity"):
            color = (color & 0xffffff00) | obj.opacity
        expected[obj.kind, color].append(tuple(getattr(obj, name) for name in SHAPE_FIELDS[obj.kind]))
    return screen, expected, [(rgba(item.color), item.x, item.y, item.font_size, item.text)
                              for item in labels if item.visible and item.text]


def decode(rows, arcs):
    shapes, labels = defaultdict(list), []
    for row in rows:
        if row == "end":
            return shapes, labels
        if row.startswith("text "):
            _, color, x, y, size, text = row.split(maxsplit=5)
            labels.append((int(color), float(x), float(y), float(size), text))
        elif row.startswith("poly "):
            _, hue, count = row.split()
            color = int(hue)
            points = [tuple(map(float, next(rows).split()[3:5])) for _ in range(int(count))]
            left, right = min(x for x, _ in points), max(x for x, _ in points)
            bottom, top = min(y for _, y in points), max(y for _, y in points)
            if count == "4":
                shapes["polygon", color].append(tuple(value for point in points for value in point))
            else:
                shapes["rounded", color].append((left, bottom, right - left, top - bottom, top - points[0][1]))
        else:
            _, kind, hue, *values = row.split()
            kind, color = int(kind), int(hue)
            assert kind != POINT
            coords = tuple(map(float, values[:len(SHAPE_FIELDS[kind])]))
            if kind == LINE and color in arcs:
                arcs[color].append(coords)
            else:
                shapes[kind, color].append(coords)
    raise AssertionError("Incomplete Crossroads scene")


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.CROSSROADS.options[0].values:
        note = taskoptions.crossroads_note({"CROSSROADS_RUNG": rung})
        assert next(rows) == f"note {rung} {note}"
    for rung in (1, 7, 16):
        for mode in range(6):
            for dark in range(2):
                where = rung, mode, dark
                assert next(rows) == f"frame {rung} {mode} {dark}"
                screen, expected, labels = scenario(*where)
                active = screen.phase in ("playing", "judged")
                hits = len(screen.run.town.junctions) if active else 0
                for junction in range(hits):
                    _, port, x, y = next(rows).split()
                    expected_point = screen._at(*screen.run.town.junctions[junction])
                    assert all(isclose(a, b, abs_tol=1e-5) for a, b in zip(map(float, (x, y)), expected_point))
                    picked = []
                    screen.steer = picked.append if screen.phase == "playing" else lambda _: None
                    screen.on_mouse_press(float(x), float(y), 1, 0)
                    assert int(port) == (picked[0] if picked else -1), where
                _, port, *_ = next(rows).split()
                assert int(port) == (4 if screen.phase in ("ready", "done") else -1)
                arcs = {color: [] for kind, color in expected if kind == "arc"}
                actual, actual_labels = decode(rows, arcs)
                for color, segments in arcs.items():
                    specs = expected.pop(("arc", color))
                    assert len(segments) == 32 * len(specs), where
                    starts = [segment[:2] for segment in segments[::32]]
                    compare_commands(starts, [(x, y + radius) for x, y, radius, *_ in specs], where)
                assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                for key, commands in expected.items():
                    compare_commands(actual[key], commands, (where, key))
                compare_commands(actual_labels, labels, where)
    assert next(rows, None) is None
    print("PASS: 36 Crossroads scenes match Python streets, traffic, lamps, controls, verdicts, and nine options notes")


if __name__ == "__main__":
    main(sys.argv[1])
