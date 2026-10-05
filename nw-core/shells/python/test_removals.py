"""Headless native Removals lifecycle and display-list smoke."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # noqa: E402


def main() -> None:
    handle = nwcore.removals_create(1, 1, 500, 1, 17)
    assert handle > 0
    assert nwcore.removals_info(handle, 0) == 0
    assert nwcore.removals_action(handle, 0, 0, 0) == 1
    assert nwcore.removals_info(handle, 0) == 1
    assert nwcore.removals_frame(handle, 0, 912, 684)
    for now_ms in range(500, 500 * 50 + 1, 500):
        nwcore.removals_advance(handle, now_ms)
        if nwcore.removals_info(handle, 0) == 2:
            break
    assert nwcore.removals_info(handle, 0) == 2
    asks = nwcore.removals_info(handle, 13)
    for at in range(asks):
        answer = nwcore.removals_value(handle, 4, at)
        assert nwcore.removals_action(handle, 1 + answer, answer,
                                      30000 + at) == 1
    assert nwcore.removals_info(handle, 0) == 3
    nwcore.removals_destroy(handle)
    print("PASS: native Python Removals lifecycle, timing, answers, frame, and cleanup")


if __name__ == "__main__":
    main()
