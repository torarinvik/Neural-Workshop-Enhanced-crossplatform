"""Compare generated Sokoban Live warehouse candidates with Python."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import sokoban, sokobanlive


def compare(rows, tag, expected, where):
    kind, *raw = next(rows).split()
    assert kind == tag and len(raw) == len(expected), (where, tag, kind, raw, expected)
    actual = tuple(float(item) if isinstance(value, float) else int(item)
                   for item, value in zip(raw, expected))
    assert actual == tuple(expected), (where, tag, actual, expected)


OUTCOMES = {"A guard caught the worker": 2, "A crate is stuck for good": 3, "Out of time": 4}


def replay(rows, floor, where, guided=False):
    run = sokobanlive.Run(floor)
    pilot = sokobanlive.Pilot() if guided else None
    limit = 6000 if guided else 360
    for tick in range(limit):
        if guided:
            ports = pilot(run)
            compare(rows, "order", (ports[0] if ports else -1,), (*where, tick))
            for port in ports:
                run.press(port)
        elif tick % 4 == 0:
            run.press((tick // 4 + tick // 13) % 4)
        run.step(1 / 30)
        queued = -1 if run.queued is None else run.queued
        result = 0 if run.result is None else 1 if run.result[0] else OUTCOMES[run.result[1]]
        point = (*where, tick)
        compare(rows, "tick", (run.t, run.player, run.ready_at, queued, result,
                               run.facing, run.pushes, run.steps), point)
        for box in sorted(run.boxes):
            compare(rows, "box", (box,), point)
        for guard in run.guards:
            compare(rows, "guard", (guard.k, guard.heading, guard.next_beat), point)
        for gate in floor.shutters:
            compare(rows, "gate", (gate.cell in run.shut_now,), point)
        if result:
            return tick + 1
    assert not guided, where
    return limit


def compare_floor(rows, requested, floor, where):
    compare(rows, "grade", floor.level if floor else requested, where)
    compare(rows, "valid", (floor is not None,), where)
    if floor is None:
        return
    room = floor.room
    compare(rows, "room", (room.player, -1 if room.minimum is None else room.minimum,
                           room.at_least, room.bound, float(floor.seconds)), where)
    alive = sokoban.live_cells(room.width, room.height, room.walls, room.goals)
    for i in range(room.width * room.height):
        compare(rows, "cell", (i in room.walls, i in room.goals, i in room.boxes, i in alive), (where, i))
    for guard in floor.patrols:
        compare(rows, "patrol", (guard.start, guard.heading, guard.phase, len(guard.cells)), where)
        for cell in guard.cells:
            compare(rows, "lane", (cell,), where)
    for shutter in floor.shutters:
        compare(rows, "shutter", shutter, where)


def lifecycle(rows):
    from types import SimpleNamespace
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui.sokobanlive import SokobanLive

    class Replay(SokobanLive):
        def __init__(self):
            self.rng = Random(17)
            self.start_rung = 1
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
            self.report = 1 if passed else OUTCOMES[message]
            super()._judge(passed, message)

    def summary(screen):
        phase = {"playing": 1, "judged": 2, "done": 3}[screen.phase]
        score = screen.score()
        run = screen.run
        compare(rows, "session", (phase, screen.rung, screen.trial, score["passed"], score["best_rung"],
                                  screen.report, run.pushes if run else 0, run.steps if run else 0,
                                  len(run.boxes & run.floor.room.goals) if run else 0,
                                  run.t if run else 0.0), screen.now)

    screen = Replay()
    screen.start_run()
    summary(screen)
    pilot = sokobanlive.Pilot()
    for trial in range(2):
        while screen.phase == "playing":
            if not trial:
                for direction in pilot(screen.run):
                    screen.steer(direction)
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
        accepted = rejected = ticks = guided_ticks = 0
        rungs = (1, 2, 4, 7, 10, 13, 16, 20, 30)
        for rung in rungs:
            for seed in (-17, 0, 3, 17):
                where = (rung, seed)
                grade = sokobanlive.grade(rung)
                floor = sokobanlive._build(grade, Random(seed))
                compare_floor(rows, grade, floor, where)
                if floor is None:
                    rejected += 1
                    continue
                accepted += 1
                room = floor.room
                plan = sokobanlive.solve(room, frozenset(set(room.boxes)), room.player)
                compare(rows, "solution", (plan is not None, len(plan or [])), where)
                for direction in plan or ():
                    compare(rows, "direction", (direction,), where)
                ticks += replay(rows, floor, where)
        for rung in rungs:
            floor = sokobanlive.deal(rung, 17)
            where = (rung, "selected")
            compare_floor(rows, sokobanlive.grade(rung), floor, where)
            guided_ticks += replay(rows, floor, where, guided=True)
        lifecycle(rows)
        assert next(rows, None) is None
    assert process.returncode == 0
    assert accepted + rejected == 36, (accepted, rejected)
    print(f"PASS: Sokoban Live matches {accepted + rejected} Python candidates and {accepted} exact solution routes")
    print(f"PASS: {ticks:,} scripted ticks plus {guided_ticks:,} reference worker ticks in {len(rungs)} selected warehouses")
    print("PASS: Sokoban Live session matches Python timing, adaptive rounds, feedback, and restart")


if __name__ == "__main__":
    main(sys.argv[1])
