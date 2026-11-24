#!/usr/bin/env python3
"""Compare batched SDL frame advances with direct controller calls."""
import ast
import ctypes
import os
from pathlib import Path

source = Path(__file__).with_name('sdl_hub_defaults_native_test.py').read_text()
tree = ast.parse(source)
cases = next(ast.literal_eval(node.value) for node in tree.body
             if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'cases' for target in node.targets))
by_name = {name: args for _, _, name, args in cases}
names = ('monkey_ladder', 'nback3d', 'marble', 'count', 'mr_time', 'graph_mapping',
         'matrix_reasoning', 'in_the_dark', 'removals', 'custody', 'concentration',
         'recognition', 'reflex', 'ncup_monte', 'tracking', 'lookout', 'pursuit',
         'out_of_sight', 'buzz_wire', 'donkey', 'two_hands', 'overrun')
lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
batch = lib.nw_sdl_advance_frame
batch.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_uint64)]
handles = (ctypes.c_int64 * (len(names) + 1))()
last = ctypes.c_uint64(190)
pairs = []
try:
    for i, name in enumerate(names):
        create = getattr(lib, 'nw_' + name + '_create')
        create.argtypes = [ctypes.c_int64] * len(by_name[name])
        create.restype = ctypes.c_int64
        action = getattr(lib, 'nw_' + name + '_action')
        action.argtypes = [ctypes.c_int64] * 4
        action.restype = ctypes.c_int64
        info = getattr(lib, 'nw_' + name + '_info')
        info.argtypes = [ctypes.c_int64] * 2
        info.restype = ctypes.c_int64
        destroy = getattr(lib, 'nw_' + name + '_destroy')
        destroy.argtypes = [ctypes.c_int64]
        destroy.restype = ctypes.c_int64
        direct, migrated = create(*by_name[name]), create(*by_name[name])
        assert direct > 0 and migrated > 0, name
        pairs.append((name, direct, migrated, action, info, destroy))
        handles[i] = migrated
        action(direct, 0, 0, 100)
        action(migrated, 0, 0, 100)
    for name, direct, _, action, _, _ in pairs:
        if name == 'monkey_ladder': action(direct, 1, 0, 200)
        elif name == 'nback3d': action(direct, 2, 0, 200)
        else:
            advance = getattr(lib, 'nw_' + name + '_advance')
            advance.argtypes = [ctypes.c_int64] * 2
            advance.restype = ctypes.c_int64
            advance(direct, 10 if name == 'marble' else 200)
    batch(handles, ctypes.byref(last))
    assert last.value == 200
    for name, direct, migrated, _, info, _ in pairs:
        for field in range(6):
            assert info(direct, field) == info(migrated, field), (name, field)
    handles[2] = 0
    last.value = 123
    batch(handles, ctypes.byref(last))
    assert last.value == 123
    batch(None, ctypes.byref(last))
    batch(handles, None)
finally:
    for _, direct, migrated, _, _, destroy in pairs:
        destroy(direct)
        destroy(migrated)
print('SDL frame advance: 22 active controllers match direct calls')
