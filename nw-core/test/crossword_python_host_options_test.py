#!/usr/bin/env python3
"""Exercise the Python Crossword adapter with the actual native controller."""
import sys
import os
import subprocess
import ast
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
core = app.load_core('crossword_create')
args = SimpleNamespace(crossword_level=2, crossword_trials=3,
    crossword_no_mistakes=False, crossword_no_adaptive=False,
    crossword_lexicon=None, seed=17, black_background=False)
names = ('ESCAPE', 'RETURN', 'SPACE', 'LEFT', 'RIGHT', 'UP', 'DOWN', 'TAB', 'BACKSPACE', 'DELETE',
         *'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
key = SimpleNamespace(**{name: i + 100 for i, name in enumerate(names)})
with tempfile.TemporaryDirectory() as directory:
    os.environ['NW_CROSSWORD_SETTINGS_PATH'] = str(Path(directory) / 'settings')
    missing = Path(directory) / 'missing.tsv'
    args.crossword_lexicon = str(missing)
    try:
        app.CrosswordSession(core, args)
        raise AssertionError('explicit missing lexicon must fail')
    except SystemExit as error:
        assert 'Cannot load Crossword lexicon' in str(error)
    index = Path(directory) / 'lexicon.tsv'
    index.write_text('ace\t1\tA clue\nact\t2\tAnother clue\n', encoding='utf-8')
    args.crossword_lexicon = str(index)
    session = app.CrosswordSession(core, args)
    assert session.state[1:4] == (2, 0, 3)
    assert session.state[12:15] == (1, 1, 1)
    assert session.frame_bytes(core)
    session.key(key.O, key)
    from renderer import decode
    from display_decode import canonical
    labels = " ".join(canonical(decode(session.frame_bytes(core))))
    assert "Crossword options" in labels and "Grids per run" in labels
    session.key(key.RIGHT, key)
    session.key(key.ESCAPE, key)
    assert session.state[1] == 2 and session.options[0] == 2
    session.key(key.O, key)
    session.key(key.RIGHT, key)
    session.key(key.DOWN, key)
    session.key(key.RIGHT, key)
    session.key(key.DOWN, key)
    session.key(key.SPACE, key)
    session.key(key.DOWN, key)
    session.key(key.SPACE, key)
    session.key(key.RETURN, key)
    assert session.state[1:4] == (3, 0, 5) and session.state[13:15] == (0, 0)
    assert (args.crossword_level, args.crossword_trials) == (3, 5)
    assert app.read_crossword_settings() == (3, 5, 0, 0)
    result = subprocess.run([sys.executable, str(root / 'shells/python/app.py'), '--screen', 'crossword',
                             '--dump', '--crossword-level', '4', '--crossword-lexicon', str(index)],
                            cwd=root, text=True, capture_output=True, check=True)
    state = ast.literal_eval(re.search(r'^# state=(\([^\n]+\)) bytes=', result.stdout, re.M).group(1))
    assert state[1] == 4 and state[3] == 5 and state[13:15] == (0, 0)
    session.key(key.SPACE, key)
    assert session.state[0] in (1, 3)  # A tiny valid index may not fill a grid.
    session.close()
    session.close()
    hub = app.TaskHubSession(core, args)
    hub.category, hub.selected = 4, 6
    hub.key(key.RETURN, key)
    child = hub.child
    hub.key(key.O, key)
    assert child.options_draft is not None
    hub.key(key.ESCAPE, key)
    assert hub.child is child and child.options_draft is None
    hub.key(key.ESCAPE, key)
    assert hub.child is None
    index.write_text('broken index', encoding='utf-8')
    try:
        app.CrosswordSession(core, args)
        raise AssertionError('invalid index must fail')
    except SystemExit as error:
        assert 'invalid' in str(error)
os.environ['NW_CROSSWORD_SETTINGS_PATH'] = str(Path(tempfile.gettempdir()) / 'unused-crossword-test-settings')
class KeyCore:
    def __init__(self):
        self.actions = []
    def crossword_create(self, *args): return 1
    def crossword_info(self, handle, field): return 1 if field == 0 else 0
    def crossword_action(self, handle, action, value, now):
        self.actions.append((action, value))
    def crossword_destroy(self, handle): return 0

args.crossword_lexicon = None
fake = KeyCore()
# Avoid automatically loading a host-specific index in this key-map check.
original_home = app.Path.home
app.Path.home = classmethod(lambda cls: Path('/nonexistent-crossword-test-home'))
try:
    keys = app.CrosswordSession(fake, args)
    keys.key(key.A, key)
    keys.key(key.O, key)
    keys.key(key.TAB, key)
    keys.key(key.BACKSPACE, key)
    assert fake.actions == [(7, 0), (7, 14), (6, 0), (8, 0)]
    keys.close()
finally:
    app.Path.home = original_home
print('crossword_python_host_options_test: PASS (options, index loading, frame, lifecycle)')
