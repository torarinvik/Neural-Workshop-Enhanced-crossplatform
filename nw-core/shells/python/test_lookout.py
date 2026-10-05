#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Lookout adapter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import LookoutSession, TaskHubSession  # noqa: E402


class Args:
    black_background = False
    seed = 23


class Keys:
    LEFT, RIGHT, UP, DOWN = 5, 6, 7, 8
    SPACE, RETURN, ESCAPE = 1, 2, 4
    F, J = 9, 10


def main() -> int:
    assert nwcore.lookout_create(7, 2, 30, 1200, 10, 1, 23) == 0
    handle = nwcore.lookout_create(8, 2, 30, 1200, 10, 1, 23)
    assert handle > 0
    try:
        assert nwcore.lookout_info(handle, 0) == 0
        assert nwcore.lookout_action(handle, 0, 0, 0) == 1
        assert nwcore.lookout_info(handle, 0) == 1
        assert nwcore.lookout_info(handle, 20) == 8
        assert nwcore.lookout_advance(handle, 100) == 1
        frame = nwcore.lookout_frame(handle, 0, 912, 684)
        assert frame.startswith(b"NKIN") and frame
    finally:
        assert nwcore.lookout_destroy(handle) == 0

    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 2, 3
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, LookoutSession)
    assert menu.child.state[LookoutSession.INFO_PHASE] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[LookoutSession.INFO_PHASE] == 1
    menu.close()
    print("PASS: native Python Lookout lifecycle, display list, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
