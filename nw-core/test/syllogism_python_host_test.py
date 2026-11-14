#!/usr/bin/env python3
"""Exercise Syllogisms Python options, input and menu routing headlessly."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'shells/python'))
import app

class Core:
    def __init__(self): self.actions=[]; self.created=[]; self.destroyed=[]; self.phase=0
    def syllogism_create(self,*values): self.created.append(values); self.phase=0; return len(self.created)
    def syllogism_destroy(self,handle): self.destroyed.append(handle); return 0
    def syllogism_info(self,handle,field): return self.phase if field==0 else 0
    def syllogism_options_frame(self,*values): return values
    def syllogism_frame(self,*values): return b'frame'
    def syllogism_action(self,handle,action,value,now):
        self.actions.append((action,value))
        if action==0: self.phase=1
        if action in (1,6): self.phase=2
        return 1

key=SimpleNamespace(ESCAPE=1,UP=2,DOWN=3,LEFT=4,RIGHT=5,SPACE=6,RETURN=7,O=8,C=9,_1=101,_9=109)
def args(): return SimpleNamespace(seed=17,black_background=False,syllogism_level=None,syllogism_trials=None,
                                    syllogism_no_working=None,syllogism_no_adaptive=None,syllogism_invented_words=None)
with tempfile.TemporaryDirectory() as temp:
    os.environ['NW_SYLLOGISM_SETTINGS_PATH']=str(Path(temp)/'settings')
    core=Core(); a=args(); session=app.SyllogismSession(core,a)
    assert session.options==[3,6,1,1,1]
    session.key(key.O,key); assert session.frame_bytes(None)==(0,0,3,6,1,1,1)
    for row in range(5):
        session.options_selection=row; session.key(key.RIGHT,key)
    session.key(key.ESCAPE,key); assert session.options==[3,6,1,1,1]
    session.key(key.O,key)
    for row in range(5):
        session.options_selection=row; session.key(key.RIGHT,key)
    session.pointer(647,113,912,684)  # apply by pointer
    assert session.options==[4,8,0,0,0] and app.read_syllogism_settings()==(4,8,0,0,0)
    assert core.created[-1]==(4,8,0,0,0,17) and core.destroyed==[1]
    session.key(key.SPACE,key); session.key(key._1+2,key)
    assert core.actions[-2:]==[(0,0),(6,2)]
    session.pointer(456,300,912,684); assert core.actions[-1]==(0,0)
    session.close(); assert core.destroyed[-1]==2
    hub=app.TaskHubSession(core,args()); hub.category=4; hub.selected=11
    hub.key(key.C,key); assert isinstance(hub.child,app.SyllogismSession) and hub.child.options_draft is not None
    hub.key(key.ESCAPE,key); assert hub.child is None
print('Syllogism Python host: settings, cancellation, apply, keyboard and menu routing pass')
