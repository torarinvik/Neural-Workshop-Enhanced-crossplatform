#!/usr/bin/env python3
"""Cross-check the native Numberology controller against Python big integers."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
core = app.load_core('numberology_value')
cases = json.loads((root / 'test/numberology_exact_oracle.json').read_text())
for case in cases:
    run = core.numberology_create(case['level'], 1, 0, case['seed'])
    assert run > 0
    assert core.numberology_action(run, 0, 0, 0) == 1
    assert core.numberology_info(run, 4) == len(case['terms'])
    shown = bytes(core.numberology_value(run, 0, i)
                  for i in range(core.numberology_info(run, 14))).decode()
    assert shown == '\n'.join(case['terms']) + '\n', case['level']
    for char in case['answer']:
        assert core.numberology_action(run, 1, ord(char), 0) == 1
    assert core.numberology_action(run, 3, 0, 0) == 1
    assert core.numberology_info(run, 8) == 1, case['level']
    answer = bytes(core.numberology_value(run, 2, i)
                   for i in range(core.numberology_info(run, 15))).decode()
    assert answer == case['answer']
    assert core.numberology_frame(run, 0, 912, 684).startswith(b'NKIN')
    assert core.numberology_destroy(run) == 0
print(f'Numberology native exact controller: {len(cases)} source cases match and grade')
