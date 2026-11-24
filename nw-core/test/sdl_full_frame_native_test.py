#!/usr/bin/env python3
"""Compare SDL options and special-task frame selection with direct writers."""
import ctypes
import os

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
def bind(name, count):
    fn = getattr(lib, name); fn.argtypes = [ctypes.c_int64] * count; fn.restype = ctypes.c_int64; return fn
dispatch = lib.nw_sdl_frame_write
dispatch.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64)] + [ctypes.c_int64] * 6
dispatch.restype = ctypes.c_int64
actual, expected = ctypes.create_string_buffer(1048576), ctypes.create_string_buffer(1048576)
cap = len(actual)
handles, options = (ctypes.c_int64 * 100)(), (ctypes.c_int64 * 42)()
cases = [
    ('syllogism', 34, 0, (1, 1, 1, 0, 1, 17), (2, 3, 1, 1, 1)),
    ('numberology', 19, 7, (1, 1, 1, 23), (2, 3, 1)),
    ('algebra', 18, 14, (1, 1, 23), (2, 3, 1, 1)),
    ('scramble', 35, 21, (1, 1, 1, 1, 17), (2, 3, 1, 1)),
    ('scrabble', 36, 28, (1, 1, 1, 1, 17), (2, 3, 1, 1)),
    ('crossword', 23, 35, (1, 1, 1, 1, 23), (2, 3, 1, 1)),
]
opened = []
try:
    for name, slot, base, args, flags in cases:
        create, destroy = bind('nw_' + name + '_create', len(args)), bind('nw_' + name + '_destroy', 1)
        handle = create(*args); assert handle > 0, name
        handles[slot] = handle; opened.append((slot, handle, destroy))
        options[base] = 1; options[base + 1] = 1
        for offset, value in enumerate(flags, 2): options[base + offset] = value
        writer = bind('nw_' + name + '_options_frame_write', 4 + len(flags))
        direct = writer(ctypes.addressof(expected), cap, 0, 1, *flags)
        # Activate each case alone while preserving its full options payload.
        saved = list(handles)
        for pos in range(37): handles[pos] = 0
        handles[slot] = handle
        routed = dispatch(ctypes.addressof(actual), cap, handles, options, 912, 684, 0, 0, 0, 0)
        assert direct > 0 and routed == direct and actual.raw[:routed] == expected.raw[:direct], name
        for pos, value in enumerate(saved): handles[pos] = value
    # All six open screens must follow the original priority order.
    for name, slot, base, args, flags in cases:
        writer = bind('nw_' + name + '_options_frame_write', 4 + len(flags))
        direct = writer(ctypes.addressof(expected), cap, 0, 1, *flags)
        routed = dispatch(ctypes.addressof(actual), cap, handles, options, 912, 684, 0, 0, 0, 0)
        assert routed == direct and actual.raw[:routed] == expected.raw[:direct], name
        handles[slot] = 0
    for name, slot, base, args, flags in (cases[0], cases[3], cases[4]):
        handle = next(h for s, h, _ in opened if s == slot)
        handles[slot] = handle; options[base] = 0
        direct = bind('nw_' + name + '_frame_write', 6)(ctypes.addressof(expected), cap, handle, 0, 912, 684)
        routed = dispatch(ctypes.addressof(actual), cap, handles, options, 912, 684, 0, 0, 0, 0)
        assert direct > 0 and routed == direct and actual.raw[:routed] == expected.raw[:direct], name
        handles[slot] = 0
    assert dispatch(ctypes.addressof(actual), cap, handles, None, 912, 684, 0, 0, 0, 0) == 0
finally:
    for _, handle, destroy in opened: destroy(handle)
print('SDL full frame selection: options, priority, and special task frames pass')
