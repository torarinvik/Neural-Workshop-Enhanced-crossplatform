#!/usr/bin/env python3
"""Numberology native text input, exact levels and promotion persistence."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'shells/python'))
import app
core=app.load_core('numberology_value')
keys=SimpleNamespace(SPACE=1,RETURN=2,BACKSPACE=3,DELETE=4,O=5,ESCAPE=6,UP=7,DOWN=8,LEFT=9,RIGHT=10,PAGEUP=11,PAGEDOWN=12)
def args(**overrides):
    values=dict(seed=19,black_background=False,numberology_level=None,
                numberology_trials=None,numberology_no_adaptive=None)
    values.update(overrides)
    return SimpleNamespace(**values)
with tempfile.TemporaryDirectory() as temporary:
    os.environ['NW_NUMBEROLOGY_SETTINGS_PATH']=str(Path(temporary)/'settings')
    os.environ['NW_NUMBEROLOGY_RESULTS_DIR']=str(Path(temporary)/'results')
    session=app.NumberologySession(core,args(numberology_level=1000,numberology_trials=1,numberology_no_adaptive=True))
    session.pointer(400,300,912,684)
    assert session.state[0]==1 and session.state[1]==1000
    assert core.numberology_info(session.handle,5)==-1
    assert core.numberology_info(session.handle,17)==-1
    with patch.object(app,'read_scramble_clipboard',return_value='-000123') as clipboard:
        session.paste(); clipboard.assert_called_once()
    assert session.state[6]==-123 and session.state[7]==6
    session.key(keys.BACKSPACE,keys)
    assert session.state[6]==-12
    session.key(keys.RETURN,keys)
    assert session.state[8]==0
    session.close()
    session=app.NumberologySession(core,args(numberology_level=1,numberology_trials=1))
    session.key(keys.SPACE,keys)
    cases=json.loads((root/"test/numberology_exact_oracle.json").read_text())
    answer=next(item["answer"] for item in cases if item["level"]==1 and item["seed"]==19)
    session.text(answer)
    session.key(keys.RETURN,keys)
    assert session.state[8]==1
    session.key(keys.SPACE,keys)
    assert session.state[0]==3
    assert app.read_numberology_settings()==(2,1,1)
    session.close()
    reopened=app.NumberologySession(core,args())
    assert reopened.options==[2,1,1]
    reopened.key(keys.O, keys)
    with patch.object(reopened, 'core', SimpleNamespace(numberology_options_frame=lambda *values: values)):
        assert reopened.frame_bytes(None) == (0, 0, 2, 1, 1)
    reopened.text('0')
    reopened.text('0')
    reopened.text('5')
    assert reopened.options_draft[0] == 5
    reopened.key(keys.BACKSPACE, keys)
    reopened.text('7')
    assert reopened.options_draft[0] == 7
    reopened.key(keys.DOWN, keys)
    reopened.key(keys.UP, keys)
    reopened.text('10000')
    assert reopened.options_draft[0] == 10000
    reopened.key(keys.DOWN, keys)
    reopened.key(keys.RIGHT, keys)
    reopened.key(keys.DOWN, keys)
    reopened.key(keys.RIGHT, keys)
    reopened.key(keys.RETURN, keys)
    assert reopened.options == [10000, 2, 0]
    assert app.read_numberology_settings() == (10000, 2, 0)
    reopened.key(keys.O, keys)
    reopened.text('123')
    reopened.key(keys.ESCAPE, keys)
    assert reopened.options == [10000, 2, 0]
    reopened.close()
    assert app.parse_numberology_level('10000')==10000
    try: app.parse_numberology_level(str(1<<63))
    except argparse.ArgumentTypeError: pass
    else: raise AssertionError('out of range level accepted')
print('Numberology Python host: big level, text/paste, grading and persisted promotion pass')
