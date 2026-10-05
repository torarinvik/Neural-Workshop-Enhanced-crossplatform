"""Native Python ABI smoke for the source-backed Donkey task."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # type: ignore  # noqa: E402


def main() -> None:
    handle = nwcore.donkey_create(1, 1, 180, 400, 1, 0, 17)
    assert handle > 0
    try:
        assert nwcore.donkey_info(handle, 0) == 0
        assert nwcore.donkey_action(handle, 0, 0, 0) == 1
        assert nwcore.donkey_info(handle, 0) == 1
        assert nwcore.donkey_advance(handle, 500) >= 1
        assert nwcore.donkey_info(handle, 0) == 2
        frame = nwcore.donkey_frame(handle, 0, 912, 684)
        assert frame
    finally:
        assert nwcore.donkey_destroy(handle) == 0
    print("PASS: native Python Donkey lifecycle, frame, and cleanup")


if __name__ == "__main__":
    main()
