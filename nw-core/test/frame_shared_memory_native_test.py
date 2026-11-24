#!/usr/bin/env python3
"""Check Elisa's native NWFB publisher with Python's shared-memory reader."""
import ctypes as c
from multiprocessing.shared_memory import SharedMemory
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile
import uuid

root = Path(__file__).resolve().parents[1]
oracle = runpy.run_path(str(root.parent / "original-neural-workshop-enhanced/nwenv/export.py"))
header = oracle["HEADER"]
native, runtime = sys.argv[1:3]
symbols = ["nw_frame_shared_create", "nw_frame_shared_publish", "nw_frame_shared_release"]
flags = shlex.split(subprocess.check_output(["pkg-config", "--libs", "sdl3"], text=True))
link_flags = ["-Wl,--allow-multiple-definition"]
if sys.platform.startswith("linux"):
    flags.append("-lm")
if sys.platform == "darwin":
    link_flags = ["-Wl,-dead_strip", *(f"-Wl,-exported_symbol,_{name}" for name in symbols)]


def attach(name):
    if sys.version_info >= (3, 13):
        return SharedMemory(name=name, track=False)
    frame = SharedMemory(name=name)
    if os.name == "posix":
        from multiprocessing import resource_tracker
        resource_tracker.unregister("/" + name, "shared_memory")
    return frame


with tempfile.TemporaryDirectory() as tmp:
    library = Path(tmp) / ("frame.dll" if os.name == "nt" else "frame.so")
    subprocess.run(["cc", "-shared", *link_flags, "-o", str(library), native, runtime, *flags], check=True)
    api = c.CDLL(str(library))
    create, publish, release = (getattr(api, name) for name in symbols)
    create.argtypes = [c.c_char_p, c.c_int64]
    create.restype = c.c_size_t
    publish.argtypes = [c.c_size_t, c.c_uint64, c.c_uint64, c.c_uint32,
                        c.c_uint32, c.c_void_p, c.c_int64, c.c_bool]
    publish.restype = c.c_int64
    release.argtypes = [c.POINTER(c.c_size_t)]
    release.restype = None
    name = "nwfb_" + uuid.uuid4().hex[:16]
    raw_name = name.encode()
    pixels = bytes(range(24))
    size = header.size + len(pixels)
    assert create(raw_name, header.size - 1) == 0
    owner = c.c_size_t(create(raw_name, size))
    assert owner.value
    try:
        assert create(raw_name, size) == 0, "a second writer must not replace this mapping"
        reader = attach(name)
        try:
            for seq, stamp, width, height, rgba, consumed in [
                (1, 987654321, 2, 3, pixels, False),
                (2, 987654322, 1, 1, bytes(reversed(pixels[:4])), True),
            ]:
                assert publish(owner.value, seq, stamp, width, height, rgba, len(rgba), consumed) == header.size + len(rgba)
                assert bytes(reader.buf[:header.size + len(rgba)]) == (
                    header.pack(oracle["MAGIC"], oracle["VERSION"], seq, stamp, width, height, consumed) + rgba
                )
            previous = bytes(reader.buf[:size])
            assert publish(owner.value, 3, 99, 8, 1, bytes(32), 32, False) == -1
            assert publish(owner.value, 3, 99, 2, 2, pixels, len(pixels), False) == -1
            assert bytes(reader.buf[:size]) == previous
        finally:
            reader.close()
    finally:
        release(c.byref(owner))
        release(c.byref(owner))
    assert owner.value == 0
    try:
        reader = attach(name)
    except FileNotFoundError:
        pass
    else:
        reader.close()
        raise AssertionError("mapping still attachable after release")
    owner.value = create(raw_name, size)
    assert owner.value, "the same name should be reusable"
    release(c.byref(owner))
print("PASS: Python reader attaches to native NWFB, including ownership and cleanup")
