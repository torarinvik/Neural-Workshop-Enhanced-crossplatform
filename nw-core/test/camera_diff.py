"""Compare Camera worlds, pose math, and movement against Python."""
import ast
import math
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from typing import Sequence, Tuple

from gunslinger_diff import check

SOURCE = Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"
sys.path.insert(0, str(SOURCE))
from neural_workshop import camera


def compare_scene(rows, scene, case):
    check(rows, "pose", scene.target, case)
    check(rows, "pose", scene.start, case)
    things = scene.things
    level = scene.level
    assert not camera.matches(scene.start, scene.target, level)
    anchors = camera.anchors(scene.target, things, level.field)
    assert anchors >= level.anchors
    check(rows, "things", (len(things), anchors), case)
    for index, thing in enumerate(things):
        shape = camera.SHAPES.index(thing.shape)
        colour = 12 if thing.occluder else camera.PALETTE.index(thing.colour)
        depth = camera.in_frame(scene.target, (thing.x, thing.size / 2, thing.z)) or 0.0
        check(rows, "thing", (shape, colour, int(thing.occluder), thing.x, thing.z,
                             thing.size, thing.spin, depth), (*case, index))
    pose = scene.start
    for step in range(50):
        move = camera.MOVES[step % len(camera.MOVES)]
        amount = 120.0 if step >= 40 else 1.0 / (step % 4 + 1)
        pose = camera.moved(pose, move, amount, level)
        check(rows, "pose", pose, (*case, step))
        check(rows, "error", (camera.distance(pose, scene.target), camera.angle(pose, scene.target),
                             camera.closeness(pose, scene.target, level),
                             int(camera.matches(pose, scene.target, level))), (*case, step))
    return len(things)


def compare_session(rows):
    rng = Random(17)
    first = camera.deal(8, rng=rng)
    level = first.level
    pose = first.start
    check(rows, "pose", pose, "first trial")
    for index, move in enumerate(camera.MOVES):
        size = (camera.STEP_DEGREES if 4 <= index <= 7 else
                camera.STEP_RISE if index >= 8 else camera.STEP_METRES)
        tolerance = level.aim if 4 <= index <= 7 else level.reach
        for amount in (1.0, 0.125, min(1 / 64, 0.5 * tolerance / size)):
            pose = camera.moved(pose, move, amount, level)
            check(rows, "pose", pose, (move, amount))
    pose = camera.moved(pose, "forward", 3.2 * 0.1 * 0.12, level)
    check(rows, "pose", pose, "slow held movement")
    pose = camera.moved(pose, "turn_left", -24 * 0.22 / 15, level)
    pose = camera.moved(pose, "look_up", -12 * 0.22 / 15, level)
    check(rows, "pose", pose, "pointer drag")
    check(rows, "result", (8, 0, camera.distance(pose, first.target),
                           camera.angle(pose, first.target), 0.5), "miss")
    second = camera.deal(7, rng=rng)
    check(rows, "pose", second.start, "second trial")
    check(rows, "result", (7, 1, 0.0, camera.angle(second.target, second.target), 2.75 - 2.31),
          "match")
    third = camera.deal(8, rng=rng)
    check(rows, "pose", third.start, "third trial")
    check(rows, "result", (8, 0, camera.distance(third.start, third.target),
                           camera.angle(third.start, third.target), 3.5 - 2.81), "last miss")
    check(rows, "mean", ((0.5 + (2.75 - 2.31) + (3.5 - 2.81)) / 3,), "summary")


def compare_meshes(rows):
    # Use the Python mesh builders without starting a window or compiling GL shaders.
    ui = SOURCE / "neural_workshop" / "ui"
    builder_source = ast.parse((ui / "render3d.py").read_text())
    builder = next(node for node in builder_source.body
                   if isinstance(node, ast.ClassDef) and node.name == "Builder")
    methods = {"__init__", "_base", "face", "box", "quad_xz"}
    builder.body = [node for node in builder.body if getattr(node, "name", "") in methods]
    namespace = {"math": math, "Sequence": Sequence, "Tuple": Tuple}
    exec(compile(ast.Module(body=[builder], type_ignores=[]), str(ui / "render3d.py"), "exec"),
         namespace)
    namespace["render3d"] = SimpleNamespace(Builder=namespace["Builder"])
    mesh_source = ast.parse((ui / "camera.py").read_text())
    methods = {"_tri", "_lathe", "_ring", "shape_builder"}
    functions = [node for node in mesh_source.body if getattr(node, "name", "") in methods]
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(ui / "camera.py"), "exec"),
         namespace)
    vertices = 0
    for kind, shape in enumerate((*camera.SHAPES, "field", "outside")):
        if kind < len(camera.SHAPES):
            mesh = namespace["shape_builder"](shape)
        else:
            mesh = namespace["Builder"]()
            half = 18.5 if shape == "field" else 18.5 * 6 + 60
            mesh.quad_xz(-half, -half, half, half, 0.0 if shape == "field" else -0.01)
        count = len(mesh.positions) // 3
        vertices += count
        check(rows, "mesh", (kind, count, len(mesh.indices)), shape)
        for i in range(0, count * 3, 3):
            check(rows, "vertex", (*mesh.positions[i:i + 3], *mesh.normals[i:i + 3]), shape)
        for index in mesh.indices:
            check(rows, "index", (index,), shape)
    for colour in (*camera.PALETTE, (0.62, 0.60, 0.56)):
        check(rows, "colour", colour, "scene palette")
    for scale in ((2.5, 2.5, 2.5), (2.5 * 1.6, 2.5, 2.5 * 0.9)):
        check(rows, "transform", (-7.0, 0.0, 12.0, *scale,
                                  math.cos(math.radians(72)), math.sin(math.radians(72))), scale)
    return vertices


def compare_views(rows):
    from pyglet.math import Mat4, Vec3

    path = SOURCE / "neural_workshop" / "ui" / "camera.py"
    module = ast.parse(path.read_text())
    task = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "CameraTask")
    task.body = [node for node in task.body if getattr(node, "name", "") in {"_view_rect", "_photo_rect"}]
    view_proj = next(node for node in module.body if getattr(node, "name", "") == "view_proj")
    size = [0, 0]
    namespace = {
        "Mat4": Mat4, "Vec3": Vec3, "world": camera, "Tuple": Tuple,
        "pixel_size": lambda: size,
        "from_top_edge": lambda edge: int(size[1] - edge * size[1] / 684),
        "from_bottom_edge": lambda edge: int(edge * (size[1] / 684)),
        "above_the_band": lambda y: max(y, size[1] - int(size[1] * 0.75) + 8),
    }
    exec(compile(ast.Module(body=[view_proj, task], type_ignores=[]), str(path), "exec"), namespace)
    task = namespace["CameraTask"]()
    pose = camera.Pose(2.0, 3.0, -7.0, 37.0, 28.0)
    for width, height in ((912, 684), (480, 720), (1736, 960)):
        size[:] = width, height
        live = task._view_rect()
        check(rows, "rect", (*live, *task._photo_rect()), tuple(size))
        check(rows, "matrix", tuple(namespace["view_proj"](pose, int(live[2]) / int(live[3]), 18.5)),
              tuple(size))
    span = 18.5 * 1.25 + 4
    eye = Vec3(*(v * span * 2.2 for v in (-0.42, 0.80, 0.30)))
    clip = Mat4.orthogonal_projection(-span, span, -span, span, 0.01, span * 5) @ Mat4.look_at(
        eye, Vec3(0.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0))
    half = Vec3(0.5, 0.5, 0.5)
    check(rows, "matrix", tuple(clip), "light clip space")
    check(rows, "matrix", tuple(Mat4.from_translation(half) @ Mat4.from_scale(half) @ clip),
          "shadow texture space")
    for scale in ((2.5, 2.5, 2.5), (2.5 * 1.6, 2.5, 2.5 * 0.9)):
        model = (Mat4.from_translation(Vec3(-7.0, 0.0, 12.0)) @
                 Mat4.from_rotation(math.radians(72), Vec3(0.0, 1.0, 0.0)) @
                 Mat4.from_scale(Vec3(*scale)))
        check(rows, "matrix", tuple(model), "object model")
        check(rows, "normal", tuple(1 / (s * s) for s in scale), "object normals")
    check(rows, "ground", (7, 6, 0, 0), "field and outside")



def main(binary):
    rows = iter(subprocess.check_output([binary], text=True, timeout=120).splitlines())
    compare_session(rows)
    vertices = compare_meshes(rows)
    compare_views(rows)
    worlds = objects = 0
    for rung in (-1, 1, 3, 4, 5, 6, 8, 12, 20, 27, 40, 75, 1000):
        level = camera.grade(rung)
        for seed in range(-1, 4):
            case = rung, seed
            rng = Random(seed)
            try:
                scene = camera.deal(rung, rng=rng)
            except camera.Unbuildable:
                scene = None
            check(rows, "case", (*case, int(scene is not None)), case)
            check(rows, "grade", (level.rung, level.objects, level.kinds, level.occluders,
                                  level.anchors, int(level.meter), level.reach, level.aim, level.field,
                                  level.lift, level.tilt, level.start, level.turn), case)
            if scene is not None:
                objects += compare_scene(rows, scene, case)
                worlds += 1
            check(rows, "rng", (rng.getrandbits(32),), case)
    assert next(rows, None) is None
    print(f"PASS: {worlds} Camera worlds, {objects} objects, and {worlds * 50} movement and judgement states, and adaptive session. {vertices} scene vertices matched")


if __name__ == "__main__":
    main(sys.argv[1])
