#!/usr/bin/env python3
"""Exercise native Algebra options, persistence, cancellation and progression."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
core = app.load_core('algebra_create_options')
key = SimpleNamespace(O=1, SPACE=2, RETURN=3, BACKSPACE=4, DELETE=5, ESCAPE=6,
                      UP=7, DOWN=8, LEFT=9, RIGHT=10)
args = SimpleNamespace(seed=19, black_background=False, algebra_level=None,
                       algebra_trials=None, algebra_no_working=None, algebra_no_adaptive=None)
with tempfile.TemporaryDirectory() as temporary:
    os.environ['NW_ALGEBRA_SETTINGS_PATH'] = str(Path(temporary) / 'options')
    s = app.AlgebraSession(core, args)
    assert s.options == [3, 6, 1, 1]
    s.key(key.O, key)
    assert s.options_draft == [3, 6, 1, 1]
    s.key(key.RIGHT, key)
    s.key(key.ESCAPE, key)
    assert s.options == [3, 6, 1, 1] and not Path(os.environ['NW_ALGEBRA_SETTINGS_PATH']).exists()
    s.key(key.O, key)
    s.key(key.RIGHT, key)
    s.key(key.DOWN, key); s.key(key.RIGHT, key)
    s.key(key.DOWN, key); s.key(key.RIGHT, key)
    s.key(key.DOWN, key); s.key(key.RIGHT, key)
    assert s.frame_bytes(core).startswith(b'NKIN')
    s.key(key.RETURN, key)
    assert s.options == [4, 8, 0, 0]
    assert app.read_algebra_settings() == (4, 8, 0, 0)
    assert (s.state[1], s.state[3], core.algebra_info(s.handle, 12), core.algebra_info(s.handle, 13)) == (4, 8, 0, 0)
    s.close()
    fresh_args = SimpleNamespace(seed=19, black_background=False, algebra_level=None,
                                 algebra_trials=None, algebra_no_working=None, algebra_no_adaptive=None)
    s = app.AlgebraSession(core, fresh_args)
    assert s.options == [4, 8, 0, 0]
    s.key(key.O, key)
    s.pointer(500, 426, 912, 684)
    assert s.options_selection == 1
    s.pointer(500, 426, 912, 684)
    assert s.options_draft[1] == 10
    s.key(key.ESCAPE, key)
    with patch.object(app.time, 'monotonic', return_value=100.0):
        s.pointer(400, 300, 912, 684)
    assert s.state[0] == 1
    with patch.object(app.time, 'monotonic', return_value=101.0), \
            patch.object(app, 'read_scramble_clipboard', return_value='X + Y/2') as clipboard:
        s.paste()
        clipboard.assert_called_once()
    typed = bytes(core.algebra_value(s.handle, 1, i) for i in range(s.state[6])).decode()
    assert typed == 'x + y/2'
    with patch.object(app.time, 'monotonic', return_value=103.5):
        s.key(key.RETURN, key)
    assert core.algebra_info(s.handle, 15) == 1
    assert core.algebra_info(s.handle, 16) == 3
    s.close()
print('Algebra Python options: defaults, cancel, apply, persistence and controller passed')
