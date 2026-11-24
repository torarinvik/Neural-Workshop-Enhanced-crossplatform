#!/usr/bin/env python3
"""Compare SDL frame dispatch with direct frame writers, headlessly."""
import ast
import ctypes
import os
from pathlib import Path

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
tree = ast.parse(Path(__file__).with_name('sdl_hub_defaults_native_test.py').read_text())
cases = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'cases' for target in node.targets))
args = {name: params for _, _, name, params in cases}
args.update(algebra=(1, 1, 23), numberology=(1, 1, 1, 23), jigsaw=(3, 1, 1, 1, 23),
            sudoku=(1, 1, 1, 1, 23), go=(1, 1, 23), crossword=(1, 1, 1, 1, 23),
            crossed_wires=(1, 1, 1, 1, 23))
names = ('you_are_here', 'sokoban', 'monkey_ladder', 'nback3d', 'marble', 'tetris',
         'count', 'mr_time', 'graph_mapping', 'matrix_reasoning', 'in_the_dark', 'fog',
         'removals', 'custody', 'concentration', 'recognition', 'trivia', 'reflex',
         'algebra', 'numberology', 'jigsaw', 'sudoku', 'go', 'crossword', 'crossed_wires',
         'ncup_monte', 'tracking', 'lookout', 'pursuit', 'out_of_sight', 'buzz_wire',
         'donkey', 'two_hands', 'overrun')
dispatch = lib.nw_sdl_task_frame_write
dispatch.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)] + [ctypes.c_int64] * 6
dispatch.restype = ctypes.c_int64
handles = (ctypes.c_int64 * len(names))()
expected, actual = ctypes.create_string_buffer(1048576), ctypes.create_string_buffer(1048576)
cap = len(actual)
def bind(name, count):
    f = getattr(lib, name); f.argtypes = [ctypes.c_int64] * count; f.restype = ctypes.c_int64; return f
for i, name in enumerate(names):
    create, destroy, frame = (bind('nw_' + name + '_' + suffix, count) for suffix, count in
                              (('create', len(args[name])), ('destroy', 1), ('frame_write', 6)))
    handle = create(*args[name])
    assert handle > 0, name
    try:
        handles[i] = handle
        direct_len = frame(ctypes.addressof(expected), cap, handle, 0, 912, 684)
        routed_len = dispatch(ctypes.addressof(actual), cap, handles, 912, 684, 0, 0, 0, 0)
        assert direct_len > 0 and routed_len == direct_len, (name, direct_len, routed_len)
        assert expected.raw[:direct_len] == actual.raw[:routed_len], name
    finally:
        handles[i] = 0
        destroy(handle)
trial = 7
for hub in (0, 1):
    writer = bind('nw_taskhub_write' if hub else 'nw_title_write', 7 if hub else 6)
    direct = (writer(ctypes.addressof(expected), cap, 2, 3, 0, 912, 684) if hub else
              writer(ctypes.addressof(expected), cap, (trial - 1) % 4, 0, 1, 1))
    routed = dispatch(ctypes.addressof(actual), cap, handles, 912, 684, hub, 2, 3, trial)
    assert routed == direct and direct > 0 and actual.raw[:routed] == expected.raw[:direct]
assert dispatch(ctypes.addressof(actual), cap, None, 912, 684, 0, 0, 0, 0) == 0
print('SDL frame dispatch: 34 task frames and hub/title match direct writers')
