"""Compare Crazy Cog session scenes with Python using windowless drawing hooks."""
from collections import Counter
from math import ceil, isclose
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
from neural_workshop import crazycog
from neural_workshop.ui.crazycog import CrazyCog
from neural_workshop.ui.taskoptions import crazycog_note


SCALE = 389 / 640
LEFT = (912 - SCALE * 1000) / 2
BOTTOM = 179


def rgba(channels):
    return int.from_bytes(bytes((*channels, 255) if len(channels) == 3 else channels), "big")


class Scene(CrazyCog):
    def __init__(self):
        self.shapes = []
        self.labels = []

    def g(self):
        return None

    def rect(self, x, y, w, h, color, group):
        left, bottom = max(0., x), max(0., y)
        width, height = min(1000., x + w) - left, min(640., y + h) - bottom
        if width > 0 and height > 0:
            self.shapes.append((1, rgba(color), LEFT + left * SCALE, BOTTOM + bottom * SCALE, width * SCALE, height * SCALE))

    def disc(self, p, r, color, group):
        x, y = p
        if r <= x <= 1000. - r and r <= y <= 640. - r:
            self.shapes.append((4, rgba(color), LEFT + x * SCALE, BOTTOM + y * SCALE, r * SCALE, 0.))

    def poly(self, *args):
        pass

    def line(self, *args):
        pass

    def oval(self, *args):
        pass

    def words(self, text, *args, **kwargs):
        self.labels.append(text)


def parse(binary):
    notes, frames = {}, []
    for row in subprocess.check_output([binary], text=True).splitlines():
        kind, data = row.split(" ", 1)
        if kind == "note":
            rung, message = data.split(" ", 1)
            notes[int(rung)] = message
        elif kind == "frame":
            label, *fields = data.split()
            texts, shapes = [], []
            frames.append((label, tuple(map(int, fields)), texts, shapes))
        elif kind == "text":
            texts.append(data)
        else:
            command, color, *coords = data.split()
            shapes.append((int(command), int(color), *map(float, coords)))
    return notes, iter(frames)


def check_geometry(frame, run):
    label, _, texts, shapes = frame
    scene = Scene()
    scene._scene(run, SCALE)
    assert not (Counter(scene.labels) - Counter(texts)), (label, scene.labels, texts)
    available = shapes.copy()
    for expected in scene.shapes:
        for i, actual in enumerate(available):
            if expected[:2] == actual[:2] and all(isclose(a, b, abs_tol=0.0001) for a, b in zip(expected[2:], actual[2:])):
                available.pop(i)
                break
        else:
            raise AssertionError((label, run.level.rung, expected))


def check(binary):
    notes, rows = parse(binary)
    options = (1, 4, 7, 10, 13, 16, 20, 25, 30)
    assert notes == {rung: crazycog_note({"COG_RUNG": rung}) for rung in options}, notes
    for rung in (1, 20):
        label, state, texts, _ = next(rows)
        assert label == "ready" and state[:4] == (0, rung, 0, 0) and "Press Space or click to start" in texts
        run = crazycog.Run(crazycog.deal(rung, rng=Random(17)))
        start = next(rows)
        assert start[0] == "start" and start[1] == (1, rung, 1, 0, 0, 0, 0, 0)
        check_geometry(start, run)
        run.hand.to(*crazycog.slot(0, run.slots()))
        crazycog.act(run, crazycog.H.PRESS)
        run.hand.to(*run.machine.motor)
        drag = next(rows)
        assert drag[0] == "drag" and drag[1][5] == run.carry
        check_geometry(drag, run)
        crazycog.act(run, crazycog.H.RELEASE)
        crazycog.act(run, crazycog.CLEAR)
        for _ in range(run.level.layers - 1):
            crazycog.act(run, crazycog.LAYER)
        layer = next(rows)
        assert layer[0] == "layer" and layer[1][4] == run.layer
        check_geometry(layer, run)
        while run.layer:
            crazycog.act(run, crazycog.LAYER)
        now = 0.
        for i in range(1, 20001):
            port = next(iter(crazycog.autopilot(run)), -1)
            if port >= 0:
                crazycog.act(run, port)
            tick = i / 60
            dt = tick - now
            now = tick
            steps = max(1, ceil(dt / (1 / 120)))
            for _ in range(steps):
                run.step(dt / steps)
                if run.result:
                    break
            if run.result:
                break
        assert run.result == (True, "Bucket up"), run.result
        for label, phase in (("judged", 2), ("feedback", 2), ("done", 3)):
            frame = next(rows)
            assert frame[:2] == (label, (phase, rung + 1, 1, 1, run.layer, 0, 1, len(run.notes))), frame[:2]
            assert run.result[1] in frame[2]
            if phase == 2:
                check_geometry(frame, run)
    assert next(rows, None) is None
    print("PASS: 14 Crazy Cog scenes match Python board geometry, controls, and session outcomes")


if __name__ == "__main__":
    check(sys.argv[1])
