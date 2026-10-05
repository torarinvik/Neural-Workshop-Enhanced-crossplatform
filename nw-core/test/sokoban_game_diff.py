#!/usr/bin/env python3
"""Differential replay for the persistent Sokoban controller vs its real UI.

The reference window is never created. ``SokobanTask`` is initialized with its
production fields, given a no-op redraw/verdict sink, and driven through the
same start/move/undo/restart methods called by its key handler. Generated
levels still come from the original ``neural_workshop.sokoban.generate``.
"""
import random
import subprocess
import sys
import types
from pathlib import Path

APP = (Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, str(APP))

from neural_workshop import sokoban as ref  # noqa: E402

# The UI module only needs taskoptions when constructing its real windowed
# widget. This controller replay deliberately uses __new__ and the source's
# run/input methods, so suppress taskoptions' optional MuJoCo import instead
# of installing a physics dependency just to test turn-based Sokoban.
sys.modules["neural_workshop.ui.taskoptions"] = types.ModuleType(
    "neural_workshop.ui.taskoptions")
from neural_workshop.ui.sokoban import SokobanTask  # noqa: E402

ref._native = None
PHASE = {"ready": 0, "pushing": 1, "solved": 2, "lost": 3, "done": 4}
SEEDS = (0, 1, 7, 17, 42)
ACTIONS = (1, 2, 3, 4, 4, 3, 2, 1, 5, 5, 6, 0, 3, 4, 1)
INFO_FIELDS = (
    "phase", "rung", "trial", "total", "player", "pushes", "moves",
    "verdict", "width", "height", "par", "minimum", "at_least", "bound",
    "solved", "lost", "best", "efficiency",
)


class VerdictSink:
    def clear(self):
        pass

    def show(self, *_args):
        pass


def reference_task(rung, seed, now):
    task = SokobanTask.__new__(SokobanTask)
    task.rng = random.Random(seed)
    task.clock = lambda: now[0]
    task.start_rung = rung
    task.rung = rung
    task.total_trials = 1
    task.adaptive = False
    task.show_traps = True
    task.level = None
    task.boxes = frozenset()
    task.player = 0
    task.pushes = 0
    task.moves = 0
    task.history = []
    task.trial = 0
    task.results = []
    task.started_at = 0.0
    task.phase = "ready"
    task.message = "Press Space to start"
    task.lost = 0
    task.verdict_shown = None
    task.verdict = VerdictSink()
    task._redraw = lambda: None
    return task


def source_action(task, action):
    if action == 0:
        if task.phase in ("ready", "done"):
            task.start_run()
        elif task.phase in ("solved", "lost"):
            task._next_trial()
    elif 1 <= action <= 4:
        dx, dy = ((0, -1), (0, 1), (-1, 0), (1, 0))[action - 1]
        task.step(dx, dy)
    elif action == 5:
        task.undo()
    elif action == 6:
        task.restart()


def snapshot_line(task, seed, rung, event):
    level = task.level
    width = 0 if level is None else level.width
    height = 0 if level is None else level.height
    if task.phase in ("solved", "lost"):
        verdict = int(bool(task.verdict_shown and task.verdict_shown[0]))
    else:
        verdict = -1
    par = task.par() if level is not None else 0
    minimum = -1 if level is None or level.minimum is None else level.minimum
    at_least = 0 if level is None else level.at_least
    bound = 0 if level is None else level.bound
    results = task.results
    pars = sum(result[2] for result in results)
    pushes = sum(result[1] for result in results)
    efficiency = round(100.0 * pars / pushes) if pushes else 0
    best = max((result[0] for result in results), default=0)
    player = getattr(task, "player", 0)
    values = [
        PHASE[task.phase], task.rung, task.trial, task.total_trials,
        player, task.pushes, task.moves, verdict, width, height, par,
        minimum, at_least, bound, len(results), task.lost, best, efficiency,
    ]
    fields = ["state", seed, rung, event, *values]
    for cells in ("walls", "goals", "traps"):
        member = set() if level is None else getattr(level, cells)
        fields.append("".join("1" if index in member else "0"
                              for index in range(width * height)))
    boxes = set() if level is None else set(task.boxes)
    fields.append("".join("1" if index in boxes else "0"
                          for index in range(width * height)))
    return ",".join(map(str, fields))


def expected_lines():
    lines = []
    for rung in (1, 2, 3):
        for seed in SEEDS:
            now = [1.0]
            task = reference_task(rung, seed, now)
            lines.append(snapshot_line(task, seed, rung, -1))
            now[0] = 1.0
            task.start_run()
            lines.append(snapshot_line(task, seed, rung, 0))
            for event, action in enumerate(ACTIONS, 1):
                now[0] = 1.0 + event * 1.25
                source_action(task, action)
                lines.append(snapshot_line(task, seed, rung, event))
    return lines


def main():
    binary = sys.argv[1]
    result = subprocess.run([binary], capture_output=True, text=True, check=True)
    got = [line for line in result.stdout.splitlines() if line.startswith("state,")]
    want = expected_lines()
    if len(got) != len(want):
        print(f"FAIL: state-line count {len(got)} vs {len(want)}")
        return 1
    failures = [(i, actual, expected) for i, (actual, expected) in enumerate(zip(got, want))
                if actual != expected]
    for index, actual, expected in failures[:8]:
        print(f"MISMATCH state {index}\n  Elisa: {actual[:260]}\n  source: {expected[:260]}")
    if failures:
        print(f"FAIL: {len(failures)}/{len(want)} controller states diverged")
        return 1
    print(f"PASS: {len(want)} Sokoban controller states identical to source UI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
