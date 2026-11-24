"""Replay Crane's original yard generator, controls, and reference driver."""
from collections import defaultdict
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import crane

FAILURES = {
    "A container was dropped hard": 2,
    "Wrong bay for that colour": 3,
    "Set down outside a bay": 4,
    "The load struck something": 5,
    "Out of time": 6,
}


def compare(rows, label, expected, where, tolerance=2e-10):
    token, *fields = next(rows).split()
    assert token == label and len(fields) == len(expected), (where, label, token, fields, expected)
    for index, (raw, value) in enumerate(zip(fields, expected)):
        if isinstance(value, float):
            assert isclose(float(raw), value, rel_tol=0, abs_tol=tolerance), (where, label, index, raw, value)
        else:
            assert int(raw) == value, (where, label, index, raw, value)


def compare_yard(rows, yard, where):
    compare(rows, "yard", (*yard.level, yard.wall_x, yard.wind_sign, yard.gust_seed), where)
    for bay in yard.bays:
        compare(rows, "bay", bay, where)
    for box in yard.boxes:
        compare(rows, "box", box, where)


def compare_tick(rows, run, port, where):
    result = 0 if run.result is None else 1 if run.result[0] else FAILURES[run.result[1]]
    held = run.held if run.held is not None else -1
    state = [port, run.t, run.x, run.v, run.cable, run.theta, run.omega, held, run.placed, result,
             run.last_grab, *run.hook(), *run.hook_velocity()]
    for i, location in enumerate(run.where):
        code = {"held": -2, "ship": -1}.get(location[0])
        state.extend((location[1] if code is None else code, *run.box_rect(i)))
    compare(rows, "tick", state, where)
    return result


def replay(rows, yard, where, mode):
    run = crane.Run(yard)
    tick = 0
    while run.result is None and (mode != 3 or tick < 900):
        if mode == 3:
            port = tick // 63 % 6 - 1
        else:
            orders = crane.autopilot(run)
            port = orders[0] if orders and orders[0] is not None else -1
        if port == crane.GRAB:
            run.grab()
        run.step(1 / 60, None if port in (-1, crane.GRAB) else port)
        result = compare_tick(rows, run, port, (*where, tick))
        tick += 1
    return tick, result


def compare_edges(rows):
    yard = crane.deal(1, seed=17)
    for scenario in (0, 2, 3, 4, 5, 6):
        run = crane.Run(yard)
        index, bay = crane._next_job(run)
        run.x, base = run.box_rect(index)
        run.cable = crane.RAIL - (base + crane.BOX_H)
        run.grab()
        compare_tick(rows, run, crane.GRAB, ("grab", scenario))
        assert run.held == index
        target = 1 - bay if scenario == 3 else bay
        run.x = 18.0 if scenario == 4 else yard.bays[target].x
        run.cable = crane.RAIL - (crane.BOX_H + (3.0 if scenario == 2 else -0.2 if scenario in (0, 5) else 0.0))
        if scenario == 5:
            run.v = 1.0
        if scenario == 6:
            run.t = yard.level.seconds
            run.step(0.01, None)
        elif scenario in (0, 5):
            run._collide()
        else:
            run.grab()
        assert compare_tick(rows, run, -1, ("edge", scenario)) == scenario


def compare_session(rows):
    from neural_workshop.ui.crane import Crane, key

    class Screen(Crane):
        def __init__(self):
            self.start_rung = self.rung = 7
            self.total_trials = 2
            self.adaptive = True
            self.rng = Random(17)
            self.now = 0.0
            self.clock = lambda: self.now
            self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
            self.keys = defaultdict(bool)
            self.scenery = []
            self._reset()

        def _redraw(self):
            pass

    assert next(rows) == "session"
    screen = Screen()
    screen.start_run()
    for at in range(1, 13):
        screen.now = at * 0.125
        if at == 1:
            screen.keys[key.RIGHT] = True
        elif at == 2:
            screen.keys[key.A] = True
        elif at == 3:
            screen.keys[key.LEFT] = True
            screen.keys[key.A] = False
        elif at == 4:
            screen.steer(crane.DOWN)
        elif at == 6:
            screen.keys.clear()
        elif at == 7:
            screen.steer(crane.GRAB)
        elif at == 10:
            screen.run.placed = len(screen.run.yard.boxes)
        screen.update(0)
        score = screen.score()
        phase = 1 if screen.phase == "playing" else 2
        expected = (phase, screen.rung, screen.trial, score["passed"], score["best_rung"],
                    getattr(screen, "feedback_until", 0.0))
        compare(rows, "phase", expected, ("session", at))
        compare_tick(rows, screen.run, -1, ("session", at))
    screen.now = screen.feedback_until
    screen.update(0)
    compare_yard(rows, screen.run.yard, "second shift")
    screen.run.t = screen.run.level.seconds
    screen.now = 5.0
    screen.update(0)
    assert screen.phase == "judged"
    # The agent publishes the judged frame and then deals immediately.
    screen._next_trial()
    score = screen.score()
    compare(rows, "done", (3, screen.rung, screen.trial, score["passed"], score["best_rung"]), "done")
    screen.start_rung, screen.total_trials, screen.adaptive = 4, 1, False
    screen.now = 6.0
    screen.start_run()
    compare_yard(rows, screen.run.yard, "restart")


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    candidates = ticks = runs = deal_edges = 0
    verdicts = set()
    while (header := next(rows)) != "edges":
        label, *numbers = header.split()
        assert label == "case", header
        rung, seed, mode = where = tuple(map(int, numbers))
        draw = Random(seed)
        if mode == 0:
            for attempt in range(3):
                compare_yard(rows, crane._build(crane.grade(rung), draw), (*where, attempt))
                candidates += 1
        elif mode == 4:
            first = crane._build(crane.grade(rung), draw)
            assert not crane.play(first)[0], where
            chosen = crane.deal(rung, seed=seed)
            assert (chosen == first) == (rung == 60), where
            compare_yard(rows, chosen, where)
            deal_edges += 1
        else:
            yard = crane.deal(rung, seed=seed) if mode == 2 else crane._build(crane.grade(rung), draw)
            compare_yard(rows, yard, where)
            count, result = replay(rows, yard, where, mode)
            ticks += count
            runs += 1
            verdicts.add(result)
        assert next(rows) == "end", where
    compare_edges(rows)
    compare_session(rows)
    assert next(rows, None) is None
    assert candidates == 99 and runs == 20 and deal_edges == 2 and 1 in verdicts
    print(f"PASS: {candidates + runs + deal_edges + 7} Crane cases match Python ({candidates} candidates, {ticks:,} ticks, retry and fallback, six contact and release scenarios, timed session)")


if __name__ == "__main__":
    main(sys.argv[1])
