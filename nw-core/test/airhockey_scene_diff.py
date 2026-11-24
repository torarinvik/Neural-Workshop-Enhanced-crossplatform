"""Compare rendered Air Hockey shapes with the Python scene without a window.

The reference's own `AirHockey._scene` draws each state; a stand-in records
its shapes, polygons and labels through the shared hand-task screen mapping,
and every one of them must appear, in order, in the Elisa frame. The host's
card, pointer, timer bar and session labels come on top, which is why this is
a subsequence check rather than an equality.

The verdict is not written down here: it is whatever `airhockey.play` makes of
the same deal, so a port that won a game the reference loses would fail.
"""
from math import cos, isclose, pi, sin
from pathlib import Path
from random import Random
import subprocess
import sys

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import airhockey
from neural_workshop.ui.airhockey import AirHockey
from neural_workshop.ui.handtask import SCREEN, clip_poly, clip_line


SCALE = 389 / 640
LEFT = (912 - 1000 * SCALE) / 2
BOTTOM = 179
JUDGED = 2


class Scene(AirHockey):
    def __init__(self):
        self.labels = []
        self.shapes = []
        self.polygons = []

    def g(self):
        return None

    def point(self, x, y):
        return LEFT + x * SCALE, BOTTOM + y * SCALE

    def rect(self, x, y, w, h, color, group):
        w, h = min(1000, x + w) - x, min(640, y + h) - y
        if w > 0 and h > 0:
            self.shapes.append((1, rgba(color), *self.point(x, y), w * SCALE, h * SCALE))

    def disc(self, at, radius, color, group):
        if radius <= at[0] <= 1000 - radius and radius <= at[1] <= 640 - radius:
            self.shapes.append((4, rgba(color), *self.point(*at[:2]), max(1, radius * SCALE), 0))
        elif -radius <= at[0] <= 1000 + radius and -radius <= at[1] <= 640 + radius:
            self.oval(at, radius, radius, color, group, n=16)

    def line(self, start, end, width, color, group):
        if start is None or end is None:
            return
        clipped = clip_line(start[:2], end[:2], SCREEN)
        if clipped:
            self.shapes.append((6, rgba(color), *self.point(*clipped[0]), *self.point(*clipped[1])))

    def poly(self, points, color, group):
        if any(point is None for point in points):
            return
        points = clip_poly([point[:2] for point in points], SCREEN)
        if len(points) < 3:
            return
        self.polygons.append((8, rgba(color), len(points), *self.point(*points[0])))
        self.polygons.extend((9, 0, 0, *self.point(*point)) for point in points[1:])

    def oval(self, point, rx, ry, color, group, n=20):
        self.poly([
            (point[0] + rx * cos(2 * pi * k / n), point[1] + ry * sin(2 * pi * k / n))
            for k in range(n)
        ], color, group)

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
    sketch._scene(run, run.t)
    _, shapes, polygons, labels = painted
    subsequence(shapes, sketch.shapes, name)
    subsequence(polygons, sketch.polygons, name)
    assert all(text in labels for text in sketch.labels), (name, labels, sketch.labels)
    return sketch


def pose(run, t):
    """The sweep's `pose`, field for field."""
    run.t, run.wait = t, 0.0
    run.puck, run.mine, run.theirs = (0.2, 0.8), (-0.3, 0.35), (0.25, 1.6)
    run.keeper, run.score = 0.1, [1, 0]


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    assert "Press Space or click to start" in frame(rows, "ready")[3]

    run = airhockey.Run(airhockey.deal(1, rng=Random(17)))
    compare("start", run, frame(rows, "start"))
    pose(run, 1.25)
    compare("posed", run, frame(rows, "posed"))

    run.t, run.wait = 0.2, 0.5
    blink = compare("blink", run, frame(rows, "blink"))
    # The point of this frame: the puck is not drawn, the two mallets are.
    posed = Scene()
    pose(run, 1.25)
    posed._scene(run, run.t)
    assert len(blink.polygons) < len(posed.polygons), "the serve blink drew the puck"

    game = airhockey.deal(20, rng=Random(17))
    run = airhockey.Run(game)
    pose(run, game.flips[0][0] + 0.5)
    assert run.far_end()
    far = compare("far", run, frame(rows, "far"))
    assert "FROM THE FAR END" in far.labels

    won, verdict = airhockey.play(airhockey.deal(1, rng=Random(17)))
    judged = frame(rows, "judged")
    assert judged[0][0] == JUDGED and judged[0][3] == (1 if won else 0), judged[0]
    assert verdict in judged[3], (verdict, judged[3])
    assert frame(rows, "hold") == judged
    done = frame(rows, "done")
    assert any(text.startswith("%d of 1 passed" % (1 if won else 0)) for text in done[3]), done[3]

    # The options note, against the reference's own taskoptions.airhockey_note.
    from neural_workshop.ui.taskoptions import airhockey_note
    notes = 0
    for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30, 0, 200):
        marker, got_rung, text = next(rows).split(" ", 2)
        assert (marker, int(got_rung)) == ("note", rung), (marker, got_rung)
        want = airhockey_note({"HOCKEY_RUNG": rung})
        assert text == want, (rung, text, want)
        notes += 1
    assert next(rows, None) is None
    print("PASS: 8 Air Hockey frames covering the table, both mallets, the puck and its serve blink, "
          "the keeper bar, the far-end camera, the score and the verdict (%s), and %d options notes"
          % (verdict, notes))


if __name__ == "__main__":
    check(sys.argv[1])
