"""Record the original Python Sonar screen without creating a window."""
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
from neural_workshop import state
from neural_workshop.ui.sonar import Sonar


RECT, BOX, CIRCLE, LINE = 1, 3, 4, 6


def rgba(colour):
    r, g, b, *alpha = colour
    return (r << 24) | (g << 16) | (b << 8) | (alpha[0] if alpha else 255)


class Label(SimpleNamespace):
    def delete(self):
        pass


class Screen(Sonar):
    def __init__(self, rung):
        self.rng = Random(17)
        self.rung = self.start_rung = rung
        self.total_trials = 1
        self.adaptive = False
        self.drawn = []
        self.clock = lambda: 0
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self._reset()

    def _redraw(self):
        if self.record:
            super()._redraw()


def expected(rung, mode, dark):
    screen = Screen(rung)
    if mode != 5:
        screen.start_run()
    if mode in (1, 2, 4):
        side = screen.round.level.side
        x, y = screen.round.target
        wrong = (y * side + x + 1) % (side * side)
        wrong = wrong % side, wrong // side
        screen.ping((0, 0))
        screen.dig(wrong)
        screen.ping(wrong)
        screen.ping((0, 0))
        screen.ping((2, 0))
    if mode in (2, 4):
        screen.dig(screen.round.target)
    if mode == 3:
        for _ in range(screen.round.deal.budget):
            screen.ping((1, 0))
    if mode == 4:
        screen.clock = lambda: screen.feedback_until
        screen.update(0)

    shapes, labels = [], []

    def shape(kind, *numbers, color, **_fields):
        shapes.append((kind, rgba(color), *numbers))
        return Label()

    def label(text, **fields):
        result = Label(text=text, visible=True, **fields)
        labels.append(result)
        return result

    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    with patch.multiple(
        import_module("pyglet.shapes"),
        Rectangle=lambda *a, **kw: shape(RECT, *a, **kw),
        RoundedRectangle=lambda *a, **kw: shape("rounded", *a, **kw),
        Circle=lambda *a, **kw: shape(CIRCLE, *a, **kw),
        Box=lambda *a, thickness, **kw: shape(BOX, *a, thickness, **kw),
    ), patch.object(import_module("pyglet.graphics"), "Batch", object), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    return screen, shapes, [(rgba(label.color), label.x, label.y, label.font_size, label.text)
                            for label in labels if label.visible and label.text]


def decode(rows):
    shapes, labels = [], []
    for row in rows:
        if row == "end":
            return shapes, labels
        if row.startswith("text "):
            _, color, x, y, size, text = row.split(maxsplit=5)
            labels.append((int(color), float(x), float(y), float(size), text))
        elif row.startswith("poly "):
            _, color, count = row.split()
            assert count == "24"
            points = [tuple(map(float, next(rows).split()[3:5])) for _ in range(int(count))]
            left, right = min(x for x, _ in points), max(x for x, _ in points)
            bottom, top = min(y for _, y in points), max(y for _, y in points)
            shapes.append(("rounded", int(color), left, bottom, right - left, top - bottom, top - points[0][1]))
        else:
            _, kind, color, *values = row.split()
            kind = int(kind)
            coordinates = {RECT: 4, CIRCLE: 3, BOX: 5, LINE: 5}[kind]
            shapes.append((kind, int(color), *map(float, values[:coordinates])))
    raise AssertionError("Incomplete scene")


def compare_commands(actual, expected, location):
    assert len(actual) == len(expected), (location, len(actual), len(expected))
    remaining = actual.copy()
    for command in expected:
        for i, candidate in enumerate(remaining):
            if len(candidate) == len(command) and all(
                isclose(a, b, abs_tol=0.00012) if isinstance(a, float) else a == b
                for a, b in zip(candidate, command)
            ):
                del remaining[i]
                break
        else:
            raise AssertionError((location, command))


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255), COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in (1, 8, 25):
        for mode in range(6):
            for dark in range(2):
                location = rung, mode, dark
                assert next(rows) == f"frame {rung} {mode} {dark}"
                screen, shapes, labels = expected(*location)
                if screen.phase == "searching":
                    side = screen.round.level.side
                    for cell in range(side * side):
                        left, bottom, size = screen._cell_rect((cell % side, cell // side))
                        x, y = screen._at(left + size / 2, bottom + size / 2)
                        assert next(rows) == f"hit {y * side + x}"
                    assert next(rows) == "outside -1 -1"
                actual_shapes, actual_labels = decode(rows)
                compare_commands(actual_shapes, shapes, location)
                compare_commands(actual_labels, labels, location)
    assert next(rows, None) is None
    print("PASS: 36 Sonar scenes matched the Python board, markers, labels, verdicts, and cell hit regions")


if __name__ == "__main__":
    main(sys.argv[1])
