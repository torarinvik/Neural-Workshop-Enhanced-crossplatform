#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Marble controller bridge."""
from __future__ import annotations

import sys
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import MarbleMazeSession, TaskHubSession  # noqa: E402


class Keys:
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    SPACE = 5
    RETURN = 6
    ESCAPE = 7
    L = 8
    R = 9


def main() -> int:
    board = bytes(nwcore.marble_board(1, 889418965))
    assert struct.unpack_from("<IIIIII", board) == (
        int.from_bytes(b"MWC1", "little"), 1, 1, 1, 4, 4)
    walls = struct.unpack_from("<I", board, 64)[0]
    holes_offset = 68 + walls * 16
    holes = struct.unpack_from("<I", board, holes_offset)[0]
    starts_offset = holes_offset + 4 + holes * 16
    starts = struct.unpack_from("<I", board, starts_offset)[0]
    assert starts == 1
    assert len(board) == starts_offset + 4 + starts * 8

    handle = nwcore.marble_create(1, 1, 0, 2600, 15000, 17)
    assert handle > 0
    try:
        assert nwcore.marble_info(handle, 0) == 0
        ready = nwcore.marble_frame(handle, 0, 912, 684)
        assert ready.startswith(b"NKIN") and len(ready) > 0
        assert nwcore.marble_action(handle, 0, 0, 0) == 1
        assert nwcore.marble_info(handle, 0) == 1
        assert nwcore.marble_action(handle, 6, 0, 0) == 1
        assert nwcore.marble_action(handle, 7, 0, 0) == 1
        assert nwcore.marble_info(handle, 11) == 3
        session = MarbleMazeSession.__new__(MarbleMazeSession)
        session.core = nwcore
        session.handle = handle
        session.release_all()
        assert nwcore.marble_info(handle, 11) == 0
        assert nwcore.marble_advance(handle, 15000) == 1
        assert nwcore.marble_info(handle, 0) == 2
        assert nwcore.marble_info(handle, 8) == 0
    finally:
        assert nwcore.marble_destroy(handle) == 0

    args = type("Args", (), {"trial": 1, "trials": 1, "adaptive": False,
                              "show_traps": True, "show_marks": True,
                              "seed": 17, "black_background": False})()
    menu = TaskHubSession(nwcore, args)
    for _ in range(2):
        menu.key(Keys.RIGHT, Keys)
    for _ in range(10):
        menu.key(Keys.DOWN, Keys)
    assert menu.category == 2 and menu.selected == 10
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, MarbleMazeSession)
    assert menu.child.state[0] == 0
    menu.child.key(Keys.RETURN, Keys)
    assert menu.child.state[0] == 0, "Enter must not start Marble Maze"
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[0] == 1
    assert menu.child.board_bytes == board, "host board must match controller rung/seed"
    menu.close()
    print("PASS: native Python Marble controller, Space-only start, display list, menu launch, held input, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
