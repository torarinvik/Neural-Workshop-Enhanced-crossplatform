#!/usr/bin/env python3
"""Compare synchronized Shadow Play pixels in the Python and SDL renderers."""

from contextlib import closing
import ctypes
import os
from pathlib import Path
from random import Random
import sys
from types import SimpleNamespace

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))

import pyglet
from pyglet.gl import glClearColor
from neural_workshop import geometry, runtime, state
from neural_workshop.ui.shadowplay import ShadowPlay
from nwenv.frames import capture_rgba
from nwenv.outcome import derive_public_outcome
from nwenv.shadowplay import ShadowPlayEnv

WIDTH, HEIGHT = 912, 684
HEADER, PUBLICATION = 36, 208
DT = 0.05


def replay(window, lib, dark, rung):
    state.window = window
    state.cfg = SimpleNamespace(BLACK_BACKGROUND=dark, COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    original = ShadowPlay.__new__(ShadowPlay)
    original.drawn, original.hits, original.scenery = [], [], []
    original.rng = Random(17)
    original._held = lambda: None
    now = 0.0
    original.clock = lambda: now
    original.start_rung, original.total_trials, original.adaptive = rung, 1, False
    original.phase, original.message, original.verdict_shown, original.run = "ready", "", None, None
    original._build_chrome()
    original.start_run()
    env = ShadowPlayEnv.__new__(ShadowPlayEnv)
    env._settled_seen = False

    handle = lib.nw_shadow_play_agent_create(rung, 1, 0, 17, 6, False)
    assert handle > 0
    packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER)
    publication = ctypes.create_string_buffer(PUBLICATION)
    compared = 0
    try:
        for tick in range(45 if rung == 1 else 25):
            # The seed-17 rung-one target needs about 30 frames of left yaw.
            if tick:
                if rung == 1 and tick <= 30:
                    original.steer(0)
                    assert lib.nw_shadow_play_agent_act(handle, 0, tick * 2 - 1) > 0
                now += DT
                env.tick(original, DT)
            count = lib.nw_shadow_play_agent_publish(
                handle, DT, tick * 2, packet, len(packet), WIDTH, HEIGHT, dark, publication)
            assert count == len(packet)
            if tick not in (0, 22, 32) and original.phase != "judged":
                continue
            shade = float(not dark)
            glClearColor(shade, shade, shade, 1.0)
            window.clear()
            original.batch.draw()
            _, _, python_pixels = capture_rgba(window)
            native_pixels = packet.raw[HEADER:]
            for frame in (python_pixels, native_pixels):
                public = derive_public_outcome(frame, WIDTH, HEIGHT, (), None)
                if original.phase == "judged":
                    assert public is not None and public["scalar"] == 1.0
                else:
                    assert public is None
            interior = [
                (70, 200, (36, 30, 34)),
                (600, 350, (110, 80, 60)),
                (456, 225, (145, 104, 74)),
            ]
            if rung == 16:
                interior.append((456, 450, (232, 185, 153)))
            if original.run.close() == 1.0:
                interior.append((291, 198, (110, 230, 140)))
            for x, y, expected in interior:
                offset = ((HEIGHT - 1 - y) * WIDTH + x) * 4
                python_rgb = tuple(python_pixels[offset:offset + 3])
                native_rgb = tuple(native_pixels[offset:offset + 3])
                assert python_rgb == native_rgb == expected, (dark, rung, tick, x, y, python_rgb, native_rgb)
            # The moving light is alpha blended, which rounds differently in SDL and OpenGL.
            offset = ((HEIGHT - 1 - 500) * WIDTH + 456) * 4
            assert max(abs(a - b) for a, b in zip(python_pixels[offset:offset + 3],
                                                 native_pixels[offset:offset + 3])) <= 3
            errors = [max(abs(a - d), abs(b - e), abs(c - f)) for a, b, c, d, e, f in zip(
                python_pixels[0::4], python_pixels[1::4], python_pixels[2::4],
                native_pixels[0::4], native_pixels[1::4], native_pixels[2::4],
            )]
            same = errors.count(0) / len(errors)
            within_four = sum(error <= 4 for error in errors) / len(errors)
            print(f"{'dark' if dark else 'light'} rung {rung}, tick {tick}: "
                  f"{same:.2%} identical, {within_four:.2%} within four RGB levels")
            compared += 1
            if original.phase == "judged":
                break
        assert compared == (4 if rung == 1 else 2)
    finally:
        lib.nw_shadow_play_agent_destroy(handle)
        original._clear_drawn()
        original._clear_trial()


if __name__ == "__main__":
    lib = ctypes.CDLL(str(Path(sys.argv[1]).resolve(strict=True)))
    lib.nw_shadow_play_agent_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
    lib.nw_shadow_play_agent_create.restype = ctypes.c_int64
    lib.nw_shadow_play_agent_act.argtypes = [ctypes.c_int64] * 3
    lib.nw_shadow_play_agent_act.restype = ctypes.c_int64
    lib.nw_shadow_play_agent_destroy.argtypes = [ctypes.c_int64]
    lib.nw_shadow_play_agent_destroy.restype = None
    lib.nw_shadow_play_agent_publish.argtypes = [
        ctypes.c_int64, ctypes.c_double, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
        ctypes.c_int32, ctypes.c_int32, ctypes.c_int64, ctypes.c_void_p,
    ]
    lib.nw_shadow_play_agent_publish.restype = ctypes.c_int64

    runtime.HEADLESS = True
    with closing(pyglet.window.Window(width=200, height=150, visible=False)) as probe:
        backing_width, backing_height = geometry.framebuffer_size(probe)
    with closing(pyglet.window.Window(width=WIDTH * 200 // backing_width,
                                      height=HEIGHT * 150 // backing_height, visible=False)) as window:
        assert geometry.framebuffer_size(window) == (WIDTH, HEIGHT)
        for dark in (False, True):
            for rung in (1, 16):
                replay(window, lib, dark, rung)
