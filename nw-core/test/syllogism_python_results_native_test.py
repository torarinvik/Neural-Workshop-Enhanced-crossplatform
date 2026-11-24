#!/usr/bin/env python3
"""Exercise Python result persistence with the built Python extension."""
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

core = app.load_core('syllogism_create')

fixture = json.loads((root / 'test/syllogism_session_oracle.json').read_text())[0]['rows'][0]
args = SimpleNamespace(seed=17, black_background=False, syllogism_level=1, syllogism_trials=1,
                       syllogism_no_working=False, syllogism_no_adaptive=True, syllogism_invented_words=False)
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    os.environ['NW_SYLLOGISM_SETTINGS_PATH'] = str(directory / 'settings')
    os.environ['NW_SYLLOGISM_RESULTS_DIR'] = str(directory / 'results')
    session = app.SyllogismSession(core, args)
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
