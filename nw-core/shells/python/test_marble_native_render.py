"""GL-context smoke for the visible native Marble Maze path."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REFERENCE_ROOT = Path(
    os.environ.get(
        "NEURAL_WORKSHOP_SOURCE_ROOT",
        str(Path(__file__).resolve().parents[5] / "Python Projects" / "neural-workshop-enhanced"),
    )
).resolve()
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "test"))
sys.path.insert(0, str(REFERENCE_ROOT))

import nwcore
import pyglet
from app import MarbleMazeSession
from marble_geometry import stage_rect
from marble_native_renderer import MarbleNativeRenderer
from marble_source_capture import float32_abi_tray
from neural_workshop import marblemaze as source_marblemaze
from pyglet.window import key


def _assert_same_marbles(native_marbles, source_marbles, label):
    fields = (
        "x", "y", "z", "vx", "vy", "vz", "wx", "wy", "wz",
        "qw", "qx", "qy", "qz", "state",
    )
    for native_marble, source_marble in zip(native_marbles, source_marbles):
        for field in fields:
            actual = getattr(native_marble, field)
            expected = getattr(source_marble, field)
            if field == "state":
                assert actual == expected, (
                    f"native/source {label} mismatch: {field}={actual!r} vs {expected!r}"
                )
            else:
                assert abs(actual - expected) <= 1e-8, (
                    f"native/source {label} mismatch: {field}={actual!r} vs {expected!r}"
                )


def _source_phase(session):
    phase = session.state[session.INFO_PHASE]
    if phase == 1:
        return "rolling"
    if phase == 2:
        return "won" if session.state[session.INFO_VERDICT] == 1 else "lost"
    if phase == 4:
        return "done"
    return "unknown"


def _source_outcome(session):
    return None if session.state[session.INFO_PHASE] == 1 else (
        "won" if session.state[session.INFO_VERDICT] == 1 else "lost"
    )


def main() -> int:
    rung = int(os.environ.get("NW_MARBLE_NATIVE_RUNG", "1"))
    frames = int(os.environ.get("NW_MARBLE_NATIVE_FRAMES", "12"))
    theme = os.environ.get("NW_MARBLE_NATIVE_THEME", "light")
    width = int(os.environ.get("NW_MARBLE_NATIVE_WIDTH", "912"))
    height = int(os.environ.get("NW_MARBLE_NATIVE_HEIGHT", "684"))
    expected_dpr = os.environ.get("NW_MARBLE_PAIR_EXPECT_DPR")
    resize_to_value = os.environ.get("NW_MARBLE_NATIVE_RESIZE_TO", "")
    outcome = os.environ.get("NW_MARBLE_NATIVE_OUTCOME", "rolling")
    resize_replay = None
    if not 1 <= rung <= 16 or not 1 <= frames <= 600:
        raise ValueError("native Marble render fixture requires rung 1..16 and 1..600 frames")
    if theme not in {"light", "dark"}:
        raise ValueError("native Marble render fixture theme must be light or dark")
    if outcome not in {"rolling", "won", "lost", "done"}:
        raise ValueError("native Marble render fixture outcome is invalid")
    if outcome != "rolling" and rung != 1:
        raise ValueError("native Marble terminal fixture currently requires rung 1")
    if width < 320 or height < 240:
        raise ValueError("native Marble render fixture requires a viewport of at least 320x240")
    if resize_to_value:
        try:
            resize_width, resize_height = (
                int(value) for value in resize_to_value.split("x")
            )
        except ValueError as exc:
            raise ValueError("native Marble resize target must look like 800x600") from exc
        if resize_width < 640 or resize_height < 480:
            raise ValueError("native Marble resize target must be at least 640x480")
    window = pyglet.window.Window(width=width, height=height, visible=False)
    if expected_dpr is not None and abs(window.scale - float(expected_dpr)) > 1e-9:
        window.close()
        raise RuntimeError(
            f"native capture DPR mismatch: requested {expected_dpr}, got {window.scale}"
        )
    args = types.SimpleNamespace(
        trials=1,
        adaptive=False,
        seed=17,
        black_background=theme == "dark",
        marble_start_rung=rung,
    )
    session = MarbleMazeSession(nwcore, args)
    renderer = None
    try:
        session.enable_native_physics()
        session.key(key.SPACE, key)
        assert session.state[0] == 1 and session.physics is not None
        assert session.board is not None

        if outcome == "rolling":
            session.key(key.RIGHT, key)
        start_positions = [
            (marble.x, marble.y) for marble in session.physics.marbles
        ]
        board_seed = session.state[session.INFO_BOARD_SEED]
        source_tray = float32_abi_tray(
            source_marblemaze.deal(rung, board_seed)
        )
        source_physics = source_marblemaze.Simulation(source_tray)
        first_frame_ms = session.last_ms
        if outcome == "rolling":
            source_nudge_due = 0.0
            for frame in range(frames):
                # The source-pair driver calls update(1/60) for every captured
                # frame. Keep both source and native simulation on that exact
                # timestep; wall-clock scheduling belongs to the interactive
                # app and is tested separately.
                dt = 1 / 60
                now_ms = first_frame_ms + (frame + 1) * 1000 / 60
                piece = min(dt, 0.05)
                source_nudge_due += piece
                while source_nudge_due >= 1 / 60:
                    source_nudge_due -= 1 / 60
                    source_physics.tilt(source_marblemaze.TILT_EAST)
                left = piece
                while left > 0.0:
                    bite = min(left, 1 / 60)
                    source_physics.step(bite)
                    left -= bite
                session.tick(now_ms, physics_dt=dt)
                _assert_same_marbles(
                    session.physics.marbles, source_physics.marbles,
                    f"frame {frame + 1}",
                )
            session.release(key.RIGHT, key)
            assert session.physics.roll > 0
            assert any(
                abs(marble.x - start_positions[index][0]) > 1e-8
                or abs(marble.y - start_positions[index][1]) > 1e-8
                for index, marble in enumerate(session.physics.marbles)
            ), "held east input did not move any marble"
        else:
            terminal_state = "home" if outcome in {"won", "done"} else "lost"
            for native_marble, source_marble in zip(
                session.physics.marbles, source_physics.marbles
            ):
                native_marble.state = source_marble.state = terminal_state
            source_physics.step(1 / 60)
            session.tick(first_frame_ms + 1000 / 60)
            assert session.state[session.INFO_PHASE] == 2, (
                "native terminal fixture did not enter feedback", session.state
            )
            _assert_same_marbles(
                session.physics.marbles, source_physics.marbles,
                f"{outcome} terminal",
            )
            if outcome == "done":
                session.tick(session.last_ms + 2600)
                assert session.state[session.INFO_PHASE] == 4, (
                    "native one-trial terminal fixture did not reach done", session.state
                )

        if resize_to_value:
            initial_points = [
                round(window.width / window.scale),
                round(window.height / window.scale),
            ]
            window.set_size(resize_width, resize_height)
            window.dispatch_events()
            final_points = [
                round(window.width / window.scale),
                round(window.height / window.scale),
            ]
            assert final_points == [resize_width, resize_height], (
                "native window resize did not reach its requested logical size",
                final_points,
                [resize_width, resize_height],
            )
            resize_replay = {
                "initialPoints": initial_points,
                "finalPoints": final_points,
            }

        renderer = MarbleNativeRenderer()
        renderer.set_board(session.board, session.grain_seed)
        window.switch_to()
        window.clear()
        assert renderer.draw(
            session.physics, window.width, window.height,
            black_background=session.black_background,
        )
        pyglet.gl.glFinish()
        assert len(renderer.marble_textures) == 3 and all(renderer.marble_textures)
        samples = pyglet.gl.GLint()
        pyglet.gl.glBindRenderbuffer(
            pyglet.gl.GL_RENDERBUFFER, renderer.colour_renderbuffer
        )
        pyglet.gl.glGetRenderbufferParameteriv(
            pyglet.gl.GL_RENDERBUFFER,
            pyglet.gl.GL_RENDERBUFFER_SAMPLES,
            ctypes.byref(samples),
        )
        pyglet.gl.glBindRenderbuffer(pyglet.gl.GL_RENDERBUFFER, 0)
        assert samples.value == 4, (
            f"expected source 4x MSAA target, got {samples.value}"
        )
        shadow_depth = (pyglet.gl.GLfloat * (1024 * 1024))()
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, renderer.shadow_texture)
        pyglet.gl.glGetTexImage(
            pyglet.gl.GL_TEXTURE_2D,
            0,
            pyglet.gl.GL_DEPTH_COMPONENT,
            pyglet.gl.GL_FLOAT,
            ctypes.cast(shadow_depth, ctypes.c_void_p),
        )
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, 0)
        shadow_min, shadow_max = min(shadow_depth), max(shadow_depth)
        assert shadow_min < 0.999, (
            "the 1024px shadow pass wrote no scene depth",
            shadow_min,
            shadow_max,
            pyglet.gl.glGetError(),
        )
        pixel = (pyglet.gl.GLubyte * 4)()
        pyglet.gl.glReadBuffer(pyglet.gl.GL_BACK)
        pyglet.gl.glReadPixels(
            window.width // 2,
            window.height // 2,
            1,
            1,
            pyglet.gl.GL_RGBA,
            pyglet.gl.GL_UNSIGNED_BYTE,
            ctypes.byref(pixel),
        )
        assert tuple(pixel[:3]) not in {(229, 231, 236), (230, 231, 236)}, (
            "the stage center still contains only its clear color",
            tuple(pixel),
        )
        error = pyglet.gl.glGetError()
        assert error == pyglet.gl.GL_NO_ERROR, f"OpenGL error {error:#x}"
        capture = os.environ.get("NW_MARBLE_RENDER_CAPTURE")
        if capture:
            color_buffer = pyglet.image.get_buffer_manager().get_color_buffer()
            Path(capture).parent.mkdir(parents=True, exist_ok=True)
            color_buffer.save(capture)
            metadata_path = os.environ.get("NW_MARBLE_RENDER_METADATA")
            if metadata_path:
                _write_capture_metadata(
                    Path(metadata_path),
                    Path(capture),
                    color_buffer.width,
                    color_buffer.height,
                    session,
                    renderer,
                    window,
                    resize_replay,
                )
            window.flip()
        print("PASS: native Marble Space start, held MuJoCo motion, and 3D GL render")
        return 0
    finally:
        if renderer is not None:
            renderer.close()
        session.close()
        window.close()


def _write_capture_metadata(path, image_path, width, height, session, renderer, window,
                            resize_replay):
    board = session.board
    physics = session.physics
    stage_x, stage_bottom, stage_width, stage_height = stage_rect(width, height)
    view_proj, eye = renderer._camera(
        renderer._pyglet, board, stage_width / max(1, stage_height)
    )
    viewport = {
        "x": stage_x,
        "y": height - stage_bottom - stage_height,
        "width": stage_width,
        "height": stage_height,
    }
    board_geometry = {
        "rung": board.rung,
        "cols": board.cols,
        "rows": board.rows,
        "width": board.width,
        "depth": board.depth,
        "cell": board.cell,
        "thickness": board.thickness,
        "height": board.height,
        "walls": [
            {"x0": wall.x0, "y0": wall.y0, "x1": wall.x1, "y1": wall.y1}
            for wall in board.walls
        ],
        "holes": [
            {"x": hole.x, "y": hole.y, "radius": hole.radius, "home": hole.home}
            for hole in board.holes
        ],
        "starts": [{"x": start.x, "y": start.y} for start in board.starts],
        "home": {"x": board.home_x, "y": board.home_y, "radius": board.home_radius},
    }
    material_root = Path(__file__).resolve().parents[2] / "res" / "marblemaze"
    asset_digest = hashlib.sha256()
    for name in ("marble_colour.png", "marble_rough.png", "marble_normal.png"):
        asset_digest.update(name.encode("utf-8"))
        asset_digest.update(b"\0")
        asset_digest.update(
            bytes.fromhex(
                hashlib.sha256((material_root / name).read_bytes()).hexdigest()
            )
        )
    elapsed_ms = round(physics.elapsed * 1000)
    camera = {
        "eye": [float(value) for value in eye],
        "viewProj": [float(value) for value in view_proj],
        "aspect": stage_width / stage_height,
    }
    marbles = [
        {
            name: getattr(marble, name)
            for name in (
                "x",
                "y",
                "z",
                "vx",
                "vy",
                "vz",
                "wx",
                "wy",
                "wz",
                "qw",
                "qx",
                "qy",
                "qz",
                "state",
            )
        }
        for marble in physics.marbles
    ]
    metadata = {
        "captureComplete": True,
        "boardSeed": session.state[session.INFO_BOARD_SEED],
        "boardGeometry": board_geometry,
        "grainSeed": session.grain_seed,
        "rung": board.rung,
        "trial": max(0, session.state[session.INFO_TRIAL] - 1),
        "elapsedMs": elapsed_ms,
        "secondsPerTray": round(board.seconds),
        "statusText": session.describe(None),
        "roll": physics.roll,
        "pitch": physics.pitch,
        "camera": camera,
        "viewport": viewport,
        "sourceWindow": {
            "points": [
                window.width // max(1, round(window.scale)),
                window.height // max(1, round(window.scale)),
            ],
            "layoutPixels": [width, height],
            "framebuffer": [width, height],
            "scale": float(window.scale),
        },
        "dpr": float(window.scale),
        "resizeReplay": resize_replay,
        "theme": os.environ.get("NW_MARBLE_NATIVE_THEME", "light"),
        "inputReplay": ({
            "held": ["E"],
            "heldFrames": int(os.environ.get("NW_MARBLE_NATIVE_FRAMES", "12")),
            "releaseFrames": 0,
            "restarted": False,
            "postRestartFrames": 0,
        } if os.environ.get("NW_MARBLE_NATIVE_OUTCOME", "rolling") == "rolling" else None),
        "assetHash": asset_digest.hexdigest(),
        "materialState": "settled:3-of-3",
        "sceneState": {
            "version": 1,
            "phase": _source_phase(session),
            "outcome": _source_outcome(session),
            "elapsedMs": elapsed_ms,
            "roll": physics.roll,
            "pitch": physics.pitch,
            "marbles": marbles,
        },
        "image": {
            "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "dimensions": [width, height],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
