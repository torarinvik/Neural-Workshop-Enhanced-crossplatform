"""Compare Rail Yard track geometry and seeded train plans against Python."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import railyard


def compare(rows, label, expected, where):
    kind, *fields = next(rows).split()
    assert kind == label and len(fields) == len(expected), (where, kind, fields, expected)
    actual = tuple(float(field) if isinstance(value, float) else int(field)
                   for field, value in zip(fields, expected))
    assert actual == tuple(expected), (where, label, actual, expected)


rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
kinds = {"switch": 0, "station": 1, "portal": 2, "merge": 3}
count = 0
for rung in range(1, 36):
    for seed in (-17, 0, 17, 2026):
        where = (rung, seed)
        yard = railyard.deal(rung, seed)
        compare(rows, "yard", (*yard.level, yard.seconds), where)
        for node, out in zip(yard.layout.nodes, yard.layout.out):
            compare(rows, "node", (kinds[node.kind], node.x, node.y, node.index, len(out)), where)
            for segment in out:
                compare(rows, "out", (segment,), where)
        for segment in yard.layout.segments:
            compare(rows, "segment", (segment.start, segment.end, segment.length, len(segment.points)), where)
            for point in segment.points:
                compare(rows, "point", point, where)
        for plan in yard.plans:
            compare(rows, "plan", plan, where)
            for leg in railyard.route(yard.layout, plan.portal, plan.station):
                compare(rows, "route", leg, where)
        count += 1
print(f"PASS: Rail Yard tracks, routes, train plans, and deadlines match Python across {count} deals")

train_states = {"due": 0, "waiting": 1, "running": 2, "right": 3, "wrong": 4, "lost": 5}
results = set()
ticks = 0
cases = [(rung, policy) for rung in (1, 4, 7, 10, 13, 16, 20, 26, 35) for policy in range(3)]
cases += [(1, 3)] + [(rung, 4) for rung in (1, 7, 13, 16, 20, 26, 35)]
for rung, policy in cases:
    run = railyard.Run(railyard.deal(rung, seed=17))
    for tick in range(5000):
        if policy == 1 and tick == 0:
            for portal in range(len(run.signals)):
                run.signal(portal)
        elif policy == 2:
            for port in range(len(run.points)):
                if (tick + 13 * port) % 47 == 0:
                    run.throw(port)
            for portal in range(len(run.signals)):
                if (tick + 31 * portal) % 171 == 0:
                    run.signal(portal)
        elif policy == 3:
            for train in run.trains:
                if train.state == "running" and train.segment == run.yard.layout.starts[0]:
                    if run.points[0].target != train.plan.station:
                        run.throw(0)
                    break
        elif policy == 4:
            ports = railyard.autopilot(run)
            compare(rows, "pilot", (sum(1 << port for port in ports),), (rung, policy, tick))
            for port in ports:
                if port < railyard.SIGNAL_PORT:
                    run.throw(port)
                else:
                    run.signal(port - railyard.SIGNAL_PORT)
        run.step(1 / 30)
        result = 0
        lost = [-1, -1]
        if run.result:
            passed, message = run.result
            if "derailed" in message or "collided" in message:
                result = 4 if "derailed" in message else 5
                lost = [train.number for train in run.trains if train.state == "lost"]
                lost += [-1] * (2 - len(lost))
            elif message.startswith("Time:"):
                result = 6 if passed else 3
            else:
                result = 1 if passed else 2
            results.add(result)
        where = (rung, policy, tick)
        compare(rows, "tick", (run.t, result, run.right_count(),
                               sum(train.state in ("right", "wrong") for train in run.trains),
                               *(run.crash or (0.0, 0.0)), *lost), where)
        for train in run.trains:
            compare(rows, "train", (train_states[train.state], train.segment, train.distance, train.left_at), where)
        for point in run.points:
            compare(rows, "switch", (point.way, point.target, point.moving), where)
        for signal in run.signals:
            compare(rows, "signal", (signal,), where)
        ticks += 1
        if run.result:
            break
    assert run.result is not None, (rung, policy)
assert results.issuperset({1, 2, 3, 4, 5}), results
print(f"PASS: Rail Yard simulation matches {ticks:,} Python ticks across {len(cases)} shifts")


from random import Random
from types import SimpleNamespace
import pyglet

pyglet.options.shadow_window = False
from neural_workshop.ui.railyard import RailYard


class Replay(RailYard):
    def __init__(self):
        self.rng = Random(17)
        self.start_rung = 13
        self.total_trials = 2
        self.adaptive = True
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.scenery = []
        self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
        self.result_code = 0

    def _redraw(self):
        pass

    def _deal(self):
        self.result_code = 0
        return super()._deal()

    def _judge(self, passed, message):
        if "derailed" in message:
            self.result_code = 4
        elif "collided" in message:
            self.result_code = 5
        elif message.startswith("Time:"):
            self.result_code = 6 if passed else 3
        else:
            self.result_code = 1 if passed else 2
        super()._judge(passed, message)


def session_row(screen):
    phase = {"ready": 0, "playing": 1, "judged": 2, "done": 3}[screen.phase]
    score = screen.score()
    compare(rows, "session", (phase, screen.rung, screen.trial, score["passed"], score["best_rung"],
                              screen.result_code, screen.run.right_count() if screen.run else 0,
                              screen.run.t if screen.run else 0.0), screen.now)


screen = Replay()
screen.start_run()
session_row(screen)
for trial in range(2):
    while screen.phase == "playing":
        if not trial:
            for port in railyard.autopilot(screen.run):
                screen.steer(port)
        screen.now += 137 if (screen.now // 11) % 3 == 0 else 11
        screen._tick()
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
print("PASS: Rail Yard controller matches Python substeps, feedback, adaptive rounds, and restart")
