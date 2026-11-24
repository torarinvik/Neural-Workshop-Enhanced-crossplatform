#!/usr/bin/env python3
"""Replay the packaged Marble Maze renderer on an isolated Xvfb display."""
import ctypes as c
from multiprocessing.shared_memory import SharedMemory
import os
import runpy
from pathlib import Path
import subprocess
import sys
import time
import uuid

x11 = c.CDLL("libX11.so.6")
xtst = c.CDLL("libXtst.so.6")
def bind(lib, name, result, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, args
    return fn

display = bind(x11, "XOpenDisplay", c.c_void_p, c.c_char_p)(None)
assert display
root = bind(x11, "XDefaultRootWindow", c.c_ulong, c.c_void_p)(display)
query = bind(x11, "XQueryTree", c.c_int, c.c_void_p, c.c_ulong,
             c.POINTER(c.c_ulong), c.POINTER(c.c_ulong), c.POINTER(c.POINTER(c.c_ulong)), c.POINTER(c.c_uint))
fetch_name = bind(x11, "XFetchName", c.c_int, c.c_void_p, c.c_ulong, c.POINTER(c.c_char_p))
focus = bind(x11, "XSetInputFocus", c.c_int, c.c_void_p, c.c_ulong, c.c_int, c.c_ulong)
flush = bind(x11, "XFlush", c.c_int, c.c_void_p)
free = bind(x11, "XFree", c.c_int, c.c_void_p)
keycode = bind(x11, "XKeysymToKeycode", c.c_ubyte, c.c_void_p, c.c_ulong)
send = bind(xtst, "XTestFakeKeyEvent", c.c_int, c.c_void_p, c.c_uint, c.c_int, c.c_ulong)

def wait(fn, child):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and child.poll() is None:
        value = fn()
        if value is not None:
            return value
        time.sleep(0.025)
    raise RuntimeError("Timed out waiting for window or rendered data")

def window():
    r = c.c_ulong()
    parent = c.c_ulong()
    children = c.POINTER(c.c_ulong)()
    count = c.c_uint()
    assert query(display, root, c.byref(r), c.byref(parent), c.byref(children), c.byref(count))
    try:
        for i in range(count.value):
            name = c.c_char_p()
            if fetch_name(display, children[i], c.byref(name)) and name:
                value = name.value
                free(name)
                if b"Neural Workshop" in value:
                    return children[i]
    finally:
        if children:
            free(children)

def press(symbol):
    key = keycode(display, symbol)
    assert send(display, key, 1, 0) and send(display, key, 0, 0)
    flush(display)

name = "nwfb_" + uuid.uuid4().hex[:16]
binary = Path(sys.argv[1])
env = dict(os.environ, SDL_VIDEODRIVER="x11", SDL_RENDER_DRIVER="software", SDL_AUDIODRIVER="dummy",
           NW_SHM=name, LIBGL_ALWAYS_SOFTWARE="1")
reference = Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced/nwenv/export.py"
header = runpy.run_path(str(reference))["HEADER"]
child = subprocess.Popen([str(binary), "--screen", "marble", "--width", "912", "--height", "684"],
                         env=env, stderr=subprocess.PIPE, text=True)
def attach():
    try:
        return SharedMemory(name=name, track=False)
    except (FileNotFoundError, ValueError):
        return None
shared = None
try:
    shared = wait(attach, child)
    target = wait(window, child)
    def sample():
        magic, version, seq, stamp, width, height, flags = header.unpack_from(shared.buf)
        if magic != b"NWFB" or not seq or (width, height) != (912, 684):
            return None
        colors = set()
        for y in range(210, 510, 5):
            for x in range(230, 680, 5):
                offset = header.size + (y * width + x) * 4
                colors.add(bytes(shared.buf[offset:offset + 4]))
        return seq, len(colors)

    ready = wait(sample, child)
    focus(display, target, 2, 0)
    press(0x20)
    def check_stage():
        frame = sample()
        return frame if frame and frame[0] > ready[0] and frame[1] > ready[1] + 100 else None
    active = wait(check_stage, child)
    print(f"PASS: X11 Marble stage reaches NWFB ({ready[1]} ready colors, {active[1]} active colors)")
    shared.close()
    shared = None
    press(0xff1b)
    _, err = child.communicate(timeout=5)
    assert child.returncode == 0, err
    assert attach() is None, "mapping still attachable after quit"
finally:
    if shared is not None:
        shared.close()
    if child.poll() is None:
        child.terminate()
    _, err = child.communicate()
    if child.returncode != 0:
        print(err, file=sys.stderr)
        leftover = attach()
        if leftover:
            leftover.unlink()
            leftover.close()
