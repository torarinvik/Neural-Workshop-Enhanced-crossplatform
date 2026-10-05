#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python 3D Maze controller."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # noqa: E402
from app import TaskHubSession  # noqa: E402


class Keys:
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    SPACE = 5
    RETURN = 6
    ESCAPE = 7


def main() -> int:
    assert nwcore.you_are_here_create(0, 1, 0, 1, 17) == -1
    handle = nwcore.you_are_here_create(1, 1, 0, 1, 17)
    assert handle > 0
    try:
        assert nwcore.you_are_here_info(handle, 0) == 0
        ready = nwcore.you_are_here_frame(handle, 0, 912, 684)
        assert isinstance(ready, bytes) and ready.startswith(b"NKIN")
        assert nwcore.you_are_here_action(handle, 0, 0) == 1
        assert nwcore.you_are_here_info(handle, 0) == 1
        assert nwcore.you_are_here_info(handle, 9) > 0
        assert nwcore.you_are_here_cell(handle, 0, 0) in (0, 1)
        walking = nwcore.you_are_here_frame(handle, 0, 1280, 720)
        assert isinstance(walking, bytes) and len(walking) > len(ready)
        assert nwcore.you_are_here_action(handle, 5, 10) == 1
        assert nwcore.you_are_here_info(handle, 6) == 0
    finally:
        assert nwcore.you_are_here_destroy(handle) == 0
    args = type("Args", (), {"trial": 1, "trials": 1, "adaptive": False,
                              "show_marks": True, "seed": 17,
                              "black_background": False})()
    menu = TaskHubSession(nwcore, args)
    assert menu.frame_bytes(nwcore, 912, 684).startswith(b"NKIN")
    for _ in range(5):
        menu.key(Keys.RIGHT, Keys)
    for _ in range(4):
        menu.key(Keys.DOWN, Keys)
    assert menu.category == 5 and menu.selected == 4
    menu.key(Keys.SPACE, Keys)
    assert menu.child is not None and menu.child.state[0] == 0
    menu.close()
    print("PASS: native Python 3D Maze lifecycle, display list, topology, resize, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
