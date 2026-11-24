#!/usr/bin/env python3
"""Exercise Python result persistence with the real SDL native controller ABI."""
import ctypes
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app

library = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
def bind(name, count):
    function = getattr(library, 'nw_' + name)
    function.argtypes = [ctypes.c_int64] * count
    function.restype = ctypes.c_int64
    return function

class Core:
    syllogism_create = staticmethod(bind('syllogism_create', 6))
    syllogism_action = staticmethod(bind('syllogism_action', 4))
    syllogism_info = staticmethod(bind('syllogism_info', 2))
    syllogism_value = staticmethod(bind('syllogism_value', 3))
    syllogism_destroy = staticmethod(bind('syllogism_destroy', 1))

fixture = json.loads((root / 'test/syllogism_session_oracle.json').read_text())[0]['rows'][0]
args = SimpleNamespace(seed=17, black_background=False, syllogism_level=1, syllogism_trials=1,
                       syllogism_no_working=False, syllogism_no_adaptive=True, syllogism_invented_words=False)
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    os.environ['NW_SYLLOGISM_SETTINGS_PATH'] = str(directory / 'settings')
    os.environ['NW_SYLLOGISM_RESULTS_DIR'] = str(directory / 'results')
    session = app.SyllogismSession(Core(), args)
    with patch('app.time.monotonic', side_effect=[1.0, 2.75, 3.0]):
        session.action(0)
        session.action(6, fixture['answer'])
        session.action(0)
    session.close()
    files = list((directory / 'results').glob('*.json'))
    assert len(files) == 1
    record = json.loads(files[0].read_text())
    assert record['task'] == 'syllogism' and record['completed'] and record['right'] == 1
    assert record['best_level'] == 1 and record['seconds'] == 1
    assert record['options'] == [1, 1, 1, 0, 1]
    assert [(row['trial'], row['level'], row['correct'], row['elapsed_ms']) for row in record['results']] == [(1, 1, True, 1750)]
    assert not list((directory / 'results').glob('*.tmp'))
print('Syllogism Python host: real native controller writes a completed source-derived result')
