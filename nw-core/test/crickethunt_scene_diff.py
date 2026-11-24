"""Compare the room Cricket Hunt draws, its verdicts and its option descriptions
with Python headlessly."""
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
from neural_workshop import crickethunt as model
from neural_workshop.ui import crickethunt, taskoptions


@lru_cache(maxsize=None)
def deal(rung):
    return model.deal(rung, rng=Random(17))


def outcome(run):
    if run.result is None:
        return 0
    ok, text = run.result
    if ok:
        return 1
    return 3 if text == "Three grabs at nothing" else 2


def scene(rung, mode):
    screen = crickethunt.CricketHunt.__new__(crickethunt.CricketHunt)
    run = model.Run(deal(rung))
    screen.run = run
    after, frame, last = -1, 1, 0.0
    while frame <= 21600 and run.result is None:
        if mode == 0 or (mode == 1 and frame > 90) or (mode == 5 and frame > 120) or (after >= 0 and frame - after > 3):
            break
        ports = model.autopilot(run)
        port = ports[0] if ports else -1
        if mode == 1:
            port = model.RIGHT if frame <= 45 else model.UP
        elif mode == 4:
            port = model.GRAB if frame <= 3 else -1
        elif mode == 5:
            port = model.FORWARD
        elif mode == 6:
            port = -1
        if port == model.GRAB:
            model.act(run, port)
        control = None if port in (-1, model.GRAB) else port
        now = frame / 60
        dt = max(0.0, min(0.1, now - last))
        last = now
        steps = max(1, int(ceil(dt / (1 / 120.0))))
        for _ in range(steps):
            run.step(dt / steps, control)
            if run.result is not None:
                break
        if after < 0 and mode == 2 and sum(run.caught) >= 1:
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
    return outcome(run), "" if run.result is None else run.result[1], shapes, labels, colours, None, order


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.CRICKET.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.crickethunt_note({'CRICKET_RUNG': rung})}"
    count = polygons = 0
    endings = set()
    for rung in (1, 4, 7, 10, 13):
        for mode in range(7):
            where = rung, mode
            result, caption, expected, labels, colours, _, order = scene(rung, mode)
            assert next(rows) == f"frame {rung} {mode} {result}", where
            assert next(rows) == f"verdict {caption}", where
            drawn = []
            for row in rows:
                drawn.append(row)
                if row == "end":
                    break
            # The order things are drawn in: far to near.
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
            endings.add(result)
            count += 1
    assert next(rows, None) is None
    assert endings == {0, 1, 2, 3}, endings
    print(f"PASS: {count} Cricket Hunt rooms (floor, ceiling, the walls and furniture far to near, the boards, the "
          f"crickets caught and the aim, all in the reference's order; tries ending {sorted(endings)}; "
          f"{polygons} polygons) and nine option descriptions matched Python")

if __name__ == "__main__":
    main(sys.argv[1])
