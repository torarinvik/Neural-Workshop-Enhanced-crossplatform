#!/usr/bin/env python3
"""Headless source-oracle replay through the SDL native ABI."""
import ctypes
import json
import os
import sys
import tempfile
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

create = bind('nw_syllogism_create', 6)
action = bind('nw_syllogism_action', 4)
info = bind('nw_syllogism_info', 2)
value = bind('nw_syllogism_value', 3)
frame_write = bind('nw_syllogism_frame_write', 6)
options_write = bind('nw_syllogism_options_frame_write', 9)
destroy = bind('nw_syllogism_destroy', 1)
buffer = ctypes.create_string_buffer(65536)
address = ctypes.addressof(buffer)
def frame(handle):
    length = frame_write(address, len(buffer), handle, 0, 912, 684)
    assert 0 < length <= len(buffer)
    return [cmd['text'] for cmd in decode(buffer.raw[:length]) if cmd['kind'] == 'text']

cases = json.loads((root / 'test/syllogism_session_oracle.json').read_text())
for case in cases:
    handle = create(case['level'], 2, 1, 0, 1, case['seed'])
    assert handle > 0
    try:
        assert action(handle, 0, 0, 1000) == 1
        for index, row in enumerate(case['rows']):
            assert info(handle, 0) == 1 and value(handle, 0, 0) == -1
            texts = frame(handle)
            assert '\n'.join(row['lines']) in texts and row['asked'] in texts
            chosen = (row['answer'] + 1) % len(row['options']) if index == 0 else row['answer']
            assert action(handle, 6, chosen, 2500 + index * 4000) == 1
            assert info(handle, 7) == index and value(handle, 0, 0) == row['answer']
            assert info(handle, 15) == index + 1
            assert value(handle, 2, index) == case['level']
            assert value(handle, 3, index) == index and value(handle, 4, index) == 1500
            assert '\n'.join(row['working']) in frame(handle)
            assert action(handle, 0, 0, 5000 + index * 4000) == 1
        assert info(handle, 14) == 3
        assert info(handle, 0) == 3 and info(handle, 8) == 1
        assert info(handle, 9) == case['level']
    finally:
        destroy(handle)
for selected in range(5):
    length = options_write(address, len(buffer), 0, selected, 3, 6, 1, 1, 1)
    assert 0 < length <= len(buffer)
    texts = [cmd['text'] for cmd in decode(buffer.raw[:length]) if cmd['kind'] == 'text']
    assert 'Syllogism options' in texts and 'Name things after real words' in texts
# A regressing clock cannot create a negative duration; restart clears history.
handle = create(1, 1, 1, 0, 1, 17)
try:
    assert action(handle, 0, 0, 1000) == 1
    assert action(handle, 6, 0, 500) == 1
    assert value(handle, 4, 0) == 0 and info(handle, 14) == 0
    assert action(handle, 0, 0, 1100) == 1 and info(handle, 0) == 3
    assert action(handle, 0, 0, 1200) == 1
    assert info(handle, 15) == 0 and value(handle, 2, 0) == -1
finally:
    destroy(handle)
# Exercise the actual SDL transition adapter and atomic result manager together.
dispatch = library.nw_syllogism_sdl_dispatch
dispatch.argtypes = [ctypes.c_int64] * 4 + [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_size_t)]
dispatch.restype = ctypes.c_int64
close_results = library.nw_syllogism_results_close
close_results.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
options = (ctypes.c_int64 * 5)(1, 1, 1, 0, 1)
manager = (ctypes.c_size_t * 2)()
with tempfile.TemporaryDirectory() as temporary:
    prior = os.environ.get('NW_SYLLOGISM_RESULTS_DIR')
    os.environ['NW_SYLLOGISM_RESULTS_DIR'] = temporary
    handle = create(*options, 17)
    try:
        assert dispatch(handle, 0, 0, 1000, options, manager) == 1
        assert dispatch(handle, 6, 0, 2750, options, manager) == 1
        correct = info(handle, 7)
        assert dispatch(handle, 6, 0, 2800, options, manager) == 2
        assert dispatch(handle, 0, 0, 3000, options, manager) == 1
        files = list(Path(temporary).glob('*.json'))
        assert len(files) == 1
        record = json.loads(files[0].read_text())
        assert record['completed'] and record['right'] == correct and record['seconds'] == 1
        assert record['options'] == list(options) and len(record['results']) == 1
        assert record['results'][0]['elapsed_ms'] == 1750 and record['results'][0]['correct'] == bool(correct)
        close_results(manager)
        assert list(manager) == [0, 0] and not list(Path(temporary).glob('*.tmp'))
    finally:
        destroy(handle)
        if prior is None: os.environ.pop('NW_SYLLOGISM_RESULTS_DIR', None)
        else: os.environ['NW_SYLLOGISM_RESULTS_DIR'] = prior
print(f'Syllogism SDL native ABI: {len(cases)} source sessions and five options frames match')
