"""Pure-Python Marble Maze meshes and camera, matching the browser scene.

The module is independent of OpenGL so its geometry and camera contract can
be verified headlessly before a Pyglet draw backend owns GPU resources.
Coordinates follow the source renderer: tray x/y becomes scene x/z, with
positive scene y pointing out of the tray.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from marble_mujoco import Board, RADIUS


HOLE_WALL_CLEARANCE = RADIUS * 0.40
CUP_COLLAR_SCALE = 1.34


def cup_collar_outer_radius(board: Board, hole) -> float | None:
    """Return a wall-safe decorative radius, without changing the opening."""
    nearest_wall = min((
        math.hypot(max(wall.x0 - hole.x, 0.0, hole.x - wall.x1),
                   max(wall.y0 - hole.y, 0.0, hole.y - wall.y1))
        for wall in board.walls
    ), default=math.inf)
    available = min(hole.radius * CUP_COLLAR_SCALE,
                    nearest_wall - HOLE_WALL_CLEARANCE)
    return available if available > hole.radius else None


@dataclass(frozen=True)
class Mesh:
    positions: tuple[float, ...]
    normals: tuple[float, ...]
    indices: tuple[int, ...]


class Builder:
    def __init__(self) -> None:
        self.positions: list[float] = []
        self.normals: list[float] = []
        self.indices: list[int] = []

    def face(
        self,
        points: tuple[tuple[float, float, float], ...],
        normal: tuple[float, float, float],
    ) -> None:
        base = len(self.positions) // 3
        for point in points:
            self.positions.extend(point)
            self.normals.extend(normal)
        self.indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))

    def box(
        self, x0: float, y0: float, z0: float, x1: float, y1: float, z1: float
    ) -> None:
        self.face(((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)), (0, 1, 0))
        self.face(((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), (0, -1, 0))
        self.face(((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)), (0, 0, 1))
        self.face(((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)), (0, 0, -1))
        self.face(((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)), (1, 0, 0))
        self.face(((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)), (-1, 0, 0))

    def tube(
        self,
        cx: float,
        cz: float,
        radius: float,
        top: float,
        bottom: float,
        segments: int = 22,
        floor_disc: bool = True,
    ) -> None:
        base = len(self.positions) // 3
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            nx, nz = math.cos(angle), math.sin(angle)
            x, z = cx + nx * radius, cz + nz * radius
            self.positions.extend((x, top, z, x, bottom, z))
            self.normals.extend((-nx, 0, -nz, -nx, 0, -nz))
        for index in range(segments):
            a = base + index * 2
            b = base + ((index + 1) % segments) * 2
            self.indices.extend((a, b, b + 1, a, b + 1, a + 1))
        if floor_disc:
            centre = len(self.positions) // 3
            self.positions.extend((cx, bottom, cz))
            self.normals.extend((0, 1, 0))
            rim = len(self.positions) // 3
            for index in range(segments):
                angle = 2 * math.pi * index / segments
                self.positions.extend(
                    (
                        cx + math.cos(angle) * radius,
                        bottom,
                        cz + math.sin(angle) * radius,
                    )
                )
                self.normals.extend((0, 1, 0))
            for index in range(segments):
                self.indices.extend((centre, rim + index, rim + (index + 1) % segments))

    def ring(
        self,
        cx: float,
        cz: float,
        inner: float,
        outer: float,
        y: float,
        segments: int = 30,
    ) -> None:
        base = len(self.positions) // 3
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            cosine, sine = math.cos(angle), math.sin(angle)
            self.positions.extend(
                (
                    cx + cosine * inner,
                    y,
                    cz + sine * inner,
                    cx + cosine * outer,
                    y,
                    cz + sine * outer,
                )
            )
            self.normals.extend((0, 1, 0, 0, 1, 0))
        for index in range(segments):
            a = base + index * 2
            b = base + ((index + 1) % segments) * 2
            self.indices.extend((a, a + 1, b + 1, a, b + 1, b))

    def sphere(self, radius: float, rings: int = 26, segments: int = 34) -> None:
        base = len(self.positions) // 3
        for ring in range(rings + 1):
            phi = math.pi * ring / rings
            y, radial = math.cos(phi), math.sin(phi)
            for step in range(segments + 1):
                theta = 2 * math.pi * step / segments
                nx, nz = radial * math.cos(theta), radial * math.sin(theta)
                self.positions.extend((nx * radius, y * radius, nz * radius))
                self.normals.extend((nx, y, nz))
        for ring in range(rings):
            for step in range(segments):
                a = base + ring * (segments + 1) + step
                b = a + segments + 1
                self.indices.extend((a, b, b + 1, a, b + 1, a + 1))

    def finish(self) -> Mesh:
        return Mesh(tuple(self.positions), tuple(self.normals), tuple(self.indices))


@dataclass(frozen=True)
class SceneGeometry:
    meshes: Mapping[str, Mesh]
    holes: tuple[tuple[float, float, float, float], ...]


def build_scene(board: Board) -> SceneGeometry:
    half_w, half_d = board.width / 2, board.depth / 2
    wx, wz = lambda x: x - half_w, lambda y: half_d - y
    body = Builder()
    body.box(-half_w, -0.013, -half_d, half_w, 0, half_d)
    frame = Builder()
    rail = 0.016
    rail_high = max(0.020, board.height * 1.25)
    slab = 0.013
    frame.box(-half_w - rail, -slab, -half_d - rail, half_w + rail, rail_high, -half_d)
    frame.box(-half_w - rail, -slab, half_d, half_w + rail, rail_high, half_d + rail)
    frame.box(-half_w - rail, -slab, -half_d, -half_w, rail_high, half_d)
    frame.box(half_w, -slab, -half_d, half_w + rail, rail_high, half_d)
    walls = Builder()
    for wall in board.walls:
        walls.box(wx(wall.x0), 0, wz(wall.y1), wx(wall.x1), board.height, wz(wall.y0))
    pits, cups, collar = Builder(), Builder(), Builder()
    for hole in board.holes:
        x, z = wx(hole.x), wz(hole.y)
        (cups if hole.home else pits).tube(x, z, hole.radius, 0, -0.032)
        if hole.home:
            outer_radius = cup_collar_outer_radius(board, hole)
            if outer_radius is not None:
                collar.ring(x, z, hole.radius, outer_radius, 0.0006)
    ball = Builder()
    ball.sphere(0.0075)
    holes = tuple(
        (wx(hole.x), wz(hole.y), hole.radius, float(hole.home))
        for hole in board.holes[:96]
    )
    return SceneGeometry(
        {
            "body": body.finish(),
            "frame": frame.finish(),
            "walls": walls.finish(),
            "pits": pits.finish(),
            "cups": cups.finish(),
            "collar": collar.finish(),
            "ball": ball.finish(),
        },
        holes,
    )


def stage_rect(width: int, height: int) -> tuple[int, int, int, int]:
    """Source renderer's physical-pixel stage (x, bottom, width, height)."""
    width, height = max(1, int(width)), max(1, int(height))
    bottom_margin = int(58 * height / 684)
    # JS/source use height - floor(0.75 * height), which is ceil(height/4)
    # for dimensions not divisible by four.
    band_ceiling = height - int(height * 0.75)
    bottom = max(bottom_margin, band_ceiling + 8)
    top = int(height - 88 * height / 684)
    return int(width * 0.03), bottom, int(width * 0.94), max(48, top - bottom)
