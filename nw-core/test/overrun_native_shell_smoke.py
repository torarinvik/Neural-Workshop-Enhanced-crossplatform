"""Native Python ABI smoke for the source-backed Overrun task."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # type: ignore  # noqa: E402


def main() -> None:
    handle = nwcore.overrun_create(1, 3, 1, 0, 0, 0, 17)
    assert handle > 0
    try:
        assert nwcore.overrun_info(handle, 0) == 0
        assert nwcore.overrun_action(handle, 0, 0, 0) == 1
        assert nwcore.overrun_info(handle, 0) == 1
        # The first generated letter is a valid source-backed write; the
        # controller owns the generated wave and grading state.
        letter = nwcore.overrun_value(handle, 3, 0)
        assert 0 <= letter <= 25
        assert nwcore.overrun_action(handle, 1, letter, 1) == 1
        assert nwcore.overrun_advance(handle, 100) >= 0
        assert nwcore.overrun_frame(handle, 0, 912, 684)
    finally:
        assert nwcore.overrun_destroy(handle) == 0
    print("PASS: native Python Overrun lifecycle, generated input, frame, and cleanup")


if __name__ == "__main__":
    main()
