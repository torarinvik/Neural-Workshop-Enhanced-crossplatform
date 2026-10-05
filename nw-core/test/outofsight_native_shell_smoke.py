"""Native Python ABI smoke for the Out of Sight controller."""

from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # type: ignore  # noqa: E402


PACKED = 2 + (2 * 6) + (2 * 6 * 7) + (1 * 6 * 7 * 8)


def main() -> None:
    handle = nwcore.out_of_sight_create(8, 2, 30, 1200, 2, PACKED, 17)
    assert handle > 0
    try:
        assert nwcore.out_of_sight_info(handle, 0) == 0
        assert nwcore.out_of_sight_action(handle, 0, 0, 0) == 1
        assert nwcore.out_of_sight_info(handle, 0) == 1
        for now_ms in (100, 500, 1000, 1500, 2500, 4000):
            nwcore.out_of_sight_advance(handle, now_ms)
        assert nwcore.out_of_sight_frame(handle, 0, 912, 684)
    finally:
        assert nwcore.out_of_sight_destroy(handle) == 0
    print("PASS: native Python Out of Sight lifecycle, frame, and cleanup")


if __name__ == "__main__":
    main()
