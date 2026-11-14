#!/usr/bin/env python3
"""Persist a real native Numberology session without opening a window."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app

core = app.load_core('numberology_value')
fixtures = json.loads((root / 'test/numberology_exact_oracle.json').read_text())
answer = next(case['answer'] for case in fixtures if case['level'] == 1 and case['seed'] == 19)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = str(Path(tmp) / 'settings')
    os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(Path(tmp) / 'results')
    args = SimpleNamespace(seed=19, black_background=False, numberology_level=1,
                           numberology_trials=1, numberology_no_adaptive=True)
    session = app.NumberologySession(core, args)
    session.action(0)
    session.text(answer)
    session.action(3)
    files = list(Path(os.environ['NW_NUMBEROLOGY_RESULTS_DIR']).glob('*.json'))
    assert len(files) == 1
    assert json.loads(files[0].read_text())['results'][0]['correct']
    session.action(0)
    session.close()
    record = json.loads(files[0].read_text())
    assert record['completed'] and record['right'] == 1 and len(record['results']) == 1
print('Numberology Python results: real native run persists and reopens')
