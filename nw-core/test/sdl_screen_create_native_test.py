#!/usr/bin/env python3
"""Compare all SDL direct-screen constructors with their prior ABI calls."""
import ast
import ctypes
import os
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent
def literal(file, name):
    tree = ast.parse((root / file).read_text())
    return next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
cases = literal('sdl_hub_defaults_native_test.py', 'cases')
frames = literal('sdl_frame_dispatch_native_test.py', 'names') + ('syllogism', 'scramble', 'scrabble')
args = {name: params for _, _, name, params in cases}
names = ('you_are_here', 'sokoban', 'monkey_ladder', 'nback3d', 'marble', 'tetris',
         'count', 'mr_time', 'graph_mapping', 'matrix_reasoning', 'in_the_dark', 'fog',
         'removals', 'custody', 'concentration', 'recognition', 'trivia', 'reflex',
         'algebra', 'syllogism', 'numberology', 'jigsaw', 'sudoku', 'go', 'crossed_wires',
         'scrabble', 'scramble', 'crossword', 'ncup_monte', 'tracking', 'lookout',
         'pursuit', 'out_of_sight', 'buzz_wire', 'donkey', 'two_hands', 'overrun')
args.update(algebra=(3, 3, 0, 0, 23), syllogism=(3, 3, 0, 1, 0, 23), numberology=(5, 3, 1, 23),
            jigsaw=(4, 3, 1, 0, 1, 23), sudoku=(4, 3, 0, 1, 23), go=(2, 3, 23),
            crossed_wires=(4, 5, 0, 1, 23), scrabble=(2, 3, 0, 1, 23),
            scramble=(2, 3, 0, 1, 17), crossword=(2, 3, 0, 1, 23))
options = (ctypes.c_int64 * 39)(4,3,1,0,1, 4,3,0,1, 2,3, 4,5,0,1,
                              2,3,0,1, 2,3,0,1, 3,3,0,0, 5,3,1,
                              2,3,0,1, 3,3,0,1,0)
lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
def bind(name, count):
    fn = getattr(lib, name); fn.argtypes = [ctypes.c_int64] * count; fn.restype = ctypes.c_int64; return fn
create_screen = lib.nw_sdl_screen_create
create_screen.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64), ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
create_screen.restype = ctypes.c_int64
shutdown = lib.nw_sdl_shutdown
shutdown.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
handles, syll, number = (ctypes.c_int64 * 100)(), (ctypes.c_size_t * 2)(), (ctypes.c_size_t * 2)()
with tempfile.TemporaryDirectory() as directory:
    key = 'APPDATA' if os.name == 'nt' else 'HOME'
    old = os.environ.get(key); os.environ[key] = directory
    try:
        assert create_screen(0, options, None, None, None) == 0
        assert create_screen(1, options, None, None, None) == 0
        assert create_screen(39, options, None, None, None) == 0
        assert create_screen(2, None, None, None, None) == 0
        for screen, name in enumerate(names, 2):
            create_name = 'nw_' + name + ('_create_options' if name in ('algebra', 'jigsaw') else '_create')
            direct = bind(create_name, len(args[name]))(*args[name])
            migrated = create_screen(screen, options, None, None, None)
            assert direct > 0 and migrated > 0, (screen, name, direct, migrated)
            try:
                if name != 'tetris':
                    info = bind('nw_' + name + '_info', 2)
                    for field in range(6): assert info(direct, field) == info(migrated, field), (name, field)
            finally:
                bind('nw_' + name + '_destroy', 1)(direct)
                handles[frames.index(name)] = migrated
                shutdown(handles, syll, number)
                assert not any(handles)
        for screen in (27, 28, 29):
            missing = os.fsencode(Path(directory) / 'missing')
            assert create_screen(screen, options, missing if screen != 28 else None,
                                 missing if screen == 28 else None, None) == 0
    finally:
        if old is None: os.environ.pop(key, None)
        else: os.environ[key] = old
print('SDL screen creation: 37 routes match direct constructors and reject missing explicit corpora')
