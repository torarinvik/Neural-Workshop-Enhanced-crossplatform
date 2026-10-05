"""Headless native In the Dark lifecycle and display-list smoke."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # noqa: E402


def main() -> None:
    handle = nwcore.in_the_dark_create(1, 1, 500, 1, 17)
    assert handle > 0
    assert nwcore.in_the_dark_info(handle, 0) == 0
    assert nwcore.in_the_dark_action(handle, 0, 0, 0) == 1
    assert nwcore.in_the_dark_info(handle, 0) == 1
    assert nwcore.in_the_dark_frame(handle, 0, 912, 684)
    for now_ms in range(500, 500 * 40 + 1, 500):
        nwcore.in_the_dark_advance(handle, now_ms)
        if nwcore.in_the_dark_info(handle, 0) == 2:
            break
    assert nwcore.in_the_dark_info(handle, 0) == 2
    asks = nwcore.in_the_dark_info(handle, 22)
    assert asks > 0
    for at in range(asks):
        colour = nwcore.in_the_dark_asked(handle, 1, at)
        assert 0 <= colour < 5
        assert nwcore.in_the_dark_action(handle, 1 + colour, colour, 501) == 1
    assert nwcore.in_the_dark_info(handle, 0) == 3
    nwcore.in_the_dark_destroy(handle)
    print("PASS: native Python In the Dark lifecycle, hidden-state answers, frame, and cleanup")


if __name__ == "__main__":
    main()
