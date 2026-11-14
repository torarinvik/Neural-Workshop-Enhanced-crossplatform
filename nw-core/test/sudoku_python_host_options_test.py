#!/usr/bin/env python3
"""Exercise the native Python Sudoku route's source defaults and CLI options."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "shells" / "python" / "app.py"
sys.path.insert(0, str(APP.parent))
import app  # noqa: E402


def state_for(*options: str) -> tuple[int, ...]:
    result = subprocess.run(
        [sys.executable, str(APP), "--screen", "sudoku", "--dump", "--seed", "17",
         *options],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"^# state=(\([^\n]+\)) bytes=", result.stdout, re.MULTILINE)
    if not match:
        raise AssertionError(f"Sudoku dump omitted its state line:\n{result.stdout}")
    return ast.literal_eval(match.group(1))


default = state_for()
assert default[1] == 3 and default[3] == 3, "source defaults must be level 3 / three puzzles"
assert default[11] == 1 and default[12] == 1, "source defaults must show clashes and adapt"

custom = state_for("--sudoku-level", "1", "--sudoku-puzzles", "1",
                   "--sudoku-no-clashes", "--sudoku-no-adaptive")
assert custom[1] == 1 and custom[3] == 1, "CLI level and puzzle count must reach the controller"
assert custom[11] == 0 and custom[12] == 0, "CLI clash and adaptive flags must reach the controller"


class FakeCore:
    def __init__(self, size: int) -> None:
        self.fields = [0] * 21
        self.fields[0] = 1
        self.fields[5] = size
        self.actions: list[tuple[int, int]] = []

    def sudoku_create(self, *options: int) -> int:
        self.options = options
        return 1

    def sudoku_info(self, _handle: int, field: int) -> int:
        return self.fields[field]

    def sudoku_action(self, _handle: int, action: int, value: int, _now: int) -> int:
        self.actions.append((action, value))
        return 1

    def sudoku_destroy(self, _handle: int) -> int:
        return 0


key_values = {name: index + 100 for index, name in enumerate((
    "SPACE", "RETURN", "UP", "DOWN", "LEFT", "RIGHT", "BACKSPACE", "DELETE",
    "_0", "NUM_0", "N", "C", "A", "B", "D", "E", "F", "G",
    *(f"_{digit}" for digit in range(1, 10)),
    *(f"NUM_{digit}" for digit in range(1, 10)),
))}
key = SimpleNamespace(**key_values)
core = FakeCore(9)
session = app.SudokuSession(core, SimpleNamespace(
    sudoku_level=3, sudoku_puzzles=3, sudoku_no_clashes=False,
    sudoku_no_adaptive=False, seed=17, black_background=False))
session.key(key.N, key)
session.key(key._1, key)
session.key(key.NUM_9, key)
session.key(key.A, key)
session.key(key.C, key)  # options key below level 12; must not write digit 12
for erase_key in (key._0, key.NUM_0, key.BACKSPACE, key.DELETE):
    session.key(erase_key, key)
assert core.actions[:4] == [(7, 0), (5, 1), (5, 9), (5, 10)], \
    "the native route must map source N and the 1-9/A-G alphabet"
assert core.actions[4:] == [(6, 0)] * 4, "all source erase keys must clear the current cell"
wide_core = FakeCore(16)
wide_session = app.SudokuSession(wide_core, SimpleNamespace(
    sudoku_level=12, sudoku_puzzles=1, sudoku_no_clashes=False,
    sudoku_no_adaptive=False, seed=17, black_background=False))
wide_session.key(key.C, key)
assert wide_core.actions == [(5, 12)], "C becomes digit twelve on a 12+ board"
session.close()
wide_session.close()

print("sudoku_python_host_options_test: PASS (defaults, four options, source keys, C/12 rule)")
