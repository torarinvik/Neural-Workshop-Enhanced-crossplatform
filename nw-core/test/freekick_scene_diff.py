"""Compare the pitch Free Kick draws, its verdicts and its option
descriptions with Python headlessly."""
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
from neural_workshop import freekick as model
from neural_workshop.ui import freekick, taskoptions

CODES = {"In the ring": 1, "Into the wall": 2, "Fell short": 3, "Wide of the goal": 4, "Over the bar": 5,
         "Saved": 6, "Out of time": 8}


@lru_cache(maxsize=None)
def deal(rung):
    return model.deal(rung, rng=Random(17))


def outcome(run):
    if run.result is None:
        return 0
    return 7 if run.result[1].startswith("In the goal, but") else CODES[run.result[1]]


def scene(rung, mode):
    screen = freekick.FreeKick.__new__(freekick.FreeKick)
    run = model.Run(deal(rung))
    screen.run = run
    after, frame, last = -1, 1, 0.0
    while frame <= 1800 and run.result is None:
        if mode == 0 or (mode == 1 and frame > 40) or (mode == 2 and after >= 0 and frame - after > 5):
            break
        port = None
        if mode == 1:
            port = model.AIM_R if frame <= 15 else (model.CURL_L if frame <= 30 else model.RAISE)
        elif mode == 4:
            port = model.KICK if frame == 1 else None
        else:
            ports = model.autopilot(run)
            port = ports[0] if ports else None
        control = None
        if port == model.KICK:
            model.act(run, port)
        else:
            control = port
        if after < 0 and run.kicked is not None and mode != 3:
            after = frame
        now = frame / 60
        dt = max(0.0, min(0.1, now - last))
        last = now
        steps = max(1, int(ceil(dt / (1 / 120.0))))
        for _ in range(steps):
            run.step(dt / steps, control)
            if run.result is not None:
                break
        frame += 1

    shapes = defaultdict(list)
    labels = []
    colours = set()
    screen.drawn, screen.batch = [], object()

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
    return outcome(run), "" if run.result is None else run.result[1], shapes, labels, colours


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.KICK.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.freekick_note({'KICK_RUNG': rung})}"
    count = polygons = 0
    endings = set()
    for rung in (1, 2, 4, 7, 10, 13, 30):
        for mode in range(5):
            where = rung, mode
            result, caption, expected, labels, colours = scene(rung, mode)
            assert next(rows) == f"frame {rung} {mode} {result}", where
            assert next(rows) == f"verdict {caption}", where
            actual, actual_labels = decode(rows, polygon_colours=colours)
            assert actual.keys() == expected.keys(), (where, sorted(actual.keys(), key=str), sorted(expected.keys(), key=str))
            for key, commands in expected.items():
                compare_commands(actual[key], commands, (where, key))
                polygons += len(commands) if key[0] == "polygon" else 0
            compare_commands(actual_labels, labels, (where, "labels"))
            endings.add(result)
            count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Free Kick pitches (the grass, the lines, the goal and its net, the ring, the keeper, the wall "
          f"jumping, the wind's flag, the drawn flight, the ball and its shadow, the dials; {polygons} clipped polygons; "
          f"rounds ending {sorted(endings)}) and nine option descriptions matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
