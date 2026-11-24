#!/usr/bin/env python3
"""Exercise SDL text routing against native controllers without a window."""
import ctypes
import ast
import os
import pathlib
import shlex
import struct
import subprocess
import sys
import tempfile
from base64 import b64decode

from public_outcome_fixture import evidence_samples, samples

TASK_SLOTS = 142

if len(sys.argv) == 3:
    with tempfile.TemporaryDirectory() as tmp:
        library = pathlib.Path(tmp) / ('native.dylib' if sys.platform == 'darwin' else 'native.so')
        flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'sdl3'], text=True))
        if sys.platform == 'darwin':
            symbols = pathlib.Path(tmp) / 'exports.txt'
            names = ['nw_public_outcome_verify_evidence', 'nw_public_frame_digest', 'nw_public_outcome_verify_frame', 'nw_public_outcome_read', 'nw_two_hands_pointer', 'nw_sdl_dispatch_text', 'nw_sdl_text_event', 'nw_sdl_text_input', 'nw_sdl_text_task_click', 'nw_numberology_results_close', 'nw_sdl_dispatch_pointer', 'nw_sdl_dispatch_pixel_pointers', 'nw_sdl_word_pointer', 'nw_sdl_syllogism_click', 'nw_sdl_syllogism_key', 'nw_sdl_word_key', 'nw_sdl_scramble_key', 'nw_sdl_algebra_key', 'nw_sdl_numberology_key', 'nw_sdl_cancel_options', 'nw_sdl_exit_hub_task', 'nw_sdl_shutdown_rows', 'nw_syllogism_results_start', 'nw_numberology_results_start', 'nw_sdl_start_screen', 'nw_sdl_fallback_key', 'nw_sdl_fallback_frame', 'nw_sdl_collect_active', 'nw_sdl_collect_routing', 'nw_sdl_bind_rows', 'nw_sdl_bind_special_rows', 'nw_sdl_collect_frame_options', 'nw_sdl_special_frame_options', 'nw_sdl_special_text_event', 'nw_sdl_active_key', 'nw_sdl_maze_arguments', 'nw_sdl_start_maze', 'nw_sdl_present_frame_theme', 'nw_sudoku_frame_write', 'nw_sdl_frame_write', 'nw_title_write', 'nw_sdl_active_release', 'nw_sdl_dispatch_key_release', 'nw_sdl_active_pointer', 'nw_sdl_dispatch_task_key', 'nw_tetris_frame_write', 'nw_tetris_destroy', 'nw_sdl_parse_configs', 'nw_sdl_collect_screen_options', 'nw_task_settings_parse', 'nw_syllogism_options_parse', 'nw_numberology_options_parse', 'nw_sdl_launch_hub', 'nw_syllogism_results_close']
            names += ['nw_' + task + '_' + suffix for task in ('numberology', 'algebra', 'scramble', 'syllogism')
                      for suffix in ('create', 'action', 'info', 'destroy')]
            names += ['nw_' + task + '_frame_write' for task in ('numberology', 'algebra', 'syllogism')]
            names += ['nw_algebra_create_options', 'nw_sdl_advance_screenshot', 'nw_marble_advance', 'nw_marble_action']
            names += ['nw_marble_board_write', 'nw_marble_mjcf_write', 'nw_nback3d_action']
            names += ['nw_' + task + '_' + suffix for task in ('reflex', 'pursuit', 'jigsaw', 'go', 'ncup_monte', 'tracking', 'two_hands', 'scrabble', 'crossword')
                      for suffix in ('create', 'action', 'info', 'destroy')]
            hub_names = ('you_are_here', 'sokoban', 'monkey_ladder', 'nback3d', 'marble', 'tetris', 'count', 'mr_time', 'graph_mapping', 'matrix_reasoning', 'in_the_dark', 'fog', 'removals', 'custody', 'concentration', 'recognition', 'trivia', 'reflex', 'algebra', 'syllogism', 'numberology', 'jigsaw', 'sudoku', 'go', 'crossed_wires', 'scramble', 'scrabble', 'crossword', 'ncup_monte', 'tracking', 'lookout', 'pursuit', 'out_of_sight', 'buzz_wire', 'donkey', 'two_hands', 'overrun')
            names += ['nw_' + name + '_create' for name in hub_names]
            names += ['nw_' + name + '_' + suffix for name in hub_names if name != 'tetris' for suffix in ('info', 'destroy')]
            names += ['nw_triage_' + suffix for suffix in
                      ('create', 'destroy', 'action', 'advance', 'info', 'frame_write',
                       'rgba_write', 'think_configure', 'think_left', 'step')]
            symbols.write_text(''.join('_' + name + '\n' for name in sorted(set(names))))
            link = ['-Wl,-dead_strip', '-Wl,-exported_symbols_list,' + str(symbols)]
        else:
            link = ['-Wl,--allow-multiple-definition']
        clipboard = pathlib.Path(tmp) / 'clipboard.c'
        clipboard.write_text(
            '#include <SDL3/SDL.h>\n'
            'char *SDL_GetClipboardText(void) { return SDL_strdup(" abc"); }\n'
        )
        subprocess.run(['cc', '-shared', '-o', str(library), str(clipboard), *sys.argv[1:], *link, *flags], check=True)
        subprocess.run([sys.executable, __file__], check=True,
                       env=dict(os.environ, NW_SDL_NATIVE_LIBRARY=str(library)))
    sys.exit(0)

test_environment = tempfile.TemporaryDirectory()
os.environ['NW_SYLLOGISM_SETTINGS_PATH'] = str(pathlib.Path(test_environment.name) / 'settings')
os.environ['NW_SYLLOGISM_RESULTS_DIR'] = str(pathlib.Path(test_environment.name) / 'results')
os.environ['NW_SCRABBLE_SETTINGS_PATH'] = str(pathlib.Path(test_environment.name) / 'scrabble')
os.environ['NW_CROSSWORD_SETTINGS_PATH'] = str(pathlib.Path(test_environment.name) / 'crossword')
os.environ['NW_SCRAMBLE_SETTINGS_PATH'] = str(pathlib.Path(test_environment.name) / 'scramble')
os.environ['NW_ALGEBRA_SETTINGS_PATH'] = str(pathlib.Path(test_environment.name) / 'algebra')
os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = str(pathlib.Path(test_environment.name) / 'numberology')
os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(pathlib.Path(test_environment.name) / 'numberology-results')
lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])

class PublicLabels(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int64) for name in ("positive", "negative", "oops")] + [
        ("scalar", ctypes.c_double)
    ]


read_public_outcome = lib.nw_public_outcome_read
read_public_outcome.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64,
                               ctypes.c_int64, ctypes.POINTER(PublicLabels)]
read_public_outcome.restype = ctypes.c_int64
frame_digest = lib.nw_public_frame_digest
frame_digest.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
frame_digest.restype = ctypes.c_int64
verify_outcome_frame = lib.nw_public_outcome_verify_frame
verify_outcome_frame.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64,
                                 ctypes.c_int64, ctypes.c_void_p, ctypes.c_double]
verify_outcome_frame.restype = ctypes.c_int64
for sample in samples():
    rgba = b64decode(sample["rgba"])
    frame = ctypes.create_string_buffer(rgba)
    labels = PublicLabels(-1, -1, -1, -1)
    dimensions = sample["width"], sample["height"]
    assert read_public_outcome(frame, len(rgba) - 1, *dimensions, ctypes.byref(labels)) == -1
    assert labels.positive == -1
    assert read_public_outcome(None, len(rgba), *dimensions, ctypes.byref(labels)) == -1
    assert read_public_outcome(frame, len(rgba), *dimensions, ctypes.byref(labels)) == int(sample["scalar"] is not None)
    assert [labels.positive, labels.negative, labels.oops] == sample["counts"]
    assert labels.scalar == (sample["scalar"] or 0.0)
    digest = ctypes.create_string_buffer(64)
    assert frame_digest(frame, len(rgba), digest) == 1
    assert digest.raw.decode("ascii") == sample["digest"]
    expected = ctypes.create_string_buffer(sample["digest"].encode("ascii"), 64)
    assert verify_outcome_frame(frame, len(rgba), *dimensions, expected, labels.scalar) == int(sample["scalar"] is not None)
    frame[3] = bytes((frame[3][0] ^ 1,))
    assert verify_outcome_frame(frame, len(rgba), *dimensions, expected, labels.scalar) == 0
print("SDL public outcome pixels and frame digests match Python")

# Triage is driven through its native ABI and read back as real SDL pixels.
triage_create = lib.nw_triage_create
triage_create.argtypes = [ctypes.c_int64] * 4
triage_create.restype = ctypes.c_int64
triage_destroy = lib.nw_triage_destroy
triage_destroy.argtypes = [ctypes.c_int64]
triage_destroy.restype = None
triage_action = lib.nw_triage_action
triage_action.argtypes = [ctypes.c_int64] * 3
triage_action.restype = ctypes.c_bool
triage_advance = lib.nw_triage_advance
triage_advance.argtypes = [ctypes.c_int64] * 2
triage_advance.restype = ctypes.c_bool
triage_info = lib.nw_triage_info
triage_info.argtypes = [ctypes.c_int64] * 2
triage_info.restype = ctypes.c_int64
triage_rgba = lib.nw_triage_rgba_write
triage_rgba.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
                       ctypes.c_int32, ctypes.c_int32]
triage_rgba.restype = ctypes.c_int64
assert not triage_create(1, 1, 2, 17)
width, height = 912, 684
rgba_frame = ctypes.create_string_buffer(width * height * 4)
rgba_size = len(rgba_frame)
triage = triage_create(1, 2, 1, -17)
assert triage
try:
    assert triage_action(triage, 17, 0)
    assert triage_info(triage, 4) == 4
    assert not triage_rgba(rgba_frame, rgba_size - 1, triage, 0, width, height)
    assert not triage_rgba(None, rgba_size, triage, 0, width, height)
    assert triage_rgba(rgba_frame, rgba_size, triage, 0, width, height) == rgba_size
    labels = PublicLabels()
    assert read_public_outcome(rgba_frame, rgba_size, width, height, ctypes.byref(labels)) == 0
    for port in (0, 8, 9, 1, 9):
        assert triage_action(triage, port, 250)
    assert triage_info(triage, 6) == 5 and triage_info(triage, 13) == 1
    assert triage_rgba(rgba_frame, rgba_size, triage, 0, width, height) == rgba_size
    assert read_public_outcome(rgba_frame, rgba_size, width, height, ctypes.byref(labels)) == 1
    assert labels.scalar == 1
    digest = ctypes.create_string_buffer(64)
    assert frame_digest(rgba_frame, rgba_size, digest) == 1
    assert verify_outcome_frame(rgba_frame, rgba_size, width, height, digest, 1.0) == 1
    assert not triage_advance(triage, 2749)
    assert triage_advance(triage, 2750)
    assert triage_action(triage, 18, 3000)
    assert triage_info(triage, 0) == 4 and not triage_action(triage, 16, 3000)
    assert triage_rgba(rgba_frame, rgba_size, triage, 1, width, height) == rgba_size
    assert read_public_outcome(rgba_frame, rgba_size, width, height, ctypes.byref(labels)) == 1
    assert labels.scalar == -1
    assert triage_advance(triage, 3001)
    assert triage_info(triage, 0) == 3 and triage_info(triage, 13) == 1
    assert triage_info(triage, 1) == 2
finally:
    triage_destroy(triage)
print("Triage native stepped ABI: signed seed, headless pixels, verified reward, timer, and forfeit pass")

triage_configure = lib.nw_triage_think_configure
triage_configure.argtypes = [ctypes.c_int64, ctypes.c_double, ctypes.c_double]
triage_configure.restype = ctypes.c_bool
triage_step = lib.nw_triage_step
triage_step.argtypes = [ctypes.c_int64, ctypes.c_double]
triage_step.restype = ctypes.c_bool
triage_balance = lib.nw_triage_think_left
triage_balance.argtypes = [ctypes.c_int64]
triage_balance.restype = ctypes.c_double
triage = triage_create(1, 3, 1, 17)
assert triage
try:
    assert not triage_configure(triage, float("inf"), 0)
    assert not triage_configure(triage, 0.1, -1)
    assert triage_configure(triage, 0.1, 0.05)
    assert triage_action(triage, 17, 0)
    assert not triage_configure(triage, 0.2, 0.1)
    assert not triage_step(triage, 0)
    assert triage_step(triage, 0.05) and triage_balance(triage) == 0.05
    assert triage_step(triage, 0.05) and triage_info(triage, 0) == 4
    assert triage_balance(triage) == 0 and triage_info(triage, 14) == 1
    assert triage_step(triage, 0.05) and triage_info(triage, 2) == 2
    assert triage_balance(triage) == 0.05 and triage_info(triage, 1) == 1
    assert triage_action(triage, 16, 200)
    assert triage_step(triage, 0.05) and triage_info(triage, 0) == 2
    assert triage_balance(triage) == 0.05
    assert triage_step(triage, 0.05) and triage_info(triage, 2) == 3
    assert triage_balance(triage) == 0.1 and triage_info(triage, 13) == 1
finally:
    triage_destroy(triage)
print("Triage native think clock: one-frame verdict, expiry, and capped refill pass")

verify_evidence = lib.nw_public_outcome_verify_evidence
verify_evidence.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64,
                            ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                            ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                            ctypes.c_double]
verify_evidence.restype = ctypes.c_int64
evidence_matrix = evidence_samples()
feedback = evidence_matrix["feedback"]
rgba = b64decode(feedback["rgba"])
for case in evidence_matrix["scenarios"]:
    buffers = []

    def address(data):
        buffer = ctypes.create_string_buffer(data)
        buffers.append(buffer)
        return ctypes.addressof(buffer)

    claim = case["outcome"]
    digests = claim["evidence_digests"]
    evidence = address("".join(digests).encode("ascii"))
    frame_rows = []
    if case["archive"] is not None:
        for digest in digests:
            data = case["archive"].get(digest)
            if data is None:
                frame_rows.extend((0, 0))
            else:
                frame = b64decode(data)
                frame_rows.extend((address(frame), len(frame)))
    archive = (ctypes.c_int64 * len(frame_rows))(*frame_rows) if frame_rows else None
    receipt_id = claim["receipt_id"] if claim["receipt_id"] is not None else -1
    selected = (case["ledger"] or {}).get(receipt_id)
    receipt = None
    if selected:
        bound = selected.get("evidence_digests")
        receipt = (ctypes.c_int64 * 7)(
            receipt_id, selected.get("receipt_id", -1), selected.get("trial_seq", -1),
            address(selected["stimulus_digest"].encode("ascii")),
            address(selected["feedback_digest"].encode("ascii")) if "feedback_digest" in selected else 0,
            address("".join(bound).encode("ascii")) if bound is not None else 0, len(bound or ()),
        )
    assert verify_evidence(rgba, len(rgba), feedback["width"], feedback["height"],
                           evidence, len(digests), archive, receipt_id, receipt,
                           claim["scalar"]) == int(case["expected"]), case["name"]
print("SDL outcome archive and receipt binding match Python")

def bind(name, args, result=ctypes.c_int64):
    f = getattr(lib, name); f.argtypes = args; f.restype = result; return f
I, P = ctypes.c_int64, ctypes.c_void_p

dispatch = bind('nw_sdl_dispatch_task_key', [I] * 3, None)
nback_create = bind('nw_nback3d_create', [I] * 7)
nback_info = bind('nw_nback3d_info', [I] * 2)
nback_action = bind('nw_nback3d_action', [I] * 4)
nback_destroy = bind('nw_nback3d_destroy', [I])
handle = nback_create(2, 1, 4, 3000, 500, 200, 23)
assert handle > 0
try:
    for offset, expected in enumerate(((1, 4, 3000), (2, 4, 3000), (2, 4, 3000),
                                       (2, 9, 3000), (2, 9, 3100), (2, 9, 3000))):
        dispatch(11, handle, 0x4000003a + offset)
        assert tuple(nback_info(handle, field) for field in (1, 3, 14)) == expected
    dispatch(11, handle, 32)
    dispatch(11, handle, 0x4000003b)
    assert nback_info(handle, 1) == 2
    for _ in range(43):
        if nback_info(handle, 0) == 4:
            break
        nback_action(handle, 2, 0, nback_info(handle, 13))
    assert nback_info(handle, 0) == 4
    dispatch(11, handle, 0x4000003b)
    dispatch(11, handle, 0x4000003c)
    dispatch(11, handle, 0x4000003e)
    assert tuple(nback_info(handle, field) for field in (1, 3, 14)) == (2, 9, 3000)
    dispatch(11, handle, 32)
    assert tuple(nback_info(handle, field) for field in (1, 3, 14)) == (3, 4, 3100)
finally:
    nback_destroy(handle)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'shells' / 'python'))
from marble_mujoco import build_mjcf, decode_board

board_write = bind('nw_marble_board_write', [I] * 4)
mjcf_write = bind('nw_marble_mjcf_write', [I] * 4)
board_buffer = ctypes.create_string_buffer(65536)
xml_buffer = ctypes.create_string_buffer(1024 * 1024)
for rung in range(1, 17):
    for seed in (17, 42, 889418965):
        size = board_write(ctypes.addressof(board_buffer), len(board_buffer), rung, seed)
        board = decode_board(board_buffer.raw[:size])
        expected = build_mjcf(board, len(board.starts)).encode()
        size = mjcf_write(ctypes.addressof(xml_buffer), len(xml_buffer), rung, seed)
        assert xml_buffer.raw[:size] == expected, (rung, seed)
        assert mjcf_write(ctypes.addressof(xml_buffer), size - 1, rung, seed) == 0
print('SDL Marble model: MJCF matches the Python reference across all 16 rungs')

def assert_seeded_options(task, handle, params, create_suffix='create'):
    create = bind(f'nw_{task}_{create_suffix}', [I] * len(params))
    destroy = bind(f'nw_{task}_destroy', [I])
    action = bind(f'nw_{task}_action', [I] * 4)
    frame_write = bind(f'nw_{task}_frame_write', [I] * 6)
    reference = create(*params)
    assert reference > 0
    try:
        frames = []
        for run in (handle, reference):
            assert action(run, 0, 0, 100) == 1
            frame = ctypes.create_string_buffer(65536)
            length = frame_write(ctypes.addressof(frame), len(frame), run, 0, 912, 684)
            assert 0 < length <= len(frame)
            frames.append(frame.raw[:length])
        assert frames[0] == frames[1], task
    finally:
        destroy(reference)

dispatch = bind('nw_sdl_dispatch_text', [I, I, I, I, ctypes.c_char_p, I, P, P, P, P], None)
text = bind('nw_sdl_text_input', [I, ctypes.c_char_p, I, I], None)
for name, params, task, field in [('numberology', (1, 1, 0, 23), 0, 16),
                                  ('algebra', (1, 1, 23), 1, 6),
                                  ('scramble', (1, 1, 1, 1, 17), 2, 5)]:
    create = bind('nw_' + name + '_create', [I] * len(params))
    action = bind('nw_' + name + '_action', [I] * 4)
    info = bind('nw_' + name + '_info', [I] * 2)
    destroy = bind('nw_' + name + '_destroy', [I])
    a, b = create(*params), create(*params)
    assert a > 0 and b > 0
    try:
        dispatch(b, task, 0, 0, b'abc', 200, None, None, None, None)
        assert info(b, field) == 0  # ready phase ignores text
        assert action(a, 0, 0, 100) == action(b, 0, 0, 100) == 1
        dispatch(b, task, 1, 1, b'abc', 200, None, None, None, None)
        assert info(b, field) == 0  # options mask task input
        sample = b'12' if task != 2 else b'ab'
        text(a, sample, 200, task)
        suppress = ctypes.c_uint8(1)
        dispatch(b, task, 0, 0, b' ' + sample if task == 2 else sample, 200,
                 ctypes.byref(suppress), None, None, None)
        assert info(a, field) == info(b, field) == 2, name
        if task == 2:
            assert suppress.value == 0
            dispatch(b, task, 0, 0, b' c', 201, ctypes.byref(suppress), None, None, None)
            text(a, b' c', 201, task)
            assert info(a, field) == info(b, field)
    finally:
        destroy(a); destroy(b)
level, editing, value = I(3), ctypes.c_uint8(0), I(0)
dispatch(0, 0, 1, 1, b'42', 0, None, ctypes.byref(level), ctypes.byref(editing), ctypes.byref(value))
assert level.value == 3 and editing.value == 0
dispatch(0, 0, 1, 0, b'a42', 0, None, ctypes.byref(level), ctypes.byref(editing), ctypes.byref(value))
assert (level.value, editing.value, value.value) == (42, 1, 42)
print('SDL text dispatch: phase, options, editing and space suppression pass')

click = bind('nw_sdl_text_task_click', [I, I, I, ctypes.c_float, ctypes.c_float, ctypes.c_int32,
             ctypes.c_int32, P, P, P, P, P], ctypes.c_int32)
# A reference-size click at (456, 210) hits option row zero.
for task in range(3):
    selected = ctypes.c_int32(0)
    draft = (I * 5)(1, 1, 1, 1, 0)
    editing = ctypes.c_uint8(1)
    assert click(task, 0, 1, 456, 210, 912, 684, ctypes.byref(selected), draft,
                 ctypes.byref(editing), None, None) == 0
    assert draft[0] == 2
    assert editing.value == (0 if task == 0 else 1)
    assert click(task, 0, 1, 0, 0, 0, 0, ctypes.byref(selected), draft,
                 ctypes.byref(editing), None, None) == 0
    assert draft[0] == 2
# Selecting another row, editing trials, and reselecting level preserve
# the digit buffer. Incrementing the already selected level clears it.
selected, editing = ctypes.c_int32(0), ctypes.c_uint8(1)
draft = (I * 5)(42, 1, 1, 1, 0)
for y, row, trials, editing_expected in ((258, 1, 1, 1), (258, 1, 2, 1),
                                         (210, 0, 2, 1), (210, 0, 2, 0)):
    assert click(0, 0, 1, 456, y, 912, 684, ctypes.byref(selected), draft,
                 ctypes.byref(editing), None, None) == 0
    assert (selected.value, draft[1], editing.value) == (row, trials, editing_expected)
for name, params, task in [('algebra', (1, 1, 23), 1), ('scramble', (1, 1, 1, 1, 17), 2)]:
    create = bind('nw_' + name + '_create', [I] * len(params))
    info = bind('nw_' + name + '_info', [I] * 2)
    destroy = bind('nw_' + name + '_destroy', [I])
    handle = create(*params)
    flag = ctypes.c_uint8(1)
    try:
        assert click(task, handle, 0, 0, 0, 0, 0, None, None, ctypes.byref(flag), None, None) == (task == 2)
        assert info(handle, 0) == 1
        if task == 2: assert flag.value == 0
        assert click(task, handle, 0, 0, 0, 0, 0, None, None, ctypes.byref(flag), None, None) == 0
    finally:
        destroy(handle)
print('SDL text-task clicks: options and controller starts pass')
create = bind('nw_numberology_create', [I] * 4)
info = bind('nw_numberology_info', [I] * 2)
destroy = bind('nw_numberology_destroy', [I])
close = bind('nw_numberology_results_close', [P], None)
handle = create(1000, 1, 0, 19)
manager = (ctypes.c_size_t * 2)()
config = (I * 4)(1000, 1, 0, 0)
with tempfile.TemporaryDirectory() as results_dir:
    previous = os.environ.get('NW_NUMBEROLOGY_RESULTS_DIR')
    os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = results_dir
    try:
        assert click(0, handle, 0, 0, 0, 912, 684, None, None, None, config, manager) == 0
        assert info(handle, 0) == 1 and info(handle, 22) > 1 and manager[0]
        assert info(handle, 21) == 1
        click(0, handle, 0, 650, 319, 912, 684, None, None, None, config, manager)
        assert info(handle, 21) == 2
        click(0, handle, 0, 250, 319, 912, 684, None, None, None, config, manager)
        assert info(handle, 21) == 1
        close(manager)
    finally:
        destroy(handle)
        if previous is None: os.environ.pop('NW_NUMBEROLOGY_RESULTS_DIR', None)
        else: os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = previous
print('SDL Numberology clicks: result manager and paging pass')

tree = ast.parse((pathlib.Path(__file__).with_name('sdl_hub_defaults_native_test.py')).read_text())
cases = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'cases' for t in n.targets))
args = {name: params for _, _, name, params in cases}
args.update(jigsaw=(3, 1, 1, 1, 23), go=(1, 1, 23))
pointer = bind('nw_sdl_dispatch_pointer', [I, I, ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32, I], None)
group = bind('nw_sdl_dispatch_pixel_pointers', [P, I, ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32], None)
for task, name in enumerate(('reflex', 'pursuit', 'jigsaw', 'go', 'ncup_monte', 'tracking', 'two_hands')):
    create = bind('nw_' + name + '_create', [I] * len(args[name]))
    destroy = bind('nw_' + name + '_destroy', [I])
    info = bind('nw_' + name + '_info', [I] * 2)
    action = bind('nw_' + name + '_action', [I] * 4)
    direct, routed = create(*args[name]), create(*args[name])
    handles = (I * 7)(); handles[task] = routed
    try:
        action(direct, 0, 0, 100); action(routed, 0, 0, 100)
        before = [info(routed, f) for f in range(6)]
        group(handles, 1, 456, 342, 912, 684)
        assert before == [info(routed, f) for f in range(6)], name
        if task == 6:
            two_hands_pointer = bind('nw_two_hands_pointer', [I] * 5)
            two_hands_pointer(direct, 500000, 500000, 0, 200)
        else:
            pointer(task, direct, 456, 342, 912, 684, 0)
        group(handles, 0, 456, 342, 912, 684)
        fields = (18, 20, 33, 34) if task == 6 else range(6)
        assert [info(direct, f) for f in fields] == [info(routed, f) for f in fields], name
    finally:
        destroy(direct); destroy(routed)
group(None, 0, 0, 0, 0, 0)
print('SDL pixel-pointer group: all seven routes and event types pass')

word = bind('nw_sdl_word_pointer', [I, I, I, I, I, ctypes.c_float, ctypes.c_float,
            ctypes.c_int32, ctypes.c_int32, P, P], None)
for task in range(2):
    selected = ctypes.c_int32(0); draft = (I * 5)(1, 1, 1, 1, 0)
    for motion, button in ((1, 0), (0, 0), (0, 3)):
        word(task, 0, 1, motion, button, 456, 210, 912, 684, ctypes.byref(selected), draft)
        assert draft[0] == 1
    word(task, 0, 1, 0, 1, 456, 210, 912, 684, ctypes.byref(selected), draft)
    assert draft[0] == 2
    # Python accepts the same option row anywhere across a wide window.
    word(task, 0, 1, 0, 2, 10, 420, 2400, 1368, ctypes.byref(selected), draft)
    assert draft[0] == 3
for task, name, params in ((0, 'scrabble', (1, 1, 1, 1, 17)), (1, 'crossword', (1, 1, 1, 1, 23))):
    create, destroy = bind('nw_' + name + '_create', [I] * len(params)), bind('nw_' + name + '_destroy', [I])
    info = bind('nw_' + name + '_info', [I] * 2)
    direct, routed = create(*params), create(*params)
    try:
        for motion, button in ((0, 1), (0, 2), (0, 3), (1, 0)):
            if not motion or task == 0:
                pointer(8 if motion else (7 if task == 0 else 9), direct, 456, 342, 912, 684, int(button == 3))
            word(task, routed, 0, motion, button, 456, 342, 912, 684, None, None)
            assert [info(direct, f) for f in range(6)] == [info(routed, f) for f in range(6)], (name, motion, button)
    finally:
        destroy(direct); destroy(routed)
print('SDL word pointer: option gating and controller routing pass')

syllogism_click = bind('nw_sdl_syllogism_click', [P] * 8 + [ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32], None)
create = bind('nw_syllogism_create', [I] * 6)
info = bind('nw_syllogism_info', [I] * 2)
destroy = bind('nw_syllogism_destroy', [I])
close = bind('nw_syllogism_results_close', [P], None)
with tempfile.TemporaryDirectory() as temp:
    old = {key: os.environ.get(key) for key in ('NW_SYLLOGISM_SETTINGS_PATH', 'NW_SYLLOGISM_RESULTS_DIR')}
    temp = test_environment.name
    handle = I(create(1, 1, 1, 0, 1, 23)); mode, opened, hub = ctypes.c_uint8(1), ctypes.c_uint8(1), ctypes.c_uint8(0)
    selected = I(0); config = (I * 5)(1, 1, 1, 0, 1); draft = (I * 5)(1, 1, 1, 0, 1); manager = (ctypes.c_size_t * 2)()
    def syllable(x, y, w=912, h=684):
        syllogism_click(ctypes.byref(handle), ctypes.byref(mode), ctypes.byref(opened), ctypes.byref(hub),
                        ctypes.byref(selected), config, draft, manager, x, y, w, h)
    try:
        syllable(456, 210); assert draft[0] == 2
        syllable(456, 258); assert selected.value == 1
        syllable(456, 258); assert draft[1] != 1
        syllable(647, 571); assert opened.value == 0 and list(config) == list(draft) and handle.value > 0
        assert pathlib.Path(temp, 'settings').exists()
        syllable(456, 342); assert info(handle.value, 0) == 1 and manager[0]
        close(manager)
        # Keyboard commands share the same option state and apply path.
        opened.value = 1; selected.value = 0
        key = bind('nw_sdl_syllogism_key', [P] * 8 + [I], None)
        def press(symbol):
            key(ctypes.byref(handle), ctypes.byref(mode), ctypes.byref(opened), ctypes.byref(hub),
                ctypes.byref(selected), config, draft, manager, symbol)
        press(1073741905); assert selected.value == 1
        previous_trials = draft[1]
        press(1073741903); assert draft[1] != previous_trials
        press(13); assert opened.value == 0 and list(config) == list(draft)
        assert_seeded_options('syllogism', handle.value, (*config, 23))
        opened.value = 1; hub.value = 1
        syllable(265, 571); assert (handle.value, mode.value, opened.value, hub.value) == (0, 0, 0, 0)
    finally:
        if handle.value: destroy(handle.value)
        for key, value in old.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
print('SDL Syllogism clicks: option selection, apply, trial start, and hub exit pass')

word_key = bind('nw_sdl_word_key', [I, P, P, P, P, P, P, P, I], None)
for task, name, params in ((0, 'scrabble', (1, 1, 1, 1, 17)), (1, 'crossword', (1, 1, 1, 1, 23))):
    create, destroy = bind('nw_' + name + '_create', [I] * len(params)), bind('nw_' + name + '_destroy', [I])
    info = bind('nw_' + name + '_info', [I] * 2)
    handle = I(create(*params)); mode, opened, hub = ctypes.c_uint8(1), ctypes.c_uint8(0), ctypes.c_uint8(0)
    selected = ctypes.c_int32(0); config = (I * 4)(1, 1, 1, 1); draft = (I * 4)()
    def press(key):
        word_key(task, ctypes.byref(handle), ctypes.byref(mode), ctypes.byref(opened), ctypes.byref(hub),
                 ctypes.byref(selected), config, draft, key)
    try:
        press(111); assert opened.value == 1 and list(draft) == list(config)
        press(1073741903); assert draft[0] == 2
        press(13); assert opened.value == 0 and list(config) == list(draft)
        assert pathlib.Path(test_environment.name, name).exists()
        direct = create(2, *params[1:])
        action = bind('nw_' + name + '_action', [I] * 4)
        try:
            action(direct, 0, 0, 100)
            if task == 0 and info(direct, 0) == 1: action(direct, 10, 0, 100)
            press(32)
            assert info(handle.value, 0) == info(direct, 0)
        finally:
            destroy(direct)
        if task == 0:
            opened.value = 1; hub.value = 1
            press(13); assert handle.value == 0 and mode.value == 0 and hub.value == 0
    finally:
        if handle.value: destroy(handle.value)
print('SDL word keys: settings, start, and hub cleanup pass')

scramble_key = bind('nw_sdl_scramble_key', [P] * 8 + [I, I], ctypes.c_int32)
create = bind('nw_scramble_create', [I] * 5)
info = bind('nw_scramble_info', [I] * 2)
destroy = bind('nw_scramble_destroy', [I])
handle = I(create(1, 1, 1, 1, 17)); mode, opened, hub, suppress = (ctypes.c_uint8(v) for v in (1, 0, 0, 0))
selected = ctypes.c_int32(0); config = (I * 4)(1, 1, 1, 1); draft = (I * 4)()
def press_scramble(symbol, paste=0):
    return scramble_key(ctypes.byref(handle), ctypes.byref(mode), ctypes.byref(opened), ctypes.byref(hub),
                        ctypes.byref(selected), config, draft, ctypes.byref(suppress), symbol, paste)
try:
    assert press_scramble(111) == 2 and opened.value == 1
    assert press_scramble(1073741903) == 0 and draft[0] == 2
    assert press_scramble(13) == 0 and opened.value == 0 and config[0] == 2
    assert pathlib.Path(test_environment.name, 'scramble').exists()
    assert press_scramble(32) == 1 and info(handle.value, 0) == 1 and suppress.value == 1
    dispatch(handle.value, 2, 0, 0, b'', 200, ctypes.byref(suppress), None, None, None)
    assert suppress.value == 1
    press_scramble(118, paste=1)
    assert suppress.value == 0 and info(handle.value, 5) == 3
    result = press_scramble(1073741912)
    assert result == (2 if info(handle.value, 0) != 1 else 0)
    opened.value = 1; hub.value = 1
    assert press_scramble(13) == 0 and handle.value == 0 and mode.value == 0 and hub.value == 0
finally:
    if handle.value: destroy(handle.value)
print('SDL Scramble keys: settings, text input, submit, and hub cleanup pass')

algebra_key = bind('nw_sdl_algebra_key', [P] * 7 + [I, I], None)
create = bind('nw_algebra_create', [I] * 3)
info = bind('nw_algebra_info', [I] * 2)
destroy = bind('nw_algebra_destroy', [I])
handle = I(create(1, 1, 23)); mode, opened, hub = (ctypes.c_uint8(v) for v in (1, 0, 0))
selected = ctypes.c_int32(0); config = (I * 4)(1, 1, 1, 1); draft = (I * 4)()
def press_algebra(symbol):
    algebra_key(ctypes.byref(handle), ctypes.byref(mode), ctypes.byref(opened), ctypes.byref(hub),
                ctypes.byref(selected), config, draft, symbol, 0)
try:
    press_algebra(111); assert opened.value == 1 and list(draft) == list(config)
    press_algebra(1073741903); assert draft[0] == 2
    press_algebra(13); assert opened.value == 0 and config[0] == 2
    assert pathlib.Path(test_environment.name, 'algebra').exists()
    assert_seeded_options('algebra', handle.value, (*config, 23), 'create_options')
    opened.value = 1
    press_algebra(13)
    press_algebra(32); assert info(handle.value, 0) == 1
    dispatch(handle.value, 1, 0, 0, b'12', 200, None, None, None, None)
    assert info(handle.value, 6) == 2
    press_algebra(8); assert info(handle.value, 6) == 1
    press_algebra(127); assert info(handle.value, 6) == 0
    opened.value = 1; hub.value = 1
    press_algebra(13); assert handle.value == 0 and mode.value == 0 and hub.value == 0
finally:
    if handle.value: destroy(handle.value)
print('SDL Algebra keys: settings, start, editing, and hub cleanup pass')

number_key = bind('nw_sdl_numberology_key', [P] * 10 + [I, I], ctypes.c_int32)
create = bind('nw_numberology_create', [I] * 4)
info = bind('nw_numberology_info', [I] * 2)
destroy = bind('nw_numberology_destroy', [I])
close = bind('nw_numberology_results_close', [P], None)
handle = I(create(1, 1, 0, 23)); mode, opened, hub, editing = (ctypes.c_uint8(v) for v in (1, 0, 0, 0))
selected = ctypes.c_int32(0); config = (I * 4)(1, 1, 0, 0); draft = (I * 4)(); edit_value = I(0); manager = (ctypes.c_size_t * 2)()
def press_number(symbol):
    return number_key(ctypes.byref(handle), ctypes.byref(mode), ctypes.byref(opened), ctypes.byref(hub),
                      ctypes.byref(selected), config, draft, ctypes.byref(editing), ctypes.byref(edit_value), manager, symbol, 0)
try:
    assert press_number(111) == 0 and opened.value == 1
    dispatch(handle.value, 0, 1, 0, b'123', 0, None, draft, ctypes.byref(editing), ctypes.byref(edit_value))
    assert (draft[0], editing.value) == (123, 1)
    press_number(0x40000052)
    assert (selected.value, draft[0], editing.value) == (0, 123, 0)
    selected.value = 2; editing.value = 1
    press_number(0x40000051)
    assert (selected.value, draft[0], editing.value) == (2, 123, 0)
    selected.value = 0
    press_number(8); assert draft[0] == 12
    press_number(13); assert opened.value == 0 and config[0] == 12
    assert pathlib.Path(test_environment.name, 'numberology').exists()
    assert_seeded_options('numberology', handle.value, (config[0], config[1], config[3], 23))
    opened.value = 1
    press_number(13)
    press_number(32); assert info(handle.value, 0) == 1 and manager[0]
    dispatch(handle.value, 0, 0, 0, b'1', 200, None, None, None, None)
    press_number(13); assert info(handle.value, 0) == 2
    close(manager)
    opened.value = 1; hub.value = 1
    assert press_number(13) == 1 and handle.value == 0 and mode.value == 0 and hub.value == 0
finally:
    if handle.value: destroy(handle.value)
print('SDL Numberology keys: settings, editing, results, and hub cleanup pass')

cancel = bind('nw_sdl_cancel_options', [P, I], ctypes.c_int32)
for index, (name, params) in enumerate((('syllogism', (1, 1, 1, 0, 1, 23)), ('numberology', (1, 1, 0, 23)),
                                        ('algebra', (1, 1, 23)), ('scramble', (1, 1, 1, 1, 17)),
                                        ('scrabble', (1, 1, 1, 1, 17)), ('crossword', (1, 1, 1, 1, 23)))):
    create = bind('nw_' + name + '_create', [I] * len(params)); destroy = bind('nw_' + name + '_destroy', [I])
    handle = I(create(*params)); mode, opened, hub = (ctypes.c_uint8(1) for _ in range(3))
    rows = (ctypes.c_size_t * 24)()
    for offset, obj in enumerate((handle, mode, opened, hub)):
        rows[index * 4 + offset] = ctypes.addressof(obj) if offset < 3 or index < 5 else 0
    try:
        assert cancel(rows, 32) == 0 and opened.value == 1
        assert cancel(rows, 27) == (2 if index in (1, 2) else 1)
        assert opened.value == 0
        if index < 5: assert handle.value == 0 and mode.value == 0 and hub.value == 0
        else: assert handle.value > 0 and mode.value == 1
    finally:
        if handle.value: destroy(handle.value)
    handle = I(create(*params)); mode, opened, hub = (ctypes.c_uint8(v) for v in (1, 1, 0))
    rows = (ctypes.c_size_t * 24)()
    for offset, obj in enumerate((handle, mode, opened, hub)):
        rows[index * 4 + offset] = ctypes.addressof(obj) if offset < 3 or index < 5 else 0
    try:
        assert cancel(rows, 27) == 1 and opened.value == 0 and handle.value > 0 and mode.value == 1
    finally:
        destroy(handle.value)
assert cancel(None, 27) == 0
print('SDL option cancellation: six tasks, hub ownership, and text-input cleanup pass')

exit_hub = bind('nw_sdl_exit_hub_task', [P, I], ctypes.c_int32)
hub_names = ('you_are_here', 'sokoban', 'monkey_ladder', 'nback3d', 'marble', 'tetris', 'count', 'mr_time', 'graph_mapping', 'matrix_reasoning', 'in_the_dark', 'fog', 'removals', 'custody', 'concentration', 'recognition', 'trivia', 'reflex', 'algebra', 'syllogism', 'numberology', 'jigsaw', 'sudoku', 'go', 'crossed_wires', 'scramble', 'scrabble', 'crossword', 'ncup_monte', 'tracking', 'lookout', 'pursuit', 'out_of_sight', 'buzz_wire', 'donkey', 'two_hands', 'overrun')
args.update(algebra=(1, 1, 23), numberology=(1, 1, 1, 23), jigsaw=(3, 1, 1, 1, 23),
            sudoku=(1, 1, 1, 1, 23), go=(1, 1, 23), crossword=(1, 1, 1, 1, 23),
            crossed_wires=(1, 1, 1, 1, 23), syllogism=(1, 1, 1, 0, 1, 17),
            scramble=(1, 1, 1, 1, 17), scrabble=(1, 1, 1, 1, 17))
for index, name in enumerate(hub_names):
    create = bind('nw_' + name + '_create', [I] * len(args[name]))
    handle, mode = I(create(*args[name])), ctypes.c_uint8(1)
    assert handle.value > 0, name
    rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
    rows[2 * index], rows[2 * index + 1] = ctypes.addressof(handle), ctypes.addressof(mode)
    assert exit_hub(rows, 0) == 0 and handle.value > 0 and mode.value == 1
    assert exit_hub(rows, 1) == (2 if index in (18, 20, 25) else 1), name
    assert handle.value == 0 and mode.value == 0, name
    assert exit_hub(rows, 1) == 0
assert exit_hub(None, 1) == 0
print('SDL task-hub exit: all 37 controllers and text-input requests pass')

launch = bind('nw_sdl_launch_hub', [I, I, P, P, P, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, P], ctypes.c_int32)
screen_options = (I * 39)(3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0,
                            1, 1, 1, 1, 1, 1, 1, 0, 1)
for target, request, expected_input in ((20, 0, 1), (20, 1, 0), (22, 0, 1), (22, 1, 1)):
    handles, modes, rows = (ctypes.c_size_t * 39)(), (ctypes.c_size_t * 39)(), (ctypes.c_size_t * 30)()
    handle, mode = I(0), ctypes.c_uint8(0)
    handles[target], modes[target] = ctypes.addressof(handle), ctypes.addressof(mode)
    config, draft = (I * 5)(1, 1, 0, 0, 1), (I * 5)()
    selected, opened, hub, editing = ctypes.c_int32(3), ctypes.c_uint8(0), ctypes.c_uint8(0), ctypes.c_uint8(1)
    row = 2 if target == 20 else 4
    for at, obj in enumerate((config, draft, selected, opened, hub, editing)):
        rows[row * 6 + at] = ctypes.addressof(obj)
    assert launch(target, request, handles, modes, screen_options, None, None, None, rows) == expected_input
    assert handle.value > 0 and mode.value == 1
    if request:
        assert opened.value == hub.value == 1 and selected.value == 0 and list(draft)[:4] == list(config)[:4]
        if target == 22: assert editing.value == 0
    destroy = bind('nw_' + ('algebra' if target == 20 else 'numberology') + '_destroy', [I])
    destroy(handle.value)
handles, modes, rows = (ctypes.c_size_t * 39)(), (ctypes.c_size_t * 39)(), (ctypes.c_size_t * 30)()
handle, mode = I(123), ctypes.c_uint8(1)
handles[27], modes[27] = ctypes.addressof(handle), ctypes.addressof(mode)
missing = os.fsencode(pathlib.Path(test_environment.name, 'missing-lexicon'))
assert launch(27, 1, handles, modes, screen_options, missing, None, None, rows) == 0
assert handle.value == 0 and mode.value == 0
print('SDL hub launch: text-input requests, option state, and failed creation pass')

fallback_key = bind('nw_sdl_fallback_key', [I, P, P], None)
fallback_frame = bind('nw_sdl_fallback_frame', [I, I, P, P, P], None)
playing, step, last, trial = ctypes.c_uint8(0), ctypes.c_uint8(0), ctypes.c_uint64(0), I(4)
fallback_key(32, ctypes.byref(playing), ctypes.byref(step)); assert playing.value == 1
fallback_key(32, ctypes.byref(playing), ctypes.byref(step)); assert playing.value == 0
fallback_key(1073741903, ctypes.byref(playing), ctypes.byref(step)); assert step.value == 1
fallback_frame(0, 0, ctypes.byref(step), ctypes.byref(last), ctypes.byref(trial)); assert trial.value == 5
step.value = 0
fallback_frame(1, 1, ctypes.byref(step), ctypes.byref(last), ctypes.byref(trial)); assert (trial.value, last.value) == (5, 0)
print('SDL fallback: playback toggles, manual steps, and maze timing pass')

collect = bind('nw_sdl_collect_active', [P, P, P], None)
frame_slots = list(range(19)) + [34, 19, 20, 21, 22, 24, 35, 36, 23] + list(range(25, 34)) + list(range(37, TASK_SLOTS))
timed_indices = (2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 17, 28, 29, 30, 31, 32, 33, 34, 35, 36, 42)
assert len(frame_slots) == TASK_SLOTS
for index in range(TASK_SLOTS):
    h, mode = I(100 + index), ctypes.c_uint8(1)
    rows = (ctypes.c_size_t * (2 * TASK_SLOTS))(); rows[2 * index], rows[2 * index + 1] = ctypes.addressof(h), ctypes.addressof(mode)
    frames, timed = (I * TASK_SLOTS)(*([-1] * TASK_SLOTS)), (I * 23)(*([-1] * 23))
    collect(rows, frames, timed)
    assert frames[frame_slots[index]] == h.value and sum(v != 0 for v in frames) == 1, index
    if index in timed_indices:
        assert timed[timed_indices.index(index)] == h.value and sum(v != 0 for v in timed) == 1, index
    else: assert not any(timed), index
    mode.value = 0; collect(rows, frames, timed)
    assert not any(frames) and not any(timed), index
print('SDL active snapshots: all frame and timer slots pass')

routing = bind('nw_sdl_collect_routing', [P, P, P], None)
key_indices = (6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 3, 11, 5, 0, 1, 2, 21, 22, None, 28, 29, 30, 31, 32, 33, 34, 35, 36, 24)
pointer_indices = (17, 31, 21, 23, 28, 29, 35)
for index in range(43):
    handle, mode = I(100 + index), ctypes.c_uint8(1)
    rows = (ctypes.c_size_t * (2 * TASK_SLOTS))(); rows[2 * index], rows[2 * index + 1] = ctypes.addressof(handle), ctypes.addressof(mode)
    keys, pointers = (I * 30)(), (I * 7)()
    routing(rows, keys, pointers)
    if index in key_indices:
        assert keys[key_indices.index(index)] == handle.value and sum(v != 0 for v in keys) == 1, index
    else: assert not any(keys), index
    if index in pointer_indices:
        assert pointers[pointer_indices.index(index)] == handle.value and sum(v != 0 for v in pointers) == 1, index
    else: assert not any(pointers), index
    mode.value = 0; routing(rows, keys, pointers)
    assert not any(keys) and not any(pointers), index
print('SDL active routing: all key and pointer slots pass')

collect_options = bind('nw_sdl_collect_frame_options', [P, P], None)
rows = (ctypes.c_size_t * 18)(); keeps = []
for row in range(6):
    opened = ctypes.c_uint8(row % 2)
    selected = I(row + 10) if row == 0 else ctypes.c_int32(row + 10)
    draft = (I * 5)(*(row * 10 + j + 1 for j in range(5)))
    keeps.append((opened, selected, draft))
    for at, obj in enumerate((opened, selected, draft)): rows[row * 3 + at] = ctypes.addressof(obj)
options = (I * 42)()
collect_options(rows, options)
for row, (opened, selected, draft) in enumerate(keeps):
    expected = [opened.value, selected.value] + (list(draft) if row == 0 else
               [draft[0], draft[1], draft[3], 0, 0] if row == 1 else
               [draft[0], draft[1], draft[2], draft[3], 0])
    assert list(options[row * 7:row * 7 + 7]) == expected, row
rows[6] = 0
collect_options(rows, options)
assert list(options[14:21]) == [0] * 7
print('SDL frame options: six overlay snapshots pass')

parse_configs = bind('nw_sdl_parse_configs', [I, P, P, P, P], ctypes.c_int32)
parse_task = bind('nw_task_settings_parse', [I, I, P, P, P, I], ctypes.c_int32)
parse_syll = bind('nw_syllogism_options_parse', [I, P, P, I])
parse_number = bind('nw_numberology_options_parse', [I, P, P, P, I], ctypes.c_int32)
args_bytes = [b'nw-sdl3', b'--crossword-level', b'4', b'--scrabble-trials', b'3',
              b'--numberology-level', b'12', b'--algebra-no-working', b'--scramble-level', b'8',
              b'--scramble-index', b'example-index', b'--scramble-sentences', b'example-sentences']
argv = (ctypes.c_char_p * len(args_bytes))(*args_bytes)
configs = [(I * 5)() for _ in range(6)]
paths = [ctypes.c_void_p() for _ in range(6)]
rows = (ctypes.c_size_t * 12)()
for row in range(6):
    rows[row * 2] = ctypes.addressof(configs[row])
    rows[row * 2 + 1] = ctypes.addressof(paths[row]) if row != 2 else 0
index, sentences = ctypes.c_void_p(), ctypes.c_void_p()
assert parse_configs(len(args_bytes), argv, rows, ctypes.byref(index), ctypes.byref(sentences)) == 0
assert ctypes.string_at(index) == b'example-index' and ctypes.string_at(sentences) == b'example-sentences'
for row, task in ((0, 0), (1, 1), (4, 2), (5, 3)):
    expected, path = (I * 5)(), ctypes.c_void_p()
    assert parse_task(task, len(args_bytes), argv, expected, ctypes.byref(path), 1) == 0
    assert list(configs[row])[:4] == list(expected)[:4] and paths[row].value == path.value
expected = (I * 5)(); assert parse_syll(len(args_bytes), argv, expected, 1) == 0
assert list(configs[2]) == list(expected)
expected, path = (I * 5)(), ctypes.c_void_p()
assert parse_number(len(args_bytes), argv, expected, ctypes.byref(path), 1) == 0
assert list(configs[3])[:4] == list(expected)[:4] and paths[3].value == path.value
invalid = (ctypes.c_char_p * 3)(b'nw-sdl3', b'--algebra-level', b'999')
assert parse_configs(3, invalid, rows, ctypes.byref(index), ctypes.byref(sentences)) == 2
print('SDL startup configs: combined parsing matches individual parsers and rejects invalid options')

collect_screen = bind('nw_sdl_collect_screen_options', [P, P, P], None)
tasks = (I * 15)(*range(100, 115))
configs = [(I * 5)(*(row * 10 + j for j in range(5))) for row in range(6)]
rows = (ctypes.c_size_t * 12)()
for row, config in enumerate(configs): rows[row * 2] = ctypes.addressof(config)
output = (I * 39)()
collect_screen(tasks, rows, output)
expected = list(tasks[4:9]) + list(tasks[:4]) + list(tasks[9:15])
expected += list(configs[0])[:4] + list(configs[1])[:4] + list(configs[4])[:4]
expected += [configs[3][0], configs[3][1], configs[3][3]] + list(configs[5])[:4] + list(configs[2])
assert list(output) == expected
print('SDL screen options: parsed task and saved configuration fields pass')

start_screen = bind('nw_sdl_start_screen', [I, P, P, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int32)
options = (I * 39)(3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0,
                    1, 1, 1, 1, 1, 1, 1, 0, 1)
for screen in range(2, 39):
    row = 26 if screen == 27 else 25 if screen == 28 else screen - 2
    handle, mode = I(0), ctypes.c_uint8(0); rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
    rows[2 * row], rows[2 * row + 1] = ctypes.addressof(handle), ctypes.addressof(mode)
    assert start_screen(screen, rows, options, None, None, None) == (1 if screen in (20, 22) else 0), screen
    assert handle.value > 0 and mode.value == 1, screen
    assert exit_hub(rows, 1) in (1, 2)
    assert handle.value == 0 and mode.value == 0
assert start_screen(0, None, None, None, None, None) == 0
assert start_screen(1, None, None, None, None, None) == 0
handle, mode, rows = I(0), ctypes.c_uint8(0), (ctypes.c_size_t * (2 * TASK_SLOTS))()
rows[52], rows[53] = ctypes.addressof(handle), ctypes.addressof(mode)
assert start_screen(27, rows, options, missing, None, None) == -1
assert handle.value == 0 and mode.value == 0
print('SDL direct startup: 37 screens, text input, and failed creation pass')

shutdown_rows = bind('nw_sdl_shutdown_rows', [P, P, P], None)
for index, name in enumerate(hub_names):
    create = bind('nw_' + name + '_create', [I] * len(args[name]))
    handle, mode = I(create(*args[name])), ctypes.c_uint8(0)
    assert handle.value > 0, name
    rows = (ctypes.c_size_t * (2 * TASK_SLOTS))(); rows[2 * index], rows[2 * index + 1] = ctypes.addressof(handle), ctypes.addressof(mode)
    syll, number = (ctypes.c_size_t * 2)(), (ctypes.c_size_t * 2)()
    shutdown_rows(rows, syll, number)
    assert handle.value == 0 and not any(syll) and not any(number), name
    shutdown_rows(rows, syll, number)
syll, number, rows = (ctypes.c_size_t * 2)(), (ctypes.c_size_t * 2)(), (ctypes.c_size_t * (2 * TASK_SLOTS))()
start_syll = bind('nw_syllogism_results_start', [P, P], None)
start_number = bind('nw_numberology_results_start', [P, I, I, ctypes.c_int32], None)
options = (I * 5)(1, 1, 1, 0, 1)
start_syll(syll, options); start_number(number, 1, 1, 1)
assert syll[0] and number[0]
shutdown_rows(rows, syll, number)
assert not any(syll) and not any(number)
print('SDL shutdown rows: 37 inactive handles and both result managers pass')

text_event = bind('nw_sdl_text_event', [P, ctypes.c_char_p], None)
specs = [('scramble', (1, 1, 1, 1, 17)), ('numberology', (1, 1, 0, 23)), ('algebra', (1, 1, 23))]
handles = [I(bind('nw_' + name + '_create', [I] * len(params))(*params)) for name, params in specs]
modes = [ctypes.c_uint8(0) for _ in specs]
opened = [ctypes.c_uint8(0) for _ in specs]
suppress, selected, level, editing, edit_value = ctypes.c_uint8(1), ctypes.c_int32(0), I(1), ctypes.c_uint8(0), I(0)
entries = (handles[0], modes[0], opened[0], suppress, handles[1], modes[1], opened[1], selected,
           level, editing, edit_value, handles[2], modes[2], opened[2])
rows = (ctypes.c_size_t * 14)(*(ctypes.addressof(obj) for obj in entries))
try:
    for i, (name, _) in enumerate(specs):
        assert handles[i].value > 0
        action = bind('nw_' + name + '_action', [I] * 4)
        info = bind('nw_' + name + '_info', [I] * 2)
        assert action(handles[i].value, 0, 0, 100) == 1
        modes[i].value = 1
        if i == 0:
            for control in (b'\r', b'\n', b'\b', b'\x7f'):
                text_event(rows, control)
            assert info(handles[i].value, 5) == 0
            assert suppress.value == 1
        text_event(rows, b' ab' if i == 0 else b'12')
        assert info(handles[i].value, (5, 16, 6)[i]) == 2, name
        if i == 0: assert suppress.value == 0
        modes[i].value = 0
    modes[1].value = 1; opened[1].value = 1
    text_event(rows, b'47'); assert level.value == 47 and editing.value == 1
    selected.value = 1; text_event(rows, b'99'); assert level.value == 47
    text_event(None, b'x'); text_event(rows, None)
    special_text = bind('nw_sdl_special_text_event', [P, ctypes.c_char_p], None)
    special = (ctypes.c_size_t * 60)()
    for base, fields in ((30, ((0, handles[0]), (1, modes[0]), (2, opened[0]), (7, suppress))),
                         (20, ((0, handles[1]), (1, modes[1]), (2, opened[1]), (4, selected), (6, level), (7, editing), (8, edit_value))),
                         (0, ((0, handles[2]), (1, modes[2]), (2, opened[2])))):
        for offset, obj in fields: special[base + offset] = ctypes.addressof(obj)
    for i, (name, _) in enumerate(specs):
        modes[i].value, opened[i].value = 1, 0
        info = bind('nw_' + name + '_info', [I] * 2); field = (5, 16, 6)[i]
        before = info(handles[i].value, field)
        special_text(special, b'xy' if i == 0 else b'34')
        assert info(handles[i].value, field) == before + 2, name
        modes[i].value = 0
    modes[1].value, opened[1].value, selected.value, editing.value = 1, 1, 0, 0
    special_text(special, b'53'); assert level.value == 53 and editing.value == 1
finally:
    for (name, _), handle in zip(specs, handles):
        bind('nw_' + name + '_destroy', [I])(handle.value)
print('SDL text event: active tasks, suppression, and option editing pass')

active_key = bind('nw_sdl_active_key', [P, P, I, I, P, P], ctypes.c_int32)
direct_key = bind('nw_sdl_dispatch_task_key', [I, I, I], None)
# Every row has valid handle/mode storage, matching the SDL shell's table.
row_handles = [I(0) for _ in range(43)]
row_modes = [ctypes.c_uint8(0) for _ in range(43)]
active_rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
for index in range(43):
    active_rows[index * 2], active_rows[index * 2 + 1] = ctypes.addressof(row_handles[index]), ctypes.addressof(row_modes[index])
special_modes = [ctypes.c_uint8(0) for _ in range(6)]
special_rows = (ctypes.c_size_t * 60)()
for index, mode in enumerate(special_modes): special_rows[index * 10 + 1] = ctypes.addressof(mode)
playing, step = ctypes.c_uint8(0), ctypes.c_uint8(0)
for task, index in [(i, index) for i, index in enumerate(key_indices) if index is not None and i != 13] + [(19, 23), (32, 4)]:
    name = hub_names[index]
    create = bind('nw_' + name + '_create', [I] * len(args[name]))
    destroy = bind('nw_' + name + '_destroy', [I])
    info = bind('nw_' + name + '_info', [I] * 2)
    direct, routed = create(*args[name]), create(*args[name])
    assert direct > 0 and routed > 0, name
    row_handles[index].value, row_modes[index].value = routed, 1
    try:
        for key in (32, 1073741904, 49, 13):
            direct_key(task, direct, key)
            assert active_key(active_rows, special_rows, key, 0, ctypes.byref(playing), ctypes.byref(step)) == 0
            assert [info(direct, field) for field in range(6)] == [info(routed, field) for field in range(6)], (name, key)
    finally:
        row_handles[index].value, row_modes[index].value = 0, 0
        destroy(direct); destroy(routed)
# Verify the special Algebra branch reaches the same option state as its direct handler.
create = bind('nw_algebra_create', [I] * 3); destroy = bind('nw_algebra_destroy', [I])
direct, routed = I(create(1, 1, 23)), I(create(1, 1, 23))
state = []
for handle in (direct, routed):
    mode, opened, hub, selected = ctypes.c_uint8(1), ctypes.c_uint8(0), ctypes.c_uint8(0), ctypes.c_int32(0)
    config, draft = (I * 4)(1, 1, 1, 1), (I * 4)()
    state.append((handle, mode, opened, hub, selected, config, draft))
try:
    a, b = state
    special_rows[0:7] = [ctypes.addressof(obj) for obj in b]
    row_handles[18].value, row_modes[18].value = routed.value, 1
    algebra_key(*(ctypes.byref(x) if not isinstance(x, ctypes.Array) else x for x in a), 111, 0)
    active_key(active_rows, special_rows, 111, 0, ctypes.byref(playing), ctypes.byref(step))
    assert a[2].value == b[2].value == 1 and list(a[6]) == list(b[6])
finally:
    destroy(direct.value); destroy(routed.value)
print('SDL active key: controller priority and Algebra options pass')

create = bind('nw_tetris_create', [I] * len(args['tetris']))
destroy = bind('nw_tetris_destroy', [I])
frame = bind('nw_tetris_frame_write', [I] * 6)
direct, routed = create(*args['tetris']), create(*args['tetris'])
row_handles[5].value, row_modes[5].value = routed, 1
try:
    for key in (32, 1073741904, 1073741903, 13):
        direct_key(13, direct, key)
        active_key(active_rows, special_rows, key, 0, ctypes.byref(playing), ctypes.byref(step))
        one, two = ctypes.create_string_buffer(65536), ctypes.create_string_buffer(65536)
        n1 = frame(ctypes.addressof(one), len(one), direct, 0, 912, 684)
        n2 = frame(ctypes.addressof(two), len(two), routed, 0, 912, 684)
        assert n1 == n2 and one.raw[:n1] == two.raw[:n2], key
finally:
    row_handles[5].value, row_modes[5].value = 0, 0
    destroy(direct); destroy(routed)
print('SDL active key: Tetris frame equivalence passes')

active_pointer = bind('nw_sdl_active_pointer', [P, P, I, I, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int], ctypes.c_int32)
direct_pointer = bind('nw_sdl_dispatch_pointer', [I, I, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int, I], None)
# Compare each pixel-coordinate route with the pre-existing direct dispatcher.
row_handles = [I(0) for _ in range(43)]
row_modes = [ctypes.c_uint8(0) for _ in range(43)]
active_rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
for index in range(43):
    active_rows[index * 2], active_rows[index * 2 + 1] = ctypes.addressof(row_handles[index]), ctypes.addressof(row_modes[index])
special_modes = [ctypes.c_uint8(0) for _ in range(6)]
special_rows = (ctypes.c_size_t * 60)()
for index, mode in enumerate(special_modes): special_rows[index * 10 + 1] = ctypes.addressof(mode)
for task, index in enumerate((17, 31, 21, 23, 28, 29, 35)):
    name = hub_names[index]
    create = bind('nw_' + name + '_create', [I] * len(args[name]))
    destroy = bind('nw_' + name + '_destroy', [I])
    info = bind('nw_' + name + '_info', [I] * 2)
    direct, routed = create(*args[name]), create(*args[name])
    assert direct > 0 and routed > 0, name
    row_handles[index].value, row_modes[index].value = routed, 1
    try:
        motion = 0
        for x, y in ((180, 160), (450, 310)):
            direct_pointer(task, direct, x * 2, y * 2, 1824, 1368, 0)
            assert active_pointer(active_rows, special_rows, motion, 0 if motion else 1, x, y, 1824, 1368, 912, 684) == 0
            assert [info(direct, field) for field in range(6)] == [info(routed, field) for field in range(6)], (name, x, y)
    finally:
        row_handles[index].value, row_modes[index].value = 0, 0
        destroy(direct); destroy(routed)
print('SDL active pointer: pixel controller routes pass')
# Compare option clicks and Scramble's text-input request through the combined route.
word_pointer = bind('nw_sdl_word_pointer', [I, I, I, I, I, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int, P, P], None)
for row, task in ((0, 1), (2, 0), (3, 2), (4, 0), (5, 1)):
    handle = I(0); mode = ctypes.c_uint8(1); opened = ctypes.c_uint8(1)
    selected_direct, selected_routed = ctypes.c_int32(0), ctypes.c_int32(0)
    draft_direct, draft_routed = (I * 5)(1, 1, 1, 1, 0), (I * 5)(1, 1, 1, 1, 0)
    editing_direct, editing_routed = ctypes.c_uint8(1), ctypes.c_uint8(1)
    offset = row * 10
    special_rows[offset:offset + 3] = [ctypes.addressof(handle), ctypes.addressof(mode), ctypes.addressof(opened)]
    special_rows[offset + 4] = ctypes.addressof(selected_routed)
    special_rows[offset + 6] = ctypes.addressof(draft_routed)
    special_rows[offset + 7] = ctypes.addressof(editing_routed)
    try:
        if row < 4:
            click(task, 0, 1, 456, 210, 912, 684, ctypes.byref(selected_direct), draft_direct, ctypes.byref(editing_direct), None, None)
        else:
            word_pointer(task, 0, 1, 0, 1, 456, 210, 912, 684, ctypes.byref(selected_direct), draft_direct)
        assert active_pointer(active_rows, special_rows, 0, 3, 1200, 420, 2400, 1368, 2400, 1368) == 0
        assert draft_routed[0] == 1
        assert active_pointer(active_rows, special_rows, 0, 2, 1200, 420, 2400, 1368, 2400, 1368) == 0
        assert selected_direct.value == selected_routed.value and list(draft_direct) == list(draft_routed), row
        if row == 2: assert editing_direct.value == editing_routed.value
    finally:
        special_rows[offset + 1] = ctypes.addressof(special_modes[row])
create = bind('nw_scramble_create', [I] * 5)
info = bind('nw_scramble_info', [I] * 2)
destroy = bind('nw_scramble_destroy', [I])
handle = I(create(1, 1, 1, 1, 17)); mode = ctypes.c_uint8(1); opened = ctypes.c_uint8(0)
selected = ctypes.c_int32(0); draft = (I * 5)(); suppress = ctypes.c_uint8(1)
special_rows[30:38] = [ctypes.addressof(handle), ctypes.addressof(mode), ctypes.addressof(opened), 0,
                        ctypes.addressof(selected), 0, ctypes.addressof(draft), ctypes.addressof(suppress)]
try:
    assert active_pointer(active_rows, special_rows, 0, 3, 0, 0, 912, 684, 912, 684) == 1
    assert info(handle.value, 0) == 1 and suppress.value == 0
finally:
    destroy(handle.value)
print('SDL active pointer: option clicks and Scramble text input pass')

# The offscreen path advances nine 30 Hz ticks from its supplied start time.
advance_screenshot = bind('nw_sdl_advance_screenshot', [P, P], None)
create_marble = bind('nw_marble_create', [I] * 6)
destroy_marble = bind('nw_marble_destroy', [I])
marble_action = bind('nw_marble_action', [I] * 4)
marble_advance = bind('nw_marble_advance', [I] * 2)
marble_info = bind('nw_marble_info', [I] * 2)
direct, offscreen = (create_marble(3, 1, 0, 2600, 0, 42) for _ in range(2))
try:
    assert direct > 0 and offscreen > 0
    for handle in (direct, offscreen):
        assert marble_action(handle, 0, 0, 0) == 1
    previous = 0
    for frame in range(1, 10):
        elapsed = frame * 1000 // 30
        marble_advance(direct, elapsed - previous)
        previous = elapsed
    timed = (I * 23)()
    timed[2] = offscreen
    clock = ctypes.c_uint64(1000)
    advance_screenshot(timed, ctypes.byref(clock))
    assert clock.value == 1300
    assert [marble_info(direct, field) for field in range(12)] == [
        marble_info(offscreen, field) for field in range(12)]
finally:
    destroy_marble(direct)
    destroy_marble(offscreen)

active_release = bind('nw_sdl_active_release', [P, I, I], None)
direct_release = bind('nw_sdl_dispatch_key_release', [I, I, I], None)
for task, index, name in ((33, 4, 'marble'), (25, 33, 'buzz_wire')):
    create = bind('nw_' + name + '_create', [I] * len(args[name]))
    destroy = bind('nw_' + name + '_destroy', [I])
    info = bind('nw_' + name + '_info', [I] * 2)
    direct, routed = create(*args[name]), create(*args[name])
    row_handles[index].value, row_modes[index].value = routed, 1
    try:
        for key in (0x40000052, 0x40000050, 0x40000051, 0x4000004f):
            direct_key(32 if task == 33 else 25, direct, key)
            direct_key(32 if task == 33 else 25, routed, key)
            direct_release(task, direct, key)
            active_release(active_rows, 0, key)
            fields = range(12) if task == 33 else range(6)
            assert [info(direct, f) for f in fields] == [info(routed, f) for f in fields], (name, key)
        if task == 33:
            for key in (0x40000052, 0x40000050, 0x40000051, 0x4000004f):
                direct_key(32, routed, key)
            active_release(active_rows, 1, 0)
            assert info(routed, 11) == 0
    finally:
        row_handles[index].value, row_modes[index].value = 0, 0
        destroy(direct); destroy(routed)
print('SDL active release: key-up routing and focus loss pass')

# The shell stores task state contiguously; each bound row must point to its own cell.
bind_rows = bind('nw_sdl_bind_rows', [P, P, P], None)
handles = (I * TASK_SLOTS)(*range(TASK_SLOTS)); modes = (ctypes.c_uint8 * TASK_SLOTS)(*([1] * TASK_SLOTS)); rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
bind_rows(handles, modes, rows)
for index in range(TASK_SLOTS):
    assert rows[index * 2] == ctypes.addressof(handles) + index * ctypes.sizeof(I)
    assert rows[index * 2 + 1] == ctypes.addressof(modes) + index
    ctypes.c_int64.from_address(rows[index * 2]).value += 100
    ctypes.c_uint8.from_address(rows[index * 2 + 1]).value = 0
    assert handles[index] == index + 100 and modes[index] == 0
bind_rows(None, modes, rows); bind_rows(handles, None, rows); bind_rows(handles, modes, None)
print(f'SDL state rows: all {TASK_SLOTS} handle and mode addresses pass')

# Overlay snapshots derive from the same state rows as event dispatch.
special_frame = bind('nw_sdl_special_frame_options', [P, P], None)
rows = (ctypes.c_size_t * 60)(); legacy = (ctypes.c_size_t * 18)()
opened = [ctypes.c_uint8(i % 2) for i in range(6)]
selected = [ctypes.c_int32(i + 1) for i in range(6)]; selected[1] = I(2)
drafts = [(I * 5)(i + 1, i + 2, i + 3, i + 4, i + 5) for i in range(6)]
for i in range(6):
    rows[i * 10 + 2], rows[i * 10 + 4], rows[i * 10 + 6] = map(ctypes.addressof, (opened[i], selected[i], drafts[i]))
for dest, source in enumerate((1, 2, 0, 3, 4, 5)):
    legacy[dest * 3:dest * 3 + 3] = [rows[source * 10 + j] for j in (2, 4, 6)]
a, b = (I * 42)(), (I * 42)()
collect_options(legacy, a); special_frame(rows, b)
assert list(a) == list(b)
print('SDL overlay rows: frame snapshots match established ordering')

bind_special = bind('nw_sdl_bind_special_rows', [P] * 11, None)
handles = (I * TASK_SLOTS)(*range(TASK_SLOTS)); modes = (ctypes.c_uint8 * TASK_SLOTS)()
configs = [(I * 5)(*(100 * row + field for field in range(5))) for row in range(6)]
config_rows = (ctypes.c_size_t * 12)()
for row in range(6): config_rows[row * 2] = ctypes.addressof(configs[row])
drafts = (I * 30)(); flags = (ctypes.c_uint8 * 18)(); selections = (ctypes.c_int32 * 6)()
syll_selection, edit_value = I(0), I(0)
syll_results, num_results = (ctypes.c_size_t * 2)(), (ctypes.c_size_t * 2)()
rows = (ctypes.c_size_t * 60)()
bind_special(handles, modes, config_rows, drafts, flags, selections, ctypes.byref(syll_selection),
             ctypes.byref(edit_value), syll_results, num_results, rows)
for row, (task, config) in enumerate(zip((18, 19, 20, 25, 26, 27), (4, 2, 3, 5, 1, 0))):
    base = row * 10; count = 5 if row == 1 else 4
    assert rows[base] == ctypes.addressof(handles) + task * ctypes.sizeof(I)
    assert rows[base + 1] == ctypes.addressof(modes) + task
    assert rows[base + 2] == ctypes.addressof(flags) + row * 3
    assert rows[base + 3] == (ctypes.addressof(flags) + row * 3 + 1 if row != 5 else 0)
    assert rows[base + 4] == (ctypes.addressof(syll_selection) if row == 1 else ctypes.addressof(selections) + row * ctypes.sizeof(ctypes.c_int32))
    assert rows[base + 5] == ctypes.addressof(configs[config])
    assert rows[base + 6] == ctypes.addressof(drafts) + row * 5 * ctypes.sizeof(I)
    assert list(drafts[row * 5:row * 5 + count]) == list(configs[config][:count])
assert rows[17] == ctypes.addressof(syll_results)
assert rows[27] == ctypes.addressof(flags) + 8 and rows[28] == ctypes.addressof(edit_value) and rows[29] == ctypes.addressof(num_results)
assert rows[37] == ctypes.addressof(flags) + 11
print('SDL overlay binding: controller, settings, flags, and results addresses pass')

# Python starts its title session at banner zero; compare all four routed banners.
frame_write = bind('nw_sdl_frame_write', [I, I, P, P, I, I, I, I, I, I])
title_write = bind('nw_title_write', [I] * 6)
handles = (I * TASK_SLOTS)(); options = (I * 42)()
for trial in range(1, 5):
    actual, expected = ctypes.create_string_buffer(65536), ctypes.create_string_buffer(65536)
    a = frame_write(ctypes.addressof(actual), len(actual), handles, options, 912, 684, 0, 0, 0, trial)
    b = title_write(ctypes.addressof(expected), len(expected), trial - 1, 0, 1, 1)
    assert a == b and actual.raw[:a] == expected.raw[:b] and a > 0, trial
print('SDL title frame: one-based trials match Python banner indices')

# Dark-theme selection must reach both title and task frame writers.
handles = (I * TASK_SLOTS)(); options = (I * 42)(); options[41] = 1
actual, expected = ctypes.create_string_buffer(65536), ctypes.create_string_buffer(65536)
a = frame_write(ctypes.addressof(actual), len(actual), handles, options, 912, 684, 0, 0, 0, 1)
b = title_write(ctypes.addressof(expected), len(expected), 0, 1, 1, 1)
assert a == b and a > 0 and actual.raw[:a] == expected.raw[:b]
create = bind('nw_sudoku_create', [I] * 5); destroy = bind('nw_sudoku_destroy', [I])
writer = bind('nw_sudoku_frame_write', [I] * 6)
handle = create(3, 3, 1, 1, 23); assert handle > 0
handles[21] = handle
try:
    a = frame_write(ctypes.addressof(actual), len(actual), handles, options, 912, 684, 0, 0, 0, 1)
    b = writer(ctypes.addressof(expected), len(expected), handle, 1, 912, 684)
    assert a == b and a > 0 and actual.raw[:a] == expected.raw[:b]
finally:
    destroy(handle)
print('SDL dark theme: title and Sudoku frame routing pass')

# Check the actual software-renderer clear color with no frame commands.
create_surface = bind('SDL_CreateSurface', [ctypes.c_int, ctypes.c_int, ctypes.c_uint32], P)
create_renderer = bind('SDL_CreateSoftwareRenderer', [P], P)
read_pixel = bind('SDL_ReadSurfacePixel', [P, ctypes.c_int, ctypes.c_int, P, P, P, P], ctypes.c_bool)
destroy_renderer = bind('SDL_DestroyRenderer', [P], None)
destroy_surface = bind('SDL_DestroySurface', [P], None)
present_theme = bind('nw_sdl_present_frame_theme', [P, P, I, ctypes.c_int, ctypes.c_int, I, I], ctypes.c_int32)
surface = create_surface(912, 684, 0x16762004); assert surface
renderer = create_renderer(surface); assert renderer
try:
    for black, expected in ((0, 255), (1, 0)):
        assert present_theme(renderer, None, 0, 4, 4, 1, black) == 0
        components = [ctypes.c_uint8() for _ in range(4)]
        assert read_pixel(surface, 0, 0, *(ctypes.byref(c) for c in components))
        assert [c.value for c in components] == [expected, expected, expected, 255]
    blend = bind('SDL_SetRenderDrawBlendMode', [P, ctypes.c_uint32], ctypes.c_bool)
    assert blend(renderer, 1)
    frame = ctypes.create_string_buffer(struct.pack('<IIII', 1313426254, 1, 1, 0) +
        struct.pack('<B3xI6fII', 2, 0xff000080, 100, 100, 40, 40, 4, 0, 0x0000ff80, 0))
    assert present_theme(renderer, frame, len(frame) - 1, 912, 684, 1, 1) == 1
    for x, y, channel in ((101, 560, 2), (120, 560, 0)):
        assert read_pixel(surface, x, y, *(ctypes.byref(c) for c in components))
        rgb = [c.value for c in components[:3]]
        assert 127 <= rgb[channel] <= 128 and sum(rgb) == rgb[channel], rgb
    frame = ctypes.create_string_buffer(struct.pack('<IIII', 1313426254, 1, 1, 0) +
        struct.pack('<B3xI6fII', 2, 0xff000080, 100, 100, 40, 40, 4, 0, 0x0000ff40, 0))
    assert present_theme(renderer, frame, len(frame) - 1, 912, 684, 1, 1) == 1
    assert read_pixel(surface, 101, 560, *(ctypes.byref(c) for c in components))
    assert 127 <= components[2].value <= 128
    assert [components[i].value for i in (0, 1, 3)] == [0, 0, 255]
    assert read_pixel(surface, 120, 560, *(ctypes.byref(c) for c in components))
    assert 127 <= components[0].value <= 128 and [c.value for c in components[1:]] == [0, 0, 255]
finally:
    destroy_renderer(renderer); destroy_surface(surface)
print('SDL software backing: light and dark pixels pass')

maze_args = bind('nw_sdl_maze_arguments', [I, P, P], ctypes.c_int32)
start_maze = bind('nw_sdl_start_maze', [I, P, P], ctypes.c_int32)
argv = (ctypes.c_char_p * 10)(b'app', b'--trial', b'3', b'--trials', b'5', b'--seed', b'42', b'--adaptive', b'--show-marks', b'--show-traps')
settings = (I * 6)()
assert maze_args(10, argv, settings) == 0 and list(settings) == [3, 5, 1, 1, 1, 42]
for raw, expected in ((b'0', 0), (b'-1', -1), (b'-9223372036854775808', -9223372036854775808), (b'9223372036854775807', 9223372036854775807)):
    seed_args = (ctypes.c_char_p * 3)(b'app', b'--seed', raw)
    assert maze_args(3, seed_args, settings) == 0 and settings[5] == expected
for raw in (b'-9223372036854775809', b'9223372036854775808', b'-', b'12x'):
    seed_args = (ctypes.c_char_p * 3)(b'app', b'--seed', raw)
    assert maze_args(3, seed_args, settings) == 2
assert maze_args(10, argv, settings) == 0
for screen, name in ((2, 'you_are_here'), (3, 'sokoban')):
    create = bind('nw_' + name + '_create', [I] * 5)
    info = bind('nw_' + name + '_info', [I] * 2)
    destroy = bind('nw_' + name + '_destroy', [I])
    direct = create(3, 5, 1, 1, 42); assert direct > 0
    handles = (I * TASK_SLOTS)(); modes = (ctypes.c_uint8 * TASK_SLOTS)(); rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
    bind_rows(handles, modes, rows)
    try:
        assert start_maze(screen, rows, settings) == 0 and modes[screen - 2] == 1
        routed = handles[screen - 2]
        assert info(routed, 1) == 3, f"{name} should expose the configured starting rung in Ready"
        assert [info(direct, i) for i in range(8)] == [info(routed, i) for i in range(8)]
    finally:
        destroy(direct)
        if handles[screen - 2]: destroy(handles[screen - 2])
print('SDL Maze startup: Python CLI settings and controller state pass')

falls_handles = (I * TASK_SLOTS)()
falls_modes = (ctypes.c_uint8 * TASK_SLOTS)()
falls_rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
falls_options = (I * 42)()
falls_buffer = ctypes.create_string_buffer(65536)
falls_playing, falls_step = ctypes.c_uint8(), ctypes.c_uint8()
falls_special = (ctypes.c_size_t * 66)()
bind_rows(falls_handles, falls_modes, falls_rows)


def falls_frame():
    length = frame_write(ctypes.addressof(falls_buffer), len(falls_buffer), falls_handles,
                         falls_options, 912, 684, 0, 0, 0, 1)
    assert length > 0
    return falls_buffer.raw[:length]


for pointer_answer in (False, True):
    assert start_screen(77, falls_rows, None, None, None, None) == 0
    assert falls_handles[73] > 0 and falls_modes[73] == 1
    try:
        assert b"Press Space to start" in falls_frame()
        assert active_key(falls_rows, falls_special, 32, 0, ctypes.byref(falls_playing),
                          ctypes.byref(falls_step)) == 0
        assert b"Does the tower stand or fall?" in falls_frame()
        if pointer_answer:
            assert active_pointer(falls_rows, falls_special, 0, 1, 0, 0, 912, 684, 912, 684) == 0
            assert b"Does the tower stand or fall?" in falls_frame()
            assert active_pointer(falls_rows, falls_special, 0, 1, 240, 474, 912, 684, 912, 684) == 0
        else:
            assert active_key(falls_rows, falls_special, 49, 0, ctypes.byref(falls_playing),
                              ctypes.byref(falls_step)) == 0
        judged = falls_frame()
        assert b"Right: it " in judged or b"No: it " in judged
    finally:
        assert exit_hub(falls_rows, 1) == 1
        assert falls_handles[73] == 0 and falls_modes[73] == 0
print('SDL Will It Fall?: start, keyboard and pointer answers, verdict, and exit pass')

sfm_handles = (I * TASK_SLOTS)()
sfm_modes = (ctypes.c_uint8 * TASK_SLOTS)()
sfm_rows = (ctypes.c_size_t * (2 * TASK_SLOTS))()
sfm_options = (I * 42)()
sfm_buffer = ctypes.create_string_buffer(65536)
sfm_playing, sfm_step = ctypes.c_uint8(), ctypes.c_uint8()
sfm_special = (ctypes.c_size_t * 66)()
bind_rows(sfm_handles, sfm_modes, sfm_rows)


def sfm_frame():
    length = frame_write(ctypes.addressof(sfm_buffer), len(sfm_buffer), sfm_handles,
                         sfm_options, 912, 684, 0, 0, 0, 1)
    assert length > 0
    return sfm_buffer.raw[:length]


for pointer_answer in (False, True):
    assert start_screen(78, sfm_rows, None, None, None, None) == 0
    assert sfm_handles[74] > 0 and sfm_modes[74] == 1
    try:
        assert b"Press Space or click to start" in sfm_frame()
        assert active_key(sfm_rows, sfm_special, 32, 0, ctypes.byref(sfm_playing),
                          ctypes.byref(sfm_step)) == 0
        assert b"What solid are the dots on?" in sfm_frame()
        if pointer_answer:
            assert active_pointer(sfm_rows, sfm_special, 0, 1, 0, 0, 912, 684, 912, 684) == 0
            assert b"What solid are the dots on?" in sfm_frame()
            assert active_pointer(sfm_rows, sfm_special, 0, 1, 200, 480, 912, 684, 912, 684) == 0
        else:
            assert active_key(sfm_rows, sfm_special, 49, 0, ctypes.byref(sfm_playing),
                              ctypes.byref(sfm_step)) == 0
        judged = sfm_frame()
        assert b"Right: a " in judged or b"No: a " in judged
    finally:
        assert exit_hub(sfm_rows, 1) == 1
        assert sfm_handles[74] == 0 and sfm_modes[74] == 0
print('SDL Shape from Motion: start, keyboard and pointer answers, verdict, and exit pass')
