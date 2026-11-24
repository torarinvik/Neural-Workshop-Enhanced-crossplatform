#!/usr/bin/env python3
"""Check every SDL window startup failure with process-local SDL stubs."""
import ctypes
import os

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
reset = lib.nw_test_sdl_reset
reset.argtypes = [ctypes.c_int]
trace = lib.nw_test_sdl_trace
trace.argtypes = [ctypes.c_int]
trace.restype = ctypes.c_int
open_window = lib.nw_sdl_window_open
open_window.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int32, ctypes.c_int32, ctypes.c_int64]
open_window.restype = ctypes.c_int64
close_window = lib.nw_sdl_window_close
close_window.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
state = (ctypes.c_size_t * 3)()
def sequence():
    return [trace(i) for i in range(12) if trace(i)]
for fault, expected in ((1, [1]), (2, [1, 2, 7]), (3, [1, 2, 3, 6, 7]),
                        (4, [1, 2, 3, 4, 5, 6, 7])):
    reset(fault)
    assert open_window(state, 912, 684, -1 if fault == 4 else 65536) == 0
    assert not any(state) and sequence() == expected, (fault, list(state), sequence())
    close_window(state)
    assert sequence() == expected
reset(0)
assert open_window(state, 912, 684, 65536) == 1 and all(state)
assert sequence() == [1, 2, 3, 4]
close_window(state); close_window(state)
assert not any(state) and sequence() == [1, 2, 3, 4, 5, 6]
print('SDL window failures: initialization, window, renderer, and buffer cleanup pass')
