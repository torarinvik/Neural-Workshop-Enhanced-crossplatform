"""Compare the Elisa ExploreOrExploit display and hit regions with the windowless Python UI."""
from importlib import import_module
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sonar_scene_diff import BOX, CIRCLE, RECT, Label, compare_commands, decode, rgba, state

from neural_workshop.ui import bandit, taskoptions


class Screen(bandit.ExploreOrExploit):
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
        limit = 3 if mode == 2 else 14 if mode == 3 else screen.run.level.pulls
        for turn in range(limit):
            screen.pull(turn % 2)
    if mode == 5:
        screen.clock = lambda: screen.feedback_until
        screen.update(0)

    shapes, labels = [], []

    def shape(kind, *numbers, color, **_fields):
        shapes.append((kind, rgba(color), *numbers))
        return Label()

    def label(text, **fields):
        result = Label(text=text, visible=True, **fields)
        result.content_width = len(text) * int(fields["font_size"] * 0.8 + 0.5)
        labels.append(result)
        return result

    state.cfg.BLACK_BACKGROUND = bool(dark)
    screen.record = True
    with patch.multiple(
        import_module("pyglet.shapes"),
        Circle=lambda *a, **kw: shape(CIRCLE, *a, **kw),
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
    active = screen.phase in ("playing", "judged")
    assert len(hits) == (screen.run.level.arms + 1 if active else 1), location
    pulled = []
    screen.pull = pulled.append if screen.phase == "playing" else lambda _arm: None
    screen.start_run = lambda: pulled.append(8)
    for _, result, x, y in hits:
        screen.on_mouse_press(float(x), float(y), import_module("pyglet.window").mouse.LEFT, 0)
        assert int(result) == (pulled.pop() if pulled else -1), (location, result, x, y)


def main(binary):
    rows = subprocess.check_output([binary], text=True).splitlines()
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rungs = taskoptions.EXPLORE_EXPLOIT.options[0].values
    for cursor, rung in enumerate(rungs):
        note = taskoptions.explore_exploit_note({"EXPLORE_EXPLOIT_RUNG": rung})
        assert rows[cursor] == f"note {rung} {note}", (rung, rows[cursor], note)
    cursor = len(rungs)
    for rung in (1, 16, 25):
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
                actual_shapes, actual_labels = decode(iter(rows[cursor:end + 1]))
                compare_commands(actual_shapes, shapes, location)
                compare_commands(actual_labels, labels, location)
                cursor = end + 1
    assert cursor == len(rows)
    print("PASS: 36 Explore or Exploit scenes matched the Python machines, labels, verdicts, hit regions, and 9 rung descriptions")


if __name__ == "__main__":
    main(sys.argv[1])
