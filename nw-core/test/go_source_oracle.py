#!/usr/bin/env python3
"""Emit a deterministic original Go UI/environment replay for common-v1."""
from __future__ import annotations

import importlib.util
import json
import random
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "original-neural-workshop-enhanced"
sys.path.insert(0, str(ORIGINAL))

from neural_workshop.go import capture_moves  # noqa: E402

# taskoptions imports the optional Marble/MuJoCo kernel even though this
# deterministic headless replay supplies all Go settings itself.
taskoptions = types.ModuleType("neural_workshop.ui.taskoptions")
taskoptions.GO_WINNING_MOVE = object()
taskoptions.settings = lambda _spec: {}
taskoptions.open_task_options = lambda *_args, **_kwargs: None
sys.modules[taskoptions.__name__] = taskoptions

from neural_workshop.ui.go import GoWinningMove  # noqa: E402

# Load the exact GoEnv.drive implementation without importing every optional
# environment (nwenv.__init__ eagerly imports the MuJoCo adapter).
nwenv = types.ModuleType("nwenv")
nwenv.__path__ = [str(ORIGINAL / "nwenv")]
sys.modules["nwenv"] = nwenv
taskenv = types.ModuleType("nwenv.taskenv")


class TaskEnv:
    @classmethod
    def verifier(cls):
        return lambda *_args, **_kwargs: None

    def drive(self, task, port):
        method = getattr(task, self.action)
        method(port)


taskenv.TaskEnv = TaskEnv
sys.modules[taskenv.__name__] = taskenv
spec = importlib.util.spec_from_file_location(
    "nwenv.go", ORIGINAL / "nwenv" / "go.py")
source_env = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = source_env
spec.loader.exec_module(source_env)

SEED = 17
LEVEL = 4
TRIALS = 5


class Verdict:
    def __init__(self):
        self.shown = None

    def clear(self):
        self.shown = None

    def show(self, good, message):
        self.shown = (good, message)


def build_ui():
    ui = GoWinningMove.__new__(GoWinningMove)
    ui.rng = random.Random(SEED)
    ui.clock = lambda: 0.0
    ui.start_difficulty = LEVEL
    ui.total_trials = TRIALS
    ui.difficulty = LEVEL
    ui.cursor_x = 0
    ui.cursor_y = 0
    ui.trial = 0
    ui.correct = 0
    ui.problem = None
    ui.phase = "ready"
    ui.message = "Press Space to start"
    ui.verdict_shown = None
    ui.verdict = Verdict()
    ui.drawn = []
    ui._redraw = lambda: None
    ui.start_run()
    return ui


PHASE = {"ready": 0, "solving": 1, "solved": 2, "failed": 2, "done": 3}


def snapshot(ui):
    problem = ui.problem
    source_verdict = None if ui.verdict_shown is None else bool(ui.verdict_shown[0])
    captured = 0
    if source_verdict and problem:
        captured = problem.capture_goal
    elif source_verdict is False and ui.message.startswith("Captured "):
        captured = int(ui.message.split(" ", 2)[1].rstrip(","))
    return {
        "phase": PHASE[ui.phase],
        "difficulty": ui.difficulty,
        "trial": ui.trial,
        "totalTrials": ui.total_trials,
        "size": problem.size if problem else 0,
        "cursorX": ui.cursor_x,
        "cursorY": ui.cursor_y,
        "correct": ui.correct,
        "verdict": source_verdict,
        "captured": captured,
        "captureOptions": problem.capture_options if problem else 0,
        "captureGoal": problem.capture_goal if problem else 0,
        "board": [stone for row in problem.board for stone in row] if problem else [],
        "target": [
            int((x, y) in problem.target)
            for y in range(problem.size) for x in range(problem.size)
        ] if problem else [],
        "message": ui.message,
        "winningPort": (
            problem.winning_move[1] * problem.size + problem.winning_move[0]
            if problem else -1
        ),
    }


def main():
    ui = build_ui()
    env = source_env.GoEnv.__new__(source_env.GoEnv)
    trace = [{"action": "start", "value": 0, "state": snapshot(ui)}]

    problem = ui.problem
    captures = capture_moves(problem.board)
    decoy = next((point for point in captures if point != problem.winning_move), None)
    if decoy is None:
        raise RuntimeError("the deterministic level-4 fixture needs a capturing decoy")
    port = decoy[1] * problem.size + decoy[0]
    source_env.GoEnv.drive(env, ui, port)
    trace.append({"action": "answer", "value": port, "state": snapshot(ui)})

    ui._next_trial()
    trace.append({"action": "next", "value": 0, "state": snapshot(ui)})
    problem = ui.problem
    captures = capture_moves(problem.board)
    empty = next((y * problem.size + x
                  for y, row in enumerate(problem.board)
                  for x, stone in enumerate(row)
                  if not stone and (x, y) not in captures), None)
    if empty is None:
        raise RuntimeError("the deterministic replay needs an empty non-capturing point")
    source_env.GoEnv.drive(env, ui, empty)
    trace.append({"action": "answer", "value": empty, "state": snapshot(ui)})

    ui._next_trial()
    trace.append({"action": "next", "value": 0, "state": snapshot(ui)})
    problem = ui.problem
    occupied = next(index for index, stone in enumerate(
        stone for row in problem.board for stone in row) if stone)
    source_env.GoEnv.drive(env, ui, occupied)
    trace.append({"action": "answer", "value": occupied, "state": snapshot(ui)})

    ui._next_trial()
    trace.append({"action": "next", "value": 0, "state": snapshot(ui)})
    problem = ui.problem
    port = problem.winning_move[1] * problem.size + problem.winning_move[0]
    source_env.GoEnv.drive(env, ui, port)
    trace.append({"action": "answer", "value": port, "state": snapshot(ui)})

    ui._next_trial()
    trace.append({"action": "next", "value": 0, "state": snapshot(ui)})
    problem = ui.problem
    port = problem.winning_move[1] * problem.size + problem.winning_move[0]
    source_env.GoEnv.drive(env, ui, port)
    trace.append({"action": "answer", "value": port, "state": snapshot(ui)})

    ui._next_trial()
    trace.append({"action": "next", "value": 0, "state": snapshot(ui)})
    print(json.dumps({"seed": SEED, "level": LEVEL, "trials": TRIALS,
                      "trace": trace}))


if __name__ == "__main__":
    main()
