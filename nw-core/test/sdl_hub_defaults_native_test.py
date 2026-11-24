#!/usr/bin/env python3
"""Compare task-hub default constructors to the existing native ABI."""
import ctypes
import os

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
hub = lib.nw_sdl_hub_create
hub.argtypes = [ctypes.c_int64, ctypes.c_int64]
hub.restype = ctypes.c_int64
hub_destroy = lib.nw_sdl_hub_destroy
hub_destroy.argtypes = [ctypes.c_int64] * 3
hub_destroy.restype = ctypes.c_int64
cases = [
    (5, 4, 'you_are_here', (1, 1, 0, 1, 17)),
    (5, 2, 'sokoban', (1, 1, 0, 1, 17)),
    (0, 1, 'monkey_ladder', (5, 2, 1, 300, 120, 1, 17)),
    (0, 0, 'nback3d', (2, 3, 20, 3000, 500, 200, 17)),
    (2, 10, 'marble', (1, 1, 0, 2600, 15000, 17)),
    (5, 6, 'tetris', (1, 25, 5, 17)),
    (3, 0, 'count', (0, 8, 5, 200, 1, 1, 23)),
    (3, 1, 'mr_time', (0, 1, 5, 3000, 400, 1, 23)),
    (4, 0, 'graph_mapping', (4, 0, 5, 3000, 1, 0, 23)),
    (4, 1, 'matrix_reasoning', (1, 5, 0, 1, 1, 1, 23)),
    (0, 2, 'in_the_dark', (1, 1, 1000, 1, 23)),
    (0, 3, 'fog', (2, 100, 1, 1, 23)),
    (0, 4, 'removals', (1, 1, 1000, 1, 23)),
    (0, 5, 'custody', (1, 1, 900, 1200, 1, 23)),
    (1, 0, 'concentration', (8, 0, 0, 900, 1, 0, 23)),
    (1, 1, 'recognition', (40, 0, 40, 4, 0, 1, 23)),
    (1, 2, 'trivia', (1, 1, 1, 1, 23)),
    (2, 0, 'reflex', (10, 1200, 400, 3, 100, 1, 23)),
    (2, 1, 'ncup_monte', (3, 10, 1, 4, 160, 750, 23)),
    (2, 2, 'tracking', (8, 2, 3, 30, 5, 1, 23)),
    (2, 3, 'lookout', (8, 2, 30, 1200, 10, 1, 23)),
    (2, 4, 'pursuit', (20, 40, 400, 90, 16, 0, 23)),
    (2, 6, 'out_of_sight', (8, 2, 30, 1200, 2, 460, 23)),
    (2, 5, 'buzz_wire', (1, 1, 1, 1, 1, 1, 23)),
    (2, 7, 'donkey', (1, 1, 180, 400, 1, 0, 23)),
    (2, 8, 'two_hands', (3, 1, 400, 1200, 1, 0, 23)),
    (2, 9, 'overrun', (1, 3, 1, 0, 0, 0, 23)),
]
for category, selected, name, args in cases:
    create = getattr(lib, 'nw_' + name + '_create')
    create.argtypes = [ctypes.c_int64] * len(args)
    create.restype = ctypes.c_int64
    destroy = getattr(lib, 'nw_' + name + '_destroy')
    destroy.argtypes = [ctypes.c_int64]
    destroy.restype = ctypes.c_int64
    original, migrated = create(*args), hub(category, selected)
    assert original > 0 and migrated > 0, (name, original, migrated)
    try:
        if name != 'tetris':
            info = getattr(lib, 'nw_' + name + '_info')
            info.argtypes = [ctypes.c_int64, ctypes.c_int64]
            info.restype = ctypes.c_int64
            for field in range(6):
                assert info(original, field) == info(migrated, field), (name, field)
    finally:
        destroy(original)
        assert hub_destroy(category, selected, migrated) == 0
assert hub(-1, 0) == 0 and hub(6, 0) == 0 and hub(4, 9) == 0
assert hub_destroy(-1, 0, 0) == -1
print('SDL task hub: 27 default controllers match direct native construction')
