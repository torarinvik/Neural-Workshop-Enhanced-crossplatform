"""Compare the Elisa Bluff display and hit regions with the windowless Python UI."""
from importlib import import_module
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, RECT, Label, compare_commands, decode, rgba, state

from neural_workshop.ui import bluff, taskoptions


class Screen(bluff.Bluff):
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
        turn = 0
        while screen.phase == "playing":
            if mode == 2 and screen.match.spot in ("b", "cb"):
                break
            if mode == 3 and len(screen.match.records) >= 14:
                break
            screen.act(turn % 2)
            turn += 1
    if mode == 5:
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
        Box=lambda *a, thickness, **kw: shape(BOX, *a, thickness, **kw),
    ), patch.multiple(
        import_module("pyglet.graphics"), Batch=object, Group=SimpleNamespace,
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._build_chrome()
    anchors = {"left": 3, "center": 4, "right": 5}
    return screen, shapes, [
        (rgba(label.color), label.x, label.y, label.font_size, label.text, anchors[label.anchor_x],
         int(getattr(label, "weight", "normal") == "bold"))
        for label in labels if label.visible and label.text
    ]


def check_hits(screen, hits, location):
    assert len(hits) == 3, location
    selected = []
    screen.act = selected.append
    screen.start_run = lambda: selected.append(bluff.PORTS)
    for _, result, x, y in hits:
        screen.on_mouse_press(float(x), float(y), bluff.mouse.LEFT, 0)
        assert int(result) == (selected.pop() if selected else -1), (location, result, x, y)


def main(binary):
    rows = subprocess.check_output([binary], text=True).splitlines()
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rounding = (0.05, 0.15, 0.25, 0.35, 1.05, -1.05, 2.25, -2.25, -0.04)
    assert rows[:len(rounding)] == [f"points {bluff._points(round(score, 1))}" for score in rounding]
    rows = rows[len(rounding):]
    rungs = taskoptions.BLUFF.options[0].values
    for cursor, rung in enumerate(rungs):
        note = taskoptions.bluff_note({"BLUFF_RUNG": rung})
        assert rows[cursor] == f"note {rung} {note}", (rung, rows[cursor], note)
    cursor = len(rungs)
    for rung in (1, 14, 21):
        for mode in range(6):
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
                frame = rows[cursor:end + 1]
                styles = [tuple(map(int, row.split()[1:])) for row in frame if row.startswith("style ")]
                actual_shapes, actual_labels = decode(iter(row for row in frame if not row.startswith("style ")))
                actual_labels = [(*label, *style) for label, style in zip(actual_labels, styles, strict=True)]
                compare_commands(actual_shapes, shapes, location)
                compare_commands(actual_labels, labels, location)
                cursor = end + 1
    assert cursor == len(rows)
    print("PASS: 36 Bluff scenes matched the Python cards, action buttons, hand log, verdicts, hit regions, and 9 rung descriptions")


if __name__ == "__main__":
    main(sys.argv[1])
