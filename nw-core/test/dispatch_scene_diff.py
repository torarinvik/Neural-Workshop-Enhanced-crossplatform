"""Compare Dispatch's Elisa display list with a windowless original UI."""
from importlib import import_module
from math import cos, radians, sin
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import CIRCLE, LINE, RECT, Label, compare_commands, decode, rgba, state

from neural_workshop import dispatch
from neural_workshop.ui import dispatch as ui, taskoptions


class VisibleLabel(Label):
    def delete(self):
        self.visible = False


class Shape(VisibleLabel):
    @property
    def position(self):
        return self.x, self.y

    @position.setter
    def position(self, point):
        self.x, self.y = point


class Screen(ui.Dispatch):
    def __init__(self, rung, coach):
        self.rng = Random(17)
        self.rung = self.start_rung = rung
        self.total_trials = 1
        self.adaptive = False
        self.coach = coach
        self.now = 0
        self.clock = lambda: self.now / 1000
        self._notes = []
        self._reset()


def expected(rung, mode, dark):
    screen = Screen(rung, mode == 3)
    shapes, labels = [], []

    def shape(kind, x, y, *args, color, thickness=1.0, start_angle=0.0, angle=360.0, **_):
        fields = dict(kind=kind, x=x, y=y, color=color, thickness=thickness, start_angle=start_angle, angle=angle,
                      opacity=color[3] if len(color) == 4 else 255, visible=True)
        names = {RECT: ("w", "h"), "rounded": ("w", "h", "radius"),
                 CIRCLE: ("radius",), "arc": ("radius",), LINE: ("x2", "y2")}[kind]
        result = Shape(**fields, **dict(zip(names, args, strict=True)))
        shapes.append(result)
        return result

    def label(text, **fields):
        result = VisibleLabel(text=text, visible=True, **fields)
        labels.append(result)
        return result

    state.cfg.BLACK_BACKGROUND = bool(dark)
    with patch.multiple(
        import_module("pyglet.shapes"),
        Rectangle=lambda *a, **kw: shape(RECT, *a, **kw),
        RoundedRectangle=lambda *a, **kw: shape("rounded", *a, **kw),
        Circle=lambda *a, **kw: shape(CIRCLE, *a, **kw),
        Line=lambda *a, **kw: shape(LINE, *a, **kw),
        Arc=lambda *a, **kw: shape("arc", *a, **kw),
    ), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace,
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
        if mode:
            screen.start_run()
        if mode == 2:
            screen.press(0)
            screen.press(ui.FIRST_REFIT)
        if mode >= 2:
            while screen.phase == "running":
                if mode == 3:
                    for unit, kind, index in dispatch.reference_orders(screen.world):
                        screen.press(unit)
                        screen.press((ui.FIRST_SLOT if kind == "incident" else ui.FIRST_REFIT) + index)
                screen.now += 250
                screen.update(0.25)
                if (mode == 2 and screen.now == 4000) or (mode == 3 and screen._coach_up):
                    break
        if mode == 2:
            screen.press(1)
            screen.press(ui.FIRST_SLOT)
            screen.press(1)
        if mode == 5:
            screen.clock = lambda: screen.feedback_until
            screen.update(0)
    return screen, commands(shapes), [
        (rgba(label.color), label.x, label.y, label.font_size, label.text)
        for label in labels if label.visible and label.text
    ]


def commands(shapes):
    rows = []
    for shape in shapes:
        if not shape.visible:
            continue
        color = rgba((*shape.color[:3], shape.opacity))
        if shape.kind == "arc":
            count = max(14, int(shape.radius / 1.25))
            step = radians(shape.angle) / count
            start = radians(shape.start_angle)
            points = [(shape.x + shape.radius * cos(start + step * i),
                       shape.y + shape.radius * sin(start + step * i)) for i in range(count + 1)]
            rows.extend((LINE, color, *a, *b, shape.thickness) for a, b in zip(points, points[1:]))
        else:
            columns = {
                RECT: ("w", "h"), "rounded": ("w", "h", "radius"), CIRCLE: ("radius",),
                LINE: ("x2", "y2", "thickness"),
            }[shape.kind]
            rows.append((shape.kind, color, shape.x, shape.y, *(getattr(shape, key) for key in columns)))
    return rows


def main(binary):
    source = subprocess.check_output([binary], text=True).splitlines()
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for cursor, rung in enumerate(taskoptions.DISPATCH.options[0].values):
        assert source[cursor] == f"note {rung} {taskoptions.dispatch_note({'DISPATCH_RUNG': rung})}"
    rows = iter(source[cursor + 1:])
    for rung in (1, 8, 25):
        for mode in range(6):
            for dark in range(2):
                location = (rung, mode, dark)
                assert next(rows) == f"frame {rung} {mode} {dark}"
                screen, shapes, labels = expected(*location)
                frame = []
                for row in rows:
                    if row == "end":
                        frame.append(row)
                        break
                    if not row.startswith("hit "):
                        frame.append(row)
                        continue
                    _, port, shift, x, y = row.split()
                    if screen.phase != "running":
                        assert int(port) == -1
                        continue
                    expected_port = screen._port_at(float(x), float(y))
                    if expected_port is None:
                        expected_port = ui.PORTS + 1
                    elif shift == "1" and ui.FIRST_STATION <= expected_port < ui.FIRST_REFIT:
                        expected_port += ui.FIRST_REFIT - ui.FIRST_STATION
                    assert int(port) == expected_port, (location, row, expected_port)
                actual_shapes, actual_labels = decode(iter(frame))
                compare_commands(actual_shapes, shapes, location)
                compare_commands(actual_labels, labels, location)
    assert next(rows, None) is None
    print("PASS: 36 Dispatch scenes, click targets, and 13 rung descriptions matched the Python UI")


if __name__ == "__main__":
    main(sys.argv[1])
