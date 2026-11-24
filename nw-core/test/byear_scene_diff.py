"""Compare the keyboard By Ear draws, its verdicts, where its clicks land and
its option descriptions with Python headlessly."""
from collections import defaultdict
from functools import lru_cache
from importlib import import_module
from math import ceil
from random import Random
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import sys

from sokobanlive_scene_diff import SHAPES, decode
from sonar_scene_diff import Label, compare_commands, rgba, state
from neural_workshop import byear as model
from neural_workshop.ui import byear, taskoptions


@lru_cache(maxsize=None)
def deal(rung):
    return model.deal(rung, rng=Random(17))


def outcome(run):
    if run.result is None:
        return 0
    if run.result[0]:
        return 1
    text = run.result[1]
    return 2 if text.startswith("A wrong") else (3 if text.startswith("Both") else 4)


def scene(rung, mode):
    screen = byear.ByEar.__new__(byear.ByEar)
    run = model.Run(deal(rung))
    screen.run = run
    after, frame, last = -1, 1, 0.0
    while frame <= 7200 and run.result is None:
        if (mode == 0 and frame > 30) or (after >= 0 and frame - after > 6):
            break
        ports = model.autopilot(run)
        key = ports[0] if ports else -1
        if mode == 3 and key >= 0 and run.done == 1:
            key = 0 if 0 not in run.tune.want[1] else 12
        if key >= 0 and mode in (1, 2, 3):
            model.act(run, key)
        now = frame / 60
        dt = max(0.0, min(0.1, now - last))
        last = now
        steps = max(1, int(ceil(dt / (1 / 120.0))))
        for _ in range(steps):
            run.step(dt / steps)
            if run.result is not None:
                break
        if after < 0:
            if (mode == 1 and len(run.pressed) >= 2) or (mode == 4 and not run.listening()):
                after = frame
        frame += 1

    shapes = defaultdict(list)
    order = []
    labels = []
    colours = set()
    screen.drawn, screen.batch, screen.hits = [], object(), []

    def frame_card(x, y, w, h, colour=None):
        screen.order = 0
        screen.clip = (x, y, x + w, y + h)

    def shape(name, *args, color, **kwargs):
        kind, _ = SHAPES[name]
        if name == "Polygon":
            args = tuple(value for point in args for value in point)
            colours.add(rgba(color))
        if name == "Line":
            args = (*args, kwargs["thickness"])
        shapes[kind, rgba(color)].append(args)
        order.append((kind, rgba(color)))
        return Label()

    def say(text, x, y, size, colour=(235, 238, 250, 255), **kwargs):
        labels.append((rgba(colour), float(x), float(y), float(size), text))

    screen.frame = frame_card
    screen.say = say
    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw))
                 for name in ("Rectangle", "Line", "Circle", "Polygon")}
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.object(
        import_module("pyglet.graphics"), "Group", SimpleNamespace
    ):
        screen._draw(*screen._area())
    hits = []
    for i in range(61):
        for j in range(25):
            x, y = 100.0 + i * 12.0, 100.0 + j * 16.0
            hits.append(next((action.__defaults__[0] for left, bottom, w, h, action in screen.hits
                              if left <= x <= left + w and bottom <= y <= bottom + h), -1))
    lit = run.tune.lit is not None and not run.listening()
    return outcome(run), "" if run.result is None else run.result[1], shapes, labels, colours, (hits, lit), order


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.EAR.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.byear_note({'EAR_RUNG': rung})}"
    count = polygons = 0
    endings, probes, lit = set(), 0, 0
    for rung in (1, 2, 4, 7, 10, 13, 16):
        for mode in range(5):
            where = rung, mode
            result, caption, expected, labels, colours, (hits, shown), order = scene(rung, mode)
            assert next(rows) == f"frame {rung} {mode} {result}", where
            assert next(rows) == f"verdict {caption}", where
            drawn = []
            for row in rows:
                drawn.append(row)
                if row == "end":
                    break
            # The order things are drawn in: the black keys over the white.
            actual_order, k = [], 0
            while k < len(drawn):
                row = drawn[k].split()
                if row[0] == "poly":
                    actual_order.append(("polygon", int(row[1])))
                    k += int(row[2])
                elif row[0] == "shape":
                    actual_order.append((int(row[1]), int(row[2])))
                k += 1
            assert actual_order == order, (where, actual_order, order)
            actual, actual_labels = decode(iter(drawn), polygon_colours=colours)
            assert actual.keys() == expected.keys(), (where, sorted(actual.keys(), key=str), sorted(expected.keys(), key=str))
            for key, commands in expected.items():
                compare_commands(actual[key], commands, (where, key))
                polygons += len(commands) if key[0] == "polygon" else 0
            compare_commands(actual_labels, labels, (where, "labels"))
            if mode == 0:
                actual_hits = next(rows).split()
                assert actual_hits[0] == "hits" and list(map(int, actual_hits[1:])) == hits, where
                probes += sum(k >= 0 for k in hits)
            endings.add(result)
            lit += shown
            count += 1
    assert next(rows, None) is None
    assert {0, 1, 2} <= endings and lit, (endings, lit)
    print(f"PASS: {count} By Ear keyboards (the keys in play and out, blue, red and gold, the steps' dots, all in the "
          f"reference's order; tries ending {sorted(endings)}, {lit} with the first key lit; {polygons} polygons), "
          f"{probes} clicks on keys and nine option descriptions matched Python")

if __name__ == "__main__":
    main(sys.argv[1])
