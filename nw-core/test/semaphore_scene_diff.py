"""Compare rendered Semaphore shapes with the Python scene without a window.

The reference's own `Semaphore._scene` draws each state; a stand-in records
its shapes, polygons and labels through the shared hand-task screen mapping,
and every one of them must appear, in order, in the Elisa frame. The host's
card, pointer and session labels come on top, which is why this is a
subsequence check rather than an equality.

Mid-game states are reached the way the sweep reaches them: semaphore.Run
stepped 1/60 s at a time, with the reference autopilot or with nobody. The
verdicts are not written down here: they are whatever `semaphore.play` and
an unattended run make of the same deal.
"""
from math import cos, isclose, pi, sin
from pathlib import Path
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import semaphore
from neural_workshop.ui.semaphore import Semaphore
from neural_workshop.ui.handtask import SCREEN, clip_poly, clip_line


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2
BOTTOM = 179


class Scene(Semaphore):
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
    return sketch


def run_for(rung):
    """The run the sweep's `session(rung)` deals: one trial, seed 17."""
    return semaphore.Run(semaphore.deal(rung, rng=Random(17)))


def walk(run, steps, piloted, until=0):
    for _ in range(steps):
        if run.result is not None:
            break
        if until == 1 and run.back():
            break
        if until == 2 and run.fogged() and run.index() is not None:
            break
        ports = semaphore.autopilot(run) if piloted else []
        if ports:
            semaphore.act(run, ports[0])
        run.step(1 / 60)


def unattended(message):
    run = semaphore.Run(message)
    while run.result is None:
        run.step(1 / 60)
    return run.result


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    assert "Press Space or click to start" in frame(rows, "ready")[3]

    run = run_for(1)
    walk(run, 200, True)
    named = compare("named", run, frame(rows, "named"))
    assert run.message.text[run.index()] in named.labels and "Z" in named.labels

    run = run_for(1)
    walk(run, 780, False)
    struck = frame(rows, "struck")
    assert struck[0][4] == run.strikes == 1, (struck[0], run.strikes)
    compare("struck", run, struck)

    run = run_for(13)
    walk(run, 6000, True, 1)
    assert run.back()
    back = compare("back", run, frame(rows, "back"))
    assert "their back is to you" in back.labels

    run = run_for(25)
    walk(run, 6000, True, 2)
    assert run.fogged()
    compare("fog", run, frame(rows, "fog"))

    message = semaphore.deal(1, rng=Random(17))
    won, verdict = semaphore.play(message)
    passed = frame(rows, "passed")
    assert won and passed[0][0] == 2 and passed[0][3] == 1, passed[0]
    assert verdict in passed[3], (verdict, passed[3])
    assert frame(rows, "hold") == passed
    done = frame(rows, "done")
    assert any(text.startswith("1 of 1 passed") for text in done[3]), done[3]

    lost, why = unattended(message)
    failed = frame(rows, "failed")
    assert not lost and failed[0][3] == 0, failed[0]
    assert why in failed[3], (why, failed[3])

    from neural_workshop.ui.taskoptions import semaphore_note
    notes = 0
    for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30, 0, 200):
        marker, got_rung, text = next(rows).split(" ", 2)
        assert (marker, int(got_rung)) == ("note", rung), (marker, got_rung)
        want = semaphore_note({"SEMA_RUNG": rung})
        assert text == want, (rung, text, want)
        notes += 1
    assert next(rows, None) is None
    print("PASS: 9 Semaphore frames covering the sea and the rolling ship, the signaller's flags and back, "
          "fog, your flags and their grips, the named letter, the chart and its peek, the message, strikes, "
          "and both verdicts (%s; %s), and %d options notes" % (verdict, why, notes))


if __name__ == "__main__":
    check(sys.argv[1])
