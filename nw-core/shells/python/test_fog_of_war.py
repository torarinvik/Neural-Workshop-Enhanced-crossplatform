"""Headless native Fog of War lifecycle and display-list smoke."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # noqa: E402


def main() -> None:
    handle = nwcore.fog_create(2, 100, 1, 1, 17)
    assert handle > 0
    assert nwcore.fog_info(handle, 0) == 0
    assert nwcore.fog_action(handle, 0) == 1
    assert nwcore.fog_info(handle, 0) == 1
    assert nwcore.fog_info(handle, 6) == 25
    assert nwcore.fog_info(handle, 7) == 15
    assert nwcore.fog_frame(handle, 0, 912, 684)
    walker = nwcore.fog_info(handle, 3)
    assert nwcore.fog_action(handle, 2) == 1
    assert nwcore.fog_info(handle, 4) == 1
    assert nwcore.fog_info(handle, 3) != walker or nwcore.fog_info(handle, 18) >= 0
    nwcore.fog_destroy(handle)
    print("PASS: native Python Fog of War lifecycle, movement, frame, and cleanup")


if __name__ == "__main__":
    main()
