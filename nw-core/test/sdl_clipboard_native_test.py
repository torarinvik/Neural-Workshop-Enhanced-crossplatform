#!/usr/bin/env python3
"""Test SDL clipboard routing with a process-local clipboard stub."""
import ctypes
import os

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
mock = lib.nw_test_clipboard_value
mock.argtypes = [ctypes.c_int]
paste = lib.nw_sdl_paste_text
paste.argtypes = [ctypes.c_int64] * 3
cases = [
    ('numberology', (1, 1, 0, 23), 0, 16, 0),
    ('algebra', (1, 1, 23), 1, 6, 0),
    ('scramble', (1, 1, 1, 1, 17), 2, 5, 1),
]
for name, args, task, length_field, value in cases:
    create = getattr(lib, 'nw_' + name + '_create')
    create.argtypes = [ctypes.c_int64] * len(args)
    create.restype = ctypes.c_int64
    action = getattr(lib, 'nw_' + name + '_action')
    action.argtypes = [ctypes.c_int64] * 4
    action.restype = ctypes.c_int64
    info = getattr(lib, 'nw_' + name + '_info')
    info.argtypes = [ctypes.c_int64] * 2
    info.restype = ctypes.c_int64
    destroy = getattr(lib, 'nw_' + name + '_destroy')
    destroy.argtypes = [ctypes.c_int64]
    handle = create(*args)
    assert handle > 0
    try:
        assert action(handle, 0, 0, 100) == 1
        mock(2)  # unavailable clipboard leaves the response untouched
        paste(handle, 200, task)
        assert info(handle, length_field) == 0
        mock(value)
        paste(handle, 300, task)
        assert info(handle, length_field) == 2
    finally:
        destroy(handle)
print('SDL clipboard: null and text input pass for all three controllers')
