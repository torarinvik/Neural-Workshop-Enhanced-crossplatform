#!/usr/bin/env python3
"""Exercise the native Scramble controller and Python task-menu adapter."""
import json
import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
core = app.load_core('scramble_create')
source = json.loads(subprocess.check_output([sys.executable, str(root / 'test/scramble_seed_oracle.py')], text=True))
args = SimpleNamespace(seed=17, black_background=False, scramble_level=1, scramble_trials=1,
                       scramble_no_count=False, scramble_no_adaptive=False)
keys = SimpleNamespace(SPACE=1, RETURN=2, NUM_ENTER=3, BACKSPACE=4, DELETE=5, ESCAPE=6, C=7, LEFT=8, RIGHT=9, UP=10, DOWN=11, O=12)
with patch.object(app.sys, 'platform', 'darwin'), patch('shutil.which', return_value='/usr/bin/pbpaste'), \
        patch('subprocess.run', return_value=SimpleNamespace(stdout='pasted\ntext')) as process:
    assert app.read_scramble_clipboard() == 'pasted\ntext'
    assert process.call_args.args[0] == ('pbpaste',)
temporary = tempfile.TemporaryDirectory()
os.environ['HOME'] = temporary.name
os.environ['NW_SCRAMBLE_SETTINGS_PATH'] = str(Path(temporary.name) / 'options')
s = app.ScrambleSession(core, args)
s.key(keys.SPACE, keys)
s.text(' ')
assert s.state[0] == 1 and s.state[5] == 0
assert core.scramble_action(s.handle, 5, 0, 0) == 2, 'host already synchronized the start clock'
shown = ''.join(' ' if v == 26 else chr(97 + v) for v in
                (core.scramble_value(s.handle, 0, i) for i in range(s.state[4])))
assert shown == source[0]['shown']
with patch.object(app, 'read_scramble_clipboard', return_value=source[0]['answer'].upper().replace(' ', '\n')) as clipboard:
    s.paste()
    clipboard.assert_called_once()
s.text('x')
s.key(keys.BACKSPACE, keys)
s.key(keys.RETURN, keys)
assert (s.state[0], s.state[6], s.state[7], s.state[1]) == (2, 1, 1, 2)
assert s.frame_bytes(core).startswith(b'NKIN')
s.key(keys.SPACE, keys)
assert s.state[0] == 3
s.key(keys.O, keys)
with patch.object(app, 'read_scramble_clipboard') as clipboard:
    s.paste()
    clipboard.assert_not_called()
from renderer import decode
from display_decode import canonical
assert 'Scramble options' in ' '.join(canonical(decode(s.frame_bytes(core))))
s.key(keys.RIGHT, keys)
s.key(keys.ESCAPE, keys)
assert s.state[0] == 3 and s.options == [1, 1, 1, 1]
s.key(keys.O, keys)
s.key(keys.RIGHT, keys)
s.key(keys.RETURN, keys)
assert (s.state[0], s.state[1], s.state[3]) == (0, 2, 1)
assert app.read_scramble_settings() == (2, 1, 1, 1)
dump = subprocess.run([sys.executable, str(root / 'shells/python/app.py'), '--screen', 'scramble',
                       '--scramble-level', '4', '--dump'], cwd=root, capture_output=True, text=True, check=True)
dump_state = ast.literal_eval(re.search(r'^# state=(\([^\n]+\)) bytes=', dump.stdout, re.M).group(1))
assert (dump_state[1], dump_state[3], dump_state[11], dump_state[12]) == (4, 1, 1, 1)
s.key(keys.SPACE, keys)
assert (s.state[0], s.state[1], s.state[2], s.state[7]) == (1, 2, 1, 0)
s.close()
s.close()
hub = app.TaskHubSession(core, args)
hub.category, hub.selected = 4, 9
hub.key(keys.C, keys)
assert isinstance(hub.child, app.ScrambleSession) and hub.child.options_draft is not None
hub.key(keys.ESCAPE, keys)
assert hub.child is None
hub.key(keys.C, keys)
hub.key(keys.RIGHT, keys)
hub.key(keys.RETURN, keys)
assert hub.child is None and app.read_scramble_settings()[0] == 3
hub.key(keys.RETURN, keys)
assert isinstance(hub.child, app.ScrambleSession)
hub.key(keys.ESCAPE, keys)
assert hub.child is None
hub.close()
index_path = Path(temporary.name) / 'lexicon.tsv'
sentence_path = Path(temporary.name) / 'sentences.txt'
index_path.write_text('cat\t1\t\na\t2\t\n')
sentence_path.write_text('a cat a cat a cat\n')
args.scramble_index, args.scramble_sentences = str(index_path), str(sentence_path)
args.scramble_level, args.scramble_trials, args.scramble_no_adaptive = 1, 1, True
loaded = app.ScrambleSession(core, args)
assert core.scramble_info(loaded.handle, 13) == 1
loaded.action(0)
loaded.text('a cat a cat a cat')
loaded.action(3)
assert loaded.state[6] == 1
loaded.close()
args.scramble_sentences = str(Path(temporary.name) / 'missing')
try:
    app.ScrambleSession(core, args)
    raise AssertionError('explicit missing corpus must fail')
except SystemExit as error:
    assert 'Cannot load Scramble corpus' in str(error)
args.scramble_index, args.scramble_sentences = str(index_path), None
index_only = app.ScrambleSession(core, args)
assert (core.scramble_info(index_only.handle, 14), core.scramble_info(index_only.handle, 15)) == (1, 0)
index_only.action(0)
assert index_only.state[0] == 3
index_only.close()
args.scramble_index, args.scramble_sentences = None, str(sentence_path)
sentences_only = app.ScrambleSession(core, args)
assert (core.scramble_info(sentences_only.handle, 14), core.scramble_info(sentences_only.handle, 15)) == (0, 1)
sentences_only.action(0)
sentences_only.text('a cat a cat a cat')
sentences_only.action(3)
assert sentences_only.state[6] == 1
sentences_only.close()
temporary.cleanup()
print('scramble_python_host_test: PASS (source deal, text, adaptive lifecycle, menu, cleanup)')
