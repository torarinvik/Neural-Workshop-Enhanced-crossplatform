"""Replay Firebreak's fire and reference crew against the frozen Python model."""
from math import isclose
from pathlib import Path
import subprocess
import sys
from random import Random
from types import SimpleNamespace

import pyglet

pyglet.options.shadow_window = False

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import firebreak
from neural_workshop.ui.firebreak import Firebreak

rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
states = {None: 0, "The fire reached the town": 1, "Still burning when time ran out": 3}
seen = set()
ticks = 0


def frame(blaze):
    label, elapsed, col, row, shovels, ready, result, burned, digest = next(rows).split()
    assert label == "frame"
    verdict = states[blaze.result[1]] if blaze.result and not blaze.result[0] else 2 if blaze.result else 0
    seen.add(verdict)
    hashed = 14695981039346656037
    for terrain, state, thrown in zip(blaze.terrain, blaze.state, blaze.thrown):
        hashed = ((hashed ^ (terrain + 6 * state + 18 * thrown)) * 1099511628211) & ((1 << 64) - 1)
    assert float(elapsed) == blaze.t and float(ready) == blaze.ready_at
    assert (int(col), int(row), int(shovels), int(result), int(burned), int(digest)) == (
        *blaze.cursor, blaze.shovels, verdict, blaze.burned(), hashed
    ), (blaze.land.rung, blaze.t, result, blaze.result)


for rung in (1, 7, 10, 13, 16, 25):
    for policy in range(2):
        assert next(rows) == f"case {rung} {policy}"
        blaze = firebreak.Blaze(firebreak.deal(rung, seed=17))
        arrive = blaze.arrival()
        for cell in range(firebreak.COLS * firebreak.ROWS):
            assert isclose(float(next(rows)), arrive.get(cell, 1e9), rel_tol=0.0, abs_tol=1e-12), (rung, cell)
        frame(blaze)
        while blaze.result is None:
            if policy:
                label, *actual_ports = next(rows).split()
                expected_ports = firebreak.autopilot(blaze)
                assert label == "ports" and list(map(int, actual_ports)) == expected_ports, (rung, blaze.t)
                for port in expected_ports:
                    firebreak.apply(blaze, port)
            blaze.step(1 / 30)
            frame(blaze)
            ticks += 1
blaze = firebreak.Blaze(firebreak.deal(13, seed=17))
blaze.t = 119.9
for fire in blaze.land.fires:
    blaze.lit_at[fire] = blaze.t
blaze.step(0.1)
frame(blaze)
assert seen == {0, 1, 2, 3}
class Screen(Firebreak):
    def __init__(self):
        self.rng = Random(-17)
        self.start_rung = 16
        self.total_trials = 2
        self.adaptive = True
        self.clock = lambda: self.now / 1000
        self.now = 0
        self.scenery = []
        self.overlay = {}
        self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
        self.last_result = 0

    def _redraw(self):
        pass

    def _judge(self, passed, message):
        self.last_result = 2 if passed else states[message]
        super()._judge(passed, message)

    def _deal(self):
        self.last_result = 0
        return super()._deal()


def session_row(screen):
    label, *fields = next(rows).split()
    assert label == "session"
    expected = {"ready": 0, "playing": 1, "judged": 2, "done": 3}[screen.phase]
    cursor = screen.blaze.cursor if screen.blaze else (0, 0)
    assert tuple(map(int, fields[:-1])) == (
        expected, screen.rung, screen.trial, screen.score()["passed"], screen.score()["best_rung"],
        screen.last_result, *cursor, screen.blaze.shovels if screen.blaze else 0,
    ), (screen.now, fields)
    assert float(fields[-1]) == (screen.blaze.t if screen.blaze else 0), (screen.now, fields)


screen = Screen()
screen.start_run()
session_row(screen)
for _ in range(2):
    screen.blaze.put(15, 9)
    screen.blaze.dig()
    screen.steer(8)
    while screen.phase == "playing":
        screen.now += 250 if not screen.blaze.t else 50
        screen.update(0)
        session_row(screen)
    screen.now += 2999
    screen.update(0)
    session_row(screen)
    screen.now += 1
    screen.update(0)
    session_row(screen)
screen.now += 1
screen.start_run()
session_row(screen)
assert next(rows, None) is None
print(f"PASS: Firebreak arrival maps, reference orders, and {ticks:,} simulation ticks match Python")
print("PASS: Firebreak round controller matches Python pointer digs, four-cell moves, frame clamp, timed verdicts, adaptation, and restart")
