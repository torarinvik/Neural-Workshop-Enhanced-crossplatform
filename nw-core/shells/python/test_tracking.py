#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python Moving Targets adapter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import TaskHubSession, TrackingSession  # noqa: E402


class Args:
    black_background = False
    seed = 23


class Keys:
    LEFT, RIGHT, UP, DOWN = 5, 6, 7, 8
    SPACE, RETURN, ESCAPE = 1, 2, 4


def main() -> int:
    assert nwcore.tracking_create(7, 2, 3, 30, 5, 1, 23) == 0
    handle = nwcore.tracking_create(8, 2, 3, 30, 5, 1, 23)
    assert handle > 0
    try:
        assert nwcore.tracking_info(handle, 0) == 0
        assert nwcore.tracking_action(handle, 0, 0, 0) == 1
        assert nwcore.tracking_info(handle, 0) == 1
        assert nwcore.tracking_advance(handle, 2000) == 1
        assert nwcore.tracking_info(handle, 0) == 2
        frame = nwcore.tracking_frame(handle, 0, 912, 684)
        assert frame.startswith(b"NKIN") and frame
    finally:
        assert nwcore.tracking_destroy(handle) == 0

    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 2, 2
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, TrackingSession)
    assert menu.child.state[0] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[0] == 1
    menu.close()
    print("PASS: native Python Moving Targets lifecycle, display list, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
