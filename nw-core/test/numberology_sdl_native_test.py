#!/usr/bin/env python3
"""Replay source-derived Numberology sessions through the SDL native ABI."""
import ctypes
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
from renderer import decode

library = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
def bind(name, count):
    function = getattr(library, name)
    function.argtypes = [ctypes.c_int64] * count
    function.restype = ctypes.c_int64
    return function

create = bind('nw_numberology_create', 4)
action = bind('nw_numberology_action', 4)
info = bind('nw_numberology_info', 2)
value = bind('nw_numberology_value', 3)
frame_write = bind('nw_numberology_frame_write', 6)
destroy = bind('nw_numberology_destroy', 1)
buffer = ctypes.create_string_buffer(1048576)
address = ctypes.addressof(buffer)
def labels(handle):
    length = frame_write(address, len(buffer), handle, 0, 912, 684)
    assert 0 < length <= len(buffer)
    return [cmd['text'] for cmd in decode(buffer.raw[:length]) if cmd['kind'] == 'text']
def text_value(handle, field, length):
    return bytes(value(handle, field, i) for i in range(length)).decode()

cases = json.loads((root / 'test/numberology_session_oracle.json').read_text())
for scenario in cases:
    handle = create(scenario['level'], scenario['trials'], int(scenario['adaptive']), scenario['seed'])
    assert handle > 0
    try:
        assert action(handle, 0, 0, 0) == 1
        for index, row in enumerate(scenario['rows']):
            assert info(handle, 0) == 1 and info(handle, 2) == index + 1
            assert action(handle, 3, 0, 0) == 2
            assert text_value(handle, 0, info(handle, 14)) == '\n'.join(row['terms']) + '\n'
            for character in row['input']:
                assert action(handle, 1, ord(character), 0) == 1
            assert action(handle, 3, 0, 0) == 1
            assert info(handle, 0) == 2 and info(handle, 10) == row['right']
            texts = labels(handle)
            assert row['message'] in texts and row['rule'] in texts
            assert action(handle, 0, 0, 0) == 1
        assert info(handle, 0) == 3 and info(handle, 13) == scenario['next_level']
        assert scenario['message'] in labels(handle)
    finally:
        destroy(handle)
# Verify that the exact sequence and judged answer remain readable over pages.
fixture = next(row for row in json.loads((root / 'test/numberology_exact_oracle.json').read_text())
               if row['level'] == 1000 and row['seed'] == 19)
handle = create(1000, 1, 0, 19)
assert handle > 0
try:
    assert action(handle, 0, 0, 0) == 1
    assert info(handle, 5) == -1 and info(handle, 15) == 0 and info(handle, 17) == -1
    assert value(handle, 2, 0) == -1
    raw = '\n'.join(fixture['terms']) + '\n'
    pages = (len(raw) + 47) // 48
    assert pages > 1 and info(handle, 22) == pages
    assert action(handle, 4, 0, 0) == 2
    reconstructed = ''
    for page in range(pages):
        assert info(handle, 21) == page + 1
        length = frame_write(address, len(buffer), handle, 0, 912, 684)
        commands = [cmd for cmd in decode(buffer.raw[:length]) if cmd['kind'] == 'text']
        assert any(cmd['text'] == f'Sequence page {page + 1}/{pages}' for cmd in commands)
        line = next(cmd['text'] for cmd in commands if cmd['y'] == 494 and cmd['bold'])
        assert all(len(part) <= 40 for part in line.split('\n'))
        reconstructed += line.replace('\n', '')
        if page + 1 < pages: assert action(handle, 5, 0, 0) == 1
    assert reconstructed == ',   '.join(fixture['terms']) + ',   ?'
    assert action(handle, 5, 0, 0) == 2
    assert action(handle, 1, ord('-'), 0) == 1
    for digit in '1234567890' * 8: assert action(handle, 1, ord(digit), 0) == 1
    assert info(handle, 16) == 80 and action(handle, 3, 0, 0) == 1
    answer_pages = (len(fixture['answer']) + 47) // 48
    assert info(handle, 23) == pages and info(handle, 24) == answer_pages
    shown_answer = ''
    for page in range(answer_pages):
        assert action(handle, 5, 0, 0) == 1
        length = frame_write(address, len(buffer), handle, 0, 912, 684)
        commands = [cmd for cmd in decode(buffer.raw[:length]) if cmd['kind'] == 'text']
        assert any(cmd['text'] == f'Answer page {page + 1}/{answer_pages}' for cmd in commands)
        shown_answer += next(cmd['text'] for cmd in commands if cmd['y'] == 494 and cmd['bold']).replace('\n', '')
    assert shown_answer == fixture['answer'] and action(handle, 5, 0, 0) == 2
finally:
    destroy(handle)
print(f'Numberology SDL native ABI: {len(cases)} source-derived sessions and long paging match')
