#!/usr/bin/env python3
"""Replay source Syllogism questions through the real Python extension."""
import json
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'shells/python'))
import app
core=app.load_core('syllogism_create')
cases=json.loads((root/'test/syllogism_session_oracle.json').read_text())
for case in cases:
    run=core.syllogism_create(case['level'],2,1,0,1,case['seed'])
    assert run>0
    try:
        assert core.syllogism_action(run,0,0,0)==1
        for index,row in enumerate(case['rows']):
            assert core.syllogism_info(run,0)==1
            assert core.syllogism_value(run,0,0)==-1
            text=[cmd['text'] for cmd in app.decode(core.syllogism_frame(run,0,912,684)) if cmd['kind']=='text']
            assert '\n'.join(row['lines']) in text and row['asked'] in text
            chosen=(row['answer']+1)%len(row['options']) if index==0 else row['answer']
            assert core.syllogism_action(run,6,chosen,0)==1
            assert core.syllogism_info(run,7)==index
            assert core.syllogism_value(run,0,0)==row['answer']
            text=[cmd['text'] for cmd in app.decode(core.syllogism_frame(run,0,912,684)) if cmd['kind']=='text']
            assert '\n'.join(row['working']) in text
            assert core.syllogism_action(run,0,0,0)==1
        assert core.syllogism_info(run,0)==3 and core.syllogism_info(run,8)==1
        assert core.syllogism_info(run,9)==case['level']
    finally:
        core.syllogism_destroy(run)
for selected in range(5):
    frame=app.decode(core.syllogism_options_frame(0,selected,3,6,1,1,1))
    texts=[cmd['text'] for cmd in frame if cmd['kind']=='text']
    assert 'Syllogism options' in texts and 'Name things after real words' in texts
print('Syllogism native Python: all source sessions, working and options render match')
