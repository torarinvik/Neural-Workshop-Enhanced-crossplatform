"""Compare the crate course and option descriptions with Python headlessly."""
from collections import defaultdict
from functools import lru_cache
from importlib import import_module
from math import ceil
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import sys

from sokobanlive_scene_diff import SHAPES, decode
from sonar_scene_diff import Label, compare_commands, rgba, state
from neural_workshop import heavier as model
from neural_workshop.ui import heavier, taskoptions


@lru_cache(maxsize=None)
def deal(rung):
    return model.deal(rung, seed=17)


def scene(rung, mode):
    screen = heavier.Heavier.__new__(heavier.Heavier)
    run = model.Run(deal(rung))
    screen.run, screen._shown = run, (id(run), run.board)
    screen.keys = defaultdict(bool)
    control = None if mode in (0, 3) else 0
    if mode > 0:
        last = 0.0
        for frame in range(1, 9 if mode == 1 else 41):
            now = frame / 10
            dt = min(0.1, now - last)
            last = now
            steps = max(1, ceil(dt / (1 / 120)))
            for _ in range(steps):
                run.step(dt / steps, 0)
    if mode == 3:
        run.answer(run.now.answer)
    if mode == 4:
        run.answer((run.now.answer + 1) % run.level.crates)
    if control is not None:
        screen.keys[heavier.PUSH_KEYS[control]] = True

    shapes, labels = defaultdict(list), []
    screen.drawn, screen.hits, screen.batch = [], [], object()

    # Let the original frame set the clip, and record lane geometry below it.
    def frame(x, y, w, h):
        screen.order = 0
        screen.clip = (x, y, x + w, y + h)

    def shape(name, *args, color, **kwargs):
        kind, _ = SHAPES[name]
        if name == "Polygon":
            kind, args = 7, tuple(value for point in args for value in point)
        if name == "Line":
            args = (*args, kwargs["thickness"])
        shapes[kind, rgba(color)].append(args)
        return Label()

    def text(words, x, y, size, colour, **_):
        labels.append((rgba(colour), x, y, size, words))

    screen.frame, screen._text = frame, text
    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw))
                 for name in ("Rectangle", "Line", "Polygon")}
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.object(
        import_module("pyglet.graphics"), "Group", SimpleNamespace
    ):
        screen._draw(*screen._area())
    for index, (left, bottom, right, top) in enumerate(screen._lanes):
        screen.keys.clear()
        screen.pointer, screen.buttons = ((left + right) / 2, (bottom + top) / 2), 1
        assert screen._held() == index
        ports = []
        screen.steer = ports.append
        screen.hits[index][-1]()
        assert ports == [model.PICK[index]]
    return shapes, labels


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.HEAVY.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.heavier_note({'HEAVY_RUNG': rung})}"
    count = 0
    for rung in (1, 4, 7, 10, 30):
        for mode in range(5):
            where = rung, mode
            assert next(rows) == f"frame {rung} {mode}"
            for index in range(model.grade(rung).crates):
                assert next(rows) == f"hit {index} {model.PICK[index]} -1"
            expected, labels = scene(rung, mode)
            actual, actual_labels = decode(rows)
            assert actual.keys() == expected.keys(), (where, actual.keys(), expected.keys())
            for key, commands in expected.items():
                compare_commands(actual[key], commands, (where, key))
            compare_commands(actual_labels, labels, where)
            count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Heavier crate courses, hit regions, and nine option descriptions matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
