#!/usr/bin/env python3
"""Headless lifecycle smoke for the native Python N-Cup Monte adapter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nwcore  # noqa: E402
from app import NCupMonteSession, TaskHubSession  # noqa: E402


class Args:
    black_background = False
    seed = 23


class Keys:
    LEFT, RIGHT, UP, DOWN = 5, 6, 7, 8
    SPACE, RETURN, ESCAPE = 1, 2, 4


def main() -> int:
    assert nwcore.ncup_monte_create(2, 8, 1, 6, 340, 1150, 23) == 0
    handle = nwcore.ncup_monte_create(3, 8, 1, 6, 340, 1150, 23)
    assert handle > 0
    try:
        assert nwcore.ncup_monte_info(handle, 0) == 0
        assert nwcore.ncup_monte_action(handle, 0, 0, 0) == 1
        assert nwcore.ncup_monte_info(handle, 0) == 1
        assert nwcore.ncup_monte_advance(handle, 1150) == 1
        frame = nwcore.ncup_monte_frame(handle, 0, 912, 684)
        assert frame.startswith(b"NKIN") and frame
    finally:
        assert nwcore.ncup_monte_destroy(handle) == 0

    menu = TaskHubSession(nwcore, Args())
    menu.category, menu.selected = 2, 1
    menu.key(Keys.SPACE, Keys)
    assert isinstance(menu.child, NCupMonteSession)
    assert menu.child.state[0] == 0
    menu.key(Keys.SPACE, Keys)
    assert menu.child.state[0] == 1
    menu.close()
    print("PASS: native Python N-Cup Monte lifecycle, display list, menu launch, and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
