"""Headless lifecycle smoke for the port-scoped 3D N-Back pymodule route."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "build" / "pymod"))

import nwcore  # type: ignore  # noqa: E402


def main() -> None:
    handle = nwcore.nback3d_create(2, 1, 4, 3000, 500, 0, 17)
    assert handle > 0
    try:
        assert nwcore.nback3d_info(handle, 0) == 0
        first = nwcore.nback3d_frame(handle, 0, 912, 684)
        assert first
        assert nwcore.nback3d_action(handle, 0, 0) == 1
        assert nwcore.nback3d_info(handle, 7) == -1
        assert nwcore.nback3d_advance(handle, 1000) == 1
        assert nwcore.nback3d_info(handle, 0) == 1
        visible = nwcore.nback3d_frame(handle, 0, 912, 684)
        assert visible != first
        assert nwcore.nback3d_action(handle, 1, 1100) in (1, 2)
        assert nwcore.nback3d_advance(handle, 1500) == 1
        assert nwcore.nback3d_info(handle, 0) == 2
    finally:
        assert nwcore.nback3d_destroy(handle) == 0
    print("PASS: Python 3D-only N-Back lifecycle, live frame, timing, input, and disposal")


if __name__ == "__main__":
    main()
