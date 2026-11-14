#!/usr/bin/env python3
"""Cross-check native Algebra generation, working and display against Python."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells' / 'python'))
import app
import renderer

core = app.load_core('algebra_create')
cases = json.loads((root / 'test' / 'algebra_working_oracle.json').read_text())
for case in cases:
    run = core.algebra_create(case['level'], 1, case['seed'])
    assert run > 0
    assert core.algebra_action(run, 0, 0, 0) == 1
    assert core.algebra_info(run, 11) == 0
    assert core.algebra_action(run, 1, ord('x'), 0) == 1
    assert core.algebra_action(run, 3, 0, 0) == 1
    length = core.algebra_info(run, 11)
    working = bytes(core.algebra_value(run, 3, i) for i in range(length)).decode()
    assert working == case['working'], (case['level'], case['seed'], working)
    commands = app.decode(core.algebra_frame(run, 0, 912, 684))
    texts = [command.get('text', '') for command in commands]
    assert working in texts
    plan = renderer.plan(commands, app.Viewport(912, 684))
    drawn = [op.fields['text'] for op in plan.ops if op.kind == 'text']
    assert all(line in drawn for line in working.split('\n'))
    assert core.algebra_destroy(run) == 0
print(f'Algebra native working: {len(cases)} original derivations match and render')
