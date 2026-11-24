"""Replay seeded Air Traffic scenarios and flight paths against Python."""
from math import isclose
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import airtraffic as model


def compare(rows, tag, expected, context):
    kind, *values = next(rows).split()
    assert kind == tag and len(values) == len(expected), (context, tag, kind, values)
    for raw, want in zip(values, expected):
        actual = float(raw) if isinstance(want, float) else int(raw)
        assert (isclose(actual, want, rel_tol=1e-13, abs_tol=1e-10)
                if isinstance(want, float) else actual == want), (context, tag, actual, want)


def fuel(value):
    return -1.0 if value is None else value


def deal(rows, rung, seed):
    sky = model.deal(rung, seed)
    grade = sky.level
    context = rung, seed
    compare(rows, "grade", (*grade[:6], fuel(grade.fuel), *grade[7:]), context)
    compare(rows, "sky", (*(sky.closure or (-1, 0.0, 0.0)),
                          -1.0 if sky.shift is None else sky.shift, sky.seconds), context)
    for runway in sky.runways:
        compare(rows, "runway", runway, context)
    for plan in sky.arrivals:
        compare(rows, "plan", (*plan[:5], fuel(plan.fuel)), context)
    for storm in sky.storms:
        compare(rows, "storm", storm, context)


MODES = {"free": 0, "hold": 1, "approach": 2, "final": 3}
NOTICES = {"landed": 0, "go around: wind change": 1, "go around: missed the runway": 2,
           "go around: runway closed": 3, "go around: runway busy": 4,
           "go around: not lined up": 5}


def verdict(run):
    if run.result is None:
        return 0, -1, -1
    passed, message = run.result
    if passed:
        return 1, -1, -1
    if message.startswith("Time:"):
        return 2, -1, -1
    slots = [int(number) - 1 for number in re.findall(r"\d+", message)]
    if "collided" in message:
        return 6, *slots
    reason = 3 if "fuel" in message else 4 if "airspace" in message else 5
    return reason, slots[0], -1


def tick_row(rows, run, context):
    result, first, second = verdict(run)
    compare(rows, "tick", (run.t, len(run.planes), len(run.sky.arrivals) - len(run.waiting),
                           -1 if run.selected is None else run.selected, run.flipped,
                           result, first, second, *(run.lost_at or (0.0, 0.0))), context)
    for plane in run.planes:
        compare(rows, "plane", (plane.number, plane.slot, plane.runway, plane.x, plane.y,
                                plane.heading, plane.target, fuel(plane.fuel), MODES[plane.mode], plane.cleared), context)
    for storm in run.storms:
        compare(rows, "storm", (storm.x, storm.y, storm.vx, storm.vy, storm.radius), context)
    for busy in run.busy_until:
        compare(rows, "busy", (busy,), context)
    compare(rows, "landed", (len(run.landed),), context)
    for plane in run.landed:
        compare(rows, "arrival", (plane,), context)
    notes = run.notes[-6:]
    compare(rows, "notes", (len(notes),), context)
    for when, what, x, y in notes:
        compare(rows, "note", (when, NOTICES[what], x, y), context)
    return result


def replay(rows, rung, seed, policy):
    run = model.Run(model.deal(rung, seed))
    for tick in range(7000):
        if policy == 1 and run.planes and tick % 113 == 0:
            pick = run.planes[(tick // 113) % len(run.planes)]
            run.select(pick.slot)
            run.order(tick // 113 % 4)
        elif policy == 2:
            for plane in run.planes:
                if not plane.cleared:
                    run.select(plane.slot)
                    run.order(model.LAND)
        elif policy == 3:
            ports = model.autopilot(run)
            expected = (-1, -1) if not ports else (ports[0] if len(ports) > 1 else -1, ports[-1] - model.SLOTS)
            compare(rows, "instruction", expected, (rung, seed, policy, tick))
            for port in ports:
                model.apply(run, port)
        run.step(1 / 30)
        result = tick_row(rows, run, (rung, seed, policy, tick))
        if result:
            return tick + 1, result, {what for _, what, _, _ in run.notes}
    raise AssertionError((rung, seed, policy, "did not finish"))


def edge_case(rows, which):
    from math import cos, radians, sin
    sky = model.deal(10, 17)
    if which == 0:
        sky = sky._replace(seconds=0.5)
    elif which == 4:
        sky = sky._replace(shift=1.01)
    run = model.Run(sky)
    run.t = 1.0
    number, arrival = run.waiting.pop(0)
    plane = model.Plane(number, arrival, 0)
    run.planes.append(plane)
    run.selected = 0
    plane.x, plane.y = run.threshold(0)
    plane.heading = plane.target = run.runway_heading(0)
    if which == 3:
        plane.x += cos(radians(plane.heading)) * 6
        plane.y += sin(radians(plane.heading)) * 6
    plane.mode = "free" if which <= 1 else "approach" if which == 4 else "final"
    plane.cleared = plane.mode != "free"
    plane.fuel = 0.01 if which == 1 else 100.0
    run.busy_until[0] = 3.0 if which == 2 else 0.0
    run.step(1 / 30)
    return tick_row(rows, run, ("edge", which)), {what for _, what, _, _ in run.notes}


def lifecycle(rows):
    from random import Random
    from types import SimpleNamespace
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui.airtraffic import AirTraffic

    class Replay(AirTraffic):
        def __init__(self):
            self.rng = Random(17)
            self.start_rung = 1
            self.total_trials = 2
            self.adaptive = True
            self.now = 0
            self.clock = lambda: self.now / 1000
            self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
            self.report = 0

        def _deal(self):
            self.report = 0
            return super()._deal()

        def _redraw(self):
            pass

        def _judge(self, passed, message):
            self.report = verdict(self.run)[0]
            super()._judge(passed, message)

    def summary(screen):
        phase = {"playing": 1, "judged": 2, "done": 3}[screen.phase]
        score = screen.score()
        run = screen.run
        compare(rows, "session", (phase, screen.rung, screen.trial, score["passed"], score["best_rung"],
                                  screen.report, len(run.landed) if run else 0,
                                  run.t if run else 0.0, screen.trail_clock if run else 0.0), screen.now)
        if run:
            for number in range(run.sky.level.planes):
                trail = screen.trails.get(number, ())
                compare(rows, "trail", (len(trail),), screen.now)
                for point in trail:
                    compare(rows, "point", point, screen.now)

    screen = Replay()
    screen.start_run()
    summary(screen)
    for trial in range(2):
        while screen.phase == "playing":
            if not trial:
                for port in model.autopilot(screen.run):
                    screen.steer(port)
            screen.now += 137 if (screen.now // 11) % 3 == 0 else 11
            screen.update(0)
            summary(screen)
        screen.now += 2999
        screen.update(0)
        summary(screen)
        screen.now += 1
        screen.update(0)
        summary(screen)
    screen.now += 1
    screen.start_run()
    summary(screen)


def main(binary):
    process = subprocess.Popen([binary], stdout=subprocess.PIPE, text=True)
    with process:
        rows = iter(process.stdout)
        for rung in range(1, 41):
            for seed in (-17, 0, 17, 2026):
                deal(rows, rung, seed)
        ticks, results, notes = 0, set(), set()
        for rung in (1, 4, 7, 10, 13, 16, 20, 25, 35):
            for policy in range(4):
                count, result, events = replay(rows, rung, 17, policy)
                ticks += count
                results.add(result)
                notes.update(events)
        for which in range(5):
            result, events = edge_case(rows, which)
            if result:
                results.add(result)
            notes.update(events)
        assert results == set(range(1, 7)), results
        assert notes == set(NOTICES), notes
        lifecycle(rows)
        assert next(rows, None) is None
    assert process.returncode == 0
    print("PASS: Air Traffic matches 160 seeded Python scenarios across rungs 1–40")
    print(f"PASS: {ticks:,} Python flight ticks, six verdicts, and six landing or go-around notices")
    print("PASS: Air Traffic session matches Python substeps, trails, feedback, adaptive rounds, and restart")


if __name__ == "__main__":
    main(sys.argv[1])
