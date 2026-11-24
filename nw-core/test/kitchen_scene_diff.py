"""Replay Kitchen's Python screen and compare the headless display list."""
from collections import defaultdict
from importlib import import_module
from math import cos, isclose, radians, sin
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sokobanlive_scene_diff import SHAPES, decode
from sonar_scene_diff import LINE, Label, compare_commands, rgba, state
from neural_workshop import kitchen as model
from neural_workshop.ui import kitchen, taskoptions


PHASE = {"ready": 0, "playing": 1, "judged": 2, "done": 3}
ORDERS = {0: 0, 2000: 4, 4000: 4, 5000: 6, 18000: 6, 20000: 12}
STOPS = {2: 125, 3: 3500, 4: 8000, 5: 11000, 6: 16000, 7: 21000}


class Screen(kitchen.Kitchen):
    def __init__(self, rung):
        self.rng = Random(17)
        self.start_rung = self.rung = rung
        self.total_trials = 2
        self.adaptive = True
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.drawn, self.scenery = [], []
        self.scenery_key = None
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self._reset()

    def _redraw(self):
        if self.record:
            super()._redraw()


def scenario(rung, mode):
    screen = Screen(rung)
    if mode:
        screen.start_run()
    if mode >= 2:
        stop = STOPS.get(mode, 600000)
        while screen.phase == "playing" and screen.now < stop:
            if mode <= 7 and screen.now in ORDERS:
                screen.steer(ORDERS[screen.now])
            if mode in (10, 11):
                for port in model.autopilot(screen.run):
                    screen.steer(port)
            screen.now += 125
            screen.update(0)
    if mode in (9, 11):
        screen.now += 2999
        screen.update(0)
        assert screen.phase == "judged"
        screen.now += 1
        screen.update(0)
        assert screen.phase == "playing"
    return screen


def capture(screen, dark, polygons=None):
    shapes, labels = defaultdict(list), []

    def shape(name, *args, color, **fields):
        kind, names = SHAPES[name]
        if name == "Polygon":
            values = tuple(value for point in args for value in point)
            if polygons is not None:
                polygons.append((rgba(color), *values))
        elif name == "Ellipse":
            x, y, rx, ry = args
            values = (x - rx, y - ry, x + rx, y + ry)
        elif name == "Sector":
            x, y, radius = args
            values = (x - radius, y, x + radius, y + radius)
        elif name == "RoundedRectangle":
            x, y, width, height, *_ = args
            values = (x, y, x + width, y + height)
        else:
            defaults = {"angle": 360.0, "start_angle": 0.0, "thickness": 1.0}
            values = tuple(args[:len(names)]) + tuple(fields.get(n, defaults.get(n)) for n in names[len(args):])
        shapes[kind, rgba(color)].append(values)
        return Label(color=color)

    def label(text, **fields):
        obj = Label(text=text, visible=True, **fields)
        obj.content_width = len(text) * int(fields["font_size"] * 0.8 + 0.5)
        labels.append(obj)
        return obj

    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw)) for name in SHAPES}
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    return shapes, [(rgba(item.color), item.x, item.y, item.font_size, item.text)
                    for item in labels if item.visible and item.text]


def compare_arcs(actual, expected, where):
    for (_, color), arcs in [(key, value) for key, value in expected.items() if key[0] == "arc"]:
        del expected["arc", color]
        lines = actual[LINE, color]
        for x, y, radius, thick, sweep, start in arcs:
            points = [(x + radius * cos(radians(start + sweep * k / 32)),
                       y + radius * sin(radians(start + sweep * k / 32))) for k in range(33)]
            segments = [(*a, *b, thick) for a, b in zip(points, points[1:])]
            def matches(index):
                return all(isclose(a, b, rel_tol=0, abs_tol=0.00012)
                           for l, r in zip(lines[index:index + 32], segments) for a, b in zip(l, r))
            match = next((i for i in range(len(lines) - 31) if matches(i)), None)
            assert match is not None, (where, color, points[0], radius, sweep, lines[:3])
            del lines[match:match + 32]
        if not lines:
            del actual[LINE, color]


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.KITCHEN.options[0].values:
        note = taskoptions.kitchen_note({"KITCHEN_RUNG": rung})
        assert next(rows) == f"note {rung} {note}"
    checked = 0
    for rung in (1, 16):
        for mode in range(12):
            for dark in range(2):
                where = rung, mode, dark
                screen = scenario(rung, mode)
                score = screen.score()
                summary = (*where, PHASE[screen.phase], screen.rung, screen.trial, score["passed"], score["best_rung"])
                assert next(rows) == "frame " + " ".join(map(str, summary)), where
                assert next(rows) == ("hit 13" if screen.phase in ("ready", "done") else "hit -1"), where
                if screen.phase == "playing":
                    for station in screen.run.shift.stations:
                        assert next(rows) == f"hit {station.port}", (where, station)
                expected, labels = capture(screen, dark)
                actual, actual_labels = decode(rows)
                compare_arcs(actual, expected, where)
                assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                for key, commands in expected.items():
                    compare_commands(actual[key], commands, (where, key))
                compare_commands(actual_labels, labels, where)
                checked += 1
    assert next(rows, None) is None
    print(f"PASS: {checked} Kitchen scenes match Python, including station hit tests and adaptive handoff")


if __name__ == "__main__":
    main(sys.argv[1])
