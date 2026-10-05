#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Pursuit adapter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import PursuitSession, TaskHubSession  # noqa: E402


class Args:
    black_background = False
    seed = 23


class Keys:
    LEFT, RIGHT, UP, DOWN = 5, 6, 7, 8
    SPACE, RETURN, ESCAPE = 1, 2, 4


def main() -> int:
    assert nwcore.pursuit_create(21, 40, 400, 90, 16, 0, 23) == 0
    handle = nwcore.pursuit_create(20, 40, 400, 90, 16, 0, 23)
    assert handle > 0
    try:
        assert nwcore.pursuit_info(handle, 0) == 0
        assert nwcore.pursuit_action(handle, 0, 0, 0) == 1
        assert nwcore.pursuit_info(handle, 0) == 1
        assert nwcore.pursuit_advance(handle, 100) == 1
        assert nwcore.pursuit_pointer(handle, 500000, 500000) == 1
        frame = nwcore.pursuit_frame(handle, 0, 912, 684)
        assert frame.startswith(b"NKIN") and frame
    finally:
        assert nwcore.pursuit_destroy(handle) == 0

    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 2, 4
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, PursuitSession)
    assert menu.child.state[PursuitSession.INFO_PHASE] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[PursuitSession.INFO_PHASE] == 1
    menu.close()
    print("PASS: native Python Pursuit lifecycle, display list, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
