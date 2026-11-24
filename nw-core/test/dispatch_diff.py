"""Compare every field of consecutive seeded Dispatch schedules against Python."""
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

import pyglet

pyglet.options.shadow_window = False

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import dispatch
from neural_workshop.ui import dispatch as ui


RUNGS = (0, 1, 3, 4, 5, 6, 8, 12, 15, 20, 21, 25, 30, 512)


def compare(actual, expected, where):
    assert len(actual) == len(expected), where
    for index, (field, value) in enumerate(zip(actual, expected)):
        parsed = float(field) if isinstance(value, float) else int(field)
        assert parsed == value, (where, index, parsed, value)


ORDER_KINDS = {"incident": 1, "station": 2, "refit": 3}
EVENT_KINDS = {"saved": 1, "lost": 2, "false": 3, "report": 4, "refit": 5}


def read(rows, label, expected, where):
    kind, *fields = next(rows).split()
    assert kind == label, (where, label, kind, fields)
    compare(fields, expected, where)


def summary(rows, world, key):
    read(rows, "end", (world.time, world.damage, world.saved, world.lost, world.false_alarms), key)


def replay(rows, deal, policy, key):
    world = dispatch.World(deal)
    cycle = 0
    while not world.over:
        where = (*key, policy, cycle)
        if policy:
            for unit, kind, number in dispatch.reference_orders(world):
                read(rows, "order", (cycle, unit, ORDER_KINDS[kind], number), where)
                assert world.send(unit, kind, number)
            for _ in range(5):
                world.step(dispatch.SIM_DT)
        else:
            unit = cycle % len(world.units)
            kind = ("incident", "station", "refit")[cycle % 3]
            index = (cycle // 3) % (dispatch.SLOTS if kind == "incident" else 3)
            read(rows, "sent", (cycle, world.send(unit, kind, index)), where)
            world.step(0.43 if cycle % 2 == 0 else 0.31)
        for event, x, y in world.take_events():
            read(rows, "event", (cycle, EVENT_KINDS[event], x, y), where)
        cycle += 1
    summary(rows, world, key)

class Screen(ui.Dispatch):
    def __init__(self):
        self.start_rung = 8
        self.total_trials = 2
        self.adaptive = True
        self.coach = True
        self.rng = Random(-17)
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)

    def _note(self, *_):
        pass

    def _sync(self):
        pass


def controller(rows):
    screen = Screen()
    screen.start_run()
    coach_codes = {"Saved one": 1, "Lost one": 2}
    for trial in range(2):
        read(rows, "trial", (screen.rung, screen.trial, screen.par), trial)
        while screen.phase == "running":
            if trial == 0:
                for unit, kind, index in dispatch.reference_orders(screen.world):
                    screen.press(unit)
                    screen.press((ui.FIRST_SLOT if kind == "incident" else ui.FIRST_REFIT) + index)
            screen.now += 250
            screen.update(0.43)
            coach = coach_codes.get(screen.verdict_shown[1], 0) if screen.verdict_shown else 0
            read(rows, "update", (2 if screen.phase == "judged" else 1, coach, screen.world.time,
                                  -1 if screen.selected is None else screen.selected), (trial, screen.now))
        score = screen.score()
        read(rows, "score", (screen.rung, score["passed"], score["mean_damage"], screen.world.saved,
                             screen.world.lost), trial)
        read(rows, "early", (0,), trial)
        screen.now += 2199
        screen.update(0)
        assert screen.phase == "judged"
        screen.now += 1
        # Use the source clock deadline to avoid binary rounding at exact equality.
        screen.clock = lambda: max(screen.now / 1000, screen.feedback_until)
        screen.update(0)
        screen.clock = lambda: screen.now / 1000
    score = screen.score()
    assert screen.phase == "done"
    read(rows, "done", (3, score["best_rung"], score["mean_damage"], 0), "complete")
    screen.start_run()
    read(rows, "restart", (screen.rung, screen.trial, screen.score()["mean_damage"]), "restart")

def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    report_count = 0
    for seed in range(17, 17 + 421 * 4, 421):
        rng = Random(seed)
        for rung in RUNGS:
            deal = dispatch.deal(rung, rng=rng)
            level, reports = deal
            compare(next(rows).split(),
                    (level.rung, level.crews, level.scout, level.false_rate, level.error,
                     *level.growth, *level.need, level.burst, *level.lull, level.length,
                     level.refit, level.factor, level.grace, dispatch.longest_life(level), len(reports)),
                    (seed, rung))
            for index, report in enumerate(reports):
                compare(next(rows).split(), report, (seed, rung, index))
            report_count += len(reports)
            replay(rows, deal, True, (seed, rung))
            replay(rows, deal, False, (seed, rung))
            summary(rows, dispatch.idle_round(deal), (seed, rung, "idle"))
            read(rows, "par", (dispatch.par(deal),), (seed, rung))
    controller(rows)
    assert next(rows, None) is None
    print(f"PASS: {4 * len(RUNGS)} Dispatch schedules and {report_count} reports matched Python exactly")
    print("PASS: Dispatch reference orders, redirect replays, all world events, idle damage, and par matched Python")
    print("PASS: Dispatch selection, coaching, feedback timing, adaptive scoring, and restart matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
