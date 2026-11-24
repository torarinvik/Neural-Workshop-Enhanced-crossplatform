#!/usr/bin/env python3
"""Compare SDL pointer routing with direct controller ABI calls."""
import ast
import ctypes
import os
from pathlib import Path

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
tree = ast.parse(Path(__file__).with_name('sdl_hub_defaults_native_test.py').read_text())
cases = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'cases' for t in n.targets))
args = {name: params for _, _, name, params in cases}
args.update(jigsaw=(3, 1, 1, 1, 23), go=(1, 1, 23), scrabble=(1, 1, 1, 1, 17), crossword=(1, 1, 1, 1, 23))
names = ('reflex', 'pursuit', 'jigsaw', 'go', 'ncup_monte', 'tracking', 'two_hands', 'scrabble', 'scrabble', 'crossword')
def bind(name, count):
    fn = getattr(lib, name); fn.argtypes = [ctypes.c_int64] * count; fn.restype = ctypes.c_int64; return fn
dispatch = lib.nw_sdl_dispatch_pointer
dispatch.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32, ctypes.c_int64]
normalize = lib.nw_sdl_normalize_pointer
normalize.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64)]
normalize.restype = ctypes.c_int64
for task, name in enumerate(names):
    create, destroy = bind('nw_' + name + '_create', len(args[name])), bind('nw_' + name + '_destroy', 1)
    action, info = bind('nw_' + name + '_action', 4), bind('nw_' + name + '_info', 2)
    pointer_count = (4, 3, 6, 6, 4, 4, 5, 8, 8, 7)[task]
    pointer = bind('nw_' + name + '_pointer', pointer_count)
    direct, migrated = create(*args[name]), create(*args[name])
    assert direct > 0 and migrated > 0, name
    try:
        if task < 7:
            action(direct, 0, 0, 100); action(migrated, 0, 0, 100)
        for x, y, right in ((0, 0, 0), (456, 342, 1), (800, 600, 0)):
            nx, ny = ctypes.c_int64(), ctypes.c_int64()
            assert normalize(x, y, 912, 684, ctypes.byref(nx), ctypes.byref(ny))
            if task in (0, 4, 5): pointer(direct, nx.value, ny.value, 200)
            elif task == 1: pointer(direct, nx.value, ny.value)
            elif task in (2, 3): pointer(direct, nx.value, ny.value, 912, 684, 200)
            elif task == 6: pointer(direct, nx.value, ny.value, 0, 200)
            elif task in (7, 8):
                phase = info(direct, 0)
                pointer(direct, nx.value, ny.value, 912, 684, 2 if right and task == 7 else 0, int(task == 8), 200)
                if task == 7 and phase != 1 and info(direct, 0) == 1: action(direct, 10, 0, 200)
            else: pointer(direct, nx.value, ny.value, 912, 684, 2 if right else 0, 200)
            dispatch(task, migrated, x, y, 912, 684, right)
            for field in range(24 if task == 6 else 6): assert info(direct, field) == info(migrated, field), (name, task, x, y, field)
        before = [info(migrated, f) for f in range(6)]
        dispatch(task, migrated, 1, 1, 0, 684, 0)
        assert before == [info(migrated, f) for f in range(6)]
    finally:
        destroy(direct); destroy(migrated)
print('SDL pointer dispatch: ten event routes match direct controller calls')
