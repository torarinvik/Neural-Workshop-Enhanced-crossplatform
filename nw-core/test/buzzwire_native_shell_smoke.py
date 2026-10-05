"""Native Python ABI smoke for Buzz Wire."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # type: ignore  # noqa: E402


def main() -> None:
    handle = nwcore.buzz_wire_create(1, 1, 1, 1, 1, 1, 17)
    assert handle > 0
    try:
        assert nwcore.buzz_wire_info(handle, 0) == 0
        assert nwcore.buzz_wire_action(handle, 0, 0, 0) == 1
        assert nwcore.buzz_wire_info(handle, 0) == 1
        assert nwcore.buzz_wire_advance(handle, 100) >= 1
        assert nwcore.buzz_wire_frame(handle, 0, 912, 684)
    finally:
        assert nwcore.buzz_wire_destroy(handle) == 0
    print("PASS: native Python Buzz Wire lifecycle, frame, and cleanup")


if __name__ == "__main__":
    main()
