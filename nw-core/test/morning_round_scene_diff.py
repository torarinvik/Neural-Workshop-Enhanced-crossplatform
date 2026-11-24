"""Record Python's Morning Round street and rulebook without a window."""
from collections import defaultdict
from functools import lru_cache
from importlib import import_module
from math import ceil, floor
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from sokobanlive_scene_diff import SHAPES, decode
from sonar_scene_diff import Label, compare_commands, rgba
from neural_workshop import morninground as model
from neural_workshop.ui.morninground import MorningRound
from neural_workshop.ui.taskoptions import ROUND, morninground_note


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2


@lru_cache(maxsize=None)
def street(rung):
    return model.deal(rung, rng=Random(17))


def scenario(rung, mode):
    run = model.Run(street(rung))
    if mode > 0:
        run.t = run.level.brief + 1
    if mode >= 2:
        run.s = 330 + 180 * (mode - 2)
        run.x = 561
        run.throw(-1)
        run.got.update({0: "ok", 1: "wrong", 2: "missed"})
        run.mistakes = 2
    if mode == 3:
        run.down_until = run.t + 1
        run.falls = 1
        if run.street.things:
            run.hit.add(0)
    if mode == 4 and len(run.street.blocks) > 1:
        run.s = run.street.blocks[1][0]
    if mode == 5:
        run.s = run.street.length - 180
    return run


def wrap(text, size, width):
    # Courier New metrics at pyglet's 96 dpi. Preserve the two spaces after
    # the rule letter until a line break makes them trailing whitespace.
    advance = floor(size * 0.8 + 0.5)
    lines = [""]
    start = 0
    for end in range(1, len(text) + 1):
        if text[end - 1] != " " and (end - start) * advance >= width:
            split = text.rfind(" ", start, end)
            if split >= start:
                lines[-1] = text[start:split].rstrip()
                start = split + 1
                lines.append("")
    lines[-1] = text[start:]
    leading = ceil(size * (96 / 72) * (1705 / 2048)) + ceil(size * (96 / 72) * (615 / 2048))
    return lines, leading


def capture(run):
    shapes, labels = defaultdict(list), []

    def shape(name, *args, color, **fields):
        kind, _ = SHAPES[name]
        values = tuple(v for point in args for v in point) if name == "Polygon" else args
        if name == "Line":
            values = (*values, fields["thickness"])
        shapes[kind, rgba(color)].append(values)
        return Label()

    def label(text, font_size, width=None, **_):
        lines, leading = wrap(text, font_size, width)
        return Label(content_height=leading * len(lines))

    def text(words, x, y, size, colour, width=None, **_):
        if width is None:
            labels.append((rgba(colour), x, y, size, words))
            return Label()
        lines, leading = wrap(words, size, width)
        labels.extend((rgba(colour), x, y - i * leading, size, line)
                      for i, line in enumerate(lines))
        return Label(content_height=leading * len(lines))

    screen = MorningRound.__new__(MorningRound)
    screen.fit = (LEFT, 179.0, SCALE)
    screen.layer = 0
    screen.drawn, screen.batch = [], object()
    screen._text = text
    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw))
                 for name in ("Rectangle", "Line", "Circle", "Polygon")}
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.object(
        import_module("pyglet.graphics"), "Group", SimpleNamespace
    ), patch.object(import_module("pyglet.text"), "Label", label):
        screen._scene(run, SCALE)
    return shapes, labels


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in ROUND.options[0].values:
        assert next(rows) == f"note {rung} {morninground_note({'ROUND_RUNG': rung})}"
    count = 0
    for rung in (1, 4, 6, 9, 12, 30):
        for mode in range(6):
            where = rung, mode
            assert next(rows) == f"frame {rung} {mode}"
            expected, labels = capture(scenario(rung, mode))
            actual, actual_labels = decode(rows, polygon_colours={color for kind, color in expected if kind == "polygon"})
            assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
            for key, commands in expected.items():
                compare_commands(actual[key], commands, (where, key))
            compare_commands(actual_labels, labels, (where, actual_labels, labels))
            count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Morning Round streets and rulebooks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
