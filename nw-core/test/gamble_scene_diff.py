"""Compare the Elisa Gamble display and hit regions with the windowless Python UI."""
from importlib import import_module
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, RECT, Label, compare_commands, decode, rgba, state

from neural_workshop.ui import gamble, taskoptions


class Screen(gamble.Gamble):
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
    if mode:
        screen.start_run()
    if mode >= 2:
        limit = 14 if mode == 2 else screen.round.level.pulls
        for turn in range(limit):
            if screen.phase != "pulling":
                break
            if mode >= 3 and turn == 5 and screen.round.level.price:
                screen.stop()
            else:
                screen.pull(0)
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
        Box=lambda *a, thickness, **kw: shape(BOX, *a, thickness, **kw),
    ), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace,
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    return screen, shapes, [(rgba(label.color), label.x, label.y, label.font_size, label.text)
                            for label in labels if label.visible and label.text]


def check_hits(screen, hits, location):
    active = screen.phase in ("pulling", "judged")
    assert len(hits) == (screen.round.level.arms + 2 if active else 1), location
    pulled = []
    screen.pull = pulled.append if screen.phase == "pulling" else lambda _arm: None
    screen.start_run = lambda: pulled.append(gamble.PORTS)
    if screen.phase == "pulling":
        screen.stop = lambda: pulled.append(gamble.STOP)
        if screen.round.level.price:
            # The Stop callback is bound at draw time.
            screen.hits[-1] = (*screen.hits[-1][:4], screen.stop)
    for _, result, x, y in hits:
        screen.on_mouse_press(float(x), float(y), gamble.mouse.LEFT, 0)
        assert int(result) == (pulled.pop() if pulled else -1), (location, result, x, y)


def main(binary):
    rows = subprocess.check_output([binary], text=True).splitlines()
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rungs = taskoptions.GAMBLE.options[0].values
    for cursor, rung in enumerate(rungs):
        note = taskoptions.gamble_note({"GAMBLE_RUNG": rung})
        assert rows[cursor] == f"note {rung} {note}", (rung, rows[cursor], note)
    cursor = len(rungs)
    for rung in (1, 18, 25):
        for mode in range(5):
            for dark in range(2):
                location = rung, mode, dark
                assert rows[cursor] == f"frame {rung} {mode} {dark}"
                end = rows.index("end", cursor + 1)
                cursor += 1
                hits = []
                while rows[cursor].startswith("hit "):
                    hits.append(rows[cursor].split())
                    cursor += 1
                screen, shapes, labels = expected(*location)
                check_hits(screen, hits, location)
                actual_shapes, actual_labels = decode(iter(rows[cursor:end + 1]))
                compare_commands(actual_shapes, shapes, location)
                compare_commands(actual_labels, labels, location)
                cursor = end + 1
    assert cursor == len(rows)
    print("PASS: 30 Gamble scenes matched the Python machines, labels, verdicts, hit regions, and 9 rung descriptions")


if __name__ == "__main__":
    main(sys.argv[1])
