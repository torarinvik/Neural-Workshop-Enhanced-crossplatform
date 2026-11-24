"""Compare Air Traffic geometry and controls using Python's windowless renderer."""
from collections import defaultdict
from importlib import import_module
from math import cos, isclose, radians, sin
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import CIRCLE, LINE, RECT, Label, compare_commands, rgba, state
from neural_workshop.ui import airtraffic, taskoptions

STAR, POINT = 17, 9
SHAPES = {
    "Rectangle": (RECT, ("x", "y", "width", "height")),
    "Line": (LINE, ("x", "y", "x2", "y2", "thickness")),
    "Circle": (CIRCLE, ("x", "y", "radius")),
    "Star": (STAR, ("x", "y", "outer", "inner", "spikes")),
    "Triangle": (7, ("x1", "y1", "x2", "y2", "x3", "y3")),
    "Sector": ("sector", ("x", "y", "radius")),
    "RoundedRectangle": ("rounded", ("x", "y", "width", "height", "radius")),
    "Polygon": ("polygon", ()),
    "Arc": ("arc", ("x", "y", "radius", "thickness", "angle", "start_angle")),
}


class Screen(airtraffic.AirTraffic):
    def __init__(self, rung):
        self.rng = Random(17)
        self.rung = self.start_rung = rung
        self.total_trials = 1
        self.adaptive = False
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.drawn, self.overlay = [], {}
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
        stop = 5000 if mode in (2, 3) else 180000
        while screen.phase == "playing" and screen.now < stop:
            if screen.now == 3200 and mode in (2, 3):
                screen.steer(0)
                screen.steer(8 if mode == 2 else 11)
            screen.now += 100
            screen.update(0)
    if mode == 5:
        screen.now += 3000
        screen.update(0)
    shapes, labels = defaultdict(list), []

    def shape(name, *args, color, **fields):
        kind, names = SHAPES[name]
        if name == "Polygon":
            values = tuple(v for point in args for v in point)
        elif name == "Sector":
            x, y, radius = args
            angles = [radians(fields["start_angle"] + fields["angle"] * j / 4) for j in range(5)]
            values = (x, y, *(v for angle in angles for v in (x + radius * cos(angle), y + radius * sin(angle))))
        elif name == "RoundedRectangle":
            x, y, width, height, *_ = args
            values = (x, y, x + width, y + height)
        else:
            values = tuple(args[:len(names)]) + tuple(
                fields.get(n, {"angle": 360.0, "start_angle": 0.0, "thickness": 1.0}.get(n))
                for n in names[len(args):]
            )
        shapes[kind, rgba(color)].append(values)
        return Label(color=color)

    def label(text, **fields):
        obj = Label(text=text, visible=True, **fields)
        obj.content_width = len(text) * fields["font_size"] * 0.65
        labels.append(obj)
        return obj

    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw)) for name in SHAPES}
    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    return screen, shapes, [(rgba(item.color), item.x, item.y, item.font_size, item.text)
                            for item in labels if item.visible and item.text]


def decode(rows):
    shapes, labels = defaultdict(list), []
    for row in rows:
        if row == "end":
            return shapes, labels
        if row.startswith("text "):
            _, color, x, y, size, text = row.split(maxsplit=5)
            labels.append((int(color), float(x), float(y), float(size), text))
        elif row.startswith("poly "):
            _, hue, count = row.split()
            color, count = int(hue), int(count)
            points = [tuple(map(float, next(rows).split()[3:5])) for _ in range(count)]
            if count == 24:
                shapes["rounded", color].append((min(x for x, _ in points), min(y for _, y in points),
                                                 max(x for x, _ in points), max(y for _, y in points)))
            else:
                kind = "sector" if color >> 8 == 0x3cdca0 else "polygon"
                shapes[kind, color].append(tuple(v for point in points for v in point))
        else:
            _, kind, hue, *values = row.split()
            kind = int(kind)
            assert kind != POINT
            fields = {RECT: 4, LINE: 5, CIRCLE: 3, STAR: 5, 7: 6}[kind]
            shapes[kind, int(hue)].append(tuple(map(float, values[:fields])))
    raise AssertionError("Incomplete Air Traffic scene")


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.AIRTRAFFIC.options[0].values:
        note = taskoptions.airtraffic_note({"AIRTRAFFIC_RUNG": rung})
        assert next(rows) == f"note {rung} {note}"
    for rung in (1, 7, 16, 30):
        for mode in range(6):
            for dark in range(2):
                where = rung, mode, dark
                assert next(rows) == f"frame {rung} {mode} {dark}"
                screen, expected, labels = scenario(*where)
                if screen.phase in ("playing", "judged"):
                    centers = [screen._at(plane.x, plane.y) for plane in screen.run.planes]
                    centers += [screen._at(runway.x, runway.y) for runway in screen.run.sky.runways]
                    for center in centers:
                        _, port, x, y = next(rows).split()
                        assert all(isclose(a, b, abs_tol=1e-5) for a, b in zip(center, map(float, (x, y))))
                        picked = []
                        screen.steer = picked.append
                        screen.on_mouse_press(float(x), float(y), 1, 0)
                        assert int(port) == (picked[0] if picked else -1), where
                _, port, *_ = next(rows).split()
                assert int(port) == (12 if screen.phase in ("ready", "done") else -1)
                actual, actual_labels = decode(rows)
                # Circular and partial outlines are tessellated by Elisa.
                # Verify the starts of each outline and remove its segments.
                for (_, color), arcs in [(key, val) for key, val in expected.items() if key[0] == "arc"]:
                    expected.pop(("arc", color))
                    lines = actual[LINE, color]
                    for x, y, radius, _, _, start in arcs:
                        first = (x + radius, y) if start == 0 else (x, y + radius)
                        i = next(i for i, line in enumerate(lines) if all(
                            isclose(a, b, abs_tol=0.00012) for a, b in zip(first, line[:2])))
                        count = 64 if color == 0x224654ff else 32
                        assert len(lines[i:i + count]) == count
                        del lines[i:i + count]
                    if not lines:
                        actual.pop((LINE, color))
                assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                for key, commands in expected.items():
                    compare_commands(actual[key], commands, (where, key))
                compare_commands(actual_labels, labels, (where, actual_labels, labels))
    assert next(rows, None) is None
    print("PASS: 48 Air Traffic scenes match Python radar, runways, storms, aircraft, verdicts, and controls")


if __name__ == "__main__":
    main(sys.argv[1])
