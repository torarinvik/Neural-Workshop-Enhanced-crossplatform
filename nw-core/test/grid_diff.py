#!/usr/bin/env python3
"""Differential harness for the explicit grid context."""
from pathlib import Path
import subprocess
import sys
import types

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import grid, state  # noqa: E402
from neural_workshop.config import DotDict  # noqa: E402


def emit(tag, *values):
    return "|".join([tag] + [str(v) for v in values])


def install(spec):
    cfg = DotDict(
        GRID_SIZE=1 + spec % 9,
        GRID_SIZE_MIN=(spec % 5) - 1,
        GRID_SIZE_MAX=2 + spec % 8,
        GRID_INCLUDE_CENTER=spec % 2 == 1,
        GRID_3D=spec % 4 == 3,
        GRID_3D_CUBES=(spec % 9) - 2,
        ACTIVE_POSITION_CELLS=0 if spec % 3 != 0 else spec % 11,
        POSITION_CELL_COUNT=0 if spec % 5 != 0 else 2 + spec % 7,
    )
    state.cfg = cfg
    state.field = types.SimpleNamespace(
        size=float(640 + spec * 17),
        center_x=456.0 + (spec % 5) / 2.0,
        center_y=342.0 + (spec % 7) / 2.0,
    )


def python_lines():
    out = []
    for spec in range(32):
        install(spec)
        low, high = grid.current_grid_bounds()
        out.append(emit("scalar", spec, low, high, grid.current_grid_size(),
                        int(grid.current_include_center()),
                        int(grid.current_grid_3d()),
                        grid.current_3d_cube_count(),
                        grid.current_3d_palette_size(),
                        grid.current_3d_color_count(), grid.current_cell_count(),
                        int(grid.current_cell_px()),
                        grid.current_active_cell_limit()))
        count = 1 + spec % 7
        out.append(emit("faces", *grid.decode_3d_pattern(spec - 4, count)))
        out.append(emit("colors", *grid.decode_3d_colors(spec - 4, count)))
        out.append(emit("active", *grid.current_active_position_ids()))
        for position in (-2, 0, 1, 2, 8, 9, 25, 64):
            x, y = grid.position_pixel_center(position)
            out.append(emit("centre", spec, position, x, y))
        x, y = grid.position_3d_node_px(spec % 8 - 2, spec % 7,
                                         spec % 11, 5 + spec % 4)
        out.append(emit("node", spec, x, y))
    return out


def main():
    got = [line for line in subprocess.run(
        [sys.argv[1]], capture_output=True, text=True, check=True
    ).stdout.splitlines() if line and not line.startswith("names|")]
    want = python_lines()
    if got != want:
        for index, (a, b) in enumerate(zip(got, want)):
            if a != b:
                print(f"FAIL: first mismatch at {index}\n  elisa:  {a}\n  python: {b}")
                break
        if len(got) != len(want):
            print(f"FAIL: line count {len(got)} vs {len(want)}")
        return 1
    print(f"PASS: {len(want)} grid cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
