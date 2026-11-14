#!/usr/bin/env python3
"""Headless Python Numberology result persistence and retry."""
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

class Core:
    def __init__(self): self.fields = [0, 1, 0, 1, 4, -1, 0, 0, -1, 1, 0, 1, 1, 1]
    def numberology_create(self, *args): return 1
    def numberology_destroy(self, handle): return 0
    def numberology_info(self, handle, field): return self.fields[field]
    def numberology_action(self, handle, action, value, now):
        if action == 0 and self.fields[0] in (0, 3): self.fields[0], self.fields[2] = 1, 1
        elif action == 3 and self.fields[0] == 1: self.fields[0], self.fields[8], self.fields[10] = 2, 1, 1
        elif action == 0 and self.fields[0] == 2: self.fields[0], self.fields[13] = 3, 2
        return 1

with tempfile.TemporaryDirectory() as tmp:
    os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = str(Path(tmp) / 'settings')
    os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(Path(tmp) / 'results')
    args = SimpleNamespace(seed=19, black_background=False, numberology_level=None,
                           numberology_trials=1, numberology_no_adaptive=None)
    session = app.NumberologySession(Core(), args)
    session.action(0)
    with patch.object(app, 'write_numberology_result', return_value=False):
        session.action(3)
    assert session.result_pending and not Path(os.environ['NW_NUMBEROLOGY_RESULTS_DIR']).exists()
    session.action(0)
    files = list(Path(os.environ['NW_NUMBEROLOGY_RESULTS_DIR']).glob('*.json'))
    assert len(files) == 1
    record = json.loads(files[0].read_text())
    assert record['completed'] and record['right'] == 1
    assert [(row['trial'], row['level'], row['correct']) for row in record['results']] == [(1, '1', True)]
    session.action(3)
    assert len(list(Path(os.environ['NW_NUMBEROLOGY_RESULTS_DIR']).glob('*.json'))) == 1
    with patch.object(app.os, 'replace', side_effect=OSError('unavailable')):
        assert not app.write_numberology_result({**record, 'right': 999})
    assert json.loads(files[0].read_text()) == record, 'failed replacement preserves the committed record'
    session.close()
    assert json.loads(files[0].read_text()) == record
    partial = app.NumberologySession(Core(), args)
    partial.action(0)
    partial.action(3)
    partial.close()
    saved = [json.loads(path.read_text()) for path in Path(os.environ['NW_NUMBEROLOGY_RESULTS_DIR']).glob('*.json')]
    assert len(saved) == 2 and sum(not item['completed'] for item in saved) == 1
    pending = app.NumberologySession(Core(), args)
    pending.action(0)
    with patch.object(app, 'write_numberology_result', return_value=False):
        pending.action(3)
        pending.action(0)
        pending.action(0)  # start the next run while the prior save is unavailable
    assert len(pending.failed_results) == 1
    pending.action(3)
    pending.close()
    saved = [json.loads(path.read_text()) for path in Path(os.environ['NW_NUMBEROLOGY_RESULTS_DIR']).glob('*.json')]
    assert len(saved) == 4, 'the previous session is retried after the next begins'


print('Numberology Python results: retry, atomic session record and disposal pass')
