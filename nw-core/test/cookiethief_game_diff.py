#!/usr/bin/env python3
"""Replay the original Cookie Thief UI lifecycle without importing pyglet."""
import ast
import random
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"
sys.path.insert(0, str(APP))
from neural_workshop import cookiethief as source

SOURCE_UI = APP / "neural_workshop/ui/cookiethief.py"
PHASES = ("ready", "setting", "running", "scored", "done")
DOOR_PHASES = (source.AWAY, source.COMING, source.WATCHING, source.GONE)


class VerdictSink:
    def clear(self):
        pass

    def show(self, *_args):
        pass


def source_controller():
    tree = ast.parse(SOURCE_UI.read_text(encoding="utf-8"), filename=str(SOURCE_UI))
    controller = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "CookieThief")
    methods = {"clamped", "_reset", "start_run", "_next_trial", "act", "update", "_coach_verdict", "_settle", "_finish", "score"}
    controller.body = [node for node in controller.body if isinstance(node, ast.FunctionDef) and node.name in methods]
    future = next(node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == "__future__")
    scope = dict(vars(source), _=lambda value: value, CLIMB_AT=0.75, DROP_BELOW=0.4, VERDICT_SECONDS=1.0)
    exec(compile(ast.Module(body=[future, controller], type_ignores=[]), str(SOURCE_UI), "exec"), scope)
    return scope["CookieThief"]


def replay(level, strategy, coach):
    run = source_controller()()
    run.start_rung = level
    run.total_trials = 5
    run.adaptive = True
    run.coach = coach
    run.beat_seconds = 0.125
    run.set_seconds = 0.25
    run.rng = random.Random(42)
    run.verdict = VerdictSink()
    run.asked = VerdictSink()
    run._update_asked = run._redraw = run._update_status = lambda *args: None
    now = 0.0
    run.clock = lambda: now
    run.start_run()
    last_thief = None
    for tick in range(600):
        now = tick * 0.125
        if run.phase == "running":
            if strategy == 0:
                run.act(source.GRAB if run.thief.eaten < run.setup.grade.quota else source.LEAVE)
            elif strategy == 1:
                run.act(source.GRAB)
            elif strategy == 2 and tick % 3:
                run.act(source.LUNGE if tick % 3 == 1 else source.GRAB)
        run.update(0)
        if run.phase == "scored" and now >= run.until:
            last_thief = run.thief
            run._next_trial()
        thief = run.thief or last_thief
        visible = -1 if run.verdict_shown is None else int(run.verdict_shown[0])
        verdict = visible if run.phase in ("scored", "done") else -1
        ticker = (tick, PHASES.index(run.phase), run.rung, run.trial, thief.beat, thief.jar,
                  thief.eaten, thief.caught, thief.pace, DOOR_PHASES.index(thief.phase), thief.reaching, verdict,
                  sum(ok for _, ok in run.results), run.cookies, run.points,
                  max((rung for rung, _ in run.results), default=0),
                  run.score()["floor"] if run.phase == "done" else 0, visible)
        yield ",".join(map(str, ticker))
        if run.phase == "done":
            return
    raise AssertionError("reference run exceeded replay duration")


def main():
    result = subprocess.run([sys.argv[1]], check=True, capture_output=True, text=True, timeout=30)
    lines = iter(result.stdout.splitlines())
    rows = 0
    coach_outcomes = set()
    for coach in (False, True):
        for level, strategy in ((1, 0), (6, 1), (10, 2), (4, 3)):
            for expected in replay(level, strategy, coach):
                got = next(lines)
                assert got == expected, (level, strategy, coach, got, expected)
                _, phase, *_, visible = map(int, got.split(","))
                if coach and phase == PHASES.index("running"):
                    coach_outcomes.add(visible)
                rows += 1
            label, length = next(lines).split(",")
            assert label == "render" and int(length) > 16
    assert coach_outcomes == {-1, 0, 1}, coach_outcomes
    assert next(lines, None) is None
    print(f"PASS: {rows} Cookie Thief clock updates match Python across eight completed runs")


if __name__ == "__main__":
    main()
