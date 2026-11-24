#!/usr/bin/env python3
"""Headless Syllogism result persistence, retries and lifecycle."""
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
    def __init__(self): self.phase = 0; self.rows = []; self.destroyed = []
    def syllogism_create(self, *args): self.phase = 0; self.rows = []; return 1
    def syllogism_destroy(self, handle): self.destroyed.append(handle); return 0
    def syllogism_info(self, handle, field):
        return {0: self.phase, 8: sum(row[1] for row in self.rows), 9: 3,
                14: sum(row[2] for row in self.rows) // 1000, 15: len(self.rows)}.get(field, 0)
    def syllogism_value(self, handle, field, at): return self.rows[at][field - 2]
    def syllogism_action(self, handle, action, value, now):
        if action == 0 and self.phase in (0, 3): self.phase = 1; self.rows = []
        elif action in (1, 6) and self.phase == 1: self.rows.append((3, int(value == 0), 1250)); self.phase = 2
        elif action == 0 and self.phase == 2: self.phase = 3
        return 1

args = SimpleNamespace(seed=17, black_background=False, syllogism_level=3, syllogism_trials=1,
                       syllogism_no_working=None, syllogism_no_adaptive=True, syllogism_invented_words=None)
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    os.environ['NW_SYLLOGISM_SETTINGS_PATH'] = str(directory / 'settings')
    os.environ['NW_SYLLOGISM_RESULTS_DIR'] = str(directory / 'results')
    core = Core(); session = app.SyllogismSession(core, args)
    session.action(0)
    with patch('app.os.replace', side_effect=OSError('unavailable')):
        session.action(6, 0)
        session.action(0)
        session.action(0)
        assert len(session.failed_results) == 1
        assert not list((directory / 'results').glob('*.json'))
    session.action(6, 1)
    rows = [json.loads(path.read_text()) for path in (directory / 'results').glob('*.json')]
    assert len(rows) == 2
    completed = next(row for row in rows if row['completed'])
    partial = next(row for row in rows if not row['completed'])
    assert completed['right'] == 1 and completed['best_level'] == 3 and completed['seconds'] == 1
    assert completed['results'][0]['level'] == 3 and completed['results'][0]['elapsed_ms'] == 1250
    assert partial['results'][0]['correct'] is False
    session.action(6, 0)  # ignored while judged
    assert len(session.result_record['results']) == 1
    session.close()
    assert core.destroyed == [1]
    assert len(list((directory / 'results').glob('*.json'))) == 2
    assert not list((directory / 'results').glob('*.tmp'))
print('Syllogism Python results: retry, unique sessions, completion and disposal pass')
