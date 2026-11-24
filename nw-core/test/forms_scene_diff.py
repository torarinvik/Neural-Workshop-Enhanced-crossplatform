"""Compare Forms' game flow, drawing and hit regions with ui/forms.py.

The reference draws with its own ``_build_chrome``; pyglet's shapes and
labels underneath are recorded instead of made. Text is measured as
textmetrics.elisa measures Courier New, so the card shrinks the same way.
"""
from importlib import import_module
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, CIRCLE, LINE, RECT, compare_commands, rgba, state

import pyglet.text  # noqa: F401  (loaded before pyglet.graphics is patched)

from neural_workshop import forms
from neural_workshop.ui import forms as ui, taskoptions

PHASES = {"ready": 0, "filling": 1, "judged": 2, "done": 3}


def advance(size):
    return int(size * 0.8 + 0.5)


def decode(rows):
    """sonar_scene_diff.decode, keeping a label's leading spaces: a typed
    space is drawn as the start of the value."""
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
            coordinates = {RECT: 4, CIRCLE: 3, BOX: 5, LINE: 5}[kind]
            shapes.append((kind, int(color), *map(float, values[:coordinates])))
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


class Screen(ui.Forms):
    def __init__(self, rung, seed):
        self.rng = Random(seed)
        self.start_rung = self.rung = rung
        self.total_trials = 3
        self.adaptive = True
        self.now = 0.0
        self.clock = lambda: self.now
        self.form, self.par, self.trial, self.feedback_until = None, 0.0, 0, 0.0
        self.drawn, self.hits = [], []
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
    drawn = [(rgba(made.color), made.x, made.y, made.font_size, made.text) for made in labels
             if made.visible and made.text]
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


def compare_grid(rows, screen, dark, where):
    """The row each grid point's press reaches, through screen.hits."""
    capture(screen, dark)
    expected = []
    for row in range(36):
        for column in range(48):
            x, y = 4.5 + column * 19.0, 2.5 + row * 19.0
            expected.append(next((index for index, (left, bottom, w, h, _) in enumerate(screen.hits)
                                  if left <= x <= left + w and bottom <= y <= bottom + h), -1))
    tag, *found = next(rows).split()
    assert tag == "grid" and list(map(int, found)) == expected, (where, [(i, a, e) for i, (a, e) in
                                                                   enumerate(zip(map(int, found), expected)) if a != e][:5])
    return sum(index >= 0 for index in expected)


def last_page(form):
    return not (form.page + 1 < form.level.pages and any(f.page > form.page for f in form.deal.fields))


def spoil(form):
    field = form.field
    if field is None:
        return forms.ENTER
    return {"digits": "1", "check": " ", "radio": forms.DOWN}.get(field.kind, "x")


def finish(rows, screen, dark, every, spoiled, label, where):
    done, drawn = not spoiled, 0
    for step in range(400):
        if screen.phase != "filling":
            break
        key = forms.reference_keys(screen.form)
        if key == forms.ENTER and not done and last_page(screen.form):
            done, key = True, spoil(screen.form)
        screen.now += 0.25
        screen.press(key)
        if step % every == 0 or screen.phase != "filling":
            drawn += compare_frame(rows, screen, label, dark, where + (step,))
    return drawn


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255), COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rungs = taskoptions.FORMS.options[0].values
    for rung in rungs:
        note = taskoptions.forms_note({"FORMS_RUNG": rung})
        assert next(rows) == f"note {rung} {note}", (next, rung, note)
    runs = drawn = hits = bounced = 0
    verdicts = set()
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
            hits += compare_grid(rows, screen, dark, where)
            if trial == 0:
                drawn += finish(rows, screen, dark, 2, False, 10, where)
            elif trial == 1:
                screen.focus_on(1)
                drawn += compare_frame(rows, screen, 11, dark, where)
                for port in (0, 4, 41, 42, 43, 45, 44, 36, 2):
                    screen.now += 0.25
                    screen.steer(port)
                    drawn += compare_frame(rows, screen, 12, dark, where + (port,))
                screen.press("Q")
                drawn += compare_frame(rows, screen, 13, dark, where)
                bounced += screen.form.bounced > 0
                drawn += finish(rows, screen, dark, 4, False, 14, where)
            else:
                drawn += finish(rows, screen, dark, 4, True, 15, where)
            verdicts.add(screen.verdict_shown[0] if screen.verdict_shown else None)
            drawn += compare_frame(rows, screen, 6, dark, where)
            screen.now += 3.5
            screen.update(0)
            drawn += compare_frame(rows, screen, 7, dark, where)
        assert next(rows) == "over", (rung, seed)
        runs += 1
    assert runs == 20 and verdicts == {True, False} and bounced, (runs, verdicts, bounced)
    print(f"PASS: {runs} Forms runs match ui/forms.py ({drawn:,} drawn shapes and labels, {hits:,} grid presses on rows, "
          f"{bounced} pages sent back, {len(rungs)} options notes)")


if __name__ == "__main__":
    main(sys.argv[1])
