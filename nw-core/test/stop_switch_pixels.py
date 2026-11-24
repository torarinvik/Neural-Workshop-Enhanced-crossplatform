#!/usr/bin/env python3
"""Compare real source and native pixels at synchronized Stop & Switch cues."""
from contextlib import closing
import ctypes
import os
from pathlib import Path
import random
import sys
from types import SimpleNamespace

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))

import pyglet
from pyglet.gl import glClearColor
from neural_workshop import geometry, state
from neural_workshop.ui.stopswitch import StopAndSwitch
from nwenv.frames import capture_rgba

WIDTH, HEIGHT = 912, 684
HEADER = 36
PUBLICATION = 208  # Ten 64-bit fields and two 64-byte digests.
lib = ctypes.CDLL(str(Path(sys.argv[1]).resolve(strict=True)))
create = lib.nw_stop_switch_agent_create
create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
create.restype = ctypes.c_int64
destroy = lib.nw_stop_switch_agent_destroy
destroy.argtypes = [ctypes.c_int64]
destroy.restype = None
act = lib.nw_stop_switch_agent_act
act.argtypes = [ctypes.c_int64] * 3
act.restype = ctypes.c_int64
publish = lib.nw_stop_switch_agent_publish
publish.argtypes = [ctypes.c_int64, ctypes.c_double, ctypes.c_int64, ctypes.c_void_p,
                    ctypes.c_int64, ctypes.c_int32, ctypes.c_int32, ctypes.c_int64, ctypes.c_void_p]
publish.restype = ctypes.c_int64

# Query the backing scale before creating the invisible reference window.
with closing(pyglet.window.Window(width=200, height=150, visible=False)) as probe:
    backing_width, backing_height = geometry.framebuffer_size(probe)
with closing(pyglet.window.Window(width=WIDTH * 200 // backing_width,
                          height=HEIGHT * 150 // backing_height, visible=False)) as window:
    state.window = window
    assert geometry.framebuffer_size(window) == (WIDTH, HEIGHT)
    for dark in (False, True):
        state.cfg = SimpleNamespace(BLACK_BACKGROUND=dark)
        original = StopAndSwitch.__new__(StopAndSwitch)
        original.drawn, original.hits = [], []
        original.rng = random.Random(0)
        now = 0.0
        original.clock = lambda: now
        original.start_rung, original.total_trials, original.adaptive = 25, 1, False
        original.phase, original.message, original.verdict_shown, original.block = "ready", "", None, None
        original._build_chrome()
        original.start_run()
        handle = create(25, 1, 0, 0, 2, False)
        assert handle > 0
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER)
        publication = ctypes.create_string_buffer(PUBLICATION)
        timestamp = 0

        def compare(label, dt, samples):
            shade = float(not dark)
            glClearColor(shade, shade, shade, 1.0)
            window.clear()
            original.batch.draw()
            _, _, python_pixels = capture_rgba(window)
            length = publish(handle, dt, timestamp, packet, len(packet), WIDTH, HEIGHT, dark, publication)
            assert length == len(packet)
            native_pixels = packet.raw[HEADER:]
            for x, y, expected in samples:
                offset = ((HEIGHT - 1 - y) * WIDTH + x) * 4
                python_rgb = tuple(python_pixels[offset:offset + 3])
                native_rgb = tuple(native_pixels[offset:offset + 3])
                assert python_rgb == native_rgb == expected, (dark, label, x, y, python_rgb, native_rgb, expected)
            identical = sum(sr == dr and sg == dg and sb == db for sr, sg, sb, dr, dg, db in zip(
                python_pixels[0::4], python_pixels[1::4], python_pixels[2::4],
                native_pixels[0::4], native_pixels[1::4], native_pixels[2::4],
            ))
            print(f"{'dark' if dark else 'light'} {label}: {identical / (WIDTH * HEIGHT):.2%} identical RGB pixels")

        stage = (24, 27, 36) if dark else (236, 240, 246)
        key_face = (38, 43, 56) if dark else (255, 255, 255)
        key_lip = (31, 35, 46) if dark else (209, 209, 209)
        muted = (150, 158, 176) if dark else (112, 120, 138)
        pending = (49, 55, 70) if dark else (220, 226, 235)
        try:
            compare("concealed cue", 0.0, [(510, 420, stage), (77, 366, key_face), (96, 344, key_lip),
                                           (456, 373, muted), (197, 202, pending)])
            now = 0.601
            timestamp += 1
            original.update(now)
            compare("orange circle", 0.601, [(285, 373, (236, 140, 40)), (322, 373, (165, 98, 28)),
                                             (360, 523, (120, 124, 134))])
            original.steer(1)
            timestamp += 1
            assert act(handle, 1, timestamp) > 0
            now += 0.601
            timestamp += 1
            original.update(0.601)
            compare("blue square before ring", 0.601, [(627, 373, (60, 120, 220)), (689, 373, stage),
                                                        (197, 202, (60, 170, 90))])
            now += 0.301
            timestamp += 1
            original.update(0.301)
            compare("stop ring", 0.301, [(627, 373, (60, 120, 220)), (688, 373, (220, 40, 40))])
        finally:
            destroy(handle)
            original._clear_drawn()
print("PASS: Stop & Switch source/native interior pixels for stage, keys, cue, circle, square, and stop ring in both themes")
