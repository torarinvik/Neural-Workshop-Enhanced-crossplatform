#!/usr/bin/env python3
"""Verify native Numberology pages reconstruct the original sequence and answer."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app

core = app.load_core('numberology_value')
case = next(item for item in json.loads((root / 'test/numberology_exact_oracle.json').read_text())
            if item['level'] == 1000 and item['seed'] == 19)
handle = core.numberology_create(1000, 1, 0, 19)
assert handle > 0
try:
    def info(field): return core.numberology_info(handle, field)
    def act(code, value=0): return core.numberology_action(handle, code, value, 0)
    def labels():
        return [cmd for cmd in app.decode(core.numberology_frame(handle, 0, 912, 684)) if cmd['kind'] == 'text']
    assert act(0) == 1
    raw = '\n'.join(case['terms']) + '\n'
    pages = (len(raw) + 47) // 48
    assert info(22) == pages and pages > 1
    assembled = ''
    for page in range(pages):
        assert info(21) == page + 1
        commands = labels()
        assert any(item['text'] == f'Sequence page {page + 1}/{pages}' for item in commands)
        line = next(item['text'] for item in commands if item['y'] == 494 and item['bold'])
        assert all(len(row) <= 40 for row in line.split('\n'))
        assembled += line.replace('\n', '')
        if page + 1 < pages: assert act(5) == 1
    assert assembled == ',   '.join(case['terms']) + ',   ?'
    assert act(1, ord('-')) == 1
    assert act(3) == 1 and info(8) == 0
    answer_pages = (len(case['answer']) + 47) // 48
    assert info(23) == pages and info(24) == answer_pages
    assembled = ''
    for page in range(answer_pages):
        assert act(5) == 1
        commands = labels()
        assert any(item['text'] == f'Answer page {page + 1}/{answer_pages}' for item in commands)
        assembled += next(item['text'] for item in commands if item['y'] == 494 and item['bold']).replace('\n', '')
    assert assembled == case['answer']
finally:
    core.numberology_destroy(handle)
print('Numberology native paging: source sequence and judged answer reconstruct')
