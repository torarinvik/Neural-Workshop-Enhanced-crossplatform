#!/usr/bin/env python3
"""Exercise the native Python Crossed Wires route and source key map."""
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
        [sys.executable, str(APP), "--screen", "crossed-wires", "--dump",
         "--seed", "17", *options],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    match = re.search(r"^# state=(\([^\n]+\)) bytes=", result.stdout, re.MULTILINE)
    if not match:
        raise AssertionError(f"Crossed Wires dump omitted its state line:\n{result.stdout}")
    return ast.literal_eval(match.group(1))


default = state_for()
assert len(default) == 27 and default[0] == 0
assert default[1] == 3 and default[3] == 5
assert default[20:22] == (1, 1), "source adaptive/grid defaults must be retained"

custom = state_for("--crossed-wires-level", "12", "--crossed-wires-rounds", "20",
                   "--crossed-wires-no-adaptive", "--crossed-wires-no-grid")
assert custom[1] == 12 and custom[3] == 20
assert custom[20:22] == (0, 0), "CLI settings must reach the controller"
invalid = subprocess.run(
    [sys.executable, str(APP), "--screen", "crossed-wires", "--dump",
     "--crossed-wires-rounds", "4"],
    cwd=ROOT, capture_output=True, text=True,
)
assert invalid.returncode != 0, "round counts outside the source choices must be rejected"


class FakeCore:
    def __init__(self, key_count: int = 4) -> None:
        self.fields = [0] * 27
        self.fields[0] = 0
        self.fields[1] = 3
        self.fields[3] = 5
        self.fields[4] = key_count
        self.actions: list[tuple[int, int]] = []
        self.closed = False

    def crossed_wires_create(self, *options: int) -> int:
        self.options = options
        return 1

    def crossed_wires_info(self, _handle: int, field: int) -> int:
        return self.fields[field]

    def crossed_wires_action(self, _handle: int, action: int, value: int,
                             _now: int) -> int:
        self.actions.append((action, value))
        if action == 0:
            self.fields[0] = 1
        return 1

    def crossed_wires_frame(self, _handle: int, _black: int,
                            _width: int, _height: int) -> bytes:
        return b"frame"

    def crossed_wires_destroy(self, _handle: int) -> int:
        self.closed = True
        return 0


key_names = (
    "SPACE", "RETURN", "UP", "RIGHT", "DOWN", "LEFT", "W", "D", "S", "A",
    "E", "C", "X", "Z", "Q", "O", "F11",
    *(f"NUM_{digit}" for digit in range(1, 10)),
)
key = SimpleNamespace(**{name: index + 100 for index, name in enumerate(key_names)})
args = SimpleNamespace(crossed_wires_level=3, crossed_wires_rounds=5,
                       crossed_wires_no_adaptive=False, crossed_wires_no_grid=False,
                       seed=17, black_background=False)

core = FakeCore(4)
session = app.CrossedWiresSession(core, args)
assert core.options == (3, 5, 1, 1, 17)
session.key(key.SPACE, key)
session.key(key.UP, key)
session.key(key.D, key)
session.key(key.S, key)
session.key(key.A, key)
session.key(key.O, key)
session.key(key.C, key)
assert core.actions == [(0, 0), (1, 0), (1, 1), (1, 2), (1, 3)], \
    "four-key source aliases, O, and C must route without restarting the task"
assert session.describe(None).startswith("Crossed Wires playing")
assert session.frame_bytes(core) == b"frame"
session.close()
assert core.closed

wide_core = FakeCore(8)
wide_session = app.CrossedWiresSession(wide_core, args)
wide_session.key(key.C, key)
wide_session.key(key.Q, key)
assert wide_core.actions == [(1, 3), (1, 7)], \
    "C/Q must retain their eight-key ports"
wide_session.close()

print("crossedwires_python_host_options_test: PASS (defaults, CLI, key maps, frame, cleanup)")
