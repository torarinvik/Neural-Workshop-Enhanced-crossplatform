#!/usr/bin/env python3
"""Exercise Elisa SDL window ownership using SDL's dummy video driver."""
import ctypes
import os
import subprocess
import sys

os.environ['SDL_VIDEODRIVER'] = 'missing-test-driver' if '--invalid-driver' in sys.argv else 'dummy'
os.environ['SDL_RENDER_DRIVER'] = 'software'
lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
open_window = lib.nw_sdl_window_open
open_window.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int32, ctypes.c_int32, ctypes.c_int64]
open_window.restype = ctypes.c_int64
close_window = lib.nw_sdl_window_close
close_window.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
quit_sdl = lib.SDL_Quit
state = (ctypes.c_size_t * 3)()
if '--invalid-driver' in sys.argv:
    assert open_window(state, 912, 684, 65536) == 0 and not any(state)
    sys.exit(0)
assert open_window(state, 912, 684, 65536) == 1 and all(state)
close_window(state)
assert not any(state)
close_window(state)
quit_sdl()
assert open_window(None, 912, 684, 65536) == 0
subprocess.run([sys.executable, __file__, '--invalid-driver'], check=True, timeout=15)
print('SDL dummy window: open, repeat close, and failed creation pass')
