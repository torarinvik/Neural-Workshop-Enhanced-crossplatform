"""Pyglet/OpenGL 3D Marble Maze stage for the native Python shell.

Geometry, camera, board coordinates, material identifiers, and tray transforms
follow the original ``ui/marblemaze.py`` and the browser renderer.  The native
shader currently uses procedural wood/chrome rather than the source's shadow
map and optional baked marble textures; those remain explicit parity work.
"""

from __future__ import annotations

import ctypes
import math
from pathlib import Path
from typing import Any

from marble_geometry import SceneGeometry, build_scene, stage_rect

ASSET_DIR = Path(__file__).resolve().parents[2] / "res" / "marblemaze"
SHADOW_SIZE = 1024
MSAA_SAMPLES = 4


class MarbleNativeRenderer:
    """Render source-sized 3D geometry into the original Marble stage box."""

    def __init__(self) -> None:
        import pyglet
        from pyglet import gl
        from pyglet.graphics.shader import Shader, ShaderProgram
        from pyglet.math import Mat4, Vec3

        self.gl = gl
        self.program = ShaderProgram(
            Shader((ASSET_DIR / "scene.vert").read_text(encoding="utf-8"), "vertex"),
            Shader((ASSET_DIR / "scene.frag").read_text(encoding="utf-8"), "fragment"),
        )
        self.shadow_program = ShaderProgram(
            Shader((ASSET_DIR / "shadow.vert").read_text(encoding="utf-8"), "vertex"),
            Shader((ASSET_DIR / "shadow.frag").read_text(encoding="utf-8"), "fragment"),
        )
        self.composite_program = ShaderProgram(
            Shader((ASSET_DIR / "composite.vert").read_text(encoding="utf-8"), "vertex"),
            Shader((ASSET_DIR / "composite.frag").read_text(encoding="utf-8"), "fragment"),
        )
        self.composite_vao = gl.GLuint()
        gl.glGenVertexArrays(1, ctypes.byref(self.composite_vao))
        self.colour_framebuffer = gl.GLuint()
        self.colour_renderbuffer = gl.GLuint()
        self.depth_renderbuffer = gl.GLuint()
        self.resolve_framebuffer = gl.GLuint()
        self.resolve_texture = gl.GLuint()
        self.target_size = (0, 0)
        self._create_shadow_target()
        self._mat4 = Mat4
        self._vec3 = Vec3
        self.geometry: SceneGeometry | None = None
        self.board = None
        self.vertex_lists: dict[str, Any] = {}
        self.shadow_vertex_lists: dict[str, Any] = {}
        self.grain_seed = 0.0
        self._pyglet = pyglet
        self.marble_texture_images = []
        self.marble_textures = self._load_marble_textures()

    def _delete_colour_target(self) -> None:
        gl = self.gl
        if self.colour_framebuffer.value:
            gl.glDeleteFramebuffers(1, ctypes.byref(self.colour_framebuffer))
            self.colour_framebuffer.value = 0
        if self.resolve_framebuffer.value:
            gl.glDeleteFramebuffers(1, ctypes.byref(self.resolve_framebuffer))
            self.resolve_framebuffer.value = 0
        if self.colour_renderbuffer.value:
            gl.glDeleteRenderbuffers(1, ctypes.byref(self.colour_renderbuffer))
            self.colour_renderbuffer.value = 0
        if self.depth_renderbuffer.value:
            gl.glDeleteRenderbuffers(1, ctypes.byref(self.depth_renderbuffer))
            self.depth_renderbuffer.value = 0
        if self.resolve_texture.value:
            gl.glDeleteTextures(1, ctypes.byref(self.resolve_texture))
            self.resolve_texture.value = 0
        self.target_size = (0, 0)

    def _ensure_colour_target(self, width: int, height: int) -> None:
        if self.target_size == (width, height):
            return
        self._delete_colour_target()
        gl = self.gl
        gl.glGenFramebuffers(1, ctypes.byref(self.colour_framebuffer))
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.colour_framebuffer)
        gl.glGenRenderbuffers(1, ctypes.byref(self.colour_renderbuffer))
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.colour_renderbuffer)
        gl.glRenderbufferStorageMultisample(
            gl.GL_RENDERBUFFER, MSAA_SAMPLES, gl.GL_RGBA8, width, height
        )
        gl.glFramebufferRenderbuffer(
            gl.GL_FRAMEBUFFER,
            gl.GL_COLOR_ATTACHMENT0,
            gl.GL_RENDERBUFFER,
            self.colour_renderbuffer,
        )
        gl.glGenRenderbuffers(1, ctypes.byref(self.depth_renderbuffer))
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.depth_renderbuffer)
        gl.glRenderbufferStorageMultisample(
            gl.GL_RENDERBUFFER, MSAA_SAMPLES, gl.GL_DEPTH_COMPONENT24, width, height
        )
        gl.glFramebufferRenderbuffer(
            gl.GL_FRAMEBUFFER,
            gl.GL_DEPTH_ATTACHMENT,
            gl.GL_RENDERBUFFER,
            self.depth_renderbuffer,
        )
        colour_status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)

        gl.glGenFramebuffers(1, ctypes.byref(self.resolve_framebuffer))
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.resolve_framebuffer)
        gl.glGenTextures(1, ctypes.byref(self.resolve_texture))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.resolve_texture)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA8,
            width,
            height,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            None,
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER,
            gl.GL_COLOR_ATTACHMENT0,
            gl.GL_TEXTURE_2D,
            self.resolve_texture,
            0,
        )
        resolve_status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        if (
            colour_status != gl.GL_FRAMEBUFFER_COMPLETE
            or resolve_status != gl.GL_FRAMEBUFFER_COMPLETE
        ):
            self._delete_colour_target()
            raise RuntimeError(
                "Marble multisample framebuffer incomplete: "
                f"colour={colour_status:#x}, resolve={resolve_status:#x}"
            )
        self.target_size = (width, height)

    def _load_marble_textures(self) -> list[int]:
        gl = self.gl
        texture_ids: list[int] = []
        for filename in ("marble_colour.png", "marble_rough.png", "marble_normal.png"):
            image = self._pyglet.image.load(str(ASSET_DIR / filename))
            texture = image.get_texture()
            texture_ids.append(texture.id)
            self.marble_texture_images.append(image)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
            gl.glTexParameteri(
                gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE
            )
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        return texture_ids

    def _create_shadow_target(self) -> None:
        gl = self.gl
        self.shadow_texture = gl.GLuint()
        self.shadow_framebuffer = gl.GLuint()
        gl.glGenTextures(1, ctypes.byref(self.shadow_texture))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.shadow_texture)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_DEPTH_COMPONENT24,
            SHADOW_SIZE,
            SHADOW_SIZE,
            0,
            gl.GL_DEPTH_COMPONENT,
            gl.GL_UNSIGNED_INT,
            None,
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glGenFramebuffers(1, ctypes.byref(self.shadow_framebuffer))
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.shadow_framebuffer)
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER,
            gl.GL_DEPTH_ATTACHMENT,
            gl.GL_TEXTURE_2D,
            self.shadow_texture,
            0,
        )
        gl.glDrawBuffer(gl.GL_NONE)
        gl.glReadBuffer(gl.GL_NONE)
        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            self._delete_shadow_target()
            raise RuntimeError(f"Marble shadow framebuffer incomplete: {status:#x}")

    def _delete_shadow_target(self) -> None:
        gl = self.gl
        texture = getattr(self, "shadow_texture", None)
        framebuffer = getattr(self, "shadow_framebuffer", None)
        if texture is not None and texture.value:
            gl.glDeleteTextures(1, ctypes.byref(texture))
            texture.value = 0
        if framebuffer is not None and framebuffer.value:
            gl.glDeleteFramebuffers(1, ctypes.byref(framebuffer))
            framebuffer.value = 0

    def _light_matrices(self, board):
        direction = (-0.38, 0.86, 0.34)
        span = max(board.width, board.depth) * 0.78
        eye = self._vec3(*(component * span * 2.2 for component in direction))
        up = (
            self._vec3(0.0, 0.0, 1.0)
            if abs(direction[1]) > 0.98
            else self._vec3(0.0, 1.0, 0.0)
        )
        view = self._mat4.look_at(eye, self._vec3(0.0, 0.0, 0.0), up)
        projection = self._mat4.orthogonal_projection(
            -span, span, -span, span, 0.01, span * 5.0
        )
        clip = projection @ view
        bias = self._mat4.from_translation(
            self._vec3(0.5, 0.5, 0.5)
        ) @ self._mat4.from_scale(self._vec3(0.5, 0.5, 0.5))
        return clip, bias @ clip

    def set_board(self, board, grain_seed: float) -> None:
        if self.board == board:
            self.grain_seed = float(grain_seed)
            return
        self._delete_meshes()
        self.board = board
        self.geometry = build_scene(board)
        for name, mesh in self.geometry.meshes.items():
            if not mesh.indices:
                continue
            self.vertex_lists[name] = self.program.vertex_list_indexed(
                len(mesh.positions) // 3,
                self.gl.GL_TRIANGLES,
                mesh.indices,
                position=("f", mesh.positions),
                normal=("f", mesh.normals),
            )
            self.shadow_vertex_lists[name] = self.shadow_program.vertex_list_indexed(
                len(mesh.positions) // 3,
                self.gl.GL_TRIANGLES,
                mesh.indices,
                position=("f", mesh.positions),
            )
        self.grain_seed = float(grain_seed)

    def _delete_meshes(self) -> None:
        for vertex_list in (
            *self.vertex_lists.values(),
            *self.shadow_vertex_lists.values(),
        ):
            vertex_list.delete()
        self.vertex_lists.clear()
        self.shadow_vertex_lists.clear()

    @staticmethod
    def _board_frame(pyglet, roll: float, pitch: float):
        from pyglet.math import Mat4, Vec3

        return Mat4.from_rotation(pitch, Vec3(1.0, 0.0, 0.0)) @ Mat4.from_rotation(
            -roll, Vec3(0.0, 0.0, 1.0)
        )

    @staticmethod
    def _camera(pyglet, board, aspect: float):
        from pyglet.math import Mat4, Vec3

        elevation = math.radians(47.0)
        fov = math.radians(36.0)
        half_v = math.tan(fov / 2.0)
        half_h = half_v * max(aspect, 0.35)
        span_x = board.width * 0.5 * 1.30
        span_z = board.depth * 0.5 * 1.30 * math.sin(elevation)
        distance = max(span_x / half_h, span_z / half_v) + board.depth * 0.25
        eye = (0.0, math.sin(elevation) * distance, math.cos(elevation) * distance)
        view = Mat4.look_at(Vec3(*eye), Vec3(0.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0))
        projection = Mat4.perspective_projection(aspect, 0.02, 12.0, fov=36.0)
        return projection @ view, eye

    @staticmethod
    def _marble_model(pyglet, marble, board, frame):
        from pyglet.math import Mat4, Vec3

        q = (marble.qw, marble.qx, marble.qy, marble.qz)
        w, x, y, z = q
        spin = Mat4(
            1 - 2 * (y * y + z * z),
            2 * (x * y + w * z),
            2 * (x * z - w * y),
            0,
            2 * (x * y - w * z),
            1 - 2 * (x * x + z * z),
            2 * (y * z + w * x),
            0,
            2 * (x * z + w * y),
            2 * (y * z - w * x),
            1 - 2 * (x * x + y * y),
            0,
            0,
            0,
            0,
            1,
        )
        position = Mat4.from_translation(
            Vec3(marble.x - board.width / 2, marble.z, board.depth / 2 - marble.y)
        )
        return frame @ position @ spin

    def draw(
        self, physics, width: int, height: int, black_background: bool = False
    ) -> bool:
        if self.geometry is None or self.board is None or physics is None:
            return False
        gl = self.gl
        x, bottom, stage_width, stage_height = stage_rect(width, height)
        if stage_width < 8 or stage_height < 8:
            return False
        self._ensure_colour_target(stage_width, stage_height)
        previous_clear = (gl.GLfloat * 4)()
        gl.glGetFloatv(gl.GL_COLOR_CLEAR_VALUE, previous_clear)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glScissor(x, bottom, stage_width, stage_height)
        shade = 0.055 if black_background else 0.90
        gl.glClearColor(
            shade, shade, shade + (0.01 if black_background else 0.005), 1.0
        )
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.colour_framebuffer)
        gl.glViewport(0, 0, stage_width, stage_height)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glClearColor(
            *(
                (0.055, 0.055, 0.065, 1.0)
                if black_background
                else (0.90, 0.905, 0.925, 1.0)
            )
        )
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glDisable(gl.GL_BLEND)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glEnable(gl.GL_MULTISAMPLE)
        gl.glEnable(gl.GL_SAMPLE_ALPHA_TO_COVERAGE)

        frame = self._board_frame(self._pyglet, physics.roll, physics.pitch)
        light_clip, light_matrix = self._light_matrices(self.board)
        view_proj, eye = self._camera(
            self._pyglet, self.board, stage_width / float(stage_height)
        )
        holes = self.geometry.holes

        shadow_program = self.shadow_program
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.shadow_framebuffer)
        gl.glViewport(0, 0, SHADOW_SIZE, SHADOW_SIZE)
        gl.glClearDepth(1.0)
        gl.glClear(gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LESS)
        gl.glDisable(gl.GL_BLEND)
        gl.glDisable(gl.GL_CULL_FACE)
        shadow_program.use()
        shadow_program["light_clip"] = light_clip
        shadow_program["hole_count"] = len(holes)
        shadow_holes = shadow_program["holes"]
        for index, hole in enumerate(holes):
            shadow_holes[index] = hole

        def draw_shadow(name: str, cut_holes: bool = False, model=None) -> None:
            vertex_list = self.shadow_vertex_lists.get(name)
            if vertex_list is None:
                return
            shadow_program["model"] = frame if model is None else model
            shadow_program["cut_holes"] = int(cut_holes)
            vertex_list.draw(gl.GL_TRIANGLES)

        draw_shadow("body", True)
        draw_shadow("frame")
        draw_shadow("walls")
        ball_list = self.vertex_lists.get("ball")
        if ball_list is not None:
            for marble in physics.marbles:
                if marble.state in ("home", "lost"):
                    continue
                draw_shadow(
                    "ball",
                    model=self._marble_model(self._pyglet, marble, self.board, frame),
                )

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.colour_framebuffer)
        gl.glViewport(0, 0, stage_width, stage_height)
        program = self.program
        program.use()
        program["view_proj"] = view_proj
        program["light_matrix"] = light_matrix
        program["eye"] = eye
        program["grain_seed"] = self.grain_seed
        program["light_direction"] = (-0.38, 0.86, 0.34)
        program["light_colour"] = (1.0, 0.97, 0.90)
        program["sky_colour"] = (0.76, 0.81, 0.90)
        program["ground_colour"] = (0.42, 0.30, 0.19)
        program["shadow_texel"] = 1.0 / SHADOW_SIZE
        program["shadows"] = 1
        program["hole_count"] = len(holes)
        uniform_holes = program["holes"]
        for index, hole in enumerate(holes):
            uniform_holes[index] = hole
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.shadow_texture)
        program["shadow_map"] = 0
        for index, (name, texture) in enumerate(
            zip(
                ("marble_colour", "marble_rough", "marble_normal"), self.marble_textures
            ),
            start=1,
        ):
            gl.glActiveTexture(gl.GL_TEXTURE0 + index)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
            program[name] = index

        def draw_mesh(
            name: str,
            material: int,
            tint: tuple[float, float, float],
            cut_holes: bool = False,
        ) -> None:
            vertex_list = self.vertex_lists.get(name)
            if vertex_list is None:
                return
            program["model"] = frame
            program["material"] = material
            program["tint"] = tint
            program["cut_holes"] = int(cut_holes)
            vertex_list.draw(gl.GL_TRIANGLES)

        draw_mesh("body", 0, (0.80, 0.63, 0.41), True)
        draw_mesh("frame", 0, (0.80, 0.63, 0.41))
        draw_mesh("walls", 1, (0.29, 0.18, 0.11))
        draw_mesh("pits", 3, (0.58, 0.44, 0.31))
        draw_mesh("cups", 3, (0.24, 0.44, 0.29))
        draw_mesh("collar", 4, (0.16, 0.55, 0.30))
        ball_list = self.vertex_lists.get("ball")
        if ball_list is not None:
            program["material"] = 2
            program["tint"] = (0.86, 0.88, 0.93)
            program["cut_holes"] = 0
            for marble in physics.marbles:
                if marble.state in ("home", "lost"):
                    continue
                program["model"] = self._marble_model(
                    self._pyglet, marble, self.board, frame
                )
                ball_list.draw(gl.GL_TRIANGLES)

        # Resolve the four-sample source stage once, then composite its texture
        # into the original stage rectangle on the host framebuffer.
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, self.colour_framebuffer)
        gl.glBindFramebuffer(gl.GL_DRAW_FRAMEBUFFER, self.resolve_framebuffer)
        gl.glBlitFramebuffer(
            0,
            0,
            stage_width,
            stage_height,
            0,
            0,
            stage_width,
            stage_height,
            gl.GL_COLOR_BUFFER_BIT,
            gl.GL_NEAREST,
        )
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glViewport(x, bottom, stage_width, stage_height)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_BLEND)
        gl.glDisable(gl.GL_SAMPLE_ALPHA_TO_COVERAGE)
        self.composite_program.use()
        self.composite_program["scene_texture"] = 0
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.resolve_texture)
        gl.glBindVertexArray(self.composite_vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)

        # Pyglet's batch renderer assumes its default framebuffer, full
        # viewport, blend function and depth/cull state on the next draw.
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glViewport(0, 0, width, height)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDisable(gl.GL_SAMPLE_ALPHA_TO_COVERAGE)
        gl.glBindVertexArray(0)
        for texture_unit in range(4):
            gl.glActiveTexture(gl.GL_TEXTURE0 + texture_unit)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glUseProgram(0)
        gl.glClearColor(*previous_clear)
        return True

    def close(self) -> None:
        self._delete_meshes()
        self._delete_shadow_target()
        self._delete_colour_target()
        if self.composite_vao.value:
            self.gl.glDeleteVertexArrays(1, ctypes.byref(self.composite_vao))
            self.composite_vao.value = 0
        self.board = None
        self.geometry = None
        self.program = None
        self.shadow_program = None
        self.composite_program = None
        self.marble_texture_images.clear()
