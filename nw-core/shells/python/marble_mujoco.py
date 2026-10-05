"""Native MuJoCo runtime for the source-backed Marble Maze board ABI.

This module mirrors the browser MuJoCo adapter and the original wrapper rules.
It is deliberately separate from the display-list fallback so callers can
report an unavailable MuJoCo dependency instead of claiming equivalent
physics when only the fallback is running.
"""
from __future__ import annotations

import math
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

GRAVITY = 9.80665
RADIUS = 0.0075
FRICTION_STATIC = 0.50
ROLLING_RESISTANCE = 0.008
VISCOUS_DRAG = 0.22
SPIN_GRIP = 0.005
REST_SPEED = 0.006
SPEED_CAP = 1.0
SUBSTEPS = 4
MAX_TILT = 0.140
TILT_STEP = 0.006
WALL_FRICTION = 0.08
MAX_BOARD_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class Wall:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class Hole:
    x: float
    y: float
    radius: float
    home: bool


@dataclass(frozen=True)
class Start:
    x: float
    y: float


@dataclass(frozen=True)
class Board:
    rung: int
    cols: int
    rows: int
    width: float
    depth: float
    cell: float
    thickness: float
    height: float
    home_x: float
    home_y: float
    home_radius: float
    seconds: float
    route: float
    walls: tuple[Wall, ...]
    holes: tuple[Hole, ...]
    starts: tuple[Start, ...]


@dataclass
class Marble:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    z: float = RADIUS
    vz: float = 0.0
    wx: float = 0.0
    wy: float = 0.0
    wz: float = 0.0
    qw: float = 1.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0
    state: str = "rolling"
    over: Hole | None = None

    @property
    def live(self) -> bool:
        return self.state in ("rolling", "falling")


def _unpack_u32(data: memoryview, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("truncated MWC1 board")
    return struct.unpack_from("<I", data, offset)[0]


def _unpack_f32(data: memoryview, offset: int) -> float:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("truncated MWC1 board")
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise ValueError("non-finite MWC1 board field")
    return value


def decode_board(payload: bytes | bytearray | memoryview) -> Board:
    """Decode the checked little-endian MWC1 v1 board transport."""
    data = memoryview(payload).cast("B")
    if len(data) > MAX_BOARD_BYTES or len(data) < 68:
        raise ValueError("invalid MWC1 board length")
    if bytes(data[:4]) != b"MWC1" or _unpack_u32(data, 4) != 1:
        raise ValueError("unsupported Marble Maze board ABI")
    if _unpack_u32(data, 8) != 1:
        raise ValueError("Marble Maze board is not built")
    rung, cols, rows = (_unpack_u32(data, offset) for offset in (12, 16, 20))
    if not (1 <= rung <= 16 and 1 <= cols <= 12 and 4 <= rows <= 10):
        raise ValueError("out-of-range MWC1 dimensions")
    scalars = tuple(_unpack_f32(data, offset) for offset in range(24, 64, 4))
    width, depth, cell, thickness, height, _home_x, _home_y, home_radius, seconds, route = scalars
    if min(width, depth, cell, thickness, height, home_radius, seconds, route) <= 0:
        raise ValueError("non-positive MWC1 geometry or timing")
    cursor = 64
    wall_count = _unpack_u32(data, cursor)
    cursor += 4
    if wall_count > 8192 or cursor + wall_count * 16 + 4 > len(data):
        raise ValueError("invalid MWC1 wall count")
    walls: list[Wall] = []
    for _ in range(wall_count):
        x0, y0, x1, y1 = (_unpack_f32(data, cursor + i * 4) for i in range(4))
        cursor += 16
        if x1 < x0 or y1 < y0:
            raise ValueError("reversed MWC1 wall bounds")
        walls.append(Wall(x0, y0, x1, y1))
    hole_count = _unpack_u32(data, cursor)
    cursor += 4
    if hole_count > 512 or cursor + hole_count * 16 + 4 > len(data):
        raise ValueError("invalid MWC1 hole count")
    holes: list[Hole] = []
    for _ in range(hole_count):
        x, y, radius = (_unpack_f32(data, cursor + i * 4) for i in range(3))
        home = _unpack_u32(data, cursor + 12)
        cursor += 16
        if radius <= 0 or home not in (0, 1):
            raise ValueError("invalid MWC1 hole")
        holes.append(Hole(x, y, radius, bool(home)))
    start_count = _unpack_u32(data, cursor)
    cursor += 4
    if not 1 <= start_count <= 8 or cursor + start_count * 8 != len(data):
        raise ValueError("invalid MWC1 start count or trailing bytes")
    starts = tuple(Start(_unpack_f32(data, cursor + i * 8),
                         _unpack_f32(data, cursor + i * 8 + 4))
                   for i in range(start_count))
    return Board(rung, cols, rows, *scalars, tuple(walls), tuple(holes), starts)


def build_mjcf(board: Board, count: int) -> str:
    """Create exactly the source-compatible model description."""
    if not 1 <= count <= 8:
        raise ValueError("Marble Maze model requires 1..8 marbles")
    crr = ROLLING_RESISTANCE * RADIUS
    parts = [
        "<mujoco>",
        f'<option integrator="implicitfast" cone="elliptic" noslip_iterations="2" timestep="0.004" gravity="0 0 -{GRAVITY:.5f}"/>',
        f'<worldbody><geom name="floor" type="plane" size="{max(board.width, 1.0) * 2:.4f} {max(board.depth, 1.0) * 2:.4f} 0.1" friction="{FRICTION_STATIC:.3f} {SPIN_GRIP:.4f} {crr:.6f}" condim="6" contype="1" conaffinity="1"/>',
    ]
    for index, wall in enumerate(board.walls):
        parts.append(
            f'<geom name="wall{index}" type="box" pos="{(wall.x0 + wall.x1) / 2:.6f} {(wall.y0 + wall.y1) / 2:.6f} {board.height / 2:.6f}" '
            f'size="{max(1e-4, (wall.x1 - wall.x0) / 2):.6f} {max(1e-4, (wall.y1 - wall.y0) / 2):.6f} {board.height / 2:.6f}" contype="0" conaffinity="0"/>'
        )
    for index in range(count):
        start = board.starts[index] if index < len(board.starts) else Start(10 + index, 10)
        parts.append(
            f'<body name="ball{index}" pos="{start.x:.6f} {start.y:.6f} {RADIUS:.6f}"><freejoint/>'
            f'<geom name="ball{index}" type="sphere" size="{RADIUS:.4f}" density="7800" '
            f'friction="{FRICTION_STATIC:.3f} {SPIN_GRIP:.4f} {crr:.6f}" condim="3" contype="1" conaffinity="1"/></body>'
        )
    parts.append("</worldbody><contact>")
    for ball in range(count):
        for wall in range(len(board.walls)):
            parts.append(
                f'<pair geom1="ball{ball}" geom2="wall{wall}" condim="3" solref="0.009 1.0" '
                f'friction="{WALL_FRICTION:.3f} {WALL_FRICTION:.3f} 0.0001 0.0001 0.0001"/>'
            )
        for other in range(ball + 1, count):
            parts.append(
                f'<pair geom1="ball{ball}" geom2="ball{other}" condim="3" solref="0.009 0.03" '
                'friction="0.05 0.05 0.0001 0.0001 0.0001"/>'
            )
    parts.append("</contact></mujoco>")
    return "".join(parts)


def _quat_rotate(q: tuple[float, float, float, float],
                 v: tuple[float, float, float]) -> tuple[float, float, float]:
    w, x, y, z = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty,
            vy + w * ty + z * tx - x * tz,
            vz + w * tz + x * ty - y * tx)


def _quat_unrotate(q: tuple[float, float, float, float],
                   v: tuple[float, float, float]) -> tuple[float, float, float]:
    return _quat_rotate((q[0], -q[1], -q[2], -q[3]), v)


class MuJoCoMarblePhysics:
    """Source-shaped held-input and MuJoCo simulation adapter."""

    def __init__(self, board: Board, mujoco: Any = None) -> None:
        if mujoco is None:
            try:
                import mujoco as mujoco_module
            except ImportError as error:
                raise RuntimeError("native Marble Maze requires the 'mujoco' Python package") from error
            mujoco = mujoco_module
        if not board.starts:
            raise ValueError("Marble Maze board has no start points")
        self.mujoco = mujoco
        self.board = board
        self.marbles: list[Marble] = []
        self.model = None
        self.data = None
        self.ball_geoms: tuple[int, ...] = ()
        self.roll = self.pitch = self.elapsed = 0.0
        self.nudge_due = 0.0
        self.cupped_this_step = self.lost_this_step = 0
        self.struck_this_step = 0.0
        self.reset()

    def reset(self) -> None:
        self.dispose_engine()
        self.marbles = [Marble(start.x, start.y) for start in self.board.starts]
        self.roll = self.pitch = self.elapsed = self.nudge_due = 0.0
        self.cupped_this_step = self.lost_this_step = 0
        self.struck_this_step = 0.0

    def dispose_engine(self) -> None:
        data, model = self.data, self.model
        # The official Python binding owns native allocations through Python
        # object lifetime; unlike the browser WASM wrapper it has no public
        # mj_deleteData/mj_deleteModel functions. Drop data before its model.
        self.data = None
        if data is not None:
            del data
        self.model = None
        if model is not None:
            del model
        self.ball_geoms = ()

    def close(self) -> None:
        self.dispose_engine()

    def tilt(self, direction: str) -> None:
        if direction == "N":
            self.pitch = max(-MAX_TILT, self.pitch - TILT_STEP)
        elif direction == "S":
            self.pitch = min(MAX_TILT, self.pitch + TILT_STEP)
        elif direction == "E":
            self.roll = min(MAX_TILT, self.roll + TILT_STEP)
        elif direction == "W":
            self.roll = max(-MAX_TILT, self.roll - TILT_STEP)
        else:
            raise ValueError(f"unknown Marble Maze tilt direction: {direction!r}")

    def level(self) -> None:
        self.roll = self.pitch = 0.0

    def advance(self, dt: float, held: Iterable[str] = ()) -> None:
        piece = min(max(float(dt) if math.isfinite(float(dt)) else 0.0, 0.0), 0.05)
        keys = tuple(sorted(set(held)))
        if keys:
            self.nudge_due += piece
            while self.nudge_due >= 1 / 60:
                self.nudge_due -= 1 / 60
                for direction in keys:
                    self.tilt(direction)
        else:
            self.nudge_due = 0.0
        left = piece
        # Match the original UI's source-time partition exactly: consume each
        # positive remainder, even when subtraction leaves a tiny final bite.
        # At the 50 ms clamp, three nominal 60 Hz bites can leave a fourth
        # floating-point remainder that still advances MuJoCo's contact state.
        while left > 0.0:
            bite = min(left, 1 / 60)
            self.step(bite)
            left -= bite

    def _ensure_engine(self) -> None:
        if self.model is not None and len(self.marbles) == len(self.ball_geoms):
            return
        self.dispose_engine()
        model = self.mujoco.MjModel.from_xml_string(build_mjcf(self.board, len(self.marbles)))
        data = self.mujoco.MjData(model)
        first_ball = 1 + len(self.board.walls)
        self.model, self.data = model, data
        self.ball_geoms = tuple(first_ball + index for index in range(len(self.marbles)))

    def step(self, dt: float) -> None:
        amount = float(dt)
        if not math.isfinite(amount) or amount <= 0:
            return
        self.cupped_this_step = self.lost_this_step = 0
        self.struck_this_step = 0.0
        self.elapsed += amount
        for _ in range(SUBSTEPS):
            self._substep(amount / SUBSTEPS)

    def _hole_under(self, marble: Marble) -> Hole | None:
        for hole in self.board.holes:
            if math.hypot(marble.x - hole.x, marble.y - hole.y) < hole.radius:
                return hole
        return None

    def _substep(self, dt: float) -> None:
        self._ensure_engine()
        model, data = self.model, self.data
        sin_r, cos_r = math.sin(self.roll), math.cos(self.roll)
        sin_p, cos_p = math.sin(self.pitch), math.cos(self.pitch)
        gx, gy = GRAVITY * sin_r, -GRAVITY * cos_r * sin_p
        gn = GRAVITY * cos_r * cos_p
        model.opt.gravity[:] = (gx, gy, -gn)
        model.opt.timestep = dt
        for index, marble in enumerate(self.marbles):
            geom = self.ball_geoms[index]
            if marble.state == "rolling":
                hole = self._hole_under(marble)
                if hole is not None:
                    marble.state, marble.over = "falling", hole
            base, vbase = index * 7, index * 6
            if marble.live:
                grounded = int(marble.state == "rolling")
                model.geom_contype[geom] = model.geom_conaffinity[geom] = grounded
                data.qpos[base:base + 7] = (marble.x, marble.y, marble.z,
                                            marble.qw, marble.qx, marble.qy, marble.qz)
                data.qvel[vbase:vbase + 6] = (
                    marble.vx, marble.vy, marble.vz,
                    *_quat_unrotate((marble.qw, marble.qx, marble.qy, marble.qz),
                                    (marble.wx, marble.wy, marble.wz)))
            else:
                model.geom_contype[geom] = model.geom_conaffinity[geom] = 0
                data.qpos[base:base + 7] = (10 + index, 10, 1, 1, 0, 0, 0)
                data.qvel[vbase:vbase + 6] = 0
        before = [(m.vx, m.vy) if m.live else None for m in self.marbles]
        self.mujoco.mj_step(model, data)
        for index, marble in enumerate(self.marbles):
            if not marble.live:
                continue
            base, vbase = index * 7, index * 6
            marble.x, marble.y, marble.z = (float(data.qpos[base + j]) for j in range(3))
            marble.qw, marble.qx, marble.qy, marble.qz = (float(data.qpos[base + j]) for j in range(3, 7))
            marble.vx, marble.vy, marble.vz = (float(data.qvel[vbase + j]) for j in range(3))
            marble.wx, marble.wy, marble.wz = _quat_rotate(
                (marble.qw, marble.qx, marble.qy, marble.qz),
                tuple(float(data.qvel[vbase + j]) for j in range(3, 6)))
        for marble in self.marbles:
            if marble.state != "falling":
                continue
            over = self._hole_under(marble)
            if over is None:
                self._over_the_lip(marble, gn)
            else:
                marble.over = over
                if marble.z <= 0.0:
                    self._swallow(marble, over)
        resting_tilt = math.hypot(gx, gy) <= ROLLING_RESISTANCE * gn
        for index, marble in enumerate(self.marbles):
            if not marble.live:
                continue
            keep = 1.0 - VISCOUS_DRAG * dt
            marble.vx *= keep
            marble.vy *= keep
            speed = math.hypot(marble.vx, marble.vy)
            if speed > SPEED_CAP:
                scale = SPEED_CAP / speed
                marble.vx *= scale
                marble.vy *= scale
                marble.wx *= scale
                marble.wy *= scale
            if marble.state == "rolling":
                if abs(marble.wz) < REST_SPEED / RADIUS:
                    marble.wz = 0.0
                if (resting_tilt and math.hypot(marble.vx, marble.vy) < REST_SPEED and
                        math.hypot(marble.wx, marble.wy) < REST_SPEED / RADIUS):
                    marble.vx = marble.vy = marble.wx = marble.wy = 0.0
            was = before[index]
            if was is not None:
                jolt = math.hypot(marble.vx - was[0] - gx * dt,
                                  marble.vy - was[1] - gy * dt)
                if jolt > 0.02:
                    self.struck_this_step = max(self.struck_this_step, min(1.0, jolt * 1.6))

    def _over_the_lip(self, marble: Marble, gn: float) -> None:
        hole = marble.over
        drop = RADIUS - marble.z
        if hole is not None and drop > 0.0:
            have = marble.vx * marble.vx + marble.vy * marble.vy
            need = 2.0 * gn * drop
            if have <= need:
                self._swallow(marble, hole)
                return
            keep = math.sqrt((have - need) / have)
            marble.vx *= keep
            marble.vy *= keep
            self.struck_this_step = max(self.struck_this_step, min(1.0, drop / RADIUS))
        marble.z, marble.vz, marble.over, marble.state = RADIUS, 0.0, None, "rolling"
        marble.wy, marble.wx = marble.vx / RADIUS, -marble.vy / RADIUS

    def _swallow(self, marble: Marble, hole: Hole) -> None:
        marble.state = "home" if hole.home else "lost"
        if hole.home:
            self.cupped_this_step += 1
        else:
            self.lost_this_step += 1

    @property
    def home(self) -> int:
        return sum(marble.state == "home" for marble in self.marbles)

    @property
    def lost(self) -> int:
        return sum(marble.state == "lost" for marble in self.marbles)

    @property
    def settled(self) -> bool:
        return not any(marble.live for marble in self.marbles)

    @property
    def won(self) -> bool:
        return all(marble.state == "home" for marble in self.marbles)

    def snapshot(self) -> tuple[tuple[float | str, ...], ...]:
        """Return complete deterministic marble state for renderer and tests."""
        return tuple((m.x, m.y, m.vx, m.vy, m.z, m.vz, m.wx, m.wy, m.wz,
                      m.qw, m.qx, m.qy, m.qz, m.state) for m in self.marbles)
