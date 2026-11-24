"""Replay seeded Crossroads towns and their reference crews against Python."""
from pathlib import Path
import subprocess
import sys
from random import Random
from types import SimpleNamespace

import pyglet

pyglet.options.shadow_window = False

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import crossroads
from neural_workshop.ui.crossroads import Crossroads

AXIS = {"EW": 0, "NS": 1}


def compare(rows, label, expected, where):
    kind, *fields = next(rows).split()
    assert kind == label and len(fields) == len(expected), (where, kind, fields, expected)
    actual = tuple(float(field) if isinstance(value, float) else int(field)
                   for field, value in zip(fields, expected))
    assert actual == tuple(expected), (where, label, actual, expected)


rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
ticks = 0
results = set()
for rung in (1, 4, 7, 10, 13, 16, 20, 25):
    town = crossroads.deal(rung, seed=17)
    compare(rows, "town", (*town.level, len(town.paths), len(town.arrivals)), rung)
    for point, green in zip(town.junctions, town.start_green):
        compare(rows, "junction", (*point, AXIS[green]), rung)
    for path in town.paths:
        compare(rows, "path", (*path[:5], len(path.crosses), AXIS[path.axis]), rung)
        for cross in path.crosses:
            compare(rows, "cross", cross, rung)
    for arrival in town.arrivals:
        compare(rows, "arrival", arrival, rung)
    for policy in range(2):
        run = crossroads.Run(town)
        while run.result is None:
            ports = crossroads.autopilot(run) if policy else []
            for port in ports:
                run.toggle(port)
            run.step(1 / 30)
            result = 0
            if run.result is not None:
                result = 1 if run.result[0] else 2 if run.result[1].startswith("Gridlock") else 3
                results.add(result)
            where = rung, policy, run.t
            compare(rows, "tick", (sum(1 << port for port in ports), run.t, result,
                                   run.served, len(run.cars), run.total_wait), where)
            for light in run.lights:
                compare(rows, "light", (AXIS[light.green], light.changing is not None, light.since), where)
            for waiting in run.backlog.values():
                compare(rows, "queue", (len(waiting),), where)
            for car in run.cars:
                compare(rows, "car", (car.path, car.s, car.v, car.ambulance, car.waited, car.colour, car.born), where)
            ticks += 1
assert results == {1, 2, 3}, results
class Screen(Crossroads):
    def __init__(self):
        self.rng = Random(-17)
        self.start_rung = 13
        self.total_trials = 2
        self.adaptive = True
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.scenery = []
        self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
        self.last_result = 0

    def _redraw(self):
        pass

    def _judge(self, passed, message):
        self.last_result = 1 if passed else 2 if message.startswith("Gridlock") else 3
        super()._judge(passed, message)

    def _deal(self):
        self.last_result = 0
        return super()._deal()


def session_row(screen):
    phase = {"ready": 0, "playing": 1, "judged": 2, "done": 3}[screen.phase]
    score = screen.score()
    compare(rows, "session", (phase, screen.rung, screen.trial, score["passed"], score["best_rung"],
                              screen.last_result, screen.run.served if screen.run else 0,
                              screen.run.t if screen.run else 0.0), screen.now)


screen = Screen()
screen.start_run()
session_row(screen)
for trial in range(2):
    while screen.phase == "playing":
        if not trial:
            for port in crossroads.autopilot(screen.run):
                screen.steer(port)
        screen.now += 250 if not screen.run.t else 50
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
print(f"PASS: Crossroads selected deals, reference switches, and {ticks:,} traffic ticks match Python")
print("PASS: Crossroads controller matches Python frame clamp, substeps, feedback, adaptation, and restart")
