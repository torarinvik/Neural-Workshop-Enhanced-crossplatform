#!/usr/bin/env python3
"""Compare Elisa SDL key dispatch to the direct native controller ABI."""
import ast
import ctypes
import os
from pathlib import Path

lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
tree = ast.parse(Path(__file__).with_name('sdl_hub_defaults_native_test.py').read_text())
cases = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'cases' for t in n.targets))
args = {name: params for _, _, name, params in cases}
args.update(jigsaw=(3, 1, 1, 1, 23), sudoku=(1, 1, 1, 1, 23), crossed_wires=(1, 1, 1, 1, 23), go=(1, 1, 23))
names = ('count', 'mr_time', 'graph_mapping', 'matrix_reasoning', 'in_the_dark', 'removals',
         'custody', 'concentration', 'recognition', 'trivia', 'reflex', 'nback3d', 'fog',
         'tetris', 'you_are_here', 'sokoban', 'monkey_ladder', 'jigsaw', 'sudoku', 'go',
         'ncup_monte', 'tracking', 'lookout', 'pursuit', 'out_of_sight', 'buzz_wire',
         'donkey', 'two_hands', 'overrun', 'crossed_wires', None, None, 'marble')
def bind(name, count):
    f = getattr(lib, name); f.argtypes = [ctypes.c_int64] * count; f.restype = ctypes.c_int64; return f
mapper = lib.nw_sdl_task_key
mapper.argtypes = [ctypes.c_int64] * 5 + [ctypes.POINTER(ctypes.c_int64)]
mapper.restype = ctypes.c_int64
dispatch = lib.nw_sdl_dispatch_task_key
dispatch.argtypes = [ctypes.c_int64] * 3
phase_ids = {0, 1, 2, 3, 7, 8, 9, 16, 17, 18, 19, 32, *range(20, 30)}
for task, name in enumerate(names):
    if name is None: continue
    create, destroy = bind('nw_' + name + '_create', len(args[name])), bind('nw_' + name + '_destroy', 1)
    action_count = 2 if task in (12, 13) else 3 if task in (2, 9, 14, 15) else 4
    action = bind('nw_' + name + '_action', action_count)
    info = None if task == 13 else bind('nw_' + name + '_info', 2)
    frame = bind('nw_' + name + '_frame_write', 6)
    direct, migrated = create(*args[name]), create(*args[name])
    assert direct > 0 and migrated > 0, name
    try:
        for key in (32, 0x40000050, ord('1'), ord('j'), 13):
            phase = info(direct, 0) if task in phase_ids else 0
            cursor = info(direct, 9) if task == 7 else 0
            count = info(direct, 2 if task == 7 else 5 if task == 18 else 4) if task in (7, 18, 29) else 0
            if task == 19 and phase == 1 and key in (32, 13):
                cursor = info(direct, 6) * info(direct, 4) + info(direct, 5)
            value = ctypes.c_int64()
            mapped = mapper(task, key, phase, cursor, count, ctypes.byref(value))
            if mapped >= 0:
                if task in (12, 13): action(direct, mapped)
                elif task == 9: action(direct, mapped, value.value)
                elif task in (2, 14, 15): action(direct, mapped, 200)
                elif task == 32: action(direct, mapped, value.value, 0)
                else: action(direct, mapped, value.value, 200)
            dispatch(task, migrated, key)
            if info:
                for field in range(6): assert info(direct, field) == info(migrated, field), (name, key, field)
            else:
                first, second = ctypes.create_string_buffer(1048576), ctypes.create_string_buffer(1048576)
                a = frame(ctypes.addressof(first), len(first), direct, 0, 912, 684)
                b = frame(ctypes.addressof(second), len(second), migrated, 0, 912, 684)
                assert a == b and first.raw[:a] == second.raw[:b], (name, key)
    finally:
        destroy(direct); destroy(migrated)
release = lib.nw_sdl_dispatch_key_release
release.argtypes = [ctypes.c_int64] * 3
for task, name in ((25, 'buzz_wire'), (33, 'marble')):
    create = bind('nw_' + name + '_create', len(args[name]))
    destroy, info = bind('nw_' + name + '_destroy', 1), bind('nw_' + name + '_info', 2)
    direct, migrated = create(*args[name]), create(*args[name])
    assert direct > 0 and migrated > 0
    try:
        for key, port in ((0x40000052, 0 if task == 25 else 4), (0x40000050, 2 if task == 25 else 3)):
            if task == 25: bind('nw_buzz_wire_action', 4)(direct, 2, port, 200)
            else: bind('nw_marble_release', 2)(direct, port)
            release(task, migrated, key)
            for field in range(6): assert info(direct, field) == info(migrated, field), (name, key, field)
    finally:
        destroy(direct); destroy(migrated)
group_dispatch = lib.nw_sdl_dispatch_key_group
group_dispatch.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.c_int64, ctypes.c_int64]
group_dispatch.restype = ctypes.c_int64
groups = ((14, 15, 16, 11), (13, 0, 1, 2, 3, 4, 12, 5, 6, 7, 8, 9, 10),
          (17, 18), (29, 20, 21, 22, 23, 24, 25, 26, 27, 28))
active = (ctypes.c_int64 * 30)()
for group, tasks in enumerate(groups):
    assert group_dispatch(active, group, 32) == 0
    for task in tasks:
        name = names[task]
        create, destroy = bind('nw_' + name + '_create', len(args[name])), bind('nw_' + name + '_destroy', 1)
        direct, migrated = create(*args[name]), create(*args[name])
        assert direct > 0 and migrated > 0
        try:
            active[task] = migrated
            assert group_dispatch(active, group, 32) == 1
            dispatch(task, direct, 32)
            if task != 13:
                info = bind('nw_' + name + '_info', 2)
                for field in range(6): assert info(direct, field) == info(migrated, field), (name, field)
            assert group_dispatch(active, group, 0) == 1  # ignored key still consumes the event
        finally:
            active[task] = 0
            destroy(direct); destroy(migrated)
maze = bind('nw_you_are_here_create', len(args['you_are_here']))(*args['you_are_here'])
sokoban = bind('nw_sokoban_create', len(args['sokoban']))(*args['sokoban'])
assert maze > 0 and sokoban > 0
try:
    active[14], active[15] = maze, sokoban
    before = bind('nw_sokoban_info', 2)(sokoban, 0)
    assert group_dispatch(active, 0, 32) == 1
    assert bind('nw_sokoban_info', 2)(sokoban, 0) == before
finally:
    active[14] = active[15] = 0
    bind('nw_you_are_here_destroy', 1)(maze)
    bind('nw_sokoban_destroy', 1)(sokoban)
assert group_dispatch(None, 0, 32) == 0 and group_dispatch(active, 99, 32) == 0
print('SDL key dispatch: 31 press routes, grouped dispatch, and release paths pass')
