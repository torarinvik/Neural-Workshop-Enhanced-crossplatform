#!/usr/bin/env python3
"""Verify SDL controller and results-manager shutdown using real native objects."""
import ast
import ctypes
import os
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent
def assignment(file, variable):
    tree = ast.parse((root / file).read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets))
cases = assignment('sdl_hub_defaults_native_test.py', 'cases')
names = assignment('sdl_frame_dispatch_native_test.py', 'names') + ('syllogism', 'scramble', 'scrabble')
args = {name: values for _, _, name, values in cases}
args.update(algebra=(1, 1, 23), numberology=(1, 1, 1, 23), jigsaw=(3, 1, 1, 1, 23),
            sudoku=(1, 1, 1, 1, 23), go=(1, 1, 23), crossword=(1, 1, 1, 1, 23),
            crossed_wires=(1, 1, 1, 1, 23), syllogism=(1, 1, 1, 0, 1, 17),
            scramble=(1, 1, 1, 1, 17), scrabble=(1, 1, 1, 1, 17))
lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
def bind(name, argtypes):
    fn = getattr(lib, name); fn.argtypes = argtypes; fn.restype = ctypes.c_int64; return fn
shutdown = lib.nw_sdl_shutdown
shutdown.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
shutdown.restype = None
handles = (ctypes.c_int64 * 100)()
syll, number = (ctypes.c_size_t * 2)(), (ctypes.c_size_t * 2)()
for i, name in enumerate(names):
    create = bind('nw_' + name + '_create', [ctypes.c_int64] * len(args[name]))
    handles[i] = create(*args[name]); assert handles[i] > 0, name
    shutdown(handles, syll, number)
    assert not any(handles) and not any(syll) and not any(number), name
    shutdown(handles, syll, number)
with tempfile.TemporaryDirectory() as tmp:
    old = {key: os.environ.get(key) for key in ('NW_SYLLOGISM_RESULTS_DIR', 'NW_NUMBEROLOGY_RESULTS_DIR')}
    os.environ['NW_SYLLOGISM_RESULTS_DIR'] = str(Path(tmp) / 'syllogism')
    os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(Path(tmp) / 'numberology')
    try:
        options = (ctypes.c_int64 * 5)(1, 1, 1, 0, 1)
        start_syll = lib.nw_syllogism_results_start
        start_syll.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_int64)]
        start_number = lib.nw_numberology_results_start
        start_number.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int64, ctypes.c_int64, ctypes.c_int32]
        start_syll(syll, options); start_number(number, 1, 1, 1)
        assert syll[0] and number[0]
        judge_syll = lib.nw_syllogism_results_judge
        judge_syll.argtypes = [ctypes.POINTER(ctypes.c_size_t)] + [ctypes.c_int64] * 4
        judge_number = lib.nw_numberology_results_judge
        judge_number.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int64, ctypes.c_int64, ctypes.c_int32]
        judge_syll(syll, 1, 1, 1, 500); judge_number(number, 1, 1, 1)
        shutdown(handles, syll, number)
        assert not any(syll) and not any(number)
        assert list((Path(tmp) / 'syllogism').glob('*.json'))
        assert list((Path(tmp) / 'numberology').glob('*.json'))
    finally:
        for key, value in old.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
print('SDL shutdown: 37 controllers and both result managers close safely')
