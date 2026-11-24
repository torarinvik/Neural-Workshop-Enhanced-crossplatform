"""Compare Desktop's game flow, drawing and pointer mapping with ui/desktop.py.

The reference draws with its own ``_build_chrome``; pyglet's shapes and
labels underneath are recorded instead of made, and read when the frame is
done, since the pointer's corners and the card's font sizes are set after
they are made. Text is measured as textmetrics.elisa measures Courier New.
"""
from importlib import import_module
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, RECT, compare_commands, rgba, state

import pyglet.text  # noqa: F401  (loaded before pyglet.graphics is patched)

from neural_workshop import desktop as model
from neural_workshop.ui import desktop as ui, taskoptions

PHASES = {"ready": 0, "working": 1, "judged": 2, "done": 3}
TRIANGLE = 7
COORDINATES = {RECT: 4, BOX: 5, TRIANGLE: 6}
FINISH = ui.DONE


def advance(size):
    return int(size * 0.8 + 0.5)


def decode(rows):
    """The frame's commands; a label keeps its leading spaces."""
    shapes, labels = [], []
    for row in rows:
        if row == "end":
            return shapes, labels
        if row.startswith("text "):
            _, color, x, y, size, text = row.split(" ", 5)
            labels.append((int(color), float(x), float(y), float(size), text))
        else:
            _, kind, color, *values = row.split()
            kind = int(kind)
            shapes.append((kind, int(color), *map(float, values[:COORDINATES[kind]])))
    raise AssertionError("Incomplete scene")


class Label:
    """A pyglet label as the port measures it; a deleted one is not drawn."""

    def __init__(self, text="", font_size=12, x=0.0, y=0.0, color=(0, 0, 0, 255), **_):
        self.text, self.font_size, self.x, self.y, self.color = text, font_size, x, y, color
        self.visible = True

    @property
    def content_width(self):
        return len(self.text) * advance(self.font_size)

    def delete(self):
        self.visible = False


class Shape:
    """A pyglet shape, read when the frame is done."""

    def __init__(self, kind, numbers, color):
        self.kind, self.numbers, self.color, self.visible = kind, list(numbers), color, True
        if kind == TRIANGLE:
            self.x, self.y, self.x2, self.y2, self.x3, self.y3 = self.numbers

    def delete(self):
        self.visible = False

    def recorded(self):
        numbers = ([self.x, self.y, self.x2, self.y2, self.x3, self.y3] if self.kind == TRIANGLE else self.numbers)
        return (self.kind, rgba(self.color), *map(float, numbers))


class Screen(ui.Desktop):
    def __init__(self, rung, seed):
        self.rng = Random(seed)
        self.start_rung = self.rung = rung
        self.total_trials = 3
        self.adaptive = True
        self.now = 0.0
        self.clock = lambda: self.now
        self.desk, self.par, self.budget, self.trial, self.feedback_until = None, 0.0, 0, 0, 0.0
        self.results, self.drawn = [], []
        self.verdict_shown = None
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self._reset()

    def _redraw(self):
        if self.record:
            super()._redraw()


def capture(screen, dark):
    shapes, labels = [], []

    def shape(kind, *numbers, color, **_fields):
        made = Shape(kind, numbers, color)
        shapes.append(made)
        return made

    def label(text="", **fields):
        made = Label(text, **fields)
        labels.append(made)
        return made

    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    with patch.multiple(
        import_module("pyglet.shapes"),
        Rectangle=lambda *a, **kw: shape(RECT, *a, **kw),
        Box=lambda *a, thickness, **kw: shape(BOX, *a, thickness, **kw),
        Triangle=lambda *a, **kw: shape(TRIANGLE, *a, **kw),
    ), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace,
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    screen.record = False
    drawn = [(rgba(made.color), made.x, made.y, made.font_size, made.text) for made in labels
             if made.visible and made.text]
    return [made.recorded() for made in shapes if made.visible], drawn


def compare_frame(rows, screen, label, dark, where):
    score = screen.score()
    verdict = 0 if screen.verdict_shown is None else (1 if screen.verdict_shown[0] else 2)
    live = screen.desk is not None and screen.phase in ("working", "judged")
    expected = [label, PHASES[screen.phase], screen.rung, screen.trial, score["passed"], score["best_rung"], verdict,
                screen.desk.clicks if live else 0]
    header = next(rows).split()
    assert header[0] == "frame" and list(map(int, header[1:])) == expected, (where, header, expected)
    shapes, labels = capture(screen, dark)
    actual_shapes, actual_labels = decode(rows)
    compare_commands(actual_shapes, shapes, where)
    compare_commands(actual_labels, labels, where)
    return len(shapes) + len(labels)


def compare_grid(rows):
    """Where each pixel of a coarse grid lands on the screen, if it does."""
    screen = Screen(1, 0)
    expected = []
    for row in range(36):
        for column in range(48):
            point = screen._on_screen(4.5 + column * 19.0, 2.5 + row * 19.0)
            expected.append(None if point is None else point)
    tag, *found = next(rows).split(" ")
    assert tag == "grid", tag
    values = iter(found)
    landed = 0
    for point in expected:
        first = next(values)
        if point is None:
            assert first == "-", (point, first)
            continue
        second = float(next(values))
        assert abs(float(first) - point[0]) < 1e-5 and abs(second - point[1]) < 1e-5, (point, first, second)
        landed += 1
    return landed


def reference(desk):
    """The reference's next action; None when it would press Done or is stuck."""
    try:
        action = model.reference_action(desk)
    except AssertionError:
        return None
    return None if action is not None and action[1] is None else action


def act(rows, screen, action, dark, label, where):
    screen.desk.pointer = tuple(map(float, action[1]))
    if action[0] == "click":
        screen.click()
        return 0
    screen.press()
    screen.desk.pointer = tuple(map(float, action[2]))
    drawn = compare_frame(rows, screen, label, dark, where)
    screen.release()
    return drawn


def finish(rows, screen, dark, every, early, label, where):
    drawn = 0
    for step in range(3000):
        if screen.phase != "working":
            break
        action = reference(screen.desk)
        screen.now += 0.25
        if action is None:
            screen.steer(FINISH)
        elif early and not screen.desk.solved and step > 2 and step % 7 == 3:
            screen.steer(FINISH)
        else:
            drawn += act(rows, screen, action, dark, label + 1, where + (step,))
        if step % every == 0 or screen.phase != "working":
            drawn += compare_frame(rows, screen, label, dark, where + (step,))
    return drawn


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255), COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rungs = taskoptions.DESKTOP.options[0].values
    for rung in rungs:
        note = taskoptions.desktop_note({"DESKTOP_RUNG": rung})
        line = next(rows)
        assert line == f"note {rung} {note}", (line, note)
    landed = compare_grid(rows)
    runs = drawn = 0
    verdicts = set()
    for header in rows:
        tag, rung, seed, dark = header.split()
        assert tag == "run", header
        rung, seed, dark = int(rung), int(seed), int(dark)
        screen = Screen(rung, seed)
        drawn += compare_frame(rows, screen, 0, dark, (rung, seed, 0))
        screen.start_run()
        drawn += compare_frame(rows, screen, 1, dark, (rung, seed, 1))
        for trial in range(3):
            where = (rung, seed, trial)
            if trial == 0:
                drawn += finish(rows, screen, dark, 3, False, 10, where)
            elif trial == 1:
                for port in (0, 4, 8, 10, 1, 12, 16, 12, 5, 13, 3, 3, 14, 7, 12):
                    screen.now += 0.25
                    screen.steer(port)
                    drawn += compare_frame(rows, screen, 12, dark, where + (port,))
                top = screen.desk.order[-1]
                screen.desk.pointer = (top.x + 40.0, top.y + 12.0)
                screen.press()
                screen.desk.pointer = (top.x + 95.0, top.y + 47.0)
                drawn += compare_frame(rows, screen, 13, dark, where)
                screen.release()
                drawn += compare_frame(rows, screen, 14, dark, where)
                drawn += finish(rows, screen, dark, 5, False, 20, where)
            else:
                drawn += finish(rows, screen, dark, 5, True, 30, where)
            verdicts.add(screen.verdict_shown[0] if screen.verdict_shown else None)
            drawn += compare_frame(rows, screen, 6, dark, where)
            screen.now += 3.0
            screen.update(0)
            drawn += compare_frame(rows, screen, 7, dark, where)
        assert next(rows) == "over", (rung, seed)
        runs += 1
    assert runs == 12 and verdicts == {True, False}, (runs, verdicts)
    print(f"PASS: {runs} Desktop runs match ui/desktop.py ({drawn:,} drawn shapes and labels, {landed:,} grid pixels "
          f"on the screen, {len(rungs)} options notes)")


if __name__ == "__main__":
    main(sys.argv[1])
