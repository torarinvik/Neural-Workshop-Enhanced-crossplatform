"""Check Escort candidate temples against the Python generator."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import escort


def compare(rows, tag, expected, context):
    kind, *values = next(rows).split()
    assert kind == tag and len(values) == len(expected), (context, tag, kind, values, expected)
    actual = tuple(float(raw) if isinstance(value, float) else int(raw)
                   for raw, value in zip(values, expected))
    assert actual == tuple(expected), (context, tag, actual, expected)


TYPES = {escort.DOOR: 0, escort.BRIDGE: 1, escort.JET: 2}
STATES = {state: n for n, state in enumerate((escort.WALKING, escort.WAITING, escort.SAFE,
                                            escort.FELL, escort.BURNED, escort.ARRIVED))}


def candidate(rows, temple, where):
    compare(rows, "candidate", (temple is not None, temple.seconds if temple else 0.0), where)
    if temple is None:
        return
    for path, delay, changes in zip(temple.paths, temple.delays, temple.paces):
        compare(rows, "walker", (len(path), delay, len(changes)), where)
        for cell in path:
            compare(rows, "cell", cell, where)
        for change in changes:
            compare(rows, "pace", change, where)
    for device, initial in zip(temple.devices, temple.start):
        lever = -1 if device.lever is None else device.lever
        compare(rows, "device", (TYPES[device.kind], device.walker, device.at,
                                  lever, device.period, device.duty, device.phase, initial), where)
    for links in temple.levers:
        compare(rows, "lever", (len(links),), where)
        for link in links:
            compare(rows, "link", (link,), where)


def replay(rows, temple, guided):
    run = escort.Run(temple)
    tick = 0
    while run.result is None:
        ports = escort.autopilot(run) if guided else []
        for port in ports:
            run.pull(port)
        run.step(1 / 30)
        code = 0
        if run.result:
            if run.result[0]:
                code = 1
            elif escort.FELL in run.state:
                code = 2
            elif escort.BURNED in run.state:
                code = 3
            else:
                code = 4
        where = temple.level.rung, guided, tick
        compare(rows, "tick", (ports[0] if ports else -1, run.t, code), where)
        for w, state in enumerate(run.state):
            compare(rows, "walker", (run.pos[w], STATES[state], run.pace[w], run.next_pace[w], *run.where(w)), where)
        for i, device in enumerate(temple.devices):
            compare(rows, "motion", (run.target[i], run.progress[i]), where)
            if device.kind == escort.JET:
                compare(rows, "jet", (run.jet_on(i), *run.jet_next(i)), where)
        for stamp in run.pulled:
            compare(rows, "pulled", (stamp,), where)
        tick += 1
    return tick, code


def lifecycle(rows):
    from types import SimpleNamespace
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui.escort import Escort

    class Replay(Escort):
        def __init__(self):
            self.rng = Random(17)
            self.start_rung = 13
            self.total_trials = 2
            self.adaptive = True
            self.now = 0
            self.clock = lambda: self.now / 1000
            self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
            self.scenery = []
            self.report = 0

        def _deal(self):
            self.report = 0
            return super()._deal()

        def _redraw(self):
            pass

        def _judge(self, passed, message):
            self.report = 1 if passed else 2 if escort.FELL in self.run.state else 3 if escort.BURNED in self.run.state else 4
            super()._judge(passed, message)

    def summary(screen):
        phase = {"playing": 1, "judged": 2, "done": 3}[screen.phase]
        score = screen.score()
        run = screen.run
        compare(rows, "session", (phase, screen.rung, screen.trial, score["passed"], score["best_rung"],
                                  screen.report, run.state.count(escort.ARRIVED) if run else 0,
                                  run.t if run else 0.0), screen.now)
        if run:
            for trail in screen.trails:
                compare(rows, "trail", (len(trail),), screen.now)
                for point in trail:
                    compare(rows, "point", point, screen.now)
            for flip in screen.flips:
                compare(rows, "flip", (flip,), screen.now)

    screen = Replay()
    screen.start_run()
    summary(screen)
    for trial in range(2):
        while screen.phase == "playing":
            if not trial:
                for port in escort.autopilot(screen.run):
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
        count = 0
        for rung in range(1, 37):
            for seed in (-17, 0, 17, 2026):
                level = escort.grade(rung)
                compare(rows, "grade", level, (rung, seed))
                draw = Random(seed)
                for attempt in range(5):
                    candidate(rows, escort._build(level, draw), (rung, seed, attempt))
                    count += 1
        ticks, results = 0, set()
        for rung in (1, 6, 7, 10, 13, 16, 20, 26):
            temple = escort.deal(rung, 17)
            candidate(rows, temple, (rung, "selected"))
            for guided in (False, True):
                count_ticks, result = replay(rows, temple, guided)
                ticks += count_ticks
                results.add(result)
        lifecycle(rows)
        assert next(rows, None) is None
    assert process.returncode == 0
    assert results == {1, 2, 3, 4}, results
    print(f"PASS: Escort matches {count} Python candidates across rungs 1–36")
    print(f"PASS: Escort matches selected deals, reference lever pulls, {ticks:,} ticks, and four outcomes")
    print("PASS: Escort session matches Python trail samples, flips, substeps, feedback, and adaptive restart")


if __name__ == "__main__":
    main(sys.argv[1])
