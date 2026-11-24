"""Compare the street Kerbside draws, and its option descriptions, with Python headlessly."""
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
from neural_workshop import kerbside as model
from neural_workshop.ui import kerbside, taskoptions

RESULTS = {None: 0, True: 1}


@lru_cache(maxsize=None)
def deal(rung):
    return model.deal(rung, seed=17)


def outcome(run):
    if run.result is None:
        return 0
    if run.result[0]:
        return 1
    return 2 if run.result[1].startswith("Hit in lane ") else 3


def scene(rung, mode):
    screen = kerbside.Kerbside.__new__(kerbside.Kerbside)
    run = model.Run(deal(rung))
    screen.run = run
    frames = (0, 20, 60, 4000, 4000)[mode]
    last = 0.0
    for frame in range(1, frames + 1):
        if run.result is not None:
            break
        if mode == 4:
            control = model.FORWARD
        else:
            ports = model.autopilot(run)
            control = ports[0] if ports else None
        now = frame / 10
        dt = max(0.0, min(0.1, now - last))
        last = now
        steps = max(1, int(ceil(dt / (1 / 120.0))))
        for _ in range(steps):
            run.step(dt / steps, control)
            if run.result is not None:
                break

    shapes = defaultdict(list)
    screen.drawn, screen.batch = [], object()

    def frame(x, y, w, h, colour=None):
        screen.order = 0
        screen.clip = (x, y, x + w, y + h)

    def shape(name, *args, color, **kwargs):
        kind, _ = SHAPES[name]
        if name == "Line":
            args = (*args, kwargs["thickness"])
        shapes[kind, rgba(color)].append(args)
        return Label()

    screen.frame = frame
    factories = {name: (lambda *args, name=name, **kw: shape(name, *args, **kw))
                 for name in ("Rectangle", "Line", "Circle")}
    with patch.multiple(import_module("pyglet.shapes"), **factories), patch.object(
        import_module("pyglet.graphics"), "Group", SimpleNamespace
    ):
        screen._draw(*screen._area())
    return outcome(run), shapes


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.KERB.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.kerbside_note({'KERB_RUNG': rung})}"
    count = 0
    endings = set()
    for rung in (1, 4, 7, 10, 30):
        for mode in range(5):
            where = rung, mode
            result, expected = scene(rung, mode)
            endings.add(result)
            assert next(rows) == f"frame {rung} {mode} {result}", where
            actual, labels = decode(rows)
            assert not labels
            assert actual.keys() == expected.keys(), (where, actual.keys(), expected.keys())
            for key, commands in expected.items():
                compare_commands(actual[key], commands, (where, key))
            count += 1
    assert next(rows, None) is None
    assert endings == {0, 1, 2}, endings
    print(f"PASS: {count} Kerbside streets (the kerbs, the lanes and their lines, parked vans, and the walker "
          f"at the start, on the way, across and struck) and nine option descriptions matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
