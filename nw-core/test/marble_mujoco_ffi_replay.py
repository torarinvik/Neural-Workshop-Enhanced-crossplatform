"""Compare a native Elisa Marble replay with Python on the exact same board."""
import math
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shells" / "python"))
from marble_mujoco import MuJoCoMarblePhysics, _quat_unrotate, decode_board
from marble_geometry import build_scene, stage_rect
from marble_native_renderer import ASSET_DIR, MarbleNativeRenderer
from pyglet.math import Mat4, Vec3

if sys.argv[2:] == ["--pixels-only"]:
    import pyglet
    from pyglet import gl

    cases = ((3, 42, 0, 0, 0), (1, 17, 1, 0, 0), (16, 42, 1, 8, 0),
             (3, 42, 0, 0, 1), (3, 42, 1, 0, 2))
    captures = [(*case, 320, 240) for case in cases]
    captures.append((16, 42, 1, 8, 0, 641, 397))
    for rung, seed, dark, ticks, outcome, width, height in captures:
        print(f"Marble rung {rung}, seed {seed}, dark {dark}, tilt ticks {ticks}, outcome {outcome}, {width}x{height}")
        payload = subprocess.check_output([sys.argv[1], "pixels", *map(str, (rung, seed, dark, ticks, outcome, width, height))])
        board_size, = struct.unpack_from("=q", payload)
        board = decode_board(payload[8:8 + board_size])
        view = struct.unpack_from("=587d", payload, 8 + board_size)
        grain = view[1]
        x, bottom, stage_width, stage_height = stage_rect(width, height)
        assert view[4:8] == (x, bottom, stage_width, stage_height), (width, height, view[4:8])
        stage_start = 8 + board_size + 587 * 8
        stage_end = stage_start + stage_width * stage_height * 4
        resolved = payload[stage_start:stage_end]
        native_hole = struct.unpack_from("=5f", payload, stage_end)
        shadow_start = stage_end + 20
        shadow_end = shadow_start + 1024 * 1024 * 4
        native_shadow = memoryview(payload)[shadow_start:shadow_end].cast("f")
        native = payload[shadow_end:]
        top = height - bottom - stage_height
        assert len(native) == width * height * 4
        window = pyglet.window.Window(width=width, height=height, visible=False)
        renderer = MarbleNativeRenderer()
        physics = MuJoCoMarblePhysics(board)
        try:
            renderer.set_board(board, grain)
            for _ in range(ticks):
                physics.advance(0.020, ("E",))
            if outcome:
                pit = board.holes[0]
                assert not pit.home
                marble = physics.marbles[0]
                marble.x, marble.y, marble.z = pit.x, pit.y, 0.000001
                physics.advance(0.010)
                assert physics.settled and physics.lost == 1
            frame = renderer._board_frame(pyglet, physics.roll, physics.pitch)
            clip, shadow_texture = renderer._light_matrices(board)
            camera, eye = renderer._camera(pyglet, board, stage_width / stage_height)
            for offset, expected in ((8, camera), (24, frame), (40, clip), (56, shadow_texture), (584, eye)):
                assert all(math.isclose(a, b, abs_tol=1e-12)
                           for a, b in zip(view[offset:], expected)), offset
            live = [marble for marble in physics.marbles if marble.live]
            assert view[3] == len(live)
            for index, marble in enumerate(live):
                model = renderer._marble_model(pyglet, marble, board, frame)
                assert all(math.isclose(a, b, abs_tol=1e-12)
                           for a, b in zip(view[456 + index * 16:], model)), index
            assert renderer.draw(physics, width, height, bool(dark))
            reference_hole = (gl.GLfloat * 5)()
            program = renderer.shadow_program.id
            gl.glGetUniformfv(program, gl.glGetUniformLocation(program, b"holes[0]"), reference_hole)
            count = gl.GLfloat()
            gl.glGetUniformfv(program, gl.glGetUniformLocation(program, b"hole_count"), count)
            reference_hole[4] = count.value
            assert view[72:72 + int(view[2]) * 4] == tuple(value for hole in renderer.geometry.holes for value in hole)
            assert native_hole == tuple(reference_hole), (native_hole, tuple(reference_hole))
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, renderer.shadow_framebuffer)
            shadow = (gl.GLfloat * (1024 * 1024))()
            gl.glReadPixels(0, 0, 1024, 1024, gl.GL_DEPTH_COMPONENT, gl.GL_FLOAT, shadow)
            shadow_changed = sum(abs(a - b) > 1e-6 for a, b in zip(native_shadow, shadow))
            native_covered = sum(depth < 1 for depth in native_shadow)
            python_covered = sum(depth < 1 for depth in shadow)
            print(f"Marble shadow depth differs at {shadow_changed} of {len(shadow)} pixels "
                  f"(covered: Elisa {native_covered}, Python {python_covered})")
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, renderer.resolve_framebuffer)
            source = (gl.GLubyte * (stage_width * stage_height * 4))()
            gl.glReadPixels(0, 0, stage_width, stage_height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, source)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            assert gl.glGetError() == gl.GL_NO_ERROR
            rgb_error = 0
            first_difference = None
            transfer_max = 0
            background = (14, 14, 17) if dark else (230, 231, 236)
            native_background = python_background = coverage_diff = 0
            for y in range(stage_height):
                for col in range(stage_width):
                    a = ((top + y) * width + x + col) * 4
                    b = ((stage_height - 1 - y) * stage_width + col) * 4
                    stage_pixel = (y * stage_width + col) * 4
                    transfer_max = max(transfer_max, *(abs(native[a + c] - resolved[stage_pixel + c]) for c in range(3)))
                    actual_rgb = tuple(resolved[stage_pixel:stage_pixel + 3])
                    expected_rgb = tuple(source[b:b + 3])
                    if actual_rgb != expected_rgb:
                        rgb_error += sum(abs(a - b) for a, b in zip(actual_rgb, expected_rgb))
                        if first_difference is None:
                            first_difference = (col, y, actual_rgb, expected_rgb)
                    native_clear = all(abs(resolved[stage_pixel + c] - background[c]) <= 1 for c in range(3))
                    python_clear = all(abs(source[b + c] - background[c]) <= 1 for c in range(3))
                    native_background += native_clear
                    python_background += python_clear
                    coverage_diff += native_clear != python_clear
            print(f"Marble SDL transfer maximum RGB difference: {transfer_max}")
            mean = rgb_error / (stage_width * stage_height * 3)
            assert transfer_max == 0
            assert shadow_changed == 0
            assert rgb_error == 0, (width, height, mean, first_difference)
            total = stage_width * stage_height
            print(f"Marble stage RGB mean absolute error {mean:.4f}/255")
            print(f"Background pixels out of {total}: Elisa {native_background}, "
                  f"Python {python_background}, disagreement {coverage_diff}")
        finally:
            physics.close()
            renderer.close()
            window.close()
    raise SystemExit(0)

for index, filename in enumerate(("scene.vert", "scene.frag", "shadow.vert", "shadow.frag",
                                  "composite.vert", "composite.frag")):
    source = subprocess.check_output([sys.argv[1], "shader", str(index)], cwd="/")
    assert source == (ASSET_DIR / filename).read_bytes(), filename
invalid = subprocess.run([sys.argv[1], "shader", "6"], capture_output=True)
assert invalid.returncode == 3 and not invalid.stdout
print("Marble SDL shader assets match Python from a different working directory")


stage = stage_rect(913, 685)
board = SimpleNamespace(width=0.33, depth=0.28)
marble = SimpleNamespace(x=0.043 + board.width / 2, y=board.depth / 2 + 0.052,
                         z=0.0075, qw=0.8, qx=0.36, qy=0.48, qz=0.0)
frame = MarbleNativeRenderer._board_frame(None, 0.11, -0.07)
camera, _ = MarbleNativeRenderer._camera(None, board, stage[2] / stage[3])
model = MarbleNativeRenderer._marble_model(None, marble, board, frame)
light_clip, light_texture = MarbleNativeRenderer._light_matrices(
    SimpleNamespace(_mat4=Mat4, _vec3=Vec3), board)
actual_view = struct.unpack("=84d", subprocess.check_output([sys.argv[1], "view"]))
assert actual_view[:4] == stage
for index, (native, oracle) in enumerate(zip(actual_view[4:], (*frame, *camera, *model, *light_clip, *light_texture))):
    assert math.isclose(native, oracle, abs_tol=1e-13), (index, native, oracle)
print("Marble viewport, camera, tray tilt, marble model, and shadow matrices match")


for rung, seed in ((1, 42), (8, 17), (16, 42)):
    payload = subprocess.check_output([sys.argv[1], str(rung), str(seed)])
    board_length, = struct.unpack_from("=q", payload)
    board = decode_board(payload[8:8 + board_length])
    scene = build_scene(board)
    hole_bytes = subprocess.check_output([sys.argv[1], str(rung), str(seed), "7"])
    assert tuple(struct.iter_unpack("=4d", hole_bytes)) == scene.holes, (rung, "shader holes")
    for part, name in enumerate(("body", "frame", "walls", "pits", "cups", "collar", "ball")):
        mesh = scene.meshes[name]
        mesh_bytes = subprocess.check_output([sys.argv[1], str(rung), str(seed), str(part)])
        coords, indices = map(int, struct.unpack_from("=2d", mesh_bytes))
        assert coords == len(mesh.positions) == len(mesh.normals), (rung, name)
        assert indices == len(mesh.indices), (rung, name)
        values = struct.unpack_from(f"={2 * coords + indices}d", mesh_bytes, 16)
        assert values[2 * coords:] == mesh.indices, (rung, name)
        for native, oracle in zip(values[:2 * coords], mesh.positions + mesh.normals):
            assert math.isclose(native, oracle, abs_tol=1e-13), (rung, name, native, oracle)
    stride = 6 + 14 * len(board.starts)
    rows = list(struct.iter_unpack("=" + "d" * stride, payload[8 + board_length:]))
    assert len(rows) == 240
    physics = MuJoCoMarblePhysics(board)
    try:
        for tick, actual in enumerate(rows):
            if tick % 60 == 45:
                physics.level()
            held = ("NESW"[tick // 60],) if tick % 60 < 45 else ()
            elapsed = 0.05 if tick % 17 == 0 else (0.010 if tick % 2 == 0 else 0.023)
            physics.advance(elapsed, held)
            expected = [
                physics.roll, physics.pitch, physics.cupped_this_step,
                physics.lost_this_step, physics.struck_this_step, physics.elapsed,
            ]
            for m in physics.marbles:
                expected.extend((m.x, m.y, m.z, m.qw, m.qx, m.qy, m.qz))
            for m in physics.marbles:
                expected.extend((m.vx, m.vy, m.vz, *_quat_unrotate(
                    (m.qw, m.qx, m.qy, m.qz), (m.wx, m.wy, m.wz))))
            expected.extend(("rolling", "falling", "home", "lost").index(m.state)
                            for m in physics.marbles)
            for field, (native, oracle) in enumerate(zip(actual, expected)):
                assert math.isclose(native, oracle, abs_tol=1e-8, rel_tol=1e-8), (
                    rung, seed, tick, field, native, oracle)
    finally:
        physics.close()
    print(f"Marble rung {rung}, seed {seed}: seven meshes and 240 trajectory samples match")

# Use the installed Python extension as the oracle when available.
try:
    import nwcore
except ImportError:
    nwcore = None

if nwcore is not None:
    for phase in (0, 1, 2, 4):
        handle = nwcore.marble_create(3, 1, 0, 2600, 0, 42)
        assert handle > 0
        try:
            if phase > 0:
                assert nwcore.marble_action(handle, 0, 0, 0) == 1
            if phase >= 2:
                assert nwcore.marble_action(handle, 3, 0, 1000) == 1
                assert nwcore.marble_action(handle, 12, 0, 1) == 1
            if phase == 4:
                assert nwcore.marble_action(handle, 5, 0, 0) == 1
            assert nwcore.marble_info(handle, 0) == phase
            for dark in (0, 1):
                native = subprocess.check_output([sys.argv[1], "chrome", str(phase), str(dark)])
                assert native == nwcore.marble_frame(handle, dark, 913, 685), (phase, dark)
        finally:
            nwcore.marble_destroy(handle)
    print("Marble desktop display lists match Python in four phases and both themes")
