"""Compare the viewfinder Steadicam draws, and its option descriptions, with Python headlessly."""
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
from neural_workshop import steadicam as model
from neural_workshop.ui import steadicam, taskoptions


@lru_cache(maxsize=None)
def deal(rung):
    return model.deal(rung, seed=17)


def outcome(run):
    if run.result is None:
        return 0
    if run.result[1] == "Lost them for 3 seconds":
        return 3
    return 1 if run.result[0] else 2


def scene(rung, mode):
    screen = steadicam.Steadicam.__new__(steadicam.Steadicam)
    run = model.Run(deal(rung))
    screen.run = run
    frames = (0, 30, 120, 20, 20)[mode]
    last = 0.0
    for frame in range(1, frames + 1):
        if run.result is not None:
            break
        if mode <= 2:
            ports = model.autopilot(run)
            control = ports[0] if ports else None
        else:
            control = model.PAN_R if mode == 3 else model.ZOOM_IN
        now = frame / 10
        dt = max(0.0, min(0.1, now - last))
        last = now
        steps = max(1, int(ceil(dt / (1 / 120.0))))
        for _ in range(steps):
            run.step(dt / steps, control)
            if run.result is not None:
                break

    shapes = defaultdict(list)
    colours = set()
    screen.drawn, screen.batch = [], object()

    def frame(x, y, w, h, colour=None):
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

    screen.frame = frame
    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw))
                 for name in ("Rectangle", "Line", "Circle", "Polygon")}
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.object(
        import_module("pyglet.graphics"), "Group", SimpleNamespace
    ):
        screen._draw(*screen._area())
    return outcome(run), shapes, colours


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.STEADY.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.steadicam_note({'STEADY_RUNG': rung})}"
    count = polygons = 0
    for rung in (1, 4, 10, 16, 30):
        for mode in range(5):
            where = rung, mode
            result, expected, colours = scene(rung, mode)
            assert next(rows) == f"frame {rung} {mode} {result}", where
            actual, labels = decode(rows, polygon_colours=colours)
            assert not labels
            assert actual.keys() == expected.keys(), (where, sorted(actual.keys(), key=str), sorted(expected.keys(), key=str))
            for key, commands in expected.items():
                compare_commands(actual[key], commands, (where, key))
                polygons += len(commands) if key[0] == "polygon" else 0
            count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Steadicam viewfinders (the sky, the grass, the trees and walkers far to near, the box framed "
          f"and not, the size marks and the cross; {polygons} clipped polygons) and nine option descriptions matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
