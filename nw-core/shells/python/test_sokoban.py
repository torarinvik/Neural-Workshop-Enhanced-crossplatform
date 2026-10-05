#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Sokoban controller."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import SokobanSession, TaskHubSession  # noqa: E402


class Keys:
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    SPACE = 5
    RETURN = 6
    ESCAPE = 7
    U = 8
    R = 9


def main() -> int:
    assert nwcore.sokoban_create(0, 1, 0, 1, 17) == -1
    handle = nwcore.sokoban_create(1, 1, 0, 1, 17)
    assert handle > 0
    try:
        assert nwcore.sokoban_info(handle, 0) == 0
        ready = nwcore.sokoban_frame(handle, 0, 912, 684)
        assert ready.startswith(b"NKIN")
        assert nwcore.sokoban_action(handle, 0, 0) == 1
        assert nwcore.sokoban_info(handle, 0) == 1
        width = nwcore.sokoban_info(handle, 8)
        height = nwcore.sokoban_info(handle, 9)
        assert width >= 5 and height >= 5
        assert nwcore.sokoban_cell(handle, 0, 0) in (0, 1)
        nwcore.sokoban_action(handle, 3, 10)
        nwcore.sokoban_action(handle, 5, 20)
        nwcore.sokoban_action(handle, 6, 30)
        playing = nwcore.sokoban_frame(handle, 0, 1280, 720)
        assert playing.startswith(b"NKIN") and len(playing) > 0
    finally:
        assert nwcore.sokoban_destroy(handle) == 0

    args = type("Args", (), {"trial": 1, "trials": 1, "adaptive": False,
                              "show_traps": True, "show_marks": True,
                              "seed": 17, "black_background": False})()
    menu = TaskHubSession(nwcore, args)
    for _ in range(5):
        menu.key(Keys.RIGHT, Keys)
    for _ in range(2):
        menu.key(Keys.DOWN, Keys)
    assert menu.category == 5 and menu.selected == 2
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, SokobanSession)
    assert menu.child.state[0] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[0] == 1
    menu.close()
    print("PASS: native Python Sokoban lifecycle, display list, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
