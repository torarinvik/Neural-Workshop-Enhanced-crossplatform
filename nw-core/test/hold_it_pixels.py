#!/usr/bin/env python3
"""Compare synchronized Python and native Hold It frames in both themes."""
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
from neural_workshop.ui.holdit import HoldIt
from nwenv.frames import capture_rgba
from nwenv.holdit import HoldItEnv
from nwenv.outcome import derive_public_outcome

WIDTH, HEIGHT = 912, 684
HEADER = 36
PUBLICATION = 208
DT = 1 / 16
OFF, FIRST, SECOND = (70, 70, 90), (255, 214, 120), (140, 220, 255)


def replay(window, lib, dark):
    state.window = window
    state.cfg = SimpleNamespace(BLACK_BACKGROUND=dark, COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    original = HoldIt.__new__(HoldIt)
    original.drawn, original.hits, original.scenery = [], [], []
    original.rng = Random(0)
    original._held = lambda: None
    now = 0.0
    original.clock = lambda: now
    original.start_rung, original.total_trials, original.adaptive = 13, 1, False
    original.phase, original.message, original.verdict_shown, original.run = "ready", "", None, None
    original._build_chrome()
    original.start_run()
    env = HoldItEnv.__new__(HoldItEnv)
    env._settled_seen = False

    handle = lib.nw_hold_it_agent_create(13, 1, 0, 0, 1, False)
    assert handle > 0
    packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER)
    publication = ctypes.create_string_buffer(PUBLICATION)
    no_duration_bars = (22, 24, 37)
    samples = {
        0: ("waiting for lamps", OFF, OFF),
        16: ("first lamp", FIRST, OFF),
        56: ("second lamp", OFF, SECOND),
        100: ("hold", FIRST, SECOND),
        153: ("verdict", OFF, OFF),
    }

    def compare(tick):
        label, first, second = samples[tick]
        shade = float(not dark)
        glClearColor(shade, shade, shade, 1.0)
        window.clear()
        original.batch.draw()
        _, _, python_pixels = capture_rgba(window)
        native_pixels = packet.raw[HEADER:]
        for frame in (python_pixels, native_pixels):
            outcome = derive_public_outcome(frame, WIDTH, HEIGHT, (), None)
            if tick == 153:
                assert outcome is not None and outcome["scalar"] == 1.0
            else:
                assert outcome is None
        interior = [
            (353, 396, first), (559, 396, second), (353, 330, (170, 140, 70)),
            (755, 450, (236, 230, 214)), (75, 190, (21, 23, 35)),
        ]
        if tick == 153:
            interior.extend([(220, 248, (120, 220, 150)), (220, 217, (255, 200, 110))])
        elif tick == 0:
            interior.append((220, 217, no_duration_bars))
        for x, y, expected in interior:
            offset = ((HEIGHT - 1 - y) * WIDTH + x) * 4
            python_rgb = tuple(python_pixels[offset:offset + 3])
            native_rgb = tuple(native_pixels[offset:offset + 3])
            assert python_rgb == native_rgb == expected, (dark, label, x, y, python_rgb, native_rgb, expected)
        errors = [max(abs(a - d), abs(b - e), abs(c - f)) for a, b, c, d, e, f in zip(
            python_pixels[0::4], python_pixels[1::4], python_pixels[2::4],
            native_pixels[0::4], native_pixels[1::4], native_pixels[2::4],
        )]
        same = errors.count(0) / len(errors)
        within_four = sum(error <= 4 for error in errors) / len(errors)
        print(f"{'dark' if dark else 'light'} {label}: {same:.2%} identical, {within_four:.2%} within four RGB levels")

    try:
        for tick in range(154):
            if tick:
                if 98 <= tick <= 152:
                    original.steer(0)
                    assert lib.nw_hold_it_agent_act(handle, 0, tick * 2 - 1) > 0
                now = tick * DT
                env.tick(original, DT)
            count = lib.nw_hold_it_agent_publish(
                handle, DT, tick * 2, packet, len(packet), WIDTH, HEIGHT, dark, publication)
            assert count == len(packet)
            if tick in samples:
                compare(tick)
        assert original.phase == "judged" and original.run.result[0]
    finally:
        lib.nw_hold_it_agent_destroy(handle)
        original._clear_drawn()
        original._clear_trial()


if __name__ == "__main__":
    lib = ctypes.CDLL(str(Path(sys.argv[1]).resolve(strict=True)))
    lib.nw_hold_it_agent_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
    lib.nw_hold_it_agent_create.restype = ctypes.c_int64
    lib.nw_hold_it_agent_act.argtypes = [ctypes.c_int64] * 3
    lib.nw_hold_it_agent_act.restype = ctypes.c_int64
    lib.nw_hold_it_agent_destroy.argtypes = [ctypes.c_int64]
    lib.nw_hold_it_agent_destroy.restype = None
    lib.nw_hold_it_agent_publish.argtypes = [
        ctypes.c_int64, ctypes.c_double, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
        ctypes.c_int32, ctypes.c_int32, ctypes.c_int64, ctypes.c_void_p,
    ]
    lib.nw_hold_it_agent_publish.restype = ctypes.c_int64

    runtime.HEADLESS = True
    with closing(pyglet.window.Window(width=200, height=150, visible=False)) as probe:
        backing_width, backing_height = geometry.framebuffer_size(probe)
    with closing(pyglet.window.Window(width=WIDTH * 200 // backing_width,
                                      height=HEIGHT * 150 // backing_height, visible=False)) as window:
        assert geometry.framebuffer_size(window) == (WIDTH, HEIGHT)
        for dark in (False, True):
            replay(window, lib, dark)
    print("PASS: Hold It lamp, clock, stage, and result-bar interior pixels in both themes")
