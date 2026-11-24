"""Compare Manual's game flow, drawing and hit regions with ui/manual.py.

The reference draws with its own ``_build_chrome``; pyglet's shapes and
labels underneath are recorded instead of made. Text is measured as
textmetrics.elisa measures Courier New, and a multiline label is split
into its lines the way the port wraps them.
"""
from importlib import import_module
from math import ceil, floor
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, CIRCLE, LINE, RECT, compare_commands, decode, rgba, state

from neural_workshop.ui import manual as ui, taskoptions

PHASES = {"ready": 0, "playing": 1, "judged": 2, "done": 3}


def advance(size):
    return floor(size * 0.8 + 0.5)


def leading(size):
    pixels = size * 96 / 72
    return ceil(pixels * 1705 / 2048) + ceil(pixels * 615 / 2048)


def wrap(text, size, width):
    """Paragraphs at newlines, each broken at the last space before the width."""
    lines = []
    for paragraph in text.split("\n"):
        start, space = 0, -1
        for at, char in enumerate(paragraph):
            if char == " ":
                space = at
            elif space >= start and (at - start + 1) * advance(size) >= width:
                lines.append(paragraph[start:space])
                start, space = space + 1, -1
        lines.append(paragraph[start:])
    return lines


class Label:
    """A pyglet label as the port measures it."""

    def __init__(self, text="", font_size=12, x=0.0, y=0.0, color=(0, 0, 0, 255), width=None, multiline=False, **_):
        self.text, self.font_size, self.x, self.y, self.color = text, font_size, x, y, color
        self.width = width if multiline else None
        self.visible = True

    @property
    def content_width(self):
        return len(self.text) * advance(self.font_size)

    @property
    def content_height(self):
        return len(wrap(self.text, self.font_size, self.width)) * leading(self.font_size)

    def delete(self):
        pass


class Screen(ui.Manual):
    def __init__(self, rung, seed):
        self.rng = Random(seed)
        self.start_rung = self.rung = rung
        self.total_trials = 3
        self.adaptive = True
        self.now = 0.0
        self.clock = lambda: self.now
        self.drawn, self.hits = [], []
        self.deal = self.panel = self.wanted = None
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self._reset()

    def _redraw(self):
        if self.record:
            super()._redraw()


def capture(screen, dark):
    shapes, labels = [], []

    def shape(kind, *numbers, color, **_fields):
        shapes.append((kind, rgba(color), *numbers))
        return Label()

    def label(text="", **fields):
        made = Label(text, **fields)
        labels.append(made)
        return made

    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    with patch.multiple(
        import_module("pyglet.shapes"),
        Circle=lambda *a, **kw: shape(CIRCLE, *a, **kw),
        Rectangle=lambda *a, **kw: shape(RECT, *a, **kw),
        Box=lambda *a, thickness, **kw: shape(BOX, *a, thickness, **kw),
        Line=lambda *a, thickness=1.0, **kw: shape(LINE, *a, float(thickness), **kw),
    ), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace,
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    screen.record = False
    drawn = []
    for made in labels:
        if not (made.visible and made.text):
            continue
        if made.width is None:
            drawn.append((rgba(made.color), made.x, made.y, made.font_size, made.text))
        else:
            drawn.extend((rgba(made.color), made.x, made.y - i * leading(made.font_size), made.font_size, line)
                         for i, line in enumerate(wrap(made.text, made.font_size, made.width)))
    return shapes, drawn


def compare_frame(rows, screen, label, dark, where):
    score = screen.score()
    verdict = 0 if screen.verdict_shown is None else (1 if screen.verdict_shown[0] else 2)
    expected = [label, PHASES[screen.phase], screen.rung, screen.trial, score["passed"], score["best_rung"], verdict]
    header = next(rows).split()
    assert header[0] == "frame" and list(map(int, header[1:])) == expected, (where, header, expected)
    shapes, labels = capture(screen, dark)
    actual_shapes, actual_labels = decode(rows)
    compare_commands(actual_shapes, shapes, where)
    compare_commands(actual_labels, labels, where)
    return len(shapes) + len(labels)


def compare_grid(rows, screen, where):
    """The port each grid point's press reaches, through screen.hits."""
    layout = screen.deal.layout
    pressed = []
    screen.flip = lambda i: pressed.append(layout[0].index(i))
    screen.turn = lambda i, w: pressed.append(ui.KNOB + 2 * layout[1].index(i) + (1 if w > 0 else 0))
    screen.press = lambda i: pressed.append(ui.BUTTON + layout[2].index(i))
    expected = []
    for row in range(36):
        for column in range(48):
            x, y = 4.5 + column * 19.0, 2.5 + row * 19.0
            # _click's first hit; Finish's is the bound method itself.
            action = next((action for left, bottom, w, h, action in screen.hits
                           if left <= x <= left + w and bottom <= y <= bottom + h), None)
            if action is None:
                expected.append(-1)
            elif getattr(action, "__func__", None) is ui.Manual.finish:
                expected.append(ui.FINISH)
            else:
                action()
                expected.append(pressed.pop())
    for name in ("flip", "turn", "press"):
        del screen.__dict__[name]
    tag, *ports = next(rows).split()
    assert tag == "grid" and list(map(int, ports)) == expected, (where, [(i, a, e) for i, (a, e) in
                                                                     enumerate(zip(map(int, ports), expected)) if a != e][:5])
    return sum(port >= 0 for port in expected)


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255), COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rungs = taskoptions.MANUAL.options[0].values
    for rung in rungs:
        note = taskoptions.manual_note({"MANUAL_RUNG": rung})
        assert next(rows) == f"note {rung} {note}", (rung, note)
    runs = frames = drawn = hits = 0
    verdicts, outlined = set(), 0
    for header in rows:
        tag, rung, seed, dark = header.split()
        assert tag == "run", header
        rung, seed, dark = int(rung), int(seed), int(dark)
        screen = Screen(rung, seed)
        drawn += compare_frame(rows, screen, 0, dark, (rung, seed, 0))
        screen.on_mouse_press(0, 0, import_module("pyglet.window").mouse.LEFT, 0)
        drawn += compare_frame(rows, screen, 1, dark, (rung, seed, 1))
        for trial in range(3):
            where = (rung, seed, trial)
            hits += compare_grid(rows, screen, where)
            if trial == 0:
                for index, port in enumerate(ui.reference_ports(screen)):
                    screen.now += 0.25
                    screen.steer(port)
                    if index % 3 == 0 or screen.phase != "playing":
                        drawn += compare_frame(rows, screen, 10, dark, where + (index,))
                        frames += 1
            elif trial == 1:
                for port in (0, 7, 14, 1, 6, 15, 14, 19):
                    screen.now += 0.25
                    screen.steer(port)
                    drawn += compare_frame(rows, screen, 11, dark, where + (port,))
                    frames += 1
                screen.on_key_press(import_module("pyglet.window").key.RETURN, 0)
            else:
                screen.finish()
            outlined += screen.phase == "judged" and not screen.verdict_shown[0]
            verdicts.add(screen.verdict_shown[0] if screen.verdict_shown else None)
            drawn += compare_frame(rows, screen, 6, dark, where)
            screen.now += 3.0
            screen.update(0)
            drawn += compare_frame(rows, screen, 7, dark, where)
            frames += 2
        assert next(rows) == "over", (rung, seed)
        runs += 1
    assert runs == 18 and verdicts == {True, False} and outlined, (runs, verdicts, outlined)
    print(f"PASS: {runs} Manual runs match ui/manual.py ({frames} frames, {drawn:,} drawn shapes and labels, "
          f"{hits:,} grid presses on controls, {outlined} wrong panels outlined, {len(rungs)} options notes)")


if __name__ == "__main__":
    main(sys.argv[1])
