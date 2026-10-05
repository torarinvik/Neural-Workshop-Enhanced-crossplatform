"""Source-builder parity and wall-safe native Marble collar geometry."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(HERE))
source_root = Path(os.environ["NEURAL_WORKSHOP_SOURCE_ROOT"])
sys.path.insert(0, str(source_root))

import nwcore
from marble_geometry import build_scene, cup_collar_outer_radius, stage_rect
from marble_mujoco import decode_board
from neural_workshop import marblemaze as source_marblemaze
from neural_workshop.ui.marblemaze import _cup_collar_outer_radius
from neural_workshop.ui.render3d import Builder as SourceBuilder


def source_meshes(board):
    half_w, half_d = board.width / 2, board.depth / 2
    wx = lambda x: x - half_w
    wz = lambda y: half_d - y
    body = SourceBuilder()
    body.box(-half_w, -0.013, -half_d, half_w, 0, half_d)
    frame = SourceBuilder()
    rail, rail_high, slab = 0.016, max(0.020, board.height * 1.25), 0.013
    frame.box(-half_w - rail, -slab, -half_d - rail, half_w + rail, rail_high, -half_d)
    frame.box(-half_w - rail, -slab, half_d, half_w + rail, rail_high, half_d + rail)
    frame.box(-half_w - rail, -slab, -half_d, -half_w, rail_high, half_d)
    frame.box(half_w, -slab, -half_d, half_w + rail, rail_high, half_d)
    walls = SourceBuilder()
    for wall in board.walls:
        walls.box(wx(wall.x0), 0, wz(wall.y1), wx(wall.x1), board.height, wz(wall.y0))
    pits, cups, collar = SourceBuilder(), SourceBuilder(), SourceBuilder()
    for hole in board.holes:
        (cups if hole.home else pits).tube(
            wx(hole.x), wz(hole.y), hole.radius, 0, -0.032
        )
        if hole.home:
            outer = _cup_collar_outer_radius(hole, board.walls)
            if outer is not None:
                collar.ring(wx(hole.x), wz(hole.y), hole.radius, outer, 0.0006)
    ball = SourceBuilder()
    ball.sphere(0.0075)
    return {
        "body": body,
        "frame": frame,
        "walls": walls,
        "pits": pits,
        "cups": cups,
        "collar": collar,
        "ball": ball,
    }


def main() -> int:
    seeds = (0, 1, 17, 314159, 1073741823)
    meshes_checked = 0
    adjusted_collars = 0
    for rung in range(1, 17):
        for seed in seeds:
            board = decode_board(nwcore.marble_board(rung, seed))
            actual = build_scene(board)
            expected = source_meshes(board)
            assert len(actual.holes) == len(board.holes)
            home = board.holes[-1]
            outer = _cup_collar_outer_radius(home, board.walls)
            assert outer == cup_collar_outer_radius(board, home)
            if rung == 14 and seed == 0:
                assert outer is None or outer < home.radius * 1.34 - 1e-9
            if outer is not None:
                if outer < home.radius * 1.34 - 1e-9:
                    adjusted_collars += 1
                for wall in board.walls:
                    dx = max(wall.x0 - home.x, 0.0, home.x - wall.x1)
                    dy = max(wall.y0 - home.y, 0.0, home.y - wall.y1)
                    assert math.hypot(dx, dy) - outer >= (
                        source_marblemaze.HOLE_WALL_CLEARANCE - 1e-9
                    ), (rung, seed, "cup collar overlaps wall", outer, wall)
            for name, builder in expected.items():
                mesh = actual.meshes[name]
                assert mesh.positions == tuple(builder.positions), (
                    rung,
                    seed,
                    name,
                    "positions",
                )
                assert mesh.normals == tuple(builder.normals), (
                    rung,
                    seed,
                    name,
                    "normals",
                )
                assert mesh.indices == tuple(builder.indices), (
                    rung,
                    seed,
                    name,
                    "indices",
                )
                meshes_checked += 1

    assert adjusted_collars > 0, "geometry sweep did not trim a home-cup collar"

    for dimensions, expected in (
        ((912, 684), (27, 179, 857, 417)),
        ((1280, 960), (38, 248, 1203, 588)),
        ((1604, 1203), (48, 309, 1507, 739)),
        ((1520, 1140), (45, 293, 1428, 700)),
    ):
        assert stage_rect(*dimensions) == expected, (
            dimensions,
            stage_rect(*dimensions),
        )

    print(
        f"PASS: native Marble geometry matches source Builder for "
        f"{meshes_checked} meshes / 80 boards; {adjusted_collars} cup "
        f"collars trimmed clear of walls; stage bounds match source"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
