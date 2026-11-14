#!/usr/bin/env python3
"""Emit an original-UI Sudoku trace for the common-v1 differential replay.

The source environment's four movement ports, sixteen digit ports, erase,
and pencil port are loaded from ``nwenv.sudoku``. Only its unrelated package
initializer is bypassed because that eagerly imports the optional MuJoCo
environment; the exact SudokuEnv.drive implementation is exercised below.
"""
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

# Sudoku's UI only consults taskoptions when its constructor opens the user
# settings store. This trace owns its values explicitly and does not open a
# window, so avoid taskoptions' import of the optional Marble/MuJoCo module.
taskoptions = types.ModuleType("neural_workshop.ui.taskoptions")
taskoptions.SUDOKU = object()
taskoptions.settings = lambda _spec: {}
taskoptions.open_task_options = lambda *_args, **_kwargs: None
sys.modules[taskoptions.__name__] = taskoptions

from neural_workshop.ui.sudoku import Sudoku  # noqa: E402
from neural_workshop.sudoku import generate, peers  # noqa: E402

# Load the actual wrapper class without running nwenv/__init__.py, which
# imports every task adapter (including optional MuJoCo). Its drive mapping
# is the subject of this differential, not the shared window/environment.
nwenv = types.ModuleType("nwenv")
nwenv.__path__ = [str(ORIGINAL / "nwenv")]
sys.modules["nwenv"] = nwenv
taskenv = types.ModuleType("nwenv.taskenv")


class TaskEnv:
    @classmethod
    def verifier(cls):
        return lambda *_args, **_kwargs: None


taskenv.TaskEnv = TaskEnv
sys.modules[taskenv.__name__] = taskenv
spec = importlib.util.spec_from_file_location(
    "nwenv.sudoku", ORIGINAL / "nwenv" / "sudoku.py")
source_env = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = source_env
spec.loader.exec_module(source_env)

LEVEL = 3
SEED = 17


class Verdict:
    def clear(self):
        self.shown = None

    def show(self, good, message):
        self.shown = (good, message)


def build_ui():
    ui = Sudoku.__new__(Sudoku)
    ui.rng = random.Random(SEED)
    ui.clock = lambda: 0.0
    ui.start_rung = LEVEL
    ui.total_trials = 1
    ui.show_clashes = True
    ui.adaptive = True
    ui.results = []
    ui.phase = "ready"
    ui.message = "Press Space to start"
    ui.verdict_shown = None
    ui.verdict = Verdict()
    ui.status = types.SimpleNamespace(text="")
    ui._redraw = lambda: None
    ui.start_run()
    ui.clock = lambda: 2.0
    return ui


PHASE = {"ready": 0, "solving": 1, "solved": 2, "done": 3}


def state(ui):
    verdict = -1 if ui.verdict_shown is None else int(bool(ui.verdict_shown[0]))
    return [PHASE[ui.phase], ui.rung, ui.trial, ui.total_trials,
            ui.size(), ui.at, int(ui.pencil), ui.mistakes, verdict,
            sum(value == 0 for value in ui.filled), int(ui.show_clashes),
            int(ui.puzzle is not None)]


def marks(ui):
    return [ui.marks.get(cell, 0) for cell in range(len(ui.filled))]


def main():
    ui = build_ui()
    env = source_env.SudokuEnv.__new__(source_env.SudokuEnv)
    initial_state = state(ui)
    records = []

    def act(port):
        source_env.SudokuEnv.drive(env, ui, port)
        records.append({"port": port, "state": state(ui),
                        "filled": list(ui.filled), "marks": marks(ui)})

    def move_to(target):
        size = ui.size()
        row, column = divmod(ui.at, size)
        target_row, target_column = divmod(target, size)
        while row > target_row:
            act(source_env.STEPS.index((0, -1)))
            row -= 1
        while row < target_row:
            act(source_env.STEPS.index((0, 1)))
            row += 1
        while column > target_column:
            act(source_env.STEPS.index((-1, 0)))
            column -= 1
        while column < target_column:
            act(source_env.STEPS.index((1, 0)))
            column += 1

    given = next(cell for cell, value in enumerate(ui.filled) if value)
    blank = next(cell for cell, value in enumerate(ui.filled) if not value)
    move_to(given)
    act(source_env.STEPS.__len__() + ui.filled[given] - 1)
    move_to(blank)
    answer = ui.puzzle.solution[blank]
    act(source_env.PENCIL)
    act(source_env.STEPS.__len__() + answer - 1)
    act(source_env.ERASE)
    act(source_env.PENCIL)

    near = peers(ui.puzzle.box)[blank]
    wrong = next(value for value in range(1, ui.size() + 1)
                 if value != answer and any(ui.filled[cell] == value for cell in near))
    act(source_env.STEPS.__len__() + wrong - 1)
    wrong_clashes = sorted(ui.clashes())
    wrong_clash_trace_index = len(records) - 1
    act(source_env.ERASE)

    blanks = [cell for cell, value in enumerate(ui.puzzle.givens) if not value]
    last = blanks[-1]
    for cell in blanks[:-1]:
        move_to(cell)
        act(source_env.STEPS.__len__() + ui.puzzle.solution[cell] - 1)
    move_to(last)
    wrong_last = ui.puzzle.solution[last] % ui.size() + 1
    act(source_env.STEPS.__len__() + wrong_last - 1)
    wrong_full_state = state(ui)
    wrong_full_trace_index = len(records) - 1
    act(source_env.ERASE)
    act(source_env.STEPS.__len__() + ui.puzzle.solution[last] - 1)
    solved_state = state(ui)
    score = ui.score()
    ui._next_trial()
    done_state = state(ui)

    print(json.dumps({
        "seed": SEED,
        "level": LEVEL,
        "total_trials": 1,
        "givens": ui.puzzle.givens,
        "solution": ui.puzzle.solution,
        "initial": initial_state,
        "trace": records,
        "wrong_clashes": wrong_clashes,
        "wrong_clash_trace_index": wrong_clash_trace_index,
        "wrong_full_state": wrong_full_state,
        "wrong_full_trace_index": wrong_full_trace_index,
        "solved_state": solved_state,
        "done_state": done_state,
        "score": score,
    }))


if __name__ == "__main__":
    main()
