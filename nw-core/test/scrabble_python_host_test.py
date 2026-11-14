#!/usr/bin/env python3
"""Native Python Scrabble routes, options, input and source-generated board."""
import json
import ast
import re
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
core = app.load_core('scrabble_create')
with tempfile.TemporaryDirectory() as directory:
    old_home = os.environ.get('HOME')
    os.environ['HOME'] = directory
    try:
        args = SimpleNamespace(scrabble_level=1, scrabble_trials=1,
            scrabble_no_premiums=False, scrabble_no_adaptive=False,
            scrabble_lexicon=None, seed=17, black_background=False)
        session = app.ScrabbleSession(core, args)
        assert session.state[0:4] == (0, 1, 0, 1)
        assert session.state[11] == 0 and session.state[17:19] == (1, 1)
        assert session.action(0) == 1
        assert session.state[0] == 1 and session.frame_bytes(core)
        assert core.scrabble_action(session.handle, 10, 0, 0) == 2, 'host already synchronized the start clock'
        oracle = json.loads(subprocess.check_output([sys.executable, str(root / 'test/scrabble_controller_oracle.py')],
            text=True, env={**os.environ, 'NW_SCRABBLE_SEED': '1', 'NW_SCRABBLE_LEVEL': '1'}))
        assert [core.scrabble_value(session.handle, 0, i) for i in range(49)] == oracle['board']
        assert session.state[9] == oracle['score']
        names = ('ESCAPE', 'O', 'C', 'SPACE', 'RETURN', 'LEFT', 'RIGHT', 'TAB', 'UP', 'DOWN', 'BACKSPACE', 'DELETE',
                 *(f'_{n}' for n in range(1, 8)), *(f'NUM_{n}' for n in range(1, 8)))
        key = SimpleNamespace(**{name: i + 100 for i, name in enumerate(names)})
        cursor = session.state[6]
        session.key(key.RIGHT, key)
        assert session.state[6] == cursor + 1
        session.key(key._1, key)
        assert core.scrabble_value(session.handle, 4, 0) == 1
        session.key(key.BACKSPACE, key)
        assert core.scrabble_value(session.handle, 4, 0) == 0
        assert session.pointer(456, 342, 912, 684, 2) == 1
        session.key(key.O, key)
        from renderer import decode
        from display_decode import canonical
        labels = " ".join(canonical(decode(session.frame_bytes(core))))
        assert "Scrabble options" in labels and "Boards per run" in labels
        session.key(key.RIGHT, key)
        session.key(key.ESCAPE, key)
        assert session.state[0] == 1 and session.state[1] == 1
        session.key(key.C, key)
        session.key(key.RIGHT, key)
        session.key(key.DOWN, key)
        session.key(key.RIGHT, key)
        session.key(key.DOWN, key)
        session.key(key.SPACE, key)
        session.key(key.DOWN, key)
        session.key(key.SPACE, key)
        session.key(key.RETURN, key)
        assert (session.state[0], session.state[1], session.state[3], *session.state[17:19]) == (0, 2, 2, 0, 0)
        assert app.read_scrabble_settings() == (2, 2, 0, 0)
        dump = subprocess.run([sys.executable, str(root / 'shells/python/app.py'), '--screen', 'scrabble',
                               '--dump', '--scrabble-level', '4'], cwd=root, capture_output=True, text=True, check=True)
        state = ast.literal_eval(re.search(r'^# state=(\([^\n]+\)) bytes=', dump.stdout, re.M).group(1))
        assert (state[1], state[3], *state[17:19]) == (4, 2, 0, 0)
        session.close()
        session.close()
        hub = app.TaskHubSession(core, args)
        hub.category, hub.selected = 4, 7
        hub.key(key.C, key)
        assert isinstance(hub.child, app.ScrabbleSession) and hub.child.options_draft is not None
        hub.key(key.ESCAPE, key)
        assert hub.child is None
        hub.key(key.C, key)
        hub.key(key.RIGHT, key)
        hub.key(key.RETURN, key)
        assert hub.child is None and args.scrabble_level == 3
        assert app.read_scrabble_settings()[0] == 3
        hub.key(key.RETURN, key)
        assert isinstance(hub.child, app.ScrabbleSession)
        hub.key(key.O, key)
        hub.key(key.ESCAPE, key)
        assert hub.child is not None and hub.child.options_draft is None
        hub.key(key.ESCAPE, key)
        assert hub.child is None
        hub.close()
        args.scrabble_lexicon = str(Path(directory) / 'missing.tsv')
        try:
            app.ScrabbleSession(core, args)
            raise AssertionError('explicit missing lexicon must fail')
        except SystemExit as error:
            assert 'Cannot load Scrabble lexicon' in str(error)
    finally:
        if old_home is None: os.environ.pop('HOME', None)
        else: os.environ['HOME'] = old_home
print('scrabble_python_host_test: PASS (offline source deal, input, pointer, menu, lifecycle)')
