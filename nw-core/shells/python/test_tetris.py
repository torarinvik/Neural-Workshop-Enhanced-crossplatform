#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Freeform Tetris adapter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import TaskHubSession, TetrisSession  # noqa: E402


class Args:
    black_background = False
    seed = 17
    trial = 1
    trials = 1
    adaptive = False
    show_traps = False
    show_marks = False


class Keys:
    LEFT, RIGHT, UP, DOWN = 1, 2, 3, 4
    SPACE, RETURN, ESCAPE, R = 5, 6, 7, 8
    _1, _2, _3, _4, _5, _6 = 9, 10, 11, 12, 13, 14


def main() -> int:
    assert nwcore.tetris_create(0, 25, 5, 17) == -1
    handle = nwcore.tetris_create(1, 25, 5, 17)
    assert handle > 0
    try:
        assert nwcore.tetris_info(handle, 0) == 0
        ready = nwcore.tetris_frame(handle, 0, 912, 684)
        assert ready.startswith(b"NKIN") and ready
        assert nwcore.tetris_action(handle, 0) == 1
        assert nwcore.tetris_info(handle, 0) == 1
        selected = nwcore.tetris_info(handle, 4)
        assert 0 <= selected < 5
        assert nwcore.tetris_action(handle, 7) == 1
        assert nwcore.tetris_info(handle, 4) == 1
        before = nwcore.tetris_info(handle, 2)
        assert nwcore.tetris_action(handle, 4) == 1
        assert nwcore.tetris_info(handle, 2) == before + 1
        assert nwcore.tetris_frame(handle, 0, 1280, 720)
    finally:
        assert nwcore.tetris_destroy(handle) == 0

    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 5, 6
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, TetrisSession)
    assert menu.child.state[0] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[0] == 1
    menu.key(Keys._2, Keys)
    assert menu.child.state[4] == 1
    menu.close()
    print("PASS: native Python Tetris lifecycle, display list, selection, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
