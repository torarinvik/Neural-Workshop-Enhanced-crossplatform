#!/usr/bin/env python3
"""Headless tests for Numberology pointer targets and letterboxing."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app

assert app.numberology_page_at(265,365) == 4
assert app.numberology_page_at(647,365) == 5
assert app.numberology_page_at(456,365) == 0
assert app.numberology_page_at(265,400) == 0
class Core:
    def __init__(self): self.actions = []; self.phase = 2; self.pages = 2
    def numberology_create(self, *args): return 1
    def numberology_info(self, handle, field): return self.phase if field == 0 else self.pages if field == 22 else 0
    def numberology_action(self, handle, action, value, now): self.actions.append(action)
    def numberology_destroy(self, handle): return 0
args = SimpleNamespace(seed=19, black_background=False, numberology_level=1,
                       numberology_trials=1, numberology_no_adaptive=True)
core = Core()
with patch.object(app, 'read_numberology_settings', return_value=(1,1,0)):
    session = app.NumberologySession(core, args)
    session.pointer(265+144,365,1200,684)
    session.pointer(647+144,365,1200,684)
    assert core.actions == [4,5], core.actions
    core.phase = 1
    session.pointer(265+144,365,1200,684)
    assert core.actions == [4,5,4]
    keys = SimpleNamespace(O=1, PAGEUP=2, PAGEDOWN=3, SPACE=4, RETURN=5, BACKSPACE=6, DELETE=7)
    session.key(keys.PAGEUP, keys)
    session.key(keys.PAGEDOWN, keys)
    assert core.actions == [4,5,4,4,5]
    core.phase = 2; core.pages = 1
    session.pointer(265+144,365,1200,684)
    assert core.actions[-1] == 0, 'single-page judgment advances normally'
    session.close()
print('Numberology Python paging targets and letterboxing pass')
