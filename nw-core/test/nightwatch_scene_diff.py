"""Compare rendered Night Watch shapes with the Python scene without a window.

The reference's own `NightWatch._scene` draws each state; a stand-in records
its shapes, polygons and labels through the shared hand-task screen mapping,
and every one of them must appear, in order, in the Elisa frame. The host's
card, pointer, time bar and session labels come on top, which is why this is
a subsequence check rather than an equality.

Mid-game states are reached the way the sweep reaches them: nightwatch.Run
stepped 1/60 s at a time with the reference autopilot, a hand that goes for
the guard and the cat, or the view turned along a wide floor. The verdicts
are whatever `nightwatch.play` and an unattended run make of the same deal.
"""
from math import cos, hypot, isclose, pi, sin
from pathlib import Path
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import nightwatch as model
from neural_workshop import hand as H
from neural_workshop.ui.nightwatch import NightWatch
from neural_workshop.ui.handtask import SCREEN, clip_poly, clip_line


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2
BOTTOM = 179


class Scene(NightWatch):
    def __init__(self):
        self.labels = []
        self.shapes = []
        self.polygons = []

    def g(self):
        return None

    def point(self, x, y):
        return LEFT + x * SCALE, BOTTOM + y * SCALE

    def rect(self, x, y, w, h, color, group):
        x1, y1 = min(1000, x + w), min(640, y + h)
        x, y = max(0.0, x), max(0.0, y)
        w, h = x1 - x, y1 - y
        if w > 0 and h > 0:
            self.shapes.append((1, rgba(color), *self.point(x, y), w * SCALE, h * SCALE))

    def disc(self, at, radius, color, group):
        if not (-radius <= at[0] <= 1000 + radius and -radius <= at[1] <= 640 + radius):
            return
        if radius <= at[0] <= 1000 - radius and radius <= at[1] <= 640 - radius:
            self.shapes.append((4, rgba(color), *self.point(*at[:2]), max(1, radius * SCALE), 0))
        else:
            self.poly([(at[0] + radius * cos(pi * k / 8), at[1] + radius * sin(pi * k / 8)) for k in range(16)],
                      color, group)

    def line(self, start, end, width, color, group):
        if start is None or end is None:
            return
        clipped = clip_line(start[:2], end[:2], SCREEN)
        if clipped:
            self.shapes.append((6, rgba(color), *self.point(*clipped[0]), *self.point(*clipped[1])))

    def poly(self, points, color, group):
        if len(points) < 3 or any(point is None for point in points):
            return
        points = clip_poly([point[:2] for point in points], SCREEN)
        if len(points) < 3:
            return
        self.polygons.append((8, rgba(color), len(points), *self.point(*points[0])))
        self.polygons.extend((9, 0, 0, *self.point(*point)) for point in points[1:])

    def words(self, text, *args, **kwargs):
        self.labels.append(text)


def rgba(color):
    return int.from_bytes(bytes((*color, 255) if len(color) == 3 else color), "big")


def frame(rows, expected):
    marker, name, *state = next(rows).split()
    assert (marker, name) == ("frame", expected), (marker, name, expected)
    shapes, polygons, labels = [], [], []
    for line in rows:
        if line == "end":
            break
        kind, *values = line.split()
        if kind == "shape":
            shapes.append(tuple(map(float, values)))
        elif kind == "poly":
            polygons.append(tuple(map(float, values)))
        else:
            labels.append(line)
    return tuple(map(int, state)), shapes, polygons, labels


def matches(actual, expected):
    return len(actual) == len(expected) and all(isclose(a, b, rel_tol=0, abs_tol=0.00015) for a, b in zip(actual, expected))


def subsequence(actual, expected, name):
    available = iter(actual)
    for wanted in expected:
        assert any(matches(item, wanted) for item in available), (name, wanted)


def compare(name, run, painted):
    sketch = Scene()
    sketch._scene(run, 1.0)
    _, shapes, polygons, labels = painted
    subsequence(shapes, sketch.shapes, name)
    subsequence(polygons, sketch.polygons, name)
    assert all(text in labels for text in sketch.labels), (name, labels, sketch.labels)
    return sketch, labels


def run_for(rung):
    """The run the sweep's `session(rung)` deals: one trial, seed 17."""
    return model.Run(model.deal(rung, rng=Random(17)))


def wrong(run):
    if run.result is not None:
        return None
    if run.hand.down:
        return H.RELEASE
    best = None
    for k, w in enumerate(run.night.walkers):
        if w.kind == model.THIEF:
            continue
        q = run.spot(k)
        if q is None:
            continue
        d = hypot(q[0] - run.hand.x, q[1] - run.hand.y)
        if best is None or d < best[0]:
            best = (d, k, q)
    if best is None:
        return None
    if run.under() == best[1]:
        return H.PRESS
    return H.toward(run.hand, best[2][0], best[2][1], tol=6.0)


def walk(run, steps, mode, until=0):
    for n in range(steps):
        if run.result is not None:
            break
        if until == 1 and run.strikes > 0:
            break
        if mode == 0:
            ports = model.autopilot(run)
            port = ports[0] if ports else None
        elif mode == 3:
            port = wrong(run)
        else:
            port = None if n % 3 else (model.LEFT if (n // 30) % 2 == 0 else model.RIGHT)
        control = None
        if port is not None:
            if port in model.EVENTS:
                model.act(run, port)
            else:
                control = port
        run.step(1 / 60, control)


def unattended(night):
    run = model.Run(night)
    while run.result is None:
        run.step(1 / 60)
    return run.result


def shot(rows, rung, steps, mode, name, until=0):
    run = run_for(rung)
    walk(run, steps, mode, until)
    painted = frame(rows, name)
    assert painted[0][4] == run.caught, (name, painted[0], run.at)
    return run, *compare(name, run, painted)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    assert "Press Space or click to start" in frame(rows, "ready")[3]

    run, _, labels = shot(rows, 1, 183, 0, "fixed")
    assert "Tonight the thieves wear red. The guard wears blue." in labels
    assert any(run.lit(k) for k in range(len(run.night.walkers))), "nobody in the torch at rung 1"
    run, _, labels = shot(rows, 10, 185, 0, "orders")
    assert run.orders() in labels and not run.level.fixed
    assert sum(run.lit(k) for k in range(len(run.night.walkers))) >= 2
    run, sketch, labels = shot(rows, 7, 100, 4, "wide")
    assert run.room() > 0 and run.cam != 0.0 and ("<  A" in labels or "D  >" in labels), (run.cam, labels)
    run, _, labels = shot(rows, 10, 4000, 3, "struck", 1)
    assert run.strikes == 1, run.strikes
    run, _, labels = shot(rows, 16, 187, 0, "weave")
    assert run.level.weave > 0 and any(run.lit(k) for k in range(len(run.night.walkers)))
    run, _, _ = shot(rows, 10, 804, 0, "cat")
    assert any(w.kind == model.CAT and run.lit(k) for k, w in enumerate(run.night.walkers)), "no cat in the torch"

    night = model.deal(1, rng=Random(17))
    won, verdict = model.play(night)
    passed = frame(rows, "passed")
    assert won and passed[0][0] == 2 and passed[0][3] == 1, passed[0]
    assert verdict in passed[3], (verdict, passed[3])
    assert frame(rows, "hold") == passed
    done = frame(rows, "done")
    assert any(text.startswith("1 of 1 passed") for text in done[3]), done[3]

    lost, why = unattended(night)
    failed = frame(rows, "failed")
    assert not lost and failed[0][3] == 0, failed[0]
    assert why in failed[3], (why, failed[3])

    from neural_workshop.ui.taskoptions import nightwatch_note
    notes = 0
    for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30, 0, 200):
        marker, got_rung, text = next(rows).split(" ", 2)
        assert (marker, int(got_rung)) == ("note", rung), (marker, got_rung)
        want = nightwatch_note({"WATCH_RUNG": rung})
        assert text == want, (rung, text, want)
        notes += 1
    assert next(rows, None) is None
    print("PASS: 11 Night Watch frames covering the dark floor and its crates, the torch, the safe and its lamp, "
          "lit thieves, guards and the cat, the orders, the whistle and strikes, the turned view and its arrows, "
          "weaving thieves, and both verdicts (%s; %s), and %d options notes" % (verdict, why, notes))


if __name__ == "__main__":
    check(sys.argv[1])
