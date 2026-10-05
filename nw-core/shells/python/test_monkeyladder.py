#!/usr/bin/env python3
"""Headless native Monkey Ladder lifecycle and concealment smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # noqa: E402
from app import MonkeyLadderSession, TaskHubSession  # noqa: E402


def main() -> int:
    handle = nwcore.monkey_ladder_create(5, 2, 1, 300, 120, 1, 17)
    assert handle > 0
    try:
        assert nwcore.monkey_ladder_info(handle, 0) == 0
        nwcore.monkey_ladder_action(handle, 0, 0, 1000)
        assert nwcore.monkey_ladder_info(handle, 0) == 1
        length = nwcore.monkey_ladder_info(handle, 4)
        assert length == 2
        answer = nwcore.monkey_ladder_cell(handle, 0, 0)
        assert 0 <= answer < 25
        frame = nwcore.monkey_ladder_frame(handle, 0, 912, 684)
        assert frame
        nwcore.monkey_ladder_action(handle, 1, 0, 2000)
        assert nwcore.monkey_ladder_info(handle, 0) == 2
        nwcore.monkey_ladder_action(handle, 2, answer, 2001)
        assert nwcore.monkey_ladder_info(handle, 5) == 1
        assert nwcore.monkey_ladder_frame(handle, 0, 912, 684)
    finally:
        assert nwcore.monkey_ladder_destroy(handle) == 0
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
        SPACE, RETURN, ESCAPE = 5, 6, 7
    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 0, 1
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, MonkeyLadderSession)
    menu.close()
    print("PASS: native Python Monkey Ladder timing, concealment, action, frame, cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
