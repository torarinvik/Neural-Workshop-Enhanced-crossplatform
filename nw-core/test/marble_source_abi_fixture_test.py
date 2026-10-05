#!/usr/bin/env python3
"""Keep the opt-in source replay's WASM Float32 geometry conversion exact."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import random
from types import SimpleNamespace
from typing import NamedTuple


CAPTURE = Path(__file__).with_name("marble_source_capture.py")
SPEC = importlib.util.spec_from_file_location("marble_source_capture", CAPTURE)
assert SPEC is not None and SPEC.loader is not None
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


class Wall(NamedTuple):
    x0: float
    y0: float
    x1: float
    y1: float


class Hole(NamedTuple):
    x: float
    y: float
    radius: float
    home: bool


class Tray(NamedTuple):
    rung: int
    cols: int
    rows: int
    width: float
    depth: float
    cell: float
    thickness: float
    height: float
    walls: tuple[Wall, ...]
    holes: tuple[Hole, ...]
    starts: tuple[tuple[float, float], ...]
    home: tuple[float, float, float]
    seconds: float
    field: str
    route: float


def f32(value: float) -> float:
    return struct.unpack("=f", struct.pack("=f", value))[0]


original = Tray(
    16, 12, 10, 0.40238201618194583, 0.336651687, 0.032865171,
    0.0036151686, 0.009859551,
    (Wall(0.0021924158, 0.0021924158, 0.4001896083, 0.0058075842),),
    (Hole(0.1518932581, 0.1190280914, 0.0122849997, True),),
    ((0.388500005, 0.256500006),),
    (0.1518932581, 0.1190280914, 0.0122849997),
    140.0, "unchanged-field", 0.5,
)
result = capture.float32_abi_tray(original)

for name in ("width", "depth", "cell", "thickness", "height"):
    assert getattr(result, name) == f32(getattr(original, name)), name
for name in ("rung", "cols", "rows", "seconds", "field", "route"):
    assert getattr(result, name) == getattr(original, name), name
assert result.walls == tuple(Wall(*(f32(value) for value in wall))
                             for wall in original.walls)
assert result.holes == tuple(Hole(f32(hole.x), f32(hole.y), f32(hole.radius),
                                  hole.home) for hole in original.holes)
assert result.starts == tuple(tuple(f32(value) for value in start)
                              for start in original.starts)
assert result.home == tuple(f32(value) for value in original.home)
assert original.width == 0.40238201618194583, "conversion must not mutate source Tray"
assert result.width != original.width, "fixture must exercise a real rounding boundary"
task = SimpleNamespace(tray=original, sim=None,
                       stage=SimpleNamespace(grain_seed=1.158501511057862),
                       rng=random.Random(17))
initial_rng_state = task.rng.getstate()
rebuilt = []
def build_scene():
    rebuilt.append(task.tray)
    task.stage.grain_seed = -1  # scene construction must not replace identity
    task.rng.random()
task._build_scene = build_scene
capture.rebuild_float32_capture_board(task, lambda tray: SimpleNamespace(tray=tray))
assert task.tray == result and task.sim.tray == result
assert rebuilt == [result], "scene and simulation must use the same rounded board"
assert task.stage.grain_seed == 1.158501511057862
assert task.rng.getstate() == initial_rng_state
def failing_scene():
    task.rng.random()
    task.stage.grain_seed = -2
    raise RuntimeError("fixture scene failure")
task._build_scene = failing_scene
try:
    capture.rebuild_float32_capture_board(task, lambda tray: SimpleNamespace(tray=tray))
except RuntimeError as error:
    assert str(error) == "fixture scene failure"
else:
    raise AssertionError("capture must not hide scene construction failure")
assert task.rng.getstate() == initial_rng_state
assert task.stage.grain_seed == 1.158501511057862
assert original.width == 0.40238201618194583
assert capture.parse_move_stages(["E+W:12", "E:20", "none:1", "W:40"]) == [
    {"held": ["E", "W"], "frames": 12},
    {"held": ["E"], "frames": 20},
    {"held": [], "frames": 1},
    {"held": ["W"], "frames": 40},
], "staged source replay must retain key overlap, release, and reverse order"
for invalid_schedule in (["E+E:2"], ["Q:2"], ["E:0"], ["E:601"], ["E:400", "W:201"]):
    try:
        capture.parse_move_stages(invalid_schedule)
    except SystemExit:
        pass
    else:
        raise AssertionError(f"invalid staged replay was accepted: {invalid_schedule}")
print("PASS: source replay Float32 ABI conversion and bounded staged input schedule")
