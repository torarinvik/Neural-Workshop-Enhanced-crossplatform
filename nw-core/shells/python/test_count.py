#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Count adapter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import CountSession, TaskHubSession  # noqa: E402


class Args:
    black_background = False
    seed = 23
    trial = 1
    trials = 5
    adaptive = False
    show_traps = False
    show_marks = False


class Keys:
    LEFT, RIGHT, UP, DOWN = 5, 6, 7, 8
    SPACE, RETURN, BACKSPACE, ESCAPE = 1, 2, 3, 4
    _0, _1, _2, _3, _4 = 10, 11, 12, 13, 14
    _5, _6, _7, _8, _9 = 15, 16, 17, 18, 19


def main() -> int:
    assert nwcore.count_create(0, 8, 5, 201, 1, 1, 23) == -1
    handle = nwcore.count_create(0, 8, 5, 200, 1, 1, 23)
    assert handle > 0
    try:
        assert nwcore.count_info(handle, 0) == 0
        assert nwcore.count_action(handle, 0, 0, 1000) == 1
        assert nwcore.count_info(handle, 0) == 1
        shown = nwcore.count_info(handle, 8)
        assert shown == 8
        frame = nwcore.count_frame(handle, 0, 912, 684)
        assert frame.startswith(b"NKIN") and frame
        assert nwcore.count_advance(handle, 1200) == 1
        assert nwcore.count_info(handle, 0) == 2
        assert nwcore.count_action(handle, 1, shown // 10, 1201) == 1
        assert nwcore.count_action(handle, 1, shown % 10, 1202) == 1
        assert nwcore.count_action(handle, 3, 1203, 0) == 1
        assert nwcore.count_info(handle, 9) == 1
    finally:
        assert nwcore.count_destroy(handle) == 0

    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 3, 0
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, CountSession)
    assert menu.child.state[0] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[0] == 1
    menu.close()
    print("PASS: native Python Count lifecycle, display list, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
