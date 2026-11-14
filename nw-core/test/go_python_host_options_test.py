#!/usr/bin/env python3
"""Exercise the native Python Go route's source defaults and CLI options."""
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
        [sys.executable, str(APP), "--screen", "go", "--dump", "--seed", "17",
         *options],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"^# state=(\([^\n]+\)) bytes=", result.stdout, re.MULTILINE)
    if not match:
        raise AssertionError(f"Go dump omitted its state line:\n{result.stdout}")
    return ast.literal_eval(match.group(1))


default = state_for()
assert len(default) == 13, "native Go state must expose the public captured-stone count"
assert default[0] == 0 and default[1] == 1 and default[3] == 10, \
    "source defaults must be ready at level 1 with ten positions"

custom = state_for("--go-level", "7", "--go-trials", "3")
assert custom[1] == 7 and custom[3] == 3, \
    "CLI Go options must reach the native controller"
invalid = subprocess.run(
    [sys.executable, str(APP), "--screen", "go", "--dump", "--go-trials", "2"],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
assert invalid.returncode != 0, "trial counts outside the source choice list must be rejected"


class FakeCore:
    def __init__(self) -> None:
        self.fields = [0] * 13
        self.fields[0:7] = [0, 1, 0, 10, 9, 4, 2]
        self.fields[8] = -1
        self.fields[11] = -1
        self.actions: list[tuple[int, int]] = []

    def go_create(self, *options: int) -> int:
        self.options = options
        return 1

    def go_info(self, _handle: int, field: int) -> int:
        return self.fields[field]

    def go_action(self, _handle: int, action: int, value: int, _now: int) -> int:
        self.actions.append((action, value))
        return 1

    def go_destroy(self, _handle: int) -> int:
        return 0


key_values = {name: index + 100 for index, name in enumerate((
    "SPACE", "RETURN", "UP", "DOWN", "LEFT", "RIGHT",
    "_0", "NUM_0", *(f"_{digit}" for digit in range(1, 10)),
    *(f"NUM_{digit}" for digit in range(1, 10)),
))}
key = SimpleNamespace(**key_values)
core = FakeCore()
session = app.GoSession(core, SimpleNamespace(
    go_level=1, go_trials=10, seed=17, black_background=False))
assert core.options == (1, 10, 17), "Go options and seed must reach the controller"
session.key(key.SPACE, key)
core.fields[0] = 1
session.key(key.LEFT, key)
session.key(key.SPACE, key)
core.fields[0] = 2
session.key(key.RETURN, key)
core.fields[0] = 3
session.key(key._0, key)
assert core.actions == [(0, 0), (5, 0), (1, 22), (2, 0), (7, 10)], \
    "Go phase keys must map start, cursor, answer, next, and level actions"
assert len(session.state) == 13 and session.state[12] == 0, \
    "the host must retain the public captured-stone field"
session.close()

print("go_python_host_options_test: PASS (defaults, CLI options, phase keys, state, cleanup)")
