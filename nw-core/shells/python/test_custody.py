#!/usr/bin/env python3
"""Focused native Chain of Custody lifecycle smoke."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # noqa: E402


def main() -> None:
    handle = nwcore.custody_create(1, 1, 900, 1200, 0, 17)
    assert handle > 0
    try:
        assert nwcore.custody_info(handle, 0) == 0
        assert nwcore.custody_action(handle, 0, 0, 0) == 1
        assert nwcore.custody_info(handle, 0) == 1
        nwcore.custody_advance(handle, 1200)
        assert nwcore.custody_info(handle, 0) == 2
        assert nwcore.custody_frame(handle, 0, 912, 684)

        for now_ms in range(2100, 50000, 900):
            nwcore.custody_advance(handle, now_ms)
            if nwcore.custody_info(handle, 0) in (3, 4):
                break
        assert nwcore.custody_info(handle, 0) in (3, 4)
    finally:
        assert nwcore.custody_destroy(handle) == 0
    print("PASS: native Python Chain of Custody lifecycle, timing, frame, and cleanup")


if __name__ == "__main__":
    main()
