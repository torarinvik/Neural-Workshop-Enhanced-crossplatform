#!/usr/bin/env python3
"""Exercise the public agent library through its platform shared-library ABI."""
import ctypes
import hashlib
import os
from pathlib import Path
import struct
import sys

from damkeeper_agent_oracle import fixture as dam_keeper_fixture
from dispatch_agent_oracle import fixture as dispatch_fixture

path = Path(sys.argv[1]).resolve(strict=True)
if sys.platform == "win32":
    # Keep the staged SDL3.dll available to the Windows loader.
    dependency_directory = os.add_dll_directory(str(path.parent))
lib = ctypes.CDLL(str(path))
width, height = 912, 684
rgba_size = width * height * 4
verify_outcome_frame = lib.nw_public_outcome_verify_frame
verify_outcome_frame.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64,
                                 ctypes.c_int64, ctypes.c_void_p, ctypes.c_double]
verify_outcome_frame.restype = ctypes.c_int64


class TriagePublication(ctypes.Structure):
    _fields_ = [(field, ctypes.c_int64) for field in (
        "frame_seq", "timestamp_ns", "done", "open_receipt", "outcome_receipt"
    )] + [("outcome_scalar", ctypes.c_double)] + [(field, ctypes.c_int64) for field in (
        "action_port", "receipt_frame_seq", "receipt_timestamp_ns", "trial"
    )] + [("digest", ctypes.c_char * 64), ("stimulus_digest", ctypes.c_char * 64)]


agent_create = lib.nw_triage_agent_create
agent_create.argtypes = [ctypes.c_int64] * 4 + [ctypes.c_double] * 2 + [ctypes.c_int64, ctypes.c_bool]
agent_create.restype = ctypes.c_int64
agent_destroy = lib.nw_triage_agent_destroy
agent_destroy.argtypes = [ctypes.c_int64]
agent_destroy.restype = None
agent_act = lib.nw_triage_agent_act
agent_act.argtypes = [ctypes.c_int64] * 3
agent_act.restype = ctypes.c_int64
agent_publish = lib.nw_triage_agent_publish
agent_publish.argtypes = [ctypes.c_int64, ctypes.c_double, ctypes.c_int64, ctypes.c_void_p,
                          ctypes.c_int64, ctypes.c_int32, ctypes.c_int32, ctypes.c_int64,
                          ctypes.POINTER(TriagePublication)]
agent_publish.restype = ctypes.c_int64
packet = ctypes.create_string_buffer(rgba_size + 36)


def publish(agent, timestamp, dt=0.05, black=0, publish_abi=agent_publish):
    publication = TriagePublication()
    assert publish_abi(agent, dt, timestamp, packet, len(packet), width, height, black,
                         ctypes.byref(publication)) == len(packet)
    assert struct.unpack_from("<4sIQQIII", packet) == (
        b"NWFB", 1, publication.frame_seq, timestamp, width, height, 0)
    assert publication.digest == hashlib.sha256(packet.raw[36:]).hexdigest().encode("ascii")
    return publication


for black, screen in ((0, (222, 226, 231, 255)), (1, (27, 30, 39, 255))):
    visual = agent_create(1, 1, 1, 17, 0, 0, 17, False)
    assert visual
    try:
        publish(visual, 1, black=black)
        # Interior samples from the first Python machine card's header and
        # recessed screen, outside the text and rounded corners.
        for x, y, color in ((120, 126, (86, 118, 196, 255)), (120, 230, screen)):
            offset = 36 + (y * width + x) * 4
            assert tuple(packet.raw[offset:offset + 4]) == color
    finally:
        agent_destroy(visual)

dense_cards = agent_create(30, 1, 0, 17, 0, 0, 17, False)
assert dense_cards
try:
    assert publish(dense_cards, 1).open_receipt == 1
    assert agent_act(dense_cards, 0, 2) == 1
    assert publish(dense_cards, 3).open_receipt == 2
finally:
    agent_destroy(dense_cards)

agent = agent_create(1, 1, 1, 17, 0, 0, 17, False)
assert agent
try:
    assert not agent_act(agent, 0, 0)
    initial = publish(agent, 1)
    assert initial.frame_seq == 1 and initial.open_receipt == 1 and not initial.outcome_receipt
    assert not agent_act(agent, 0, 0)
    idle = publish(agent, 2)
    assert idle.open_receipt == initial.open_receipt
    for index, port in enumerate((0, 8, 9, 1, 9), 1):
        assert agent_act(agent, port, 2 * index + 1) == index
        assert not agent_act(agent, 16, 2 * index + 1)
        result = publish(agent, 2 * index + 2)
        if index < 5:
            assert not result.outcome_receipt and result.open_receipt == index + 1
    assert not result.open_receipt and result.outcome_receipt == 5 and result.outcome_scalar == 1
    assert result.stimulus_digest == initial.digest and result.action_port == 9
    assert result.receipt_frame_seq == 6 and result.receipt_timestamp_ns == 11
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                result.digest, 1.0) == 1
    finished = publish(agent, 13)
    assert finished.done and not finished.open_receipt and not finished.outcome_receipt
finally:
    agent_destroy(agent)

agent = agent_create(12, 2, 1, -17, 0.05, 0.05, 20, False)
assert agent
try:
    initial = publish(agent, 101)
    assert not agent_act(agent, 19, 102)
    dropped = TriagePublication()
    assert not agent_publish(agent, 0.05, 102, packet, len(packet) - 1, width, height, 0,
                             ctypes.byref(dropped))
    flag = publish(agent, 102)
    assert flag.frame_seq == 2 and flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert flag.action_port == -1 and flag.stimulus_digest == initial.digest
    assert not agent_act(agent, 0, 103)
    next_trial = publish(agent, 103)
    assert next_trial.open_receipt == 2 and next_trial.trial == 2 and not next_trial.outcome_receipt
finally:
    agent_destroy(agent)

agent = agent_create(1, 1, 1, 17, 0, 0, 20, True)
assert agent
try:
    initial = publish(agent, 1)
    assert agent_act(agent, 19, 2) == 1
    quiet = publish(agent, 3)
    assert quiet.outcome_receipt == 1 and quiet.outcome_scalar == 0 and quiet.open_receipt == 2
    assert quiet.action_port == 19 and quiet.digest == initial.digest
    assert agent_act(agent, 16, 4) == 2
    assert publish(agent, 5).outcome_scalar == -1
    assert not publish(agent, 6).outcome_receipt
finally:
    agent_destroy(agent)
print("Triage native agent: receipt locking, NWFB pixels, sparse/neutral outcomes, and timeout pass")


delay_create = lib.nw_delay_agent_create
delay_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
delay_create.restype = ctypes.c_int64
delay_destroy = lib.nw_delay_agent_destroy
delay_destroy.argtypes = agent_destroy.argtypes
delay_destroy.restype = None
delay_act = lib.nw_delay_agent_act
delay_act.argtypes = agent_act.argtypes
delay_act.restype = ctypes.c_int64
agent_publish = lib.nw_delay_agent_publish
agent_publish.argtypes = lib.nw_triage_agent_publish.argtypes
agent_publish.restype = ctypes.c_int64

width, height = 456, 342
rgba_size = width * height * 4
packet = ctypes.create_string_buffer(rgba_size + 36)
assert not delay_create(1, 1, 1, 17, 1, False)
delay = delay_create(1, 1, 1, 17, 2, False)
assert delay
try:
    initial = publish(delay, 0, dt=0.0625)
    assert initial.open_receipt == 1
    result = initial
    for tick in range(960):
        if tick % 64 == 0:
            assert delay_act(delay, 1, tick * 2 + 1) == result.open_receipt
            assert not delay_act(delay, 0, tick * 2 + 1)
        result = publish(delay, tick * 2 + 2, dt=0.0625)
        if tick < 959:
            assert not result.outcome_receipt
    assert result.outcome_scalar == 1 and result.outcome_receipt
    assert result.stimulus_digest == initial.digest
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                result.digest, 1.0) == 1
    completed = publish(delay, 1921, dt=0.0625)
    assert completed.done and not completed.outcome_receipt
finally:
    delay_destroy(delay)
print("Delay native agent: 960 clock ticks, receipts, verified win, and completion pass")

stop_create = lib.nw_stop_switch_agent_create
stop_create.argtypes = delay_create.argtypes
stop_create.restype = ctypes.c_int64
stop_destroy = lib.nw_stop_switch_agent_destroy
stop_destroy.argtypes = delay_destroy.argtypes
stop_destroy.restype = None
stop_act = lib.nw_stop_switch_agent_act
stop_act.argtypes = delay_act.argtypes
stop_act.restype = ctypes.c_int64
agent_publish = lib.nw_stop_switch_agent_publish
agent_publish.argtypes = lib.nw_triage_agent_publish.argtypes
agent_publish.restype = ctypes.c_int64

assert not stop_create(1, 1, 1, 17, 1, False)
stop = stop_create(1, 1, 1, 17, 2, False)
assert stop
try:
    stamp = 0
    first = publish(stop, stamp, dt=0.0625)
    assert first.open_receipt == 1
    # Python Random(17) produces this sequence for its first rung-one block.
    for port in (1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0):
        for _ in range(10):
            stamp += 1
            before = publish(stop, stamp, dt=0.0625)
            assert before.open_receipt and not before.outcome_receipt
        stamp += 1
        assert stop_act(stop, port, stamp) == before.open_receipt
        assert not stop_act(stop, 1 - port, stamp)
    verdict = publish(stop, stamp + 1, dt=0.0625)
    assert verdict.outcome_scalar == 1 and verdict.outcome_receipt == before.open_receipt
    assert verdict.stimulus_digest == first.digest and not verdict.done
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                verdict.digest, 1.0) == 1
    completed = publish(stop, stamp + 2, dt=0.0625)
    assert completed.done and not completed.open_receipt and not completed.outcome_receipt
finally:
    stop_destroy(stop)
print("Stop & Switch native agent: seeded answers, one pixel-verified verdict, and completion pass")

hold_create = lib.nw_hold_it_agent_create
hold_create.argtypes = delay_create.argtypes
hold_create.restype = ctypes.c_int64
hold_destroy = lib.nw_hold_it_agent_destroy
hold_destroy.argtypes = delay_destroy.argtypes
hold_destroy.restype = None
hold_act = lib.nw_hold_it_agent_act
hold_act.argtypes = delay_act.argtypes
hold_act.restype = ctypes.c_int64
agent_publish = lib.nw_hold_it_agent_publish
agent_publish.argtypes = lib.nw_triage_agent_publish.argtypes
agent_publish.restype = ctypes.c_int64
hold_audio = lib.nw_hold_it_agent_audio
hold_audio.argtypes = [ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64]
hold_audio.restype = ctypes.c_int64

assert not hold_create(1, 1, 1, 17, 0, False)
hold = hold_create(1, 1, 1, 17, 1, False)
assert hold
pcm = ctypes.create_string_buffer(5520)
try:
    first = result = publish(hold, 0, dt=0.0625)
    assert first.open_receipt == 1
    assert hold_audio(hold, pcm, len(pcm)) == 0
    for tick in range(1, 73):
        if tick > 50:
            assert hold_act(hold, 0, tick * 2 - 1) == result.open_receipt
            assert not hold_act(hold, 0, tick * 2 - 1)
        result = publish(hold, tick * 2, dt=0.0625)
        assert result.open_receipt and not result.outcome_receipt
        assert hold_audio(hold, pcm, len(pcm)) == 5512
        if tick <= 12:
            assert not any(pcm.raw[:5512])
        if tick == 13:
            assert any(pcm.raw[:5512])
        assert hold_audio(hold, pcm, len(pcm)) == 0
    verdict = publish(hold, 146, dt=0.0625)
    assert verdict.outcome_scalar == 1 and verdict.outcome_receipt == result.open_receipt
    assert verdict.stimulus_digest == first.digest and not verdict.done
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                verdict.digest, 1.0) == 1
    completed = publish(hold, 147, dt=0.0625)
    assert completed.done and not completed.open_receipt and not completed.outcome_receipt
    assert hold_audio(hold, pcm, len(pcm)) == 0
finally:
    hold_destroy(hold)
print("Hold It native agent: per-frame hold, elapsed PCM, one pixel-verified verdict, and completion pass")


notebook_create = lib.nw_notebook_agent_create
notebook_create.argtypes = agent_create.argtypes
notebook_create.restype = ctypes.c_int64
notebook_act = lib.nw_notebook_agent_act
notebook_act.argtypes, notebook_act.restype = agent_act.argtypes, agent_act.restype
notebook_destroy = lib.nw_notebook_agent_destroy
notebook_destroy.argtypes, notebook_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
notebook_publish_abi = lib.nw_notebook_agent_publish
notebook_publish_abi.argtypes, notebook_publish_abi.restype = agent_publish.argtypes, agent_publish.restype


def notebook_publish(agent, timestamp):
    return publish(agent, timestamp, publish_abi=notebook_publish_abi)


assert not notebook_create(1, 1, 1, 17, 0, 0, 12, False)
assert not notebook_create(4097, 1, 1, 17, 0, 0, 13, False)
notebook = notebook_create(1, 1, 1, 17, 0, 0, 13, False)
assert notebook
try:
    initial = notebook_publish(notebook, 1)
    assert initial.open_receipt == 1
    assert notebook_act(notebook, 4, 2) == 1
    written = notebook_publish(notebook, 3)
    assert written.open_receipt == 2 and written.digest != initial.digest
    assert notebook_act(notebook, 12, 4) == 2
    question = notebook_publish(notebook, 5)
    assert question.open_receipt == 3 and question.digest != written.digest
    # Python seed 17 offers 604 and the recorded code 112, in that order.
    assert notebook_act(notebook, 1, 6) == 3
    verdict = notebook_publish(notebook, 7)
    assert not verdict.open_receipt and verdict.outcome_receipt == 3
    assert verdict.stimulus_digest == initial.digest and verdict.action_port == 1
    assert verdict.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                verdict.digest, verdict.outcome_scalar) == 1
    assert notebook_publish(notebook, 8).done
finally:
    notebook_destroy(notebook)

notebook = notebook_create(2, 2, 1, 17, 0.1, 0.05, 13, False)
assert notebook
try:
    assert notebook_publish(notebook, 1).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not notebook_publish(notebook, 2).outcome_receipt
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert packet.raw[36 + width * 3:40 + width * 3] != bytes((96, 120, 168, 255))
    flag = notebook_publish(notebook, 3)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    new_trial = notebook_publish(notebook, 4)
    assert new_trial.trial == 2 and new_trial.open_receipt == 2
    assert notebook_publish(notebook, 5).outcome_scalar == -1
    assert notebook_publish(notebook, 6).done
finally:
    notebook_destroy(notebook)
print("PASS: native Notebook agent writes, advances, answers, settles, and forfeits")

rooms_create = lib.nw_where_was_it_agent_create
rooms_create.argtypes, rooms_create.restype = agent_create.argtypes, agent_create.restype
rooms_act = lib.nw_where_was_it_agent_act
rooms_act.argtypes, rooms_act.restype = agent_act.argtypes, agent_act.restype
rooms_destroy = lib.nw_where_was_it_agent_destroy
rooms_destroy.argtypes, rooms_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
rooms_publish_abi = lib.nw_where_was_it_agent_publish
rooms_publish_abi.argtypes, rooms_publish_abi.restype = agent_publish.argtypes, agent_publish.restype


def rooms_publish(agent, timestamp):
    return publish(agent, timestamp, publish_abi=rooms_publish_abi)


assert not rooms_create(20, 1, 1, 17, 0, 0, 30, False)
rooms = rooms_create(20, 1, 1, 17, 0, 0, 31, False)
assert rooms
try:
    initial = rooms_publish(rooms, 1)
    for i in range(1, 6):
        assert rooms_act(rooms, 30, i * 2) == i
        view = rooms_publish(rooms, i * 2 + 1)
        assert view.open_receipt == i + 1 and not view.outcome_receipt
    # The Python oracle's rung-20 deal removes a solid from cell 7.
    assert rooms_act(rooms, 7, 12) == 6
    verdict = rooms_publish(rooms, 13)
    assert not verdict.open_receipt and verdict.outcome_receipt == 6
    assert verdict.stimulus_digest == initial.digest and verdict.action_port == 7
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, 1.0) == 1
    assert rooms_publish(rooms, 14).done
finally:
    rooms_destroy(rooms)

rooms = rooms_create(20, 2, 1, 17, 0.1, 0.05, 31, False)
assert rooms
try:
    assert rooms_publish(rooms, 1).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not rooms_publish(rooms, 2).outcome_receipt
    flag = rooms_publish(rooms, 3)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1.0) == 1
    assert rooms_publish(rooms, 4).trial == 2
    assert rooms_publish(rooms, 5).outcome_scalar == -1
    assert rooms_publish(rooms, 6).done
finally:
    rooms_destroy(rooms)
print("PASS: native Where Was It? agent study, answer, outcome pixels, think clock, and cleanup")

nearer_create = lib.nw_which_is_nearer_agent_create
nearer_create.argtypes, nearer_create.restype = delay_create.argtypes, delay_create.restype
nearer_act = lib.nw_which_is_nearer_agent_act
nearer_act.argtypes, nearer_act.restype = agent_act.argtypes, agent_act.restype
nearer_destroy = lib.nw_which_is_nearer_agent_destroy
nearer_destroy.argtypes, nearer_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
nearer_publish = lib.nw_which_is_nearer_agent_publish
nearer_publish.argtypes, nearer_publish.restype = agent_publish.argtypes, agent_publish.restype
assert not nearer_create(20, 1, 1, 17, 5, False)
for ports, scalar in (((1, 0, 2), 1.0), ((0,), -1.0)):
    nearer = nearer_create(20, 1, 1, 17, 6, False)
    assert nearer
    try:
        first = publish(nearer, 1, publish_abi=nearer_publish)
        moving = publish(nearer, 2, dt=0.6, publish_abi=nearer_publish)
        assert moving.digest != first.digest and moving.open_receipt == first.open_receipt
        for index, port in enumerate(ports):
            stamp = index * 2 + 3
            assert nearer_act(nearer, port, stamp) == index + 1
            feedback = publish(nearer, stamp + 1, publish_abi=nearer_publish)
            if index < len(ports) - 1:
                assert not feedback.outcome_receipt and feedback.open_receipt == index + 2
        assert feedback.outcome_scalar == scalar and feedback.outcome_receipt == len(ports)
        assert feedback.stimulus_digest == first.digest and not feedback.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, feedback.digest, scalar) == 1
        finished = publish(nearer, stamp + 2, publish_abi=nearer_publish)
        assert finished.done and not finished.outcome_receipt
    finally:
        nearer_destroy(nearer)
print("PASS: native Which Is Nearer? agent sway, ordered picks, win and loss pixels, and cleanup")

mirror_create = lib.nw_same_or_mirror_agent_create
mirror_create.argtypes, mirror_create.restype = agent_create.argtypes, agent_create.restype
mirror_act = lib.nw_same_or_mirror_agent_act
mirror_act.argtypes, mirror_act.restype = agent_act.argtypes, agent_act.restype
mirror_destroy = lib.nw_same_or_mirror_agent_destroy
mirror_destroy.argtypes, mirror_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
mirror_publish = lib.nw_same_or_mirror_agent_publish
mirror_publish.argtypes, mirror_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not mirror_create(1, 1, 1, 17, 0, 0, 4, False)
for rung, choice, scalar in ((1, 0, 1.0), (25, 2, 1.0), (25, 0, -1.0)):
    mirror = mirror_create(rung, 1, 1, 17, 0, 0, 5, False)
    assert mirror
    try:
        initial = publish(mirror, 1, publish_abi=mirror_publish)
        assert initial.open_receipt == 1
        assert mirror_act(mirror, choice, 2) == 1
        verdict = publish(mirror, 3, publish_abi=mirror_publish)
        assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == scalar
        assert verdict.stimulus_digest == initial.digest and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, scalar) == 1
        finished = publish(mirror, 4, publish_abi=mirror_publish)
        assert finished.done and not finished.outcome_receipt
    finally:
        mirror_destroy(mirror)
mirror = mirror_create(1, 2, 1, 17, 0.1, 0.05, 5, False)
assert mirror
try:
    assert publish(mirror, 1, publish_abi=mirror_publish).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(mirror, 2, publish_abi=mirror_publish).outcome_receipt
    flag = publish(mirror, 3, publish_abi=mirror_publish)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert publish(mirror, 4, publish_abi=mirror_publish).trial == 2
    assert publish(mirror, 5, publish_abi=mirror_publish).outcome_scalar == -1
    assert publish(mirror, 6, publish_abi=mirror_publish).done
finally:
    mirror_destroy(mirror)
print("PASS: native Same or Mirror? agent pair, unshaded row, verdict pixels, think clock, and cleanup")

pov_create = lib.nw_point_of_view_agent_create
pov_create.argtypes, pov_create.restype = agent_create.argtypes, agent_create.restype
pov_act = lib.nw_point_of_view_agent_act
pov_act.argtypes, pov_act.restype = agent_act.argtypes, agent_act.restype
pov_destroy = lib.nw_point_of_view_agent_destroy
pov_destroy.argtypes, pov_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
pov_publish = lib.nw_point_of_view_agent_publish
pov_publish.argtypes, pov_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not pov_create(1, 1, 1, 17, 0, 0, 4, False)
for rung, choice, scalar in ((1, 2, 1.0), (20, 2, 1.0), (20, 0, -1.0)):
    pov = pov_create(rung, 1, 1, 17, 0, 0, 5, False)
    assert pov
    try:
        initial = publish(pov, 1, publish_abi=pov_publish)
        assert initial.open_receipt == 1
        assert pov_act(pov, choice, 2) == 1
        verdict = publish(pov, 3, publish_abi=pov_publish)
        assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == scalar
        assert verdict.stimulus_digest == initial.digest and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, scalar) == 1
        finished = publish(pov, 4, publish_abi=pov_publish)
        assert finished.done and not finished.outcome_receipt
    finally:
        pov_destroy(pov)
pov = pov_create(1, 2, 1, 17, 0.1, 0.05, 5, False)
assert pov
try:
    assert publish(pov, 1, publish_abi=pov_publish).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(pov, 2, publish_abi=pov_publish).outcome_receipt
    flag = publish(pov, 3, publish_abi=pov_publish)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert publish(pov, 4, publish_abi=pov_publish).trial == 2
    assert publish(pov, 5, publish_abi=pov_publish).outcome_scalar == -1
    assert publish(pov, 6, publish_abi=pov_publish).done
finally:
    pov_destroy(pov)
print("PASS: native Point of View agent camera views, verdict pixels, think clock, and cleanup")

inside_create = lib.nw_inside_or_out_agent_create
inside_create.argtypes, inside_create.restype = agent_create.argtypes, agent_create.restype
inside_act = lib.nw_inside_or_out_agent_act
inside_act.argtypes, inside_act.restype = agent_act.argtypes, agent_act.restype
inside_destroy = lib.nw_inside_or_out_agent_destroy
inside_destroy.argtypes, inside_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
inside_publish = lib.nw_inside_or_out_agent_publish
inside_publish.argtypes, inside_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not inside_create(1, 1, 1, 17, 0, 0, 1, False)
for rung, choice, scalar in ((1, 0, 1.0), (20, 1, 1.0), (25, 1, -1.0), (30, 0, 1.0)):
    inside = inside_create(rung, 1, 1, 17, 0, 0, 2, False)
    assert inside
    try:
        initial = publish(inside, 1, publish_abi=inside_publish)
        assert initial.open_receipt == 1
        assert inside_act(inside, choice, 2) == 1
        verdict = publish(inside, 3, publish_abi=inside_publish)
        assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == scalar
        assert verdict.stimulus_digest == initial.digest and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, scalar) == 1
        finished = publish(inside, 4, publish_abi=inside_publish)
        assert finished.done and not finished.outcome_receipt
    finally:
        inside_destroy(inside)
inside = inside_create(1, 2, 1, 17, 0.1, 0.05, 2, False)
assert inside
try:
    assert publish(inside, 1, publish_abi=inside_publish).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(inside, 2, publish_abi=inside_publish).outcome_receipt
    flag = publish(inside, 3, publish_abi=inside_publish)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert publish(inside, 4, publish_abi=inside_publish).trial == 2
    assert publish(inside, 5, publish_abi=inside_publish).outcome_scalar == -1
    assert publish(inside, 6, publish_abi=inside_publish).done
finally:
    inside_destroy(inside)
print("PASS: native Inside or Out? agent outlines and dots, verdict pixels, think clock, and cleanup")

touching_create = lib.nw_touching_agent_create
touching_create.argtypes, touching_create.restype = agent_create.argtypes, agent_create.restype
touching_act = lib.nw_touching_agent_act
touching_act.argtypes, touching_act.restype = agent_act.argtypes, agent_act.restype
touching_destroy = lib.nw_touching_agent_destroy
touching_destroy.argtypes, touching_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
touching_publish = lib.nw_touching_agent_publish
touching_publish.argtypes, touching_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not touching_create(1, 1, 1, 17, 0, 0, 5, False)
for rung, choice, scalar in ((1, 2, 1.0), (7, 1, -1.0), (10, 0, 1.0), (25, 1, 1.0)):
    touching = touching_create(rung, 1, 1, 17, 0, 0, 6, False)
    assert touching
    try:
        initial = publish(touching, 1, publish_abi=touching_publish)
        assert initial.open_receipt == 1
        assert touching_act(touching, choice, 2) == 1
        verdict = publish(touching, 3, publish_abi=touching_publish)
        assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == scalar
        assert verdict.stimulus_digest == initial.digest and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, scalar) == 1
        finished = publish(touching, 4, publish_abi=touching_publish)
        assert finished.done and not finished.outcome_receipt
    finally:
        touching_destroy(touching)
touching = touching_create(1, 2, 1, 17, 0.1, 0.05, 6, False)
assert touching
try:
    assert publish(touching, 1, publish_abi=touching_publish).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(touching, 2, publish_abi=touching_publish).outcome_receipt
    flag = publish(touching, 3, publish_abi=touching_publish)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert publish(touching, 4, publish_abi=touching_publish).trial == 2
    assert publish(touching, 5, publish_abi=touching_publish).outcome_scalar == -1
    assert publish(touching, 6, publish_abi=touching_publish).done
finally:
    touching_destroy(touching)
print("PASS: native Touching? agent shapes and counts, verdict pixels, think clock, and cleanup")

crossings_create = lib.nw_crossings_agent_create
crossings_create.argtypes, crossings_create.restype = agent_create.argtypes, agent_create.restype
crossings_act = lib.nw_crossings_agent_act
crossings_act.argtypes, crossings_act.restype = agent_act.argtypes, agent_act.restype
crossings_destroy = lib.nw_crossings_agent_destroy
crossings_destroy.argtypes, crossings_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
crossings_publish = lib.nw_crossings_agent_publish
crossings_publish.argtypes, crossings_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not crossings_create(1, 1, 1, 17, 0, 0, 6, False)
for rung, choice, scalar in ((1, 2, 1.0), (7, 1, -1.0), (10, 2, 1.0), (25, 5, 1.0)):
    crossings = crossings_create(rung, 1, 1, 17, 0, 0, 7, False)
    assert crossings
    try:
        initial = publish(crossings, 1, publish_abi=crossings_publish)
        assert initial.open_receipt == 1
        assert crossings_act(crossings, choice, 2) == 1
        verdict = publish(crossings, 3, publish_abi=crossings_publish)
        assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == scalar
        assert verdict.stimulus_digest == initial.digest and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, scalar) == 1
        finished = publish(crossings, 4, publish_abi=crossings_publish)
        assert finished.done and not finished.outcome_receipt
    finally:
        crossings_destroy(crossings)
crossings = crossings_create(1, 2, 1, 17, 0.1, 0.05, 7, False)
assert crossings
try:
    assert publish(crossings, 1, publish_abi=crossings_publish).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(crossings, 2, publish_abi=crossings_publish).outcome_receipt
    flag = publish(crossings, 3, publish_abi=crossings_publish)
    assert flag.outcome_receipt == 1 and flag.outcome_scalar == -1
    assert publish(crossings, 4, publish_abi=crossings_publish).trial == 2
    assert publish(crossings, 5, publish_abi=crossings_publish).outcome_scalar == -1
    assert publish(crossings, 6, publish_abi=crossings_publish).done
finally:
    crossings_destroy(crossings)
print("PASS: native Crossings agent crossing counts and decoys, verdict pixels, think clock, and cleanup")

time_it_create = lib.nw_time_it_agent_create
time_it_create.argtypes, time_it_create.restype = hold_create.argtypes, hold_create.restype
time_it_act = lib.nw_time_it_agent_act
time_it_act.argtypes, time_it_act.restype = hold_act.argtypes, hold_act.restype
time_it_destroy = lib.nw_time_it_agent_destroy
time_it_destroy.argtypes, time_it_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
time_it_publish = lib.nw_time_it_agent_publish
time_it_publish.argtypes, time_it_publish.restype = agent_publish.argtypes, agent_publish.restype
time_it_audio = lib.nw_time_it_agent_audio
time_it_audio.argtypes, time_it_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not time_it_create(1, 1, 1, 17, 0, False)
time_it = time_it_create(1, 1, 1, 17, 1, False)
assert time_it
samples = ctypes.create_string_buffer(2230)
try:
    initial = publish(time_it, 0, dt=0.025, publish_abi=time_it_publish)
    assert initial.open_receipt == 1 and not time_it_audio(time_it, samples, len(samples))
    for tick in range(1, 94):
        frame = publish(time_it, tick * 2, dt=0.025, publish_abi=time_it_publish)
        assert frame.open_receipt == 1 and not frame.outcome_receipt
        assert time_it_audio(time_it, samples, len(samples)) == 2204
        if tick == 1:
            assert any(samples.raw[:2204])
        if tick == 90:
            assert not any(samples.raw[:2204])
        assert not time_it_audio(time_it, samples, len(samples))
    assert time_it_act(time_it, 0, 187) == frame.open_receipt
    assert not time_it_act(time_it, 0, 187)
    verdict = publish(time_it, 188, dt=0.025, publish_abi=time_it_publish)
    assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == 1
    assert not verdict.done
    assert not time_it_audio(time_it, samples, len(samples))
    assert publish(time_it, 189, dt=0.025, publish_abi=time_it_publish).done
finally:
    time_it_destroy(time_it)
print("Time It native agent: timed press, elapsed stereo PCM, pixel-verified verdict, and completion pass")

balance_create = lib.nw_balance_agent_create
balance_create.argtypes, balance_create.restype = hold_create.argtypes, hold_create.restype
balance_act = lib.nw_balance_agent_act
balance_act.argtypes, balance_act.restype = hold_act.argtypes, hold_act.restype
balance_destroy = lib.nw_balance_agent_destroy
balance_destroy.argtypes, balance_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
balance_publish = lib.nw_balance_agent_publish
balance_publish.argtypes, balance_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not balance_create(1, 1, 1, 17, 1, False)
for port in (0, 1):
    balance = balance_create(1, 1, 1, 17, 2, False)
    assert balance
    try:
        first = publish(balance, 0, dt=0.025, publish_abi=balance_publish)
        assert first.open_receipt == 1
        assert balance_act(balance, port, 1) == first.open_receipt
        pushed = publish(balance, 2, dt=0.025, publish_abi=balance_publish)
        assert pushed.open_receipt == 2 and pushed.digest != first.digest
        for tick in range(3, 200):
            frame = publish(balance, tick, dt=0.025, publish_abi=balance_publish)
            if frame.outcome_receipt:
                assert frame.outcome_scalar == -1 and not frame.done
                break
        else:
            raise AssertionError("Balance never judged the failed course")
        assert publish(balance, tick + 1, dt=0.025, publish_abi=balance_publish).done
    finally:
        balance_destroy(balance)
print("Balance native agent: single-frame pushes, falling-pole verdict, and completion pass")

juggler_create = lib.nw_juggler_agent_create
juggler_create.argtypes, juggler_create.restype = hold_create.argtypes, hold_create.restype
juggler_act = lib.nw_juggler_agent_act
juggler_act.argtypes, juggler_act.restype = hold_act.argtypes, hold_act.restype
juggler_destroy = lib.nw_juggler_agent_destroy
juggler_destroy.argtypes, juggler_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
juggler_publish = lib.nw_juggler_agent_publish
juggler_publish.argtypes, juggler_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not juggler_create(1, 1, 1, 17, 1, False)
for port in (0, 1):
    juggler = juggler_create(1, 1, 1, 17, 2, False)
    assert juggler
    try:
        first = publish(juggler, 0, dt=0.025, publish_abi=juggler_publish)
        assert first.open_receipt == 1
        assert juggler_act(juggler, port, 1) == first.open_receipt
        pushed = publish(juggler, 2, dt=0.025, publish_abi=juggler_publish)
        assert pushed.open_receipt == 2 and pushed.digest != first.digest
        for tick in range(3, 200):
            frame = publish(juggler, tick, dt=0.025, publish_abi=juggler_publish)
            if frame.outcome_receipt:
                assert frame.outcome_scalar == -1 and not frame.done
                break
        else:
            raise AssertionError("Juggler never judged the failed course")
        assert publish(juggler, tick + 1, dt=0.025, publish_abi=juggler_publish).done
    finally:
        juggler_destroy(juggler)
print("Juggler native agent: single-frame pushes, dropped-ball verdict, and completion pass")

lander_create = lib.nw_lander_agent_create
lander_create.argtypes, lander_create.restype = hold_create.argtypes, hold_create.restype
lander_act = lib.nw_lander_agent_act
lander_act.argtypes, lander_act.restype = hold_act.argtypes, hold_act.restype
lander_destroy = lib.nw_lander_agent_destroy
lander_destroy.argtypes, lander_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
lander_publish = lib.nw_lander_agent_publish
lander_publish.argtypes, lander_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not lander_create(1, 1, 1, 17, 4, False)
for port in (0, 3):
    lander = lander_create(1, 1, 1, 17, 5, False)
    assert lander
    try:
        first = publish(lander, 0, dt=0.025, publish_abi=lander_publish)
        assert first.open_receipt == 1
        assert lander_act(lander, port, 1) == first.open_receipt
        pushed = publish(lander, 2, dt=0.025, publish_abi=lander_publish)
        assert pushed.open_receipt == 2 and pushed.digest != first.digest
        for tick in range(3, 500):
            frame = publish(lander, tick, dt=0.025, publish_abi=lander_publish)
            if frame.outcome_receipt:
                assert frame.outcome_scalar == -1 and not frame.done
                break
        else:
            raise AssertionError("Lander never judged the failed landing")
        assert publish(lander, tick + 1, dt=0.025, publish_abi=lander_publish).done
    finally:
        lander_destroy(lander)
print("Lander native agent: single-frame thrust and turn, crash verdict, and completion pass")

beat_create = lib.nw_beat_agent_create
beat_create.argtypes, beat_create.restype = hold_create.argtypes, hold_create.restype
beat_act = lib.nw_beat_agent_act
beat_act.argtypes, beat_act.restype = hold_act.argtypes, hold_act.restype
beat_destroy = lib.nw_beat_agent_destroy
beat_destroy.argtypes, beat_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
beat_publish = lib.nw_beat_agent_publish
beat_publish.argtypes, beat_publish.restype = agent_publish.argtypes, agent_publish.restype
beat_audio = lib.nw_beat_agent_audio
beat_audio.argtypes, beat_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not beat_create(1, 1, 1, 17, 0, False)
beat = beat_create(1, 1, 1, 17, 1, False)
assert beat
samples = ctypes.create_string_buffer(2230)
try:
    frame = publish(beat, 0, dt=0.025, publish_abi=beat_publish)
    assert frame.open_receipt == 1 and not beat_audio(beat, samples, len(samples))
    for tick in range(1, 520):
        if 288 <= tick - 1 <= 448 and (tick - 1 - 288) % 32 == 0:
            assert beat_act(beat, 0, tick * 2 - 1) == frame.open_receipt
            assert not beat_act(beat, 0, tick * 2 - 1)
        receipt = frame.open_receipt
        frame = publish(beat, tick * 2, dt=0.025, publish_abi=beat_publish)
        length = beat_audio(beat, samples, len(samples))
        assert 0 < length <= 2204 and length % 4 == 0
        if tick == 33:
            assert any(samples.raw[:length])
        if tick == 300:
            assert not any(samples.raw[:length])
        assert not beat_audio(beat, samples, len(samples))
        if frame.outcome_receipt:
            assert frame.outcome_receipt == receipt and frame.outcome_scalar == 1 and not frame.done, (
                tick, frame.outcome_receipt, receipt, frame.outcome_scalar, frame.done)
            break
    else:
        raise AssertionError("Keep the Beat never judged the song")
    assert publish(beat, tick * 2 + 1, dt=0.025, publish_abi=beat_publish).done
finally:
    beat_destroy(beat)
print("Keep the Beat native agent: timed taps, elapsed stereo PCM, pixel-verified verdict, and completion pass")

glider_create = lib.nw_glider_agent_create
glider_create.argtypes, glider_create.restype = hold_create.argtypes, hold_create.restype
glider_act = lib.nw_glider_agent_act
glider_act.argtypes, glider_act.restype = hold_act.argtypes, hold_act.restype
glider_destroy = lib.nw_glider_agent_destroy
glider_destroy.argtypes, glider_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
glider_publish = lib.nw_glider_agent_publish
glider_publish.argtypes, glider_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not glider_create(1, 1, 1, 17, 0, False)
port = 0
glider = glider_create(1, 1, 1, 17, 1, False)
assert glider
try:
    first = publish(glider, 0, dt=0.025, publish_abi=glider_publish)
    assert first.open_receipt == 1
    assert glider_act(glider, port, 1) == first.open_receipt
    pushed = publish(glider, 2, dt=0.025, publish_abi=glider_publish)
    assert pushed.open_receipt == 2 and pushed.digest != first.digest
    for tick in range(3, 500):
        frame = publish(glider, tick, dt=0.025, publish_abi=glider_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1 and not frame.done
            break
    else:
        raise AssertionError("Glider never judged the failed flight")
    assert publish(glider, tick + 1, dt=0.025, publish_abi=glider_publish).done
finally:
    glider_destroy(glider)
print("Glider native agent: single-frame lift, canyon-floor verdict, and completion pass")

catch_create = lib.nw_catch_agent_create
catch_create.argtypes, catch_create.restype = hold_create.argtypes, hold_create.restype
catch_act = lib.nw_catch_agent_act
catch_act.argtypes, catch_act.restype = hold_act.argtypes, hold_act.restype
catch_mask = lib.nw_catch_agent_act_mask
catch_mask.argtypes, catch_mask.restype = hold_act.argtypes, hold_act.restype
catch_destroy = lib.nw_catch_agent_destroy
catch_destroy.argtypes, catch_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
catch_publish = lib.nw_catch_agent_publish
catch_publish.argtypes, catch_publish.restype = agent_publish.argtypes, agent_publish.restype
catch_audio = lib.nw_catch_agent_audio
catch_audio.argtypes, catch_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not catch_create(20, 1, 1, 17, 7, False)
catch_handle = catch_create(20, 1, 1, 17, 8, False)
assert catch_handle
samples = ctypes.create_string_buffer(2230)
try:
    first = publish(catch_handle, 0, dt=0.025, publish_abi=catch_publish)
    assert first.open_receipt == 1
    assert not catch_mask(catch_handle, 256, 1)
    assert catch_mask(catch_handle, 105, 1) == first.open_receipt
    assert not catch_act(catch_handle, 0, 1)
    pushed = publish(catch_handle, 2, dt=0.025, publish_abi=catch_publish)
    assert pushed.open_receipt == 2 and pushed.digest != first.digest
    sounded = False
    frame = pushed
    for tick in range(3, 500):
        assert catch_mask(catch_handle, 105, tick) == frame.open_receipt
        frame = publish(catch_handle, tick, dt=0.025, publish_abi=catch_publish)
        length = catch_audio(catch_handle, samples, len(samples))
        sounded |= any(samples.raw[:length])
        if frame.outcome_receipt:
            assert sounded and frame.outcome_scalar == -1 and not frame.done
            assert frame.action_port == 256 + 105
            break
    else:
        raise AssertionError("Catch never judged the dropped balls")
    assert publish(catch_handle, tick + 1, dt=0.025, publish_abi=catch_publish).done
finally:
    catch_destroy(catch_handle)
print("Catch native agent: simultaneous baskets, elapsed stereo PCM, pixel-verified verdict, and completion pass")

echo_cave_create = lib.nw_echo_cave_agent_create
echo_cave_create.argtypes, echo_cave_create.restype = hold_create.argtypes, hold_create.restype
echo_cave_act = lib.nw_echo_cave_agent_act
echo_cave_act.argtypes, echo_cave_act.restype = hold_act.argtypes, hold_act.restype
echo_cave_mask = lib.nw_echo_cave_agent_act_mask
echo_cave_mask.argtypes, echo_cave_mask.restype = hold_act.argtypes, hold_act.restype
echo_cave_destroy = lib.nw_echo_cave_agent_destroy
echo_cave_destroy.argtypes, echo_cave_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
echo_cave_publish = lib.nw_echo_cave_agent_publish
echo_cave_publish.argtypes, echo_cave_publish.restype = agent_publish.argtypes, agent_publish.restype
echo_cave_audio = lib.nw_echo_cave_agent_audio
echo_cave_audio.argtypes, echo_cave_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not echo_cave_create(10, 1, 1, 17, 8, False)
echo_cave_handle = echo_cave_create(10, 1, 1, 17, 9, False)
assert echo_cave_handle
samples = ctypes.create_string_buffer(2230)
try:
    first = publish(echo_cave_handle, 0, dt=0.025, publish_abi=echo_cave_publish)
    assert first.open_receipt == 1
    assert not echo_cave_mask(echo_cave_handle, 512, 1)
    assert echo_cave_mask(echo_cave_handle, 288, 1) == first.open_receipt
    assert not echo_cave_act(echo_cave_handle, 0, 1)
    pushed = publish(echo_cave_handle, 2, dt=0.025, publish_abi=echo_cave_publish)
    assert pushed.open_receipt == 2 and pushed.digest != first.digest
    sounded = False
    frame = pushed
    for tick in range(3, 500):
        assert echo_cave_mask(echo_cave_handle, 288, tick) == frame.open_receipt
        frame = publish(echo_cave_handle, tick, dt=0.025, publish_abi=echo_cave_publish)
        length = echo_cave_audio(echo_cave_handle, samples, len(samples))
        sounded |= any(samples.raw[:length])
        if frame.outcome_receipt:
            assert sounded and frame.outcome_scalar == -1 and not frame.done
            assert frame.action_port == 512 + 288
            break
    else:
        raise AssertionError("Echo Cave never judged the cave flight")
    assert publish(echo_cave_handle, tick + 1, dt=0.025, publish_abi=echo_cave_publish).done
finally:
    echo_cave_destroy(echo_cave_handle)
print("Echo Cave native agent: simultaneous steering and clicks, elapsed stereo PCM, pixel-verified verdict, and completion pass")

drone_hoops_create = lib.nw_drone_hoops_agent_create
drone_hoops_create.argtypes, drone_hoops_create.restype = hold_create.argtypes, hold_create.restype
drone_hoops_act = lib.nw_drone_hoops_agent_act
drone_hoops_act.argtypes, drone_hoops_act.restype = hold_act.argtypes, hold_act.restype
drone_hoops_mask = lib.nw_drone_hoops_agent_act_mask
drone_hoops_mask.argtypes, drone_hoops_mask.restype = hold_act.argtypes, hold_act.restype
drone_hoops_destroy = lib.nw_drone_hoops_agent_destroy
drone_hoops_destroy.argtypes, drone_hoops_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
drone_hoops_publish = lib.nw_drone_hoops_agent_publish
drone_hoops_publish.argtypes, drone_hoops_publish.restype = agent_publish.argtypes, agent_publish.restype
drone_hoops_audio = lib.nw_drone_hoops_agent_audio
drone_hoops_audio.argtypes, drone_hoops_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not drone_hoops_create(10, 1, 1, 17, 9, False)
drone_hoops_handle = drone_hoops_create(10, 1, 1, 17, 10, False)
assert drone_hoops_handle
samples = ctypes.create_string_buffer(2230)
try:
    first = publish(drone_hoops_handle, 0, dt=0.025, publish_abi=drone_hoops_publish)
    assert first.open_receipt == 1
    assert not drone_hoops_mask(drone_hoops_handle, 1024, 1)
    assert drone_hoops_mask(drone_hoops_handle, 513, 1) == first.open_receipt
    assert not drone_hoops_act(drone_hoops_handle, 0, 1)
    pushed = publish(drone_hoops_handle, 2, dt=0.025, publish_abi=drone_hoops_publish)
    assert pushed.open_receipt == 2 and pushed.digest != first.digest
    sounded = False
    frame = pushed
    for tick in range(3, 2600):
        assert drone_hoops_mask(drone_hoops_handle, 513, tick) == frame.open_receipt
        frame = publish(drone_hoops_handle, tick, dt=0.025, publish_abi=drone_hoops_publish)
        length = drone_hoops_audio(drone_hoops_handle, samples, len(samples))
        sounded |= any(samples.raw[:length])
        if frame.outcome_receipt:
            assert sounded and frame.outcome_scalar == -1 and not frame.done
            assert frame.action_port == 1024 + 513
            break
    else:
        raise AssertionError("Drone Hoops never judged the flight")
    assert publish(drone_hoops_handle, tick + 1, dt=0.025, publish_abi=drone_hoops_publish).done
finally:
    drone_hoops_destroy(drone_hoops_handle)
print("Drone Hoops native agent: simultaneous flight controls, elapsed stereo PCM, pixel-verified verdict, and completion pass")


field_create = lib.nw_field_manual_agent_create
field_create.argtypes, field_create.restype = hold_create.argtypes, hold_create.restype
field_act = lib.nw_field_manual_agent_act
field_act.argtypes, field_act.restype = hold_act.argtypes, hold_act.restype
field_destroy = lib.nw_field_manual_agent_destroy
field_destroy.argtypes, field_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
field_publish = lib.nw_field_manual_agent_publish
field_publish.argtypes, field_publish.restype = agent_publish.argtypes, agent_publish.restype
field_audio = lib.nw_field_manual_agent_audio
field_audio.argtypes, field_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not field_create(1, 1, 1, 17, 24, False)
field_handle = field_create(1, 1, 1, 17, 25, False)
assert field_handle
samples = ctypes.create_string_buffer(8820)
try:
    frame = publish(field_handle, 0, dt=1e-12, publish_abi=field_publish)
    assert frame.open_receipt == 1
    for index, port in enumerate((7, 7, 2, 8, 2, 8, 2, 12, 13), 1):
        assert field_act(field_handle, port, index * 2) == frame.open_receipt
        frame = publish(field_handle, index * 2 + 1, dt=1 / 60, publish_abi=field_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == 1 and frame.action_port == 13
    sounded = False
    while (length := field_audio(field_handle, samples, len(samples))) > 0:
        sounded |= any(samples.raw[:length])
    assert sounded
    assert publish(field_handle, 20, dt=1 / 60, publish_abi=field_publish).done
finally:
    field_destroy(field_handle)
print("Field Manual native agent: seeded switch order, stereo PCM and pixel-verified verdict pass")


safe_create = lib.nw_safecracker_agent_create
safe_create.argtypes, safe_create.restype = hold_create.argtypes, hold_create.restype
safe_act = lib.nw_safecracker_agent_act
safe_act.argtypes, safe_act.restype = hold_act.argtypes, hold_act.restype
safe_destroy = lib.nw_safecracker_agent_destroy
safe_destroy.argtypes, safe_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
safe_publish = lib.nw_safecracker_agent_publish
safe_publish.argtypes, safe_publish.restype = agent_publish.argtypes, agent_publish.restype
safe_audio = lib.nw_safecracker_agent_audio
safe_audio.argtypes, safe_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not safe_create(1, 1, 1, 17, 40, False)
safe_handle = safe_create(1, 1, 1, 17, 41, False)
assert safe_handle
samples = ctypes.create_string_buffer(8820)
try:
    frame = publish(safe_handle, 0, dt=1e-12, publish_abi=safe_publish)
    assert frame.open_receipt == 1
    for index, port in enumerate((28, 29, 18, 27, 1, 1, 2, 2, 12, 0, 10, 9, 3, 13, 4, 4, 10, 4, 10, 5, 12, 4, 4, 4, 4), 1):
        assert safe_act(safe_handle, port, index * 2) == frame.open_receipt
        frame = publish(safe_handle, index * 2 + 1, dt=1 / 60, publish_abi=safe_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == 1 and frame.action_port == 4
    sounded = False
    while (length := safe_audio(safe_handle, samples, len(samples))) > 0:
        sounded |= any(samples.raw[:length])
    assert sounded
    assert publish(safe_handle, 52, dt=1 / 60, publish_abi=safe_publish).done
finally:
    safe_destroy(safe_handle)
print("Safecracker native agent: word lock, dial, lever, stereo PCM and pixel-verified verdict pass")


stage_create = lib.nw_stagehand_agent_create
stage_create.argtypes, stage_create.restype = hold_create.argtypes, hold_create.restype
stage_act = lib.nw_stagehand_agent_act
stage_act.argtypes, stage_act.restype = hold_act.argtypes, hold_act.restype
stage_destroy = lib.nw_stagehand_agent_destroy
stage_destroy.argtypes, stage_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
stage_publish = lib.nw_stagehand_agent_publish
stage_publish.argtypes, stage_publish.restype = agent_publish.argtypes, agent_publish.restype
stage_audio = lib.nw_stagehand_agent_audio
stage_audio.argtypes, stage_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not stage_create(1, 1, 1, 17, 18, False)
stage_handle = stage_create(1, 1, 1, 17, 19, False)
assert stage_handle
samples = ctypes.create_string_buffer(8820)
try:
    frame = publish(stage_handle, 0, dt=1e-12, publish_abi=stage_publish)
    assert frame.open_receipt == 1
    for index, port in enumerate((4, 5, 5, 12, 6, 6, 7, 7, 4, 7, 5, 5, 13, 18), 1):
        assert stage_act(stage_handle, port, index * 2) == frame.open_receipt
        frame = publish(stage_handle, index * 2 + 1, dt=1 / 60, publish_abi=stage_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == 1 and frame.action_port == 18
    sounded = False
    while (length := stage_audio(stage_handle, samples, len(samples))) > 0:
        sounded |= any(samples.raw[:length])
    assert sounded
    assert publish(stage_handle, 30, dt=1 / 60, publish_abi=stage_publish).done
finally:
    stage_destroy(stage_handle)
print("Stagehand native agent: prop drag and thunder cue, stereo PCM and pixel-verified verdict pass")


dock_create = lib.nw_loading_dock_agent_create
dock_create.argtypes, dock_create.restype = hold_create.argtypes, hold_create.restype
dock_act = lib.nw_loading_dock_agent_act
dock_act.argtypes, dock_act.restype = hold_act.argtypes, hold_act.restype
dock_destroy = lib.nw_loading_dock_agent_destroy
dock_destroy.argtypes, dock_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
dock_publish = lib.nw_loading_dock_agent_publish
dock_publish.argtypes, dock_publish.restype = agent_publish.argtypes, agent_publish.restype
dock_audio = lib.nw_loading_dock_agent_audio
dock_audio.argtypes, dock_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not dock_create(1, 1, 1, 17, 19, False)
dock_handle = dock_create(1, 1, 1, 17, 20, False)
assert dock_handle
samples = ctypes.create_string_buffer(8820)
try:
    frame = publish(dock_handle, 0, dt=1e-12, publish_abi=dock_publish)
    assert frame.open_receipt == 1
    sounded = False
    # Reverse briefly, then click the unfilled truck's lamp.
    for index, port in enumerate((15, 9, 3, 10, 5, 5, 12, 13), 1):
        assert dock_act(dock_handle, port, index * 2) == frame.open_receipt
        frame = publish(dock_handle, index * 2 + 1, dt=1 / 60, publish_abi=dock_publish)
        while (length := dock_audio(dock_handle, samples, len(samples))) > 0:
            sounded |= any(samples.raw[:length])
    assert sounded
    assert frame.outcome_receipt and frame.outcome_scalar == -1 and frame.action_port == 13
    assert publish(dock_handle, 18, dt=1 / 60, publish_abi=dock_publish).done
finally:
    dock_destroy(dock_handle)
print("Loading Dock native agent: reverse alarm, stereo PCM and pixel-verified short-send verdict pass")


gun_create = lib.nw_gunslinger_agent_create
gun_create.argtypes, gun_create.restype = hold_create.argtypes, hold_create.restype
gun_act = lib.nw_gunslinger_agent_act
gun_act.argtypes, gun_act.restype = hold_act.argtypes, hold_act.restype
gun_destroy = lib.nw_gunslinger_agent_destroy
gun_destroy.argtypes, gun_destroy.restype = hold_destroy.argtypes, hold_destroy.restype
gun_publish = lib.nw_gunslinger_agent_publish
gun_publish.argtypes, gun_publish.restype = agent_publish.argtypes, agent_publish.restype
gun_audio = lib.nw_gunslinger_agent_audio
gun_audio.argtypes, gun_audio.restype = hold_audio.argtypes, hold_audio.restype

assert not gun_create(4, 1, 1, 17, 14, False)
gun_handle = gun_create(4, 1, 1, 17, 15, False)
assert gun_handle
samples = ctypes.create_string_buffer(8820)
try:
    frame = publish(gun_handle, 0, dt=1e-12, publish_abi=gun_publish)
    assert frame.open_receipt == 1
    assert gun_act(gun_handle, 14, 2) == frame.open_receipt
    frame = publish(gun_handle, 3, dt=1 / 60, publish_abi=gun_publish)
    length = gun_audio(gun_handle, samples, len(samples))
    assert length > 0 and any(samples.raw[:length])
    assert gun_act(gun_handle, 12, 4) == frame.open_receipt
    frame = publish(gun_handle, 5, dt=1 / 60, publish_abi=gun_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == -1 and frame.action_port == 12
    assert publish(gun_handle, 6, dt=1 / 60, publish_abi=gun_publish).done
finally:
    gun_destroy(gun_handle)
print("Gunslinger native agent: hammer, stereo PCM and pixel-verified early-shot verdict pass")

falls_create = lib.nw_will_it_fall_agent_create
falls_create.argtypes, falls_create.restype = agent_create.argtypes, agent_create.restype
falls_act = lib.nw_will_it_fall_agent_act
falls_act.argtypes, falls_act.restype = agent_act.argtypes, agent_act.restype
falls_destroy = lib.nw_will_it_fall_agent_destroy
falls_destroy.argtypes, falls_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
falls_publish = lib.nw_will_it_fall_agent_publish
falls_publish.argtypes, falls_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not falls_create(1, 1, 1, 17, 0, 0, 7, False)
for choice, scalar in ((1, 1.0), (0, -1.0)):
    falls_handle = falls_create(10, 1, 1, 17, 0, 0, 8, False)
    assert falls_handle
    try:
        initial = publish(falls_handle, 1, publish_abi=falls_publish)
        assert initial.open_receipt == 1
        assert falls_act(falls_handle, choice, 2) == 1
        assert not falls_act(falls_handle, 1 - choice, 2)
        verdict = publish(falls_handle, 3, publish_abi=falls_publish)
        assert verdict.outcome_receipt == 1 and verdict.outcome_scalar == scalar
        assert verdict.stimulus_digest == initial.digest and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                    verdict.digest, scalar) == 1
        assert publish(falls_handle, 4, publish_abi=falls_publish).done
    finally:
        falls_destroy(falls_handle)

falls_handle = falls_create(1, 2, 1, 17, 0.1, 0.05, 8, False)
assert falls_handle
try:
    assert publish(falls_handle, 1, dt=0.15, publish_abi=falls_publish).open_receipt == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert falls_act(falls_handle, 7, 2) == 1
    after_noop = publish(falls_handle, 3, publish_abi=falls_publish)
    assert after_noop.open_receipt == 2 and not after_noop.outcome_receipt
    flag = publish(falls_handle, 4, publish_abi=falls_publish)
    assert flag.outcome_receipt == after_noop.open_receipt and flag.outcome_scalar == -1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
    assert publish(falls_handle, 5, publish_abi=falls_publish).trial == 2
    assert publish(falls_handle, 6, publish_abi=falls_publish).outcome_scalar == -1
    assert publish(falls_handle, 7, publish_abi=falls_publish).done
finally:
    falls_destroy(falls_handle)
print("PASS: native Will It Fall? agent, eight ports, receipt and verdict pixels, think clock, and cleanup")

sfm_create = lib.nw_shape_from_motion_agent_create
sfm_create.argtypes, sfm_create.restype = delay_create.argtypes, delay_create.restype
sfm_act = lib.nw_shape_from_motion_agent_act
sfm_act.argtypes, sfm_act.restype = agent_act.argtypes, agent_act.restype
sfm_destroy = lib.nw_shape_from_motion_agent_destroy
sfm_destroy.argtypes, sfm_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
sfm_publish = lib.nw_shape_from_motion_agent_publish
sfm_publish.argtypes, sfm_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not sfm_create(1, 1, 1, 17, 5, False)
for choice, scalar in ((0, 1.0), (1, -1.0)):
    sfm_handle = sfm_create(1, 1, 1, 17, 6, False)
    assert sfm_handle
    try:
        first = publish(sfm_handle, 1, publish_abi=sfm_publish)
        moving = publish(sfm_handle, 2, dt=0.6, publish_abi=sfm_publish)
        assert first.open_receipt == moving.open_receipt == 1 and moving.digest != first.digest
        assert sfm_act(sfm_handle, 5, 3) == 1  # Unused on this three-button cloud.
        noop = publish(sfm_handle, 4, publish_abi=sfm_publish)
        assert noop.open_receipt == 2 and not noop.outcome_receipt
        assert sfm_act(sfm_handle, choice, 5) == 2
        assert not sfm_act(sfm_handle, 1 - choice, 5)
        verdict = publish(sfm_handle, 6, publish_abi=sfm_publish)
        assert verdict.outcome_receipt == 2 and verdict.outcome_scalar == scalar
        assert verdict.action_port == choice and not verdict.done
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                    verdict.digest, scalar) == 1
        assert publish(sfm_handle, 7, publish_abi=sfm_publish).done
    finally:
        sfm_destroy(sfm_handle)
print("PASS: native Shape from Motion animation, six ports, no-op answer, pixel-verified verdict, and cleanup")

dam_create = lib.nw_dam_keeper_agent_create
dam_create.argtypes, dam_create.restype = delay_create.argtypes, delay_create.restype
dam_act = lib.nw_dam_keeper_agent_act
dam_act.argtypes, dam_act.restype = agent_act.argtypes, agent_act.restype
dam_destroy = lib.nw_dam_keeper_agent_destroy
dam_destroy.argtypes, dam_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
dam_publish = lib.nw_dam_keeper_agent_publish
dam_publish.argtypes, dam_publish.restype = agent_publish.argtypes, agent_publish.restype


def check_dam_keeper():
    source = dam_keeper_fixture()
    dt = 1 / source["frameHz"]
    seed = source["seed"]
    assert not dam_create(1, 1, 0, seed, 5, False)
    # A half-size viewport retains verdict glyphs and keeps the replay quick.
    w, h = 456, 342
    bytes_rgba = w * h * 4
    frame = ctypes.create_string_buffer(bytes_rgba + 36)

    def observe(handle, stamp):
        result = TriagePublication()
        assert dam_publish(handle, dt, stamp, frame, len(frame), w, h, 0,
                           ctypes.byref(result)) == len(frame)
        assert result.frame_seq == stamp
        return result

    for trace in source["runs"]:
        handle = dam_create(1, 1, 0, seed, 6, False)
        assert handle
        try:
            latest = observe(handle, 1)
            assert latest.open_receipt == 1 and not latest.outcome_receipt
            ports = dict(trace["actions"])
            for tick in range(1, trace["ticks"] + 1):
                expected_receipt = latest.open_receipt
                if tick in ports:
                    assert dam_act(handle, ports[tick], tick) == expected_receipt
                    assert not dam_act(handle, ports[tick], tick)
                latest = observe(handle, tick + 1)
                assert not latest.done
                if tick < trace["ticks"]:
                    assert latest.open_receipt and not latest.outcome_receipt
            assert latest.outcome_receipt == expected_receipt > 0
            assert latest.outcome_scalar == trace["scalar"]
            assert latest.digest == hashlib.sha256(frame.raw[36:]).hexdigest().encode("ascii")
            assert verify_outcome_frame(ctypes.byref(frame, 36), bytes_rgba, w, h,
                                        latest.digest, trace["scalar"]) == 1
            assert observe(handle, trace["ticks"] + 2).done
        finally:
            dam_destroy(handle)
    print("PASS: native Dam Keeper matches Python stepped passes and losses, gate receipts, and rendered verdicts")


check_dam_keeper()

sonar_create = lib.nw_sonar_agent_create
sonar_create.argtypes, sonar_create.restype = agent_create.argtypes, agent_create.restype
sonar_act = lib.nw_sonar_agent_act
sonar_act.argtypes, sonar_act.restype = agent_act.argtypes, agent_act.restype
sonar_destroy = lib.nw_sonar_agent_destroy
sonar_destroy.argtypes, sonar_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
sonar_publish = lib.nw_sonar_agent_publish
sonar_publish.argtypes, sonar_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not sonar_create(1, 1, 1, 17, 0, 0, 5, False)
assert not sonar_create(1, 1, 1, 17, float("inf"), 0, 6, False)
sonar = sonar_create(1, 1, 1, 17, 0, 0, 6, False)
assert sonar
try:
    first = publish(sonar, 1, publish_abi=sonar_publish)
    assert first.open_receipt == 1
    for tick, port in enumerate((4, 3, 3, 1), start=1):
        assert sonar_act(sonar, port, 2 * tick) == first.open_receipt
        assert not sonar_act(sonar, port, 2 * tick)
        first = publish(sonar, 2 * tick + 1, publish_abi=sonar_publish)
        assert first.open_receipt == tick + 1 and not first.outcome_receipt
    assert sonar_act(sonar, 5, 10) == first.open_receipt
    scored = publish(sonar, 11, publish_abi=sonar_publish)
    assert scored.outcome_scalar == 1 and scored.outcome_receipt == first.open_receipt
    assert scored.action_port == 5
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, scored.digest, 1) == 1
    done = publish(sonar, 12, publish_abi=sonar_publish)
    assert done.done and not done.outcome_receipt
finally:
    sonar_destroy(sonar)

sonar = sonar_create(25, 2, 1, 17, 0.1, 0.05, 6, False)
assert sonar
try:
    first = publish(sonar, 1, publish_abi=sonar_publish)
    assert first.open_receipt
    assert not publish(sonar, 2, publish_abi=sonar_publish).outcome_receipt
    flag = publish(sonar, 3, publish_abi=sonar_publish)
    assert flag.outcome_scalar == -1 and flag.outcome_receipt == first.open_receipt
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
    second = publish(sonar, 4, publish_abi=sonar_publish)
    assert second.trial == 2 and second.open_receipt > first.open_receipt
    flag = publish(sonar, 5, publish_abi=sonar_publish)
    assert flag.outcome_scalar == -1 and flag.outcome_receipt == second.open_receipt
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
    done = publish(sonar, 6, publish_abi=sonar_publish)
    assert done.done and not done.outcome_receipt
finally:
    sonar_destroy(sonar)
print("PASS: native Sonar action receipts, think-clock expiry and refill, and rendered verdicts on both board sizes")

drshape_create = lib.nw_dr_shape_agent_create
drshape_create.argtypes, drshape_create.restype = delay_create.argtypes, delay_create.restype
drshape_act = lib.nw_dr_shape_agent_act
drshape_act.argtypes, drshape_act.restype = agent_act.argtypes, agent_act.restype
drshape_destroy = lib.nw_dr_shape_agent_destroy
drshape_destroy.argtypes, drshape_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
drshape_publish = lib.nw_dr_shape_agent_publish
drshape_publish.argtypes, drshape_publish.restype = agent_publish.argtypes, agent_publish.restype
drshape_audio = lib.nw_dr_shape_agent_audio
drshape_audio.argtypes = [ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64]
drshape_audio.restype = ctypes.c_int64

assert not drshape_create(1, 1, 1, 17, 5, False)
shape = drshape_create(1, 1, 1, 17, 6, False)
assert shape
try:
    volume = ctypes.create_string_buffer(8820)
    first = publish(shape, 1, dt=0.1, publish_abi=drshape_publish)
    assert first.open_receipt == 1
    assert not drshape_audio(shape, volume, len(volume))
    assert drshape_act(shape, 0, 2) == first.open_receipt
    moving = publish(shape, 3, dt=0.1, publish_abi=drshape_publish)
    assert not moving.outcome_receipt and moving.open_receipt == 2
    heard = False
    for stamp in range(4, 75):
        moving = publish(shape, stamp, dt=0.1, publish_abi=drshape_publish)
        length = drshape_audio(shape, volume, len(volume))
        heard |= length > 0 and any(volume.raw[:length])
    assert heard and moving.open_receipt == 2
    assert drshape_act(shape, 0, 75) == moving.open_receipt
    verdict = publish(shape, 76, dt=0.1, publish_abi=drshape_publish)
    assert verdict.outcome_scalar == 1 and verdict.outcome_receipt == moving.open_receipt
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                verdict.digest, 1.0) == 1
    assert publish(shape, 77, dt=0.1, publish_abi=drshape_publish).done
finally:
    drshape_destroy(shape)
print("PASS: native Dr Shape stereo audio, reveal, six ports, verified verdict, and teardown")

tuner_create = lib.nw_tuner_agent_create
tuner_create.argtypes, tuner_create.restype = delay_create.argtypes, delay_create.restype
tuner_act = lib.nw_tuner_agent_act
tuner_act.argtypes, tuner_act.restype = agent_act.argtypes, agent_act.restype
tuner_destroy = lib.nw_tuner_agent_destroy
tuner_destroy.argtypes, tuner_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
tuner_publish = lib.nw_tuner_agent_publish
tuner_publish.argtypes, tuner_publish.restype = agent_publish.argtypes, agent_publish.restype
tuner_audio = lib.nw_tuner_agent_audio
tuner_audio.argtypes = [ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64]
tuner_audio.restype = ctypes.c_int64

assert not tuner_create(1, 1, 1, 17, 5, False)
radio = tuner_create(1, 1, 1, 17, 6, False)
assert radio
try:
    pcm = ctypes.create_string_buffer(8820)
    current = publish(radio, 1, dt=0.1, publish_abi=tuner_publish)
    assert current.open_receipt and not tuner_audio(radio, pcm, len(pcm))
    stamp, heard = 1, False
    # Seed 17 starts at 43.309. Twelve coarse down frames reach 16.909,
    # within 0.096 of Python's target station at 16.814.
    for frame in range(28):
        if frame < 12:
            stamp += 1
            assert tuner_act(radio, 0, stamp) == current.open_receipt
        stamp += 1
        current = publish(radio, stamp, dt=0.1, publish_abi=tuner_publish)
        length = tuner_audio(radio, pcm, len(pcm))
        assert length % 4 == 0
        heard |= length > 0 and any(pcm.raw[:length])
        assert not current.outcome_receipt
    assert heard
    stamp += 1
    assert tuner_act(radio, 4, stamp) == current.open_receipt
    for _ in range(12):
        stamp += 1
        current = publish(radio, stamp, dt=0.1, publish_abi=tuner_publish)
        if current.outcome_receipt:
            break
    assert current.outcome_receipt and current.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                current.digest, 1.0) == 1
    assert publish(radio, stamp + 1, dt=0.1, publish_abi=tuner_publish).done
finally:
    tuner_destroy(radio)
print("PASS: native Tuner ports, elapsed stereo audio, lock verdict, and teardown")

shadow_play_create = lib.nw_shadow_play_agent_create
shadow_play_create.argtypes, shadow_play_create.restype = delay_create.argtypes, delay_create.restype
shadow_play_act = lib.nw_shadow_play_agent_act
shadow_play_act.argtypes, shadow_play_act.restype = agent_act.argtypes, agent_act.restype
shadow_play_destroy = lib.nw_shadow_play_agent_destroy
shadow_play_destroy.argtypes, shadow_play_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
shadow_play_publish = lib.nw_shadow_play_agent_publish
shadow_play_publish.argtypes, shadow_play_publish.restype = agent_publish.argtypes, agent_publish.restype
shadow_play_audio = lib.nw_shadow_play_agent_audio
shadow_play_audio.argtypes = [ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64]
shadow_play_audio.restype = ctypes.c_int64

assert not shadow_play_create(1, 1, 1, 17, 5, False)
shadow = shadow_play_create(1, 1, 1, 17, 6, False)
assert shadow
try:
    pcm = ctypes.create_string_buffer(8820)
    current = publish(shadow, 1, dt=0.05, publish_abi=shadow_play_publish)
    assert current.open_receipt and not shadow_play_audio(shadow, pcm, len(pcm))
    stamp, heard = 1, False
    # Python seed 17 needs 1.556 radians of left yaw, or 30 frames at 20 Hz.
    for frame in range(50):
        if frame < 30:
            stamp += 1
            assert shadow_play_act(shadow, 0, stamp) == current.open_receipt
        stamp += 1
        current = publish(shadow, stamp, dt=0.05, publish_abi=shadow_play_publish)
        length = shadow_play_audio(shadow, pcm, len(pcm))
        assert length % 4 == 0
        heard |= length > 0 and any(pcm.raw[:length])
        if current.outcome_receipt:
            break
    assert heard and current.outcome_receipt and current.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height,
                                current.digest, 1.0) == 1
    assert publish(shadow, stamp + 1, dt=0.05, publish_abi=shadow_play_publish).done
finally:
    shadow_play_destroy(shadow)
print("PASS: native Shadow Play held yaw, elapsed stereo PCM, verified verdict, and teardown")

captcha_create = lib.nw_captcha_agent_create
captcha_create.argtypes, captcha_create.restype = agent_create.argtypes, agent_create.restype
captcha_act = lib.nw_captcha_agent_act
captcha_act.argtypes, captcha_act.restype = agent_act.argtypes, agent_act.restype
captcha_destroy = lib.nw_captcha_agent_destroy
captcha_destroy.argtypes, captcha_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
captcha_publish = lib.nw_captcha_agent_publish
captcha_publish.argtypes, captcha_publish.restype = agent_publish.argtypes, agent_publish.restype
assert not captcha_create(1, 1, 1, 17, 0, 0, 24, False)

captcha = captcha_create(1, 1, 1, 17, 0.25, 0.25, 25, False)
assert captcha
try:
    current = publish(captcha, 1, dt=0.05, publish_abi=captcha_publish)
    stamp = 1
    alphabet = "ACDEFGHJKMNPQRTUVWXY347"
    for char in "MNUJ":
        stamp += 1
        assert captcha_act(captcha, alphabet.index(char), stamp) == current.open_receipt
        assert not captcha_act(captcha, 24, stamp)
        stamp += 1
        current = publish(captcha, stamp, dt=0.05, publish_abi=captcha_publish)
        assert current.open_receipt and not current.outcome_receipt
    stamp += 1
    receipt = captcha_act(captcha, 24, stamp)
    verdict = publish(captcha, stamp + 1, dt=0.05, publish_abi=captcha_publish)
    assert verdict.outcome_receipt == receipt and verdict.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, verdict.digest, 1) == 1
    assert publish(captcha, stamp + 2, dt=0.05, publish_abi=captcha_publish).done
finally:
    captcha_destroy(captcha)

captcha = captcha_create(1, 2, 1, 17, 0.1, 0.05, 25, False)
assert captcha
try:
    assert publish(captcha, 1, dt=0.05, publish_abi=captcha_publish).open_receipt
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(captcha, 2, dt=0.05, publish_abi=captcha_publish).outcome_receipt
    for trial, stamp in ((1, 3), (2, 5)):
        flag = publish(captcha, stamp, dt=0.05, publish_abi=captcha_publish)
        assert flag.trial == trial and flag.outcome_receipt and flag.outcome_scalar == -1
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
        after = publish(captcha, stamp + 1, dt=0.05, publish_abi=captcha_publish)
        assert after.done if trial == 2 else (after.trial == 2 and after.open_receipt)
finally:
    captcha_destroy(captcha)
print("PASS: native Captcha action receipts, timeout, refill, pixel-verified verdicts, and cleanup")

signals_create = lib.nw_signals_agent_create
signals_create.argtypes, signals_create.restype = agent_create.argtypes, agent_create.restype
signals_act = lib.nw_signals_agent_act
signals_act.argtypes, signals_act.restype = agent_act.argtypes, agent_act.restype
signals_destroy = lib.nw_signals_agent_destroy
signals_destroy.argtypes, signals_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
signals_publish = lib.nw_signals_agent_publish
signals_publish.argtypes, signals_publish.restype = agent_publish.argtypes, agent_publish.restype
assert not signals_create(12, 1, 1, 17, 0, 0, 15, False)

signals = signals_create(12, 1, 1, 17, 0, 0, 16, False)
assert signals
try:
    current = publish(signals, 1, publish_abi=signals_publish)
    # Source solution includes both roles and eight two-part messages.
    ports = (0, 11, 15, 0, 9, 10, 1, 11, 15, 0, 9, 14,
             3, 12, 15, 3, 12, 14, 3, 12, 10, 3, 9, 8)
    assert not signals_act(signals, 16, 2)
    for index, port in enumerate(ports):
        stamp = 2 * index + 2
        receipt = signals_act(signals, port, stamp)
        assert receipt == current.open_receipt != 0
        assert not signals_act(signals, port, stamp)
        current = publish(signals, stamp + 1, publish_abi=signals_publish)
        if index < len(ports) - 1:
            assert current.open_receipt > receipt and not current.outcome_receipt
    assert current.outcome_receipt == receipt and current.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, current.digest, 1) == 1
    assert publish(signals, stamp + 2, publish_abi=signals_publish).done
finally:
    signals_destroy(signals)

signals = signals_create(1, 2, 1, 17, 0.1, 0.05, 16, False)
assert signals
try:
    assert publish(signals, 1, publish_abi=signals_publish).open_receipt
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not publish(signals, 2, publish_abi=signals_publish).outcome_receipt
    for trial, stamp in ((1, 3), (2, 5)):
        flag = publish(signals, stamp, publish_abi=signals_publish)
        assert flag.trial == trial and flag.outcome_receipt and flag.outcome_scalar == -1
        assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
        after = publish(signals, stamp + 1, publish_abi=signals_publish)
        assert after.done if trial == 2 else (after.trial == 2 and after.open_receipt)
finally:
    signals_destroy(signals)
print("PASS: native Signals two-glyph receipts, pixel-verified verdicts, clock refill, and cleanup")

fold_it_create = lib.nw_fold_it_agent_create
fold_it_create.argtypes, fold_it_create.restype = agent_create.argtypes, agent_create.restype
fold_it_act = lib.nw_fold_it_agent_act
fold_it_act.argtypes, fold_it_act.restype = agent_act.argtypes, agent_act.restype
fold_it_destroy = lib.nw_fold_it_agent_destroy
fold_it_destroy.argtypes, fold_it_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
fold_it_publish = lib.nw_fold_it_agent_publish
fold_it_publish.argtypes, fold_it_publish.restype = agent_publish.argtypes, agent_publish.restype
assert not fold_it_create(25, 2, 1, 17, 0.1, 0.05, 5, False)

fold_it = fold_it_create(25, 2, 1, 17, 0.1, 0.05, 6, False)
assert fold_it
try:
    first = publish(fold_it, 1, publish_abi=fold_it_publish)
    assert first.open_receipt and first.trial == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not fold_it_act(fold_it, 6, 2)
    # Python's first rung-25 puzzle at session seed 17 has answer 3.
    receipt = fold_it_act(fold_it, 2, 2)
    assert receipt == first.open_receipt
    assert not fold_it_act(fold_it, 0, 2)
    win = publish(fold_it, 3, publish_abi=fold_it_publish)
    assert win.outcome_receipt == receipt and win.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, win.digest, 1) == 1
    second = publish(fold_it, 4, publish_abi=fold_it_publish)
    assert second.trial == 2 and second.open_receipt > receipt and not second.outcome_receipt
    assert not publish(fold_it, 5, publish_abi=fold_it_publish).outcome_receipt
    flag = publish(fold_it, 6, publish_abi=fold_it_publish)
    assert flag.trial == 2 and flag.outcome_receipt == second.open_receipt and flag.outcome_scalar == -1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
    assert publish(fold_it, 7, publish_abi=fold_it_publish).done
finally:
    fold_it_destroy(fold_it)
print("PASS: native Fold It six ports, receipt-linked pixel verdicts, think clock, and cleanup")

who_knows_what_create = lib.nw_who_knows_what_agent_create
who_knows_what_create.argtypes, who_knows_what_create.restype = agent_create.argtypes, agent_create.restype
who_knows_what_act = lib.nw_who_knows_what_agent_act
who_knows_what_act.argtypes, who_knows_what_act.restype = agent_act.argtypes, agent_act.restype
who_knows_what_destroy = lib.nw_who_knows_what_agent_destroy
who_knows_what_destroy.argtypes, who_knows_what_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
who_knows_what_publish = lib.nw_who_knows_what_agent_publish
who_knows_what_publish.argtypes, who_knows_what_publish.restype = agent_publish.argtypes, agent_publish.restype
assert not who_knows_what_create(25, 2, 1, 222, 0.1, 0.05, 3, False)

who_knows_what = who_knows_what_create(25, 2, 1, 222, 0.1, 0.05, 4, False)
assert who_knows_what
try:
    first = publish(who_knows_what, 1, publish_abi=who_knows_what_publish)
    assert first.open_receipt and first.trial == 1
    assert packet.raw[36:40] == bytes((96, 120, 168, 255))
    assert not who_knows_what_act(who_knows_what, 4, 2)
    # Python's first rung-25 story at session seed 222 asks for the drawer.
    receipt = who_knows_what_act(who_knows_what, 2, 2)
    assert receipt == first.open_receipt
    assert not who_knows_what_act(who_knows_what, 0, 2)
    win = publish(who_knows_what, 3, publish_abi=who_knows_what_publish)
    assert win.outcome_receipt == receipt and win.outcome_scalar == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, win.digest, 1) == 1
    second = publish(who_knows_what, 4, publish_abi=who_knows_what_publish)
    assert second.trial == 2 and second.open_receipt > receipt and not second.outcome_receipt
    assert not publish(who_knows_what, 5, publish_abi=who_knows_what_publish).outcome_receipt
    flag = publish(who_knows_what, 6, publish_abi=who_knows_what_publish)
    assert flag.trial == 2 and flag.outcome_receipt == second.open_receipt and flag.outcome_scalar == -1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
    assert publish(who_knows_what, 7, publish_abi=who_knows_what_publish).done
finally:
    who_knows_what_destroy(who_knows_what)
print("PASS: native Who Knows What? four ports, receipt-linked pixel verdicts, think clock, and cleanup")

gamble_create = lib.nw_gamble_agent_create
gamble_create.argtypes, gamble_create.restype = agent_create.argtypes, agent_create.restype
gamble_act = lib.nw_gamble_agent_act
gamble_act.argtypes, gamble_act.restype = agent_act.argtypes, agent_act.restype
gamble_destroy = lib.nw_gamble_agent_destroy
gamble_destroy.argtypes, gamble_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
gamble_publish = lib.nw_gamble_agent_publish
gamble_publish.argtypes, gamble_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not gamble_create(1, 1, 1, 17, 0, 0, 8, False)
assert not gamble_create(1, 1, 1, 17, float("inf"), 0, 9, False)
gamble = gamble_create(1, 1, 1, 17, 0, 0, 9, False)
assert gamble
try:
    frame = publish(gamble, 1, publish_abi=gamble_publish)
    for tick in range(1, 26):
        acted = frame.open_receipt
        assert acted and gamble_act(gamble, 1, 2 * tick) == acted
        assert not gamble_act(gamble, 1, 2 * tick)
        frame = publish(gamble, 2 * tick + 1, publish_abi=gamble_publish)
        if tick < 25:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == acted and frame.outcome_scalar == 1
    assert frame.action_port == 1
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, frame.digest, 1) == 1
    done = publish(gamble, 52, publish_abi=gamble_publish)
    assert done.done and not done.outcome_receipt
finally:
    gamble_destroy(gamble)

gamble = gamble_create(18, 2, 1, 17, 0.1, 0.05, 9, False)
assert gamble
try:
    first = publish(gamble, 1, publish_abi=gamble_publish)
    assert first.open_receipt
    assert not publish(gamble, 2, publish_abi=gamble_publish).outcome_receipt
    flag = publish(gamble, 3, publish_abi=gamble_publish)
    assert flag.outcome_scalar == -1 and flag.outcome_receipt == first.open_receipt
    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, flag.digest, -1) == 1
    second = publish(gamble, 4, publish_abi=gamble_publish)
    assert second.trial == 2 and second.open_receipt > first.open_receipt
    assert gamble_act(gamble, 8, 5) == second.open_receipt
    loss = publish(gamble, 6, publish_abi=gamble_publish)
    assert loss.outcome_receipt == second.open_receipt and loss.outcome_scalar == -1
    assert loss.action_port == 8
    done = publish(gamble, 7, publish_abi=gamble_publish)
    assert done.done and not done.outcome_receipt
finally:
    gamble_destroy(gamble)
print("PASS: native Gamble receipts, source-backed play, timeout and Stop verdicts, and completion")

dispatch_create = lib.nw_dispatch_agent_create
dispatch_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool] * 2
dispatch_create.restype = ctypes.c_int64
dispatch_act = lib.nw_dispatch_agent_act
dispatch_act.argtypes, dispatch_act.restype = agent_act.argtypes, agent_act.restype
dispatch_destroy = lib.nw_dispatch_agent_destroy
dispatch_destroy.argtypes, dispatch_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
dispatch_publish = lib.nw_dispatch_agent_publish
dispatch_publish.argtypes, dispatch_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not dispatch_create(8, 1, 0, 17, 17, False, True)
for coached in (False, True):
    handle = dispatch_create(8, 1, 0, 17, 18, coached, True)
    assert handle
    try:
        frame = publish(handle, 1, dt=0.1, publish_abi=dispatch_publish)
        ticks = dispatch_fixture(coached)
        for index, (port, scalar, words, judged) in enumerate(ticks, 1):
            acted = frame.open_receipt
            assert acted and dispatch_act(handle, port, 2 * index) == acted
            assert not dispatch_act(handle, port, 2 * index)
            frame = publish(handle, 2 * index + 1, dt=0.1, publish_abi=dispatch_publish)
            assert not frame.done
            if coached or scalar:
                assert (frame.outcome_receipt, frame.outcome_scalar, frame.action_port) == (acted, scalar, port), (
                    coached, index, words, frame.outcome_scalar)
                if scalar:
                    assert verify_outcome_frame(ctypes.byref(packet, 36), rgba_size, width, height, frame.digest, scalar) == 1
            else:
                assert not frame.outcome_receipt
            assert bool(frame.open_receipt) != judged
        frame = publish(handle, 2 * len(ticks) + 2, dt=0.1, publish_abi=dispatch_publish)
        assert frame.done and not frame.outcome_receipt
    finally:
        dispatch_destroy(handle)
print("PASS: native Dispatch clock, Python sparse and coached replays, rendered verdicts, and completion")

bluff_create = lib.nw_bluff_agent_create
bluff_create.argtypes, bluff_create.restype = agent_create.argtypes, agent_create.restype
bluff_act = lib.nw_bluff_agent_act
bluff_act.argtypes, bluff_act.restype = agent_act.argtypes, agent_act.restype
bluff_destroy = lib.nw_bluff_agent_destroy
bluff_destroy.argtypes, bluff_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
bluff_publish = lib.nw_bluff_agent_publish
bluff_publish.argtypes, bluff_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not bluff_create(1, 1, 1, 17, 0, 0, 1, False)
assert not bluff_create(1, 1, 1, 17, float("inf"), 0, 2, False)
bluff = bluff_create(1, 1, 0, 17, 0, 0, 2, False)
assert bluff
try:
    frame = publish(bluff, 1, publish_abi=bluff_publish)
    for move in range(1, 23):
        receipt = frame.open_receipt
        assert receipt and bluff_act(bluff, (move + 1) % 2, 2 * move) == receipt
        assert not bluff_act(bluff, (move + 1) % 2, 2 * move)
        frame = publish(bluff, 2 * move + 1, publish_abi=bluff_publish)
        if move < 22:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(bluff, 46, publish_abi=bluff_publish).done
finally:
    bluff_destroy(bluff)

bluff = bluff_create(3, 2, 1, 17, 0.1, 0.05, 2, False)
assert bluff
try:
    first = publish(bluff, 1, publish_abi=bluff_publish)
    assert first.open_receipt and not publish(bluff, 2, publish_abi=bluff_publish).outcome_receipt
    flag = publish(bluff, 3, publish_abi=bluff_publish)
    assert flag.outcome_receipt == first.open_receipt and flag.outcome_scalar == -1
    second = publish(bluff, 4, publish_abi=bluff_publish)
    assert second.open_receipt and not second.outcome_receipt
    flag = publish(bluff, 5, publish_abi=bluff_publish)
    assert flag.outcome_receipt == second.open_receipt and flag.outcome_scalar == -1
    assert publish(bluff, 6, publish_abi=bluff_publish).done
finally:
    bluff_destroy(bluff)
print("PASS: native Bluff receipts, seeded play, two timed forfeits, refill, and completion")

bandit_create = lib.nw_explore_exploit_agent_create
bandit_create.argtypes, bandit_create.restype = agent_create.argtypes, agent_create.restype
bandit_act = lib.nw_explore_exploit_agent_act
bandit_act.argtypes, bandit_act.restype = agent_act.argtypes, agent_act.restype
bandit_destroy = lib.nw_explore_exploit_agent_destroy
bandit_destroy.argtypes, bandit_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
bandit_publish = lib.nw_explore_exploit_agent_publish
bandit_publish.argtypes, bandit_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not bandit_create(1, 1, 1, 17, 0, 0, 7, False)
assert not bandit_create(1, 1, 1, 17, float("inf"), 0, 8, False)
bandit = bandit_create(16, 1, 0, 17, 0, 0, 8, False)
assert bandit
try:
    frame = publish(bandit, 1, publish_abi=bandit_publish)
    for pull in range(61):
        receipt = frame.open_receipt
        port = 7 if pull == 0 else 0
        stamp = 2 * pull + 2
        assert receipt and bandit_act(bandit, port, stamp) == receipt
        assert not bandit_act(bandit, port, stamp)
        frame = publish(bandit, stamp + 1, publish_abi=bandit_publish)
        if pull < 60:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(bandit, 124, publish_abi=bandit_publish).done
finally:
    bandit_destroy(bandit)

bandit = bandit_create(16, 2, 1, 17, 0.1, 0.05, 8, False)
assert bandit
try:
    first = publish(bandit, 1, publish_abi=bandit_publish)
    assert first.open_receipt and not publish(bandit, 2, publish_abi=bandit_publish).outcome_receipt
    flag = publish(bandit, 3, publish_abi=bandit_publish)
    assert flag.outcome_receipt == first.open_receipt and flag.outcome_scalar == -1
    second = publish(bandit, 4, publish_abi=bandit_publish)
    assert second.trial == 2 and second.open_receipt and not second.outcome_receipt
    flag = publish(bandit, 5, publish_abi=bandit_publish)
    assert flag.outcome_receipt == second.open_receipt and flag.outcome_scalar == -1
    assert publish(bandit, 6, publish_abi=bandit_publish).done
finally:
    bandit_destroy(bandit)
print("PASS: native Explore or Exploit eight ports, receipts, seeded play, forfeits, refill, and completion")

firebreak_create = lib.nw_firebreak_agent_create
firebreak_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
firebreak_create.restype = ctypes.c_int64
firebreak_act = lib.nw_firebreak_agent_act
firebreak_act.argtypes, firebreak_act.restype = agent_act.argtypes, agent_act.restype
firebreak_destroy = lib.nw_firebreak_agent_destroy
firebreak_destroy.argtypes, firebreak_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
firebreak_publish = lib.nw_firebreak_agent_publish
firebreak_publish.argtypes, firebreak_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not firebreak_create(16, 1, 1, 17, 8, False)
firebreak = firebreak_create(16, 1, 1, 17, 9, False)
assert firebreak
try:
    frame = publish(firebreak, 1, publish_abi=firebreak_publish)
    # Reproduce the same right jump, dig, and 20 Hz clock as the Python replay.
    for tick in range(370):
        receipt = frame.open_receipt
        port = 8 if tick == 0 else 4 if tick == 1 else 0
        stamp = 2 * tick + 2
        assert receipt and firebreak_act(firebreak, port, stamp) == receipt
        assert not firebreak_act(firebreak, port, stamp)
        frame = publish(firebreak, stamp + 1, publish_abi=firebreak_publish)
        if tick < 369:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(firebreak, 742, publish_abi=firebreak_publish).done
finally:
    firebreak_destroy(firebreak)
print("PASS: native Firebreak nine ports, verified Python verdict at tick 370, and completion")

crossroads_create = lib.nw_crossroads_agent_create
crossroads_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
crossroads_create.restype = ctypes.c_int64
crossroads_act = lib.nw_crossroads_agent_act
crossroads_act.argtypes, crossroads_act.restype = agent_act.argtypes, agent_act.restype
crossroads_destroy = lib.nw_crossroads_agent_destroy
crossroads_destroy.argtypes, crossroads_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
crossroads_publish = lib.nw_crossroads_agent_publish
crossroads_publish.argtypes, crossroads_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not crossroads_create(16, 1, 1, 17, 3, False)
crossroads = crossroads_create(16, 1, 1, 17, 4, False)
assert crossroads
try:
    frame = publish(crossroads, 1, publish_abi=crossroads_publish)
    # Reproduce Python’s first-junction switching at 20 Hz.
    for tick in range(333):
        receipt = frame.open_receipt
        stamp = 2 * tick + 2
        assert receipt and crossroads_act(crossroads, 0, stamp) == receipt
        assert not crossroads_act(crossroads, 0, stamp)
        frame = publish(crossroads, stamp + 1, publish_abi=crossroads_publish)
        if tick < 332:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(crossroads, 668, publish_abi=crossroads_publish).done
finally:
    crossroads_destroy(crossroads)
print("PASS: native Crossroads four ports, verified Python verdict at tick 333, and completion")

railyard_create = lib.nw_railyard_agent_create
railyard_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
railyard_create.restype = ctypes.c_int64
railyard_act = lib.nw_railyard_agent_act
railyard_act.argtypes, railyard_act.restype = agent_act.argtypes, agent_act.restype
railyard_destroy = lib.nw_railyard_agent_destroy
railyard_destroy.argtypes, railyard_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
railyard_publish = lib.nw_railyard_agent_publish
railyard_publish.argtypes, railyard_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not railyard_create(16, 1, 1, 17, 16, False)
railyard = railyard_create(16, 1, 1, 17, 17, False)
assert railyard
try:
    frame = publish(railyard, 1, publish_abi=railyard_publish)
    # Reproduce Python’s repeated throws of the first set of points at 20 Hz.
    for tick in range(95):
        receipt = frame.open_receipt
        stamp = 2 * tick + 2
        assert receipt and railyard_act(railyard, 0, stamp) == receipt
        assert not railyard_act(railyard, 0, stamp)
        frame = publish(railyard, stamp + 1, publish_abi=railyard_publish)
        if tick < 94:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(railyard, 192, publish_abi=railyard_publish).done
finally:
    railyard_destroy(railyard)
print("PASS: native Rail Yard 17 ports, verified Python derailment at tick 95, and completion")

airtraffic_create = lib.nw_airtraffic_agent_create
airtraffic_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
airtraffic_create.restype = ctypes.c_int64
airtraffic_act = lib.nw_airtraffic_agent_act
airtraffic_act.argtypes, airtraffic_act.restype = agent_act.argtypes, agent_act.restype
airtraffic_destroy = lib.nw_airtraffic_agent_destroy
airtraffic_destroy.argtypes, airtraffic_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
airtraffic_publish = lib.nw_airtraffic_agent_publish
airtraffic_publish.argtypes, airtraffic_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not airtraffic_create(16, 1, 1, 17, 11, False)
airtraffic = airtraffic_create(16, 1, 1, 17, 12, False)
assert airtraffic
try:
    frame = publish(airtraffic, 1, publish_abi=airtraffic_publish)
    # Reproduce Python’s repeated attempts to select slot 1 at 20 Hz.
    for tick in range(339):
        receipt = frame.open_receipt
        stamp = 2 * tick + 2
        assert receipt and airtraffic_act(airtraffic, 0, stamp) == receipt
        assert not airtraffic_act(airtraffic, 0, stamp)
        frame = publish(airtraffic, stamp + 1, publish_abi=airtraffic_publish)
        if tick < 338:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(airtraffic, 680, publish_abi=airtraffic_publish).done
finally:
    airtraffic_destroy(airtraffic)
print("PASS: native Air Traffic 12 ports, verified Python airspace verdict at tick 339, and completion")

escort_create = lib.nw_escort_agent_create
escort_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
escort_create.restype = ctypes.c_int64
escort_act = lib.nw_escort_agent_act
escort_act.argtypes, escort_act.restype = agent_act.argtypes, agent_act.restype
escort_destroy = lib.nw_escort_agent_destroy
escort_destroy.argtypes, escort_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
escort_publish = lib.nw_escort_agent_publish
escort_publish.argtypes, escort_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not escort_create(16, 1, 1, 17, 5, False)
escort = escort_create(16, 1, 1, 17, 6, False)
assert escort
try:
    frame = publish(escort, 1, publish_abi=escort_publish)
    # Reproduce Python’s two lever pulls half a second apart at 20 Hz.
    for tick in range(205):
        receipt = frame.open_receipt
        port = 0 if tick == 0 else 1 if tick == 10 else 5
        stamp = 2 * tick + 2
        assert receipt and escort_act(escort, port, stamp) == receipt
        assert not escort_act(escort, port, stamp)
        frame = publish(escort, stamp + 1, publish_abi=escort_publish)
        if tick < 204:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(escort, 412, publish_abi=escort_publish).done
finally:
    escort_destroy(escort)
print("PASS: native Escort 6 ports, verified Python flame verdict at tick 205, and completion")

sokobanlive_create = lib.nw_sokobanlive_agent_create
sokobanlive_create.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_bool]
sokobanlive_create.restype = ctypes.c_int64
sokobanlive_act = lib.nw_sokobanlive_agent_act
sokobanlive_act.argtypes, sokobanlive_act.restype = agent_act.argtypes, agent_act.restype
sokobanlive_destroy = lib.nw_sokobanlive_agent_destroy
sokobanlive_destroy.argtypes, sokobanlive_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
sokobanlive_publish = lib.nw_sokobanlive_agent_publish
sokobanlive_publish.argtypes, sokobanlive_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not sokobanlive_create(1, 1, 1, 17, 3, False)
sokobanlive = sokobanlive_create(1, 1, 1, 17, 4, False)
assert sokobanlive
try:
    frame = publish(sokobanlive, 1, publish_abi=sokobanlive_publish)
    # Reproduce Python’s repeated down moves at 20 Hz.
    for tick in range(12):
        receipt = frame.open_receipt
        port = 1
        stamp = 2 * tick + 2
        assert receipt and sokobanlive_act(sokobanlive, port, stamp) == receipt
        assert not sokobanlive_act(sokobanlive, port, stamp)
        frame = publish(sokobanlive, stamp + 1, publish_abi=sokobanlive_publish)
        if tick < 11:
            assert not frame.outcome_receipt
    assert frame.outcome_receipt == receipt and frame.outcome_scalar == -1
    assert publish(sokobanlive, 26, publish_abi=sokobanlive_publish).done
finally:
    sokobanlive_destroy(sokobanlive)
print("PASS: native Sokoban Live 4 ports, verified Python stuck verdict at tick 12, and completion")

kitchen_create = lib.nw_kitchen_agent_create
kitchen_create.argtypes, kitchen_create.restype = sokobanlive_create.argtypes, sokobanlive_create.restype
kitchen_destroy = lib.nw_kitchen_agent_destroy
kitchen_destroy.argtypes, kitchen_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
kitchen_publish = lib.nw_kitchen_agent_publish
kitchen_publish.argtypes, kitchen_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not kitchen_create(1, 1, 0, 17, 12, False)
kitchen = kitchen_create(1, 1, 0, 17, 13, False)
assert kitchen
try:
    frame = publish(kitchen, 1, publish_abi=kitchen_publish)
    assert frame.open_receipt
    for tick in range(1, 1568):
        frame = publish(kitchen, tick + 1, publish_abi=kitchen_publish)
        if frame.outcome_receipt:
            break
    assert tick == 1567 and frame.outcome_scalar == -1, (tick, frame.outcome_scalar)
    assert publish(kitchen, tick + 2, publish_abi=kitchen_publish).done
finally:
    kitchen_destroy(kitchen)
print("PASS: native Kitchen clocked agent, thirteen ports, ticket-expiration verdict, and completion")

crane_create = lib.nw_crane_agent_create
crane_create.argtypes, crane_create.restype = kitchen_create.argtypes, kitchen_create.restype
crane_act = lib.nw_crane_agent_act
crane_act.argtypes, crane_act.restype = agent_act.argtypes, agent_act.restype
crane_destroy = lib.nw_crane_agent_destroy
crane_destroy.argtypes, crane_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
crane_publish = lib.nw_crane_agent_publish
crane_publish.argtypes, crane_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not crane_create(1, 1, 0, 17, 4, False)
crane = crane_create(1, 1, 0, 17, 5, False)
assert crane
try:
    frame = publish(crane, 1, publish_abi=crane_publish)
    assert frame.open_receipt and crane_act(crane, 4, 2) == frame.open_receipt
    for tick in range(1, 2402):
        frame = publish(crane, tick + 2, publish_abi=crane_publish)
        if frame.outcome_receipt:
            break
    assert tick == 2401 and frame.outcome_scalar == -1, (tick, frame.outcome_scalar)
    assert publish(crane, tick + 3, publish_abi=crane_publish).done
finally:
    crane_destroy(crane)
print("PASS: native Crane five-port agent, Python timeout, verdict, and completion")

ferry_create = lib.nw_ferry_agent_create
ferry_create.argtypes, ferry_create.restype = crane_create.argtypes, crane_create.restype
ferry_act = lib.nw_ferry_agent_act
ferry_act.argtypes, ferry_act.restype = agent_act.argtypes, agent_act.restype
ferry_destroy = lib.nw_ferry_agent_destroy
ferry_destroy.argtypes, ferry_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
ferry_publish = lib.nw_ferry_agent_publish
ferry_publish.argtypes, ferry_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not ferry_create(1, 1, 0, 17, 5, False)
ferry_agent = ferry_create(1, 1, 0, 17, 6, False)
assert ferry_agent
try:
    frame = publish(ferry_agent, 1, publish_abi=ferry_publish)
    for tick in range(1, 2474):
        if tick == 2473:
            assert frame.open_receipt and ferry_act(ferry_agent, 2, tick + 1) == frame.open_receipt
        frame = publish(ferry_agent, tick + 1, publish_abi=ferry_publish)
        if frame.outcome_receipt:
            break
    assert tick == 2473 and frame.outcome_scalar == -1, (tick, frame.outcome_scalar)
    assert publish(ferry_agent, tick + 2, publish_abi=ferry_publish).done
finally:
    ferry_destroy(ferry_agent)
print("PASS: native Ferry six-port agent, Python drift verdict, and completion")

docking_create = lib.nw_docking_agent_create
docking_create.argtypes, docking_create.restype = ferry_create.argtypes, ferry_create.restype
docking_act = lib.nw_docking_agent_act
docking_act.argtypes, docking_act.restype = agent_act.argtypes, agent_act.restype
docking_destroy = lib.nw_docking_agent_destroy
docking_destroy.argtypes, docking_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
docking_publish = lib.nw_docking_agent_publish
docking_publish.argtypes, docking_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not docking_create(1, 1, 0, 17, 11, False)
docking_agent = docking_create(1, 1, 0, 17, 12, False)
assert docking_agent
try:
    frame = publish(docking_agent, 1, publish_abi=docking_publish)
    assert frame.open_receipt and docking_act(docking_agent, 11, 2) == frame.open_receipt
    # The initial 0.25 m/s drift crosses 12 m in 48 s, well off centre.
    for tick in range(1, 963):
        frame = publish(docking_agent, tick + 2, publish_abi=docking_publish)
        if frame.outcome_receipt:
            break
    assert tick in (960, 961) and frame.outcome_scalar == -1, (tick, frame.outcome_scalar)
    assert publish(docking_agent, tick + 3, publish_abi=docking_publish).done
finally:
    docking_destroy(docking_agent)
print("PASS: native Docking twelve-port agent, contact verdict, and completion")

rover_create = lib.nw_rover_agent_create
rover_create.argtypes, rover_create.restype = docking_create.argtypes, docking_create.restype
rover_act = lib.nw_rover_agent_act
rover_act.argtypes, rover_act.restype = agent_act.argtypes, agent_act.restype
rover_destroy = lib.nw_rover_agent_destroy
rover_destroy.argtypes, rover_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
rover_publish = lib.nw_rover_agent_publish
rover_publish.argtypes, rover_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not rover_create(4, 1, 0, 17, 3, False)
rover_agent = rover_create(4, 1, 0, 17, 4, False)
assert rover_agent
try:
    frame = publish(rover_agent, 1, dt=0.1, publish_abi=rover_publish)
    for tick in range(1, 27):
        assert frame.open_receipt and rover_act(rover_agent, 0, 2 * tick) == frame.open_receipt
        frame = publish(rover_agent, 2 * tick + 1, dt=0.1, publish_abi=rover_publish)
        if frame.outcome_receipt:
            break
    # Python's seed-17 rung-four drive-only run hits the first rock at 2.4583 s.
    assert tick == 25 and frame.outcome_scalar == -1, (tick, frame.outcome_scalar)
    assert publish(rover_agent, 2 * tick + 2, dt=0.1, publish_abi=rover_publish).done
finally:
    rover_destroy(rover_agent)
print("PASS: native Rover four-port agent, Python rock collision, and completion")

unicycle_create = lib.nw_unicycle_agent_create
unicycle_create.argtypes, unicycle_create.restype = rover_create.argtypes, rover_create.restype
unicycle_act = lib.nw_unicycle_agent_act
unicycle_act.argtypes, unicycle_act.restype = agent_act.argtypes, agent_act.restype
unicycle_destroy = lib.nw_unicycle_agent_destroy
unicycle_destroy.argtypes, unicycle_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
unicycle_publish = lib.nw_unicycle_agent_publish
unicycle_publish.argtypes, unicycle_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not unicycle_create(1, 1, 0, 17, 7, False)
unicycle_agent = unicycle_create(1, 1, 0, 17, 8, False)
assert unicycle_agent
try:
    frame = publish(unicycle_agent, 1, dt=0.1, publish_abi=unicycle_publish)
    for tick in range(1, 5):
        assert frame.open_receipt and unicycle_act(unicycle_agent, 7, 2 * tick) == frame.open_receipt
        frame = publish(unicycle_agent, 2 * tick + 1, dt=0.1, publish_abi=unicycle_publish)
        if frame.outcome_receipt:
            break
    # Python’s combined back-pedal and forward lean falls at 0.2917 s.
    assert tick == 3 and frame.outcome_scalar == -1, (tick, frame.outcome_scalar)
    assert publish(unicycle_agent, 2 * tick + 2, dt=0.1, publish_abi=unicycle_publish).done
finally:
    unicycle_destroy(unicycle_agent)
print("PASS: native Unicycle eight-port agent, Python fall verdict, and completion")


morning_round_create = lib.nw_morning_round_agent_create
morning_round_create.argtypes, morning_round_create.restype = rover_create.argtypes, rover_create.restype
morning_round_act = lib.nw_morning_round_agent_act
morning_round_act.argtypes, morning_round_act.restype = agent_act.argtypes, agent_act.restype
morning_round_destroy = lib.nw_morning_round_agent_destroy
morning_round_destroy.argtypes, morning_round_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
morning_round_publish = lib.nw_morning_round_agent_publish
morning_round_publish.argtypes, morning_round_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not morning_round_create(1, 1, 0, 17, 5, False)
morning_round_agent = morning_round_create(1, 1, 0, 17, 6, False)
assert morning_round_agent
try:
    frame = publish(morning_round_agent, 1, dt=0.1, publish_abi=morning_round_publish)
    for step in range(1, 240):
        assert frame.open_receipt
        port = 4 if step == 25 else 2
        assert morning_round_act(morning_round_agent, port, 2 * step) == frame.open_receipt
        frame = publish(morning_round_agent, 2 * step + 1, dt=0.1, publish_abi=morning_round_publish)
        if frame.outcome_receipt:
            break
    assert frame.outcome_scalar == -1
    assert publish(morning_round_agent, 2 * step + 2, dt=0.1, publish_abi=morning_round_publish).done
finally:
    morning_round_destroy(morning_round_agent)
print("PASS: native Morning Round six-port agent, controls, verdict, and completion")

heavier_create = lib.nw_heavier_agent_create
heavier_create.argtypes, heavier_create.restype = rover_create.argtypes, rover_create.restype
heavier_act = lib.nw_heavier_agent_act
heavier_act.argtypes, heavier_act.restype = agent_act.argtypes, agent_act.restype
heavier_destroy = lib.nw_heavier_agent_destroy
heavier_destroy.argtypes, heavier_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
heavier_publish = lib.nw_heavier_agent_publish
heavier_publish.argtypes, heavier_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not heavier_create(1, 1, 0, 17, 7, False)
heavier_agent = heavier_create(1, 1, 0, 17, 8, False)
assert heavier_agent
try:
    frame = publish(heavier_agent, 1, dt=0.1, publish_abi=heavier_publish)
    assert heavier_act(heavier_agent, 0, 2) == frame.open_receipt
    frame = publish(heavier_agent, 3, dt=0.1, publish_abi=heavier_publish)
    assert heavier_act(heavier_agent, 6, 4) == frame.open_receipt
    frame = publish(heavier_agent, 5, dt=0.1, publish_abi=heavier_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == -1
    assert publish(heavier_agent, 6, dt=0.1, publish_abi=heavier_publish).done
finally:
    heavier_destroy(heavier_agent)
print("PASS: native Heavier eight-port agent, push, answer, verdict, and completion")

full_stop_create = lib.nw_full_stop_agent_create
full_stop_create.argtypes, full_stop_create.restype = rover_create.argtypes, rover_create.restype
full_stop_act = lib.nw_full_stop_agent_act
full_stop_act.argtypes, full_stop_act.restype = agent_act.argtypes, agent_act.restype
full_stop_destroy = lib.nw_full_stop_agent_destroy
full_stop_destroy.argtypes, full_stop_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
full_stop_publish = lib.nw_full_stop_agent_publish
full_stop_publish.argtypes, full_stop_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not full_stop_create(1, 1, 0, 17, 15, False)
full_stop_agent = full_stop_create(1, 1, 0, 17, 16, False)
assert full_stop_agent
try:
    frame = publish(full_stop_agent, 1, dt=0.1, publish_abi=full_stop_publish)
    assert full_stop_act(full_stop_agent, 14, 2) == frame.open_receipt
    frame = publish(full_stop_agent, 3, dt=0.1, publish_abi=full_stop_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == -1
    assert publish(full_stop_agent, 4, dt=0.1, publish_abi=full_stop_publish).done
finally:
    full_stop_destroy(full_stop_agent)
print("PASS: native Full Stop sixteen-port agent, submission, verdict, and completion")

missing_word_create = lib.nw_missing_word_agent_create
missing_word_create.argtypes, missing_word_create.restype = rover_create.argtypes, rover_create.restype
missing_word_act = lib.nw_missing_word_agent_act
missing_word_act.argtypes, missing_word_act.restype = agent_act.argtypes, agent_act.restype
missing_word_destroy = lib.nw_missing_word_agent_destroy
missing_word_destroy.argtypes, missing_word_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
missing_word_publish = lib.nw_missing_word_agent_publish
missing_word_publish.argtypes, missing_word_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not missing_word_create(1, 1, 0, 17, 15, False)
missing_word_agent = missing_word_create(1, 1, 0, 17, 16, False)
assert missing_word_agent
try:
    frame = publish(missing_word_agent, 1, dt=0.1, publish_abi=missing_word_publish)
    assert missing_word_act(missing_word_agent, 14, 2) == frame.open_receipt
    frame = publish(missing_word_agent, 3, dt=0.1, publish_abi=missing_word_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == -1
    assert publish(missing_word_agent, 4, dt=0.1, publish_abi=missing_word_publish).done
finally:
    missing_word_destroy(missing_word_agent)
print("PASS: native The Missing Word sixteen-port agent, submission, verdict, and completion")

proofreader_create = lib.nw_proofreader_agent_create
proofreader_create.argtypes, proofreader_create.restype = rover_create.argtypes, rover_create.restype
proofreader_act = lib.nw_proofreader_agent_act
proofreader_act.argtypes, proofreader_act.restype = agent_act.argtypes, agent_act.restype
proofreader_destroy = lib.nw_proofreader_agent_destroy
proofreader_destroy.argtypes, proofreader_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
proofreader_publish = lib.nw_proofreader_agent_publish
proofreader_publish.argtypes, proofreader_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not proofreader_create(1, 1, 0, 17, 15, False)
proofreader_agent = proofreader_create(1, 1, 0, 17, 16, False)
assert proofreader_agent
try:
    frame = publish(proofreader_agent, 1, dt=0.1, publish_abi=proofreader_publish)
    assert proofreader_act(proofreader_agent, 14, 2) == frame.open_receipt
    frame = publish(proofreader_agent, 3, dt=0.1, publish_abi=proofreader_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == -1
    assert publish(proofreader_agent, 4, dt=0.1, publish_abi=proofreader_publish).done
finally:
    proofreader_destroy(proofreader_agent)
print("PASS: native The Proofreader sixteen-port agent, submission, verdict, and completion")

figures_of_speech_create = lib.nw_figures_of_speech_agent_create
figures_of_speech_create.argtypes, figures_of_speech_create.restype = rover_create.argtypes, rover_create.restype
figures_of_speech_act = lib.nw_figures_of_speech_agent_act
figures_of_speech_act.argtypes, figures_of_speech_act.restype = agent_act.argtypes, agent_act.restype
figures_of_speech_destroy = lib.nw_figures_of_speech_agent_destroy
figures_of_speech_destroy.argtypes, figures_of_speech_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
figures_of_speech_publish = lib.nw_figures_of_speech_agent_publish
figures_of_speech_publish.argtypes, figures_of_speech_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not figures_of_speech_create(1, 1, 0, 17, 7, False)
figures_of_speech_agent = figures_of_speech_create(1, 1, 0, 17, 8, False)
assert figures_of_speech_agent
try:
    timestamp = 1
    for _ in range(150):
        frame = publish(figures_of_speech_agent, timestamp, dt=0.1, publish_abi=figures_of_speech_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(figures_of_speech_agent, timestamp + 1, dt=0.1,
                           publish_abi=figures_of_speech_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert figures_of_speech_act(figures_of_speech_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a verdict")
finally:
    figures_of_speech_destroy(figures_of_speech_agent)
print("PASS: native Figures of Speech eight-port agent, fixed-answer loss, and raster publication")

lines_create = lib.nw_between_the_lines_agent_create
lines_create.argtypes, lines_create.restype = rover_create.argtypes, rover_create.restype
lines_act = lib.nw_between_the_lines_agent_act
lines_act.argtypes, lines_act.restype = agent_act.argtypes, agent_act.restype
lines_destroy = lib.nw_between_the_lines_agent_destroy
lines_destroy.argtypes, lines_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
lines_publish = lib.nw_between_the_lines_agent_publish
lines_publish.argtypes, lines_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not lines_create(1, 1, 0, 17, 7, False)
lines_agent = lines_create(1, 1, 0, 17, 8, False)
assert lines_agent
try:
    timestamp = 1
    for _ in range(800):
        frame = publish(lines_agent, timestamp, dt=0.1, publish_abi=lines_publish)
        if frame.outcome_receipt:
            # No round is dealt that one number pressed throughout passes.
            assert frame.outcome_scalar == -1
            assert publish(lines_agent, timestamp + 1, dt=0.1, publish_abi=lines_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert lines_act(lines_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Between the Lines verdict")
finally:
    lines_destroy(lines_agent)
print("PASS: native Between the Lines eight-port agent, fixed-answer loss, and raster publication")

second_create = lib.nw_second_thoughts_agent_create
second_create.argtypes, second_create.restype = rover_create.argtypes, rover_create.restype
second_act = lib.nw_second_thoughts_agent_act
second_act.argtypes, second_act.restype = agent_act.argtypes, agent_act.restype
second_destroy = lib.nw_second_thoughts_agent_destroy
second_destroy.argtypes, second_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
second_publish = lib.nw_second_thoughts_agent_publish
second_publish.argtypes, second_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not second_create(1, 1, 0, 17, 7, False)
second_agent = second_create(1, 1, 0, 17, 8, False)
assert second_agent
try:
    timestamp = 1
    for _ in range(800):
        frame = publish(second_agent, timestamp, dt=0.1, publish_abi=second_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(second_agent, timestamp + 1, dt=0.1, publish_abi=second_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert second_act(second_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Second Thoughts verdict")
finally:
    second_destroy(second_agent)
print("PASS: native Second Thoughts eight-port agent, fixed-answer loss, and raster publication")

argue_create = lib.nw_bad_argument_agent_create
argue_create.argtypes, argue_create.restype = rover_create.argtypes, rover_create.restype
argue_act = lib.nw_bad_argument_agent_act
argue_act.argtypes, argue_act.restype = agent_act.argtypes, agent_act.restype
argue_destroy = lib.nw_bad_argument_agent_destroy
argue_destroy.argtypes, argue_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
argue_publish = lib.nw_bad_argument_agent_publish
argue_publish.argtypes, argue_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not argue_create(1, 1, 0, 17, 7, False)
argue_agent = argue_create(1, 1, 0, 17, 8, False)
assert argue_agent
try:
    timestamp = 1
    for _ in range(800):
        frame = publish(argue_agent, timestamp, dt=0.1, publish_abi=argue_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(argue_agent, timestamp + 1, dt=0.1, publish_abi=argue_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert argue_act(argue_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Bad Argument verdict")
finally:
    argue_destroy(argue_agent)
print("PASS: native Bad Argument eight-port agent, fixed-answer loss, and raster publication")

sense_create = lib.nw_social_sense_agent_create
sense_create.argtypes, sense_create.restype = rover_create.argtypes, rover_create.restype
sense_act = lib.nw_social_sense_agent_act
sense_act.argtypes, sense_act.restype = agent_act.argtypes, agent_act.restype
sense_destroy = lib.nw_social_sense_agent_destroy
sense_destroy.argtypes, sense_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
sense_publish = lib.nw_social_sense_agent_publish
sense_publish.argtypes, sense_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not sense_create(1, 1, 0, 17, 7, False)
sense_agent = sense_create(1, 1, 0, 17, 8, False)
assert sense_agent
try:
    timestamp = 1
    for _ in range(800):
        frame = publish(sense_agent, timestamp, dt=0.1, publish_abi=sense_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(sense_agent, timestamp + 1, dt=0.1, publish_abi=sense_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert sense_act(sense_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Social Sense verdict")
finally:
    sense_destroy(sense_agent)
print("PASS: native Social Sense eight-port agent, fixed-answer loss, and raster publication")

feel_create = lib.nw_which_feeling_agent_create
feel_create.argtypes, feel_create.restype = rover_create.argtypes, rover_create.restype
feel_act = lib.nw_which_feeling_agent_act
feel_act.argtypes, feel_act.restype = agent_act.argtypes, agent_act.restype
feel_destroy = lib.nw_which_feeling_agent_destroy
feel_destroy.argtypes, feel_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
feel_publish = lib.nw_which_feeling_agent_publish
feel_publish.argtypes, feel_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not feel_create(1, 1, 0, 17, 7, False)
feel_agent = feel_create(1, 1, 0, 17, 8, False)
assert feel_agent
try:
    timestamp = 1
    for _ in range(1600):
        frame = publish(feel_agent, timestamp, dt=0.1, publish_abi=feel_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(feel_agent, timestamp + 1, dt=0.1, publish_abi=feel_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert feel_act(feel_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Which Feeling verdict")
finally:
    feel_destroy(feel_agent)
print("PASS: native Which Feeling eight-port agent, fixed-answer loss, and raster publication")

# The seed dialogues' strongest feeling is always listed first, so the
# fixed player answers the second and loses.
strong_create = lib.nw_how_strongly_agent_create
strong_create.argtypes, strong_create.restype = rover_create.argtypes, rover_create.restype
strong_act = lib.nw_how_strongly_agent_act
strong_act.argtypes, strong_act.restype = agent_act.argtypes, agent_act.restype
strong_destroy = lib.nw_how_strongly_agent_destroy
strong_destroy.argtypes, strong_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
strong_publish = lib.nw_how_strongly_agent_publish
strong_publish.argtypes, strong_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not strong_create(1, 1, 0, 17, 7, False)
strong_agent = strong_create(1, 1, 0, 17, 8, False)
assert strong_agent
try:
    timestamp = 1
    for _ in range(1600):
        frame = publish(strong_agent, timestamp, dt=0.1, publish_abi=strong_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(strong_agent, timestamp + 1, dt=0.1, publish_abi=strong_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert strong_act(strong_agent, 1, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a How Strongly verdict")
finally:
    strong_destroy(strong_agent)
print("PASS: native How Strongly eight-port agent, fixed-answer loss, and raster publication")

# The seed story's feeling, Touched, is the second choice, so always
# answering the first loses.
read_create = lib.nw_reading_people_agent_create
read_create.argtypes, read_create.restype = rover_create.argtypes, rover_create.restype
read_act = lib.nw_reading_people_agent_act
read_act.argtypes, read_act.restype = agent_act.argtypes, agent_act.restype
read_destroy = lib.nw_reading_people_agent_destroy
read_destroy.argtypes, read_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
read_publish = lib.nw_reading_people_agent_publish
read_publish.argtypes, read_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not read_create(1, 1, 0, 17, 7, False)
read_agent = read_create(1, 1, 0, 17, 8, False)
assert read_agent
try:
    timestamp = 1
    for _ in range(1600):
        frame = publish(read_agent, timestamp, dt=0.1, publish_abi=read_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(read_agent, timestamp + 1, dt=0.1, publish_abi=read_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert read_act(read_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Reading People verdict")
finally:
    read_destroy(read_agent)
print("PASS: native Reading People eight-port agent, fixed-answer loss, and raster publication")

# Pressing the first answer every time leaves too many wrong to pass.
why_create = lib.nw_why_they_feel_agent_create
why_create.argtypes, why_create.restype = rover_create.argtypes, rover_create.restype
why_act = lib.nw_why_they_feel_agent_act
why_act.argtypes, why_act.restype = agent_act.argtypes, agent_act.restype
why_destroy = lib.nw_why_they_feel_agent_destroy
why_destroy.argtypes, why_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
why_publish = lib.nw_why_they_feel_agent_publish
why_publish.argtypes, why_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not why_create(1, 1, 0, 17, 7, False)
why_agent = why_create(1, 1, 0, 17, 8, False)
assert why_agent
try:
    timestamp = 1
    for _ in range(1600):
        frame = publish(why_agent, timestamp, dt=0.1, publish_abi=why_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(why_agent, timestamp + 1, dt=0.1, publish_abi=why_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert why_act(why_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Why They Feel verdict")
finally:
    why_destroy(why_agent)
print("PASS: native Why They Feel eight-port agent, fixed-answer loss, and raster publication")

tone_create = lib.nw_tone_of_voice_agent_create
tone_create.argtypes, tone_create.restype = rover_create.argtypes, rover_create.restype
tone_act = lib.nw_tone_of_voice_agent_act
tone_act.argtypes, tone_act.restype = agent_act.argtypes, agent_act.restype
tone_destroy = lib.nw_tone_of_voice_agent_destroy
tone_destroy.argtypes, tone_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
tone_publish = lib.nw_tone_of_voice_agent_publish
tone_publish.argtypes, tone_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not tone_create(1, 1, 0, 17, 7, False)
tone_agent = tone_create(1, 1, 0, 17, 8, False)
assert tone_agent
try:
    timestamp = 1
    for _ in range(1600):
        frame = publish(tone_agent, timestamp, dt=0.1, publish_abi=tone_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(tone_agent, timestamp + 1, dt=0.1, publish_abi=tone_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert tone_act(tone_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Tone of Voice verdict")
finally:
    tone_destroy(tone_agent)
print("PASS: native Tone of Voice eight-port agent, fixed-answer loss, and raster publication")

emo_create = lib.nw_emotion_agent_create
emo_create.argtypes, emo_create.restype = rover_create.argtypes, rover_create.restype
emo_act = lib.nw_emotion_agent_act
emo_act.argtypes, emo_act.restype = agent_act.argtypes, agent_act.restype
emo_destroy = lib.nw_emotion_agent_destroy
emo_destroy.argtypes, emo_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
emo_publish = lib.nw_emotion_agent_publish
emo_publish.argtypes, emo_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not emo_create(1, 1, 0, 17, 7, False)
emo_agent = emo_create(1, 1, 0, 17, 8, False)
assert emo_agent
try:
    timestamp = 1
    for _ in range(1600):
        frame = publish(emo_agent, timestamp, dt=0.1, publish_abi=emo_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(emo_agent, timestamp + 1, dt=0.1, publish_abi=emo_publish).done
            break
        timestamp += 1
        if frame.open_receipt:
            assert emo_act(emo_agent, 0, timestamp) == frame.open_receipt
            timestamp += 1
    else:
        raise AssertionError("The fixed-answer player did not receive a Emotion verdict")
finally:
    emo_destroy(emo_agent)
print("PASS: native Emotion eight-port agent, fixed-answer loss, and raster publication")

crazy_cog_create = lib.nw_crazy_cog_agent_create
crazy_cog_create.argtypes, crazy_cog_create.restype = rover_create.argtypes, rover_create.restype
crazy_cog_act = lib.nw_crazy_cog_agent_act
crazy_cog_act.argtypes, crazy_cog_act.restype = agent_act.argtypes, agent_act.restype
crazy_cog_destroy = lib.nw_crazy_cog_agent_destroy
crazy_cog_destroy.argtypes, crazy_cog_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
crazy_cog_publish = lib.nw_crazy_cog_agent_publish
crazy_cog_publish.argtypes, crazy_cog_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not crazy_cog_create(20, 1, 0, 17, 16, False)
crazy_cog = crazy_cog_create(20, 1, 0, 17, 17, False)
assert crazy_cog
try:
    front = publish(crazy_cog, 1, publish_abi=crazy_cog_publish)
    assert front.open_receipt and not front.done
    assert crazy_cog_act(crazy_cog, 17, 2) == 0
    assert crazy_cog_act(crazy_cog, 15, 2) == front.open_receipt
    deeper = publish(crazy_cog, 3, publish_abi=crazy_cog_publish)
    assert deeper.open_receipt != front.open_receipt and deeper.digest != front.digest
    assert crazy_cog_act(crazy_cog, 16, 4) == deeper.open_receipt
    front_again = publish(crazy_cog, 5, publish_abi=crazy_cog_publish)
    assert front_again.open_receipt != deeper.open_receipt
finally:
    crazy_cog_destroy(crazy_cog)
print("PASS: native Crazy Cog seventeen-port agent, plane changes, receipts, and raster publication")

cipher_abyss_create = lib.nw_cipher_abyss_agent_create
cipher_abyss_create.argtypes, cipher_abyss_create.restype = rover_create.argtypes, rover_create.restype
cipher_abyss_act = lib.nw_cipher_abyss_agent_act
cipher_abyss_act.argtypes, cipher_abyss_act.restype = agent_act.argtypes, agent_act.restype
cipher_abyss_destroy = lib.nw_cipher_abyss_agent_destroy
cipher_abyss_destroy.argtypes, cipher_abyss_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
cipher_abyss_publish = lib.nw_cipher_abyss_agent_publish
cipher_abyss_publish.argtypes, cipher_abyss_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not cipher_abyss_create(1, 1, 0, 17, 36, False)
cipher_abyss = cipher_abyss_create(1, 1, 0, 17, 37, False)
assert cipher_abyss
try:
    first = publish(cipher_abyss, 1, publish_abi=cipher_abyss_publish)
    assert first.open_receipt and not first.done
    assert cipher_abyss_act(cipher_abyss, 37, 2) == 0
    frame = first
    # Start the test, then enter the two Python reference answers.
    for timestamp, port in enumerate((24, 14, 14, 15, 23, 14, 14, 14, 23), start=1):
        assert cipher_abyss_act(cipher_abyss, port, 2 * timestamp) == frame.open_receipt
        frame = publish(cipher_abyss, 2 * timestamp + 1, publish_abi=cipher_abyss_publish)
    assert frame.outcome_receipt and frame.outcome_scalar == 1
    assert frame.digest != first.digest
    assert publish(cipher_abyss, 20, publish_abi=cipher_abyss_publish).done
finally:
    cipher_abyss_destroy(cipher_abyss)
print("PASS: native Cipher Abyss 37-port agent, seeded win, receipts, and raster publication")

potter_create = lib.nw_potters_wheel_agent_create
potter_create.argtypes, potter_create.restype = rover_create.argtypes, rover_create.restype
potter_act = lib.nw_potters_wheel_agent_act
potter_act.argtypes, potter_act.restype = agent_act.argtypes, agent_act.restype
potter_destroy = lib.nw_potters_wheel_agent_destroy
potter_destroy.argtypes, potter_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
potter_publish = lib.nw_potters_wheel_agent_publish
potter_publish.argtypes, potter_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not potter_create(4, 1, 0, 17, 16, False)
potter_agent = potter_create(4, 1, 0, 17, 17, False)
assert potter_agent
try:
    reset = publish(potter_agent, 1, publish_abi=potter_publish)
    assert reset.open_receipt and not reset.done
    assert potter_act(potter_agent, 17, 2) == 0
    assert potter_act(potter_agent, 14, 2) == reset.open_receipt
    speed = publish(potter_agent, 3, publish_abi=potter_publish)
    assert speed.digest != reset.digest
    assert potter_act(potter_agent, 12, 4) == speed.open_receipt
    for timestamp in range(5, 25):
        frame = publish(potter_agent, timestamp, dt=0.1, publish_abi=potter_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert frame.digest != speed.digest
            assert publish(potter_agent, timestamp + 1, publish_abi=potter_publish).done
            break
    else:
        raise AssertionError("Holding the pointer against the clay's axis did not collapse the pot")
finally:
    potter_destroy(potter_agent)
print("PASS: native Potter's Wheel 17-port agent, collapse verdict, receipts, and raster publication")

conductor_create = lib.nw_conductor_agent_create
conductor_create.argtypes, conductor_create.restype = rover_create.argtypes, rover_create.restype
conductor_act = lib.nw_conductor_agent_act
conductor_act.argtypes, conductor_act.restype = agent_act.argtypes, agent_act.restype
conductor_destroy = lib.nw_conductor_agent_destroy
conductor_destroy.argtypes, conductor_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
conductor_publish = lib.nw_conductor_agent_publish
conductor_publish.argtypes, conductor_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not conductor_create(1, 1, 0, 17, 15, False)
conductor_agent = conductor_create(1, 1, 0, 17, 16, False)
assert conductor_agent
try:
    frame = publish(conductor_agent, 1, publish_abi=conductor_publish)
    assert frame.open_receipt and not frame.done
    assert conductor_act(conductor_agent, 16, 2) == 0
    for timestamp in range(2, 10, 2):
        assert conductor_act(conductor_agent, 14, timestamp) == frame.open_receipt
        frame = publish(conductor_agent, timestamp + 1, publish_abi=conductor_publish)
    assert frame.outcome_scalar == -1 and frame.outcome_receipt
    assert publish(conductor_agent, 10, publish_abi=conductor_publish).done
finally:
    conductor_destroy(conductor_agent)
print("PASS: native Conductor 16-port agent, slip verdict, receipts, and raster publication")

tightrope_create = lib.nw_tightrope_agent_create
tightrope_create.argtypes, tightrope_create.restype = rover_create.argtypes, rover_create.restype
tightrope_act = lib.nw_tightrope_agent_act
tightrope_act.argtypes, tightrope_act.restype = agent_act.argtypes, agent_act.restype
tightrope_destroy = lib.nw_tightrope_agent_destroy
tightrope_destroy.argtypes, tightrope_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
tightrope_publish = lib.nw_tightrope_agent_publish
tightrope_publish.argtypes, tightrope_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not tightrope_create(1, 1, 0, 17, 14, False)
tightrope_agent = tightrope_create(1, 1, 0, 17, 15, False)
assert tightrope_agent
try:
    ready = publish(tightrope_agent, 1, publish_abi=tightrope_publish)
    assert ready.open_receipt and not ready.done
    assert tightrope_act(tightrope_agent, 15, 2) == 0
    assert tightrope_act(tightrope_agent, 14, 2) == ready.open_receipt
    moving = publish(tightrope_agent, 3, publish_abi=tightrope_publish)
    assert moving.digest != ready.digest
    assert tightrope_act(tightrope_agent, 9, 4) == moving.open_receipt
    for timestamp in range(5, 45):
        frame = publish(tightrope_agent, timestamp, dt=0.1, publish_abi=tightrope_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1 and frame.digest != moving.digest
            assert publish(tightrope_agent, timestamp + 1, publish_abi=tightrope_publish).done
            break
    else:
        raise AssertionError("The unbalanced walker did not fall")
finally:
    tightrope_destroy(tightrope_agent)
print("PASS: native Tightrope 15-port agent, falling verdict, receipts, and raster publication")


signpainter_create = lib.nw_sign_painter_agent_create
signpainter_create.argtypes, signpainter_create.restype = rover_create.argtypes, rover_create.restype
signpainter_act = lib.nw_sign_painter_agent_act
signpainter_act.argtypes, signpainter_act.restype = agent_act.argtypes, agent_act.restype
signpainter_destroy = lib.nw_sign_painter_agent_destroy
signpainter_destroy.argtypes, signpainter_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
signpainter_publish = lib.nw_sign_painter_agent_publish
signpainter_publish.argtypes, signpainter_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not signpainter_create(4, 1, 0, 17, 18, False)
signpainter_agent = signpainter_create(4, 1, 0, 17, 19, False)
assert signpainter_agent
try:
    ready = publish(signpainter_agent, 1, publish_abi=signpainter_publish)
    assert ready.open_receipt and not ready.done
    assert signpainter_act(signpainter_agent, 19, 2) == 0
    assert signpainter_act(signpainter_agent, 14, 2) == ready.open_receipt
    painted = publish(signpainter_agent, 3, publish_abi=signpainter_publish)
    assert painted.digest != ready.digest
    for timestamp, port in enumerate((12, 13, 12, 13, 12), start=2):
        stamp = 2 * timestamp
        assert signpainter_act(signpainter_agent, port, stamp) == painted.open_receipt
        painted = publish(signpainter_agent, stamp + 1, publish_abi=signpainter_publish)
    assert painted.outcome_scalar == -1 and painted.outcome_receipt
    assert publish(signpainter_agent, 14, publish_abi=signpainter_publish).done
finally:
    signpainter_destroy(signpainter_agent)
print("PASS: native Sign Painter 19-port agent, wrong-colour verdict, receipts, and raster publication")


bartender_create = lib.nw_bartender_agent_create
bartender_create.argtypes, bartender_create.restype = rover_create.argtypes, rover_create.restype
bartender_act = lib.nw_bartender_agent_act
bartender_act.argtypes, bartender_act.restype = agent_act.argtypes, agent_act.restype
bartender_destroy = lib.nw_bartender_agent_destroy
bartender_destroy.argtypes, bartender_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
bartender_publish = lib.nw_bartender_agent_publish
bartender_publish.argtypes, bartender_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not bartender_create(1, 1, 0, 17, 14, False)
bartender_agent = bartender_create(1, 1, 0, 17, 15, False)
assert bartender_agent
try:
    ready = publish(bartender_agent, 1, publish_abi=bartender_publish)
    assert ready.open_receipt and not ready.done
    assert bartender_act(bartender_agent, 15, 2) == 0
    assert bartender_act(bartender_agent, 14, 2) == ready.open_receipt
    iced = publish(bartender_agent, 3, publish_abi=bartender_publish)
    assert iced.digest != ready.digest
    assert bartender_act(bartender_agent, 14, 4) == iced.open_receipt
    assert publish(bartender_agent, 5, publish_abi=bartender_publish).digest == ready.digest
finally:
    bartender_destroy(bartender_agent)
print("PASS: native Bartender 15-port agent, ice toggle, receipts, and raster publication")


lockpick_create = lib.nw_lock_pick_agent_create
lockpick_create.argtypes, lockpick_create.restype = rover_create.argtypes, rover_create.restype
lockpick_act = lib.nw_lock_pick_agent_act
lockpick_act.argtypes, lockpick_act.restype = agent_act.argtypes, agent_act.restype
lockpick_destroy = lib.nw_lock_pick_agent_destroy
lockpick_destroy.argtypes, lockpick_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
lockpick_publish = lib.nw_lock_pick_agent_publish
lockpick_publish.argtypes, lockpick_publish.restype = agent_publish.argtypes, agent_publish.restype

assert not lockpick_create(1, 1, 0, 17, 14, False)
lockpick_agent = lockpick_create(1, 1, 0, 17, 15, False)
assert lockpick_agent
try:
    frame = publish(lockpick_agent, 1, publish_abi=lockpick_publish)
    assert frame.open_receipt and not frame.done
    assert lockpick_act(lockpick_agent, 15, 2) == 0
    for timestamp in range(2, 100, 2):
        assert lockpick_act(lockpick_agent, 14, timestamp) == frame.open_receipt
        frame = publish(lockpick_agent, timestamp + 1, dt=0.1, publish_abi=lockpick_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(lockpick_agent, timestamp + 2, publish_abi=lockpick_publish).done
            break
    else:
        raise AssertionError("Continuous tension did not produce the slipped-wrench verdict")
finally:
    lockpick_destroy(lockpick_agent)
print("PASS: native Lock Pick 15-port agent, latched tension, slip verdict, receipts, and raster publication")


airhockey_create = lib.nw_air_hockey_agent_create
airhockey_create.argtypes, airhockey_create.restype = rover_create.argtypes, rover_create.restype
airhockey_act = lib.nw_air_hockey_agent_act
airhockey_act.argtypes, airhockey_act.restype = agent_act.argtypes, agent_act.restype
airhockey_destroy = lib.nw_air_hockey_agent_destroy
airhockey_destroy.argtypes, airhockey_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
airhockey_publish = lib.nw_air_hockey_agent_publish
airhockey_publish.argtypes, airhockey_publish.restype = agent_publish.argtypes, agent_publish.restype

# Sixteen ports: the hand's fourteen, then the bar's Left (14) and Right (15).
assert not airhockey_create(1, 1, 0, 17, 15, False)
airhockey_agent = airhockey_create(1, 1, 0, 17, 16, False)
assert airhockey_agent
try:
    frame = publish(airhockey_agent, 1, publish_abi=airhockey_publish)
    assert frame.open_receipt and not frame.done
    assert airhockey_act(airhockey_agent, 16, 2) == 0
    # Nobody moves the mallet; the bar is nudged left and right in turn. The
    # game must still reach a verdict, and it is not a win.
    for timestamp in range(2, 4000, 2):
        port = 14 if timestamp % 8 < 4 else 15
        assert airhockey_act(airhockey_agent, port, timestamp) == frame.open_receipt
        frame = publish(airhockey_agent, timestamp + 1, dt=0.1, publish_abi=airhockey_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(airhockey_agent, timestamp + 2, publish_abi=airhockey_publish).done
            break
    else:
        raise AssertionError("An unattended Air Hockey game never reached a verdict")
finally:
    airhockey_destroy(airhockey_agent)
print("PASS: native Air Hockey 16-port agent, latched bar, unattended-game verdict, receipts, and raster publication")


semaphore_create = lib.nw_semaphore_agent_create
semaphore_create.argtypes, semaphore_create.restype = rover_create.argtypes, rover_create.restype
semaphore_act = lib.nw_semaphore_agent_act
semaphore_act.argtypes, semaphore_act.restype = agent_act.argtypes, agent_act.restype
semaphore_destroy = lib.nw_semaphore_agent_destroy
semaphore_destroy.argtypes, semaphore_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
semaphore_publish = lib.nw_semaphore_agent_publish
semaphore_publish.argtypes, semaphore_publish.restype = agent_publish.argtypes, agent_publish.restype

# Forty ports: the hand's fourteen, then the letters A (14) to Z (39).
assert not semaphore_create(1, 1, 0, 17, 39, False)
semaphore_agent = semaphore_create(1, 1, 0, 17, 40, False)
assert semaphore_agent
try:
    frame = publish(semaphore_agent, 1, publish_abi=semaphore_publish)
    assert frame.open_receipt and not frame.done
    assert semaphore_act(semaphore_agent, 40, 2) == 0
    # The flags never move; Q is typed at every step. Each signal is struck
    # as a mismatch, and the message must fail.
    for timestamp in range(2, 4000, 2):
        assert semaphore_act(semaphore_agent, 14 + 16, timestamp) == frame.open_receipt
        frame = publish(semaphore_agent, timestamp + 1, dt=0.1, publish_abi=semaphore_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(semaphore_agent, timestamp + 2, publish_abi=semaphore_publish).done
            break
    else:
        raise AssertionError("A struck Semaphore message never reached a verdict")
finally:
    semaphore_destroy(semaphore_agent)
print("PASS: native Semaphore 40-port agent, typed letters, mismatch verdict, receipts, and raster publication")


puppets_create = lib.nw_shadow_puppets_agent_create
puppets_create.argtypes, puppets_create.restype = rover_create.argtypes, rover_create.restype
puppets_act = lib.nw_shadow_puppets_agent_act
puppets_act.argtypes, puppets_act.restype = agent_act.argtypes, agent_act.restype
puppets_destroy = lib.nw_shadow_puppets_agent_destroy
puppets_destroy.argtypes, puppets_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
puppets_publish = lib.nw_shadow_puppets_agent_publish
puppets_publish.argtypes, puppets_publish.restype = agent_publish.argtypes, agent_publish.restype

# Sixteen ports: the hand's fourteen, then roll left (14) and right (15).
assert not puppets_create(1, 1, 0, 17, 15, False)
puppets_agent = puppets_create(1, 1, 0, 17, 16, False)
assert puppets_agent
try:
    frame = publish(puppets_agent, 1, publish_abi=puppets_publish)
    assert frame.open_receipt and not frame.done
    assert puppets_act(puppets_agent, 16, 2) == 0
    # Nobody drags the figure; it is rolled a little each way in turn. The
    # time must still run out to a verdict, and it is not a pass.
    for timestamp in range(2, 4000, 2):
        port = 14 if timestamp % 8 < 4 else 15
        assert puppets_act(puppets_agent, port, timestamp) == frame.open_receipt
        frame = publish(puppets_agent, timestamp + 1, dt=0.1, publish_abi=puppets_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(puppets_agent, timestamp + 2, publish_abi=puppets_publish).done
            break
    else:
        raise AssertionError("An unturned Shadow Puppets figure never reached a verdict")
finally:
    puppets_destroy(puppets_agent)
print("PASS: native Shadow Puppets 16-port agent, roll ports, timed-out verdict, receipts, and raster publication")


watch_create = lib.nw_night_watch_agent_create
watch_create.argtypes, watch_create.restype = rover_create.argtypes, rover_create.restype
watch_act = lib.nw_night_watch_agent_act
watch_act.argtypes, watch_act.restype = agent_act.argtypes, agent_act.restype
watch_destroy = lib.nw_night_watch_agent_destroy
watch_destroy.argtypes, watch_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
watch_publish = lib.nw_night_watch_agent_publish
watch_publish.argtypes, watch_publish.restype = agent_publish.argtypes, agent_publish.restype

# Sixteen ports: the hand's fourteen, then turn left (14) and right (15).
assert not watch_create(1, 1, 0, 17, 15, False)
watch_agent = watch_create(1, 1, 0, 17, 16, False)
assert watch_agent
try:
    frame = publish(watch_agent, 1, publish_abi=watch_publish)
    assert frame.open_receipt and not frame.done
    assert watch_act(watch_agent, 16, 2) == 0
    # Nobody catches anyone; the view is turned a little each way in turn.
    # A thief reaches the safe, and it is not a pass.
    for timestamp in range(2, 4000, 2):
        port = 14 if timestamp % 8 < 4 else 15
        assert watch_act(watch_agent, port, timestamp) == frame.open_receipt
        frame = publish(watch_agent, timestamp + 1, dt=0.1, publish_abi=watch_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(watch_agent, timestamp + 2, publish_abi=watch_publish).done
            break
    else:
        raise AssertionError("An unwatched Night Watch never reached a verdict")
finally:
    watch_destroy(watch_agent)
print("PASS: native Night Watch 16-port agent, turning ports, robbed verdict, receipts, and raster publication")


kerb_create = lib.nw_kerbside_agent_create
kerb_create.argtypes, kerb_create.restype = rover_create.argtypes, rover_create.restype
kerb_act = lib.nw_kerbside_agent_act
kerb_act.argtypes, kerb_act.restype = agent_act.argtypes, agent_act.restype
kerb_destroy = lib.nw_kerbside_agent_destroy
kerb_destroy.argtypes, kerb_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
kerb_publish = lib.nw_kerbside_agent_publish
kerb_publish.argtypes, kerb_publish.restype = agent_publish.argtypes, agent_publish.restype

# Two ports: walk (0) and step back (1).
assert not kerb_create(1, 1, 0, 17, 1, False)
kerb_agent = kerb_create(1, 1, 0, 17, 2, False)
assert kerb_agent
try:
    frame = publish(kerb_agent, 1, publish_abi=kerb_publish)
    assert frame.open_receipt and not frame.done
    assert kerb_act(kerb_agent, 2, 2) == 0
    # A walker who does not listen walks out at once and is struck.
    for timestamp in range(2, 4000, 2):
        assert kerb_act(kerb_agent, 0, timestamp) == frame.open_receipt
        frame = publish(kerb_agent, timestamp + 1, dt=0.1, publish_abi=kerb_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(kerb_agent, timestamp + 2, publish_abi=kerb_publish).done
            break
    else:
        raise AssertionError("A Kerbside walker never reached a verdict")
finally:
    kerb_destroy(kerb_agent)
print("PASS: native Kerbside 2-port agent, walking port, struck verdict, receipts, and raster publication")


steady_create = lib.nw_steadicam_agent_create
steady_create.argtypes, steady_create.restype = rover_create.argtypes, rover_create.restype
steady_act = lib.nw_steadicam_agent_act
steady_act.argtypes, steady_act.restype = agent_act.argtypes, agent_act.restype
steady_destroy = lib.nw_steadicam_agent_destroy
steady_destroy.argtypes, steady_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
steady_publish = lib.nw_steadicam_agent_publish
steady_publish.argtypes, steady_publish.restype = agent_publish.argtypes, agent_publish.restype

# Six ports: pan left and right, tilt up and down, zoom in and out.
assert not steady_create(1, 1, 0, 17, 5, False)
steady_agent = steady_create(1, 1, 0, 17, 6, False)
assert steady_agent
try:
    frame = publish(steady_agent, 1, publish_abi=steady_publish)
    assert frame.open_receipt and not frame.done
    assert steady_act(steady_agent, 6, 2) == 0
    # A camera that only pans right loses the walker.
    for timestamp in range(2, 4000, 2):
        assert steady_act(steady_agent, 1, timestamp) == frame.open_receipt
        frame = publish(steady_agent, timestamp + 1, dt=0.1, publish_abi=steady_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(steady_agent, timestamp + 2, publish_abi=steady_publish).done
            break
    else:
        raise AssertionError("A Steadicam take never reached a verdict")
finally:
    steady_destroy(steady_agent)
print("PASS: native Steadicam 6-port agent, panning port, lost verdict, receipts, and raster publication")


kick_create = lib.nw_free_kick_agent_create
kick_create.argtypes, kick_create.restype = rover_create.argtypes, rover_create.restype
kick_act = lib.nw_free_kick_agent_act
kick_act.argtypes, kick_act.restype = agent_act.argtypes, agent_act.restype
kick_destroy = lib.nw_free_kick_agent_destroy
kick_destroy.argtypes, kick_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
kick_publish = lib.nw_free_kick_agent_publish
kick_publish.argtypes, kick_publish.restype = agent_publish.argtypes, agent_publish.restype

# Nine ports: eight dials and the kick.
assert not kick_create(1, 1, 0, 17, 8, False)
kick_agent = kick_create(1, 1, 0, 17, 9, False)
assert kick_agent
try:
    frame = publish(kick_agent, 1, publish_abi=kick_publish)
    assert frame.open_receipt and not frame.done
    assert kick_act(kick_agent, 9, 2) == 0
    # The first kick as set, struck at once, lands off the ring.
    assert kick_act(kick_agent, 8, 2) == frame.open_receipt
    for timestamp in range(3, 4000, 2):
        frame = publish(kick_agent, timestamp, dt=0.1, publish_abi=kick_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(kick_agent, timestamp + 1, publish_abi=kick_publish).done
            break
    else:
        raise AssertionError("A Free Kick never reached a verdict")
finally:
    kick_destroy(kick_agent)
print("PASS: native Free Kick 9-port agent, kicking port, missed verdict, receipts, and raster publication")


glove_create = lib.nw_glove_agent_create
glove_create.argtypes, glove_create.restype = rover_create.argtypes, rover_create.restype
glove_act = lib.nw_glove_agent_act
glove_act.argtypes, glove_act.restype = agent_act.argtypes, agent_act.restype
glove_destroy = lib.nw_glove_agent_destroy
glove_destroy.argtypes, glove_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
glove_publish = lib.nw_glove_agent_publish
glove_publish.argtypes, glove_publish.restype = agent_publish.argtypes, agent_publish.restype

# Four ports: up, down, left and right.
assert not glove_create(1, 1, 0, 17, 3, False)
glove_agent = glove_create(1, 1, 0, 17, 4, False)
assert glove_agent
try:
    frame = publish(glove_agent, 1, publish_abi=glove_publish)
    assert frame.open_receipt and not frame.done
    assert glove_act(glove_agent, 4, 2) == 0
    assert glove_act(glove_agent, 0, 2) == frame.open_receipt
    # Nobody at the glove after that: the pitches go by.
    for timestamp in range(3, 4000, 2):
        frame = publish(glove_agent, timestamp, dt=0.1, publish_abi=glove_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(glove_agent, timestamp + 1, publish_abi=glove_publish).done
            break
    else:
        raise AssertionError("A Glove inning never reached a verdict")
finally:
    glove_destroy(glove_agent)
print("PASS: native Glove 4-port agent, the up port, missed verdict, receipts, and raster publication")


ear_create = lib.nw_by_ear_agent_create
ear_create.argtypes, ear_create.restype = rover_create.argtypes, rover_create.restype
ear_act = lib.nw_by_ear_agent_act
ear_act.argtypes, ear_act.restype = agent_act.argtypes, agent_act.restype
ear_destroy = lib.nw_by_ear_agent_destroy
ear_destroy.argtypes, ear_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
ear_publish = lib.nw_by_ear_agent_publish
ear_publish.argtypes, ear_publish.restype = agent_publish.argtypes, agent_publish.restype

# Thirteen ports, the keys from C to C.
assert not ear_create(1, 1, 0, 17, 12, False)
ear_agent = ear_create(1, 1, 0, 17, 13, False)
assert ear_agent
try:
    frame = publish(ear_agent, 1, publish_abi=ear_publish)
    assert frame.open_receipt and not frame.done
    assert ear_act(ear_agent, 13, 2) == 0
    # A key while the tune plays, which it ignores; then nobody plays it back.
    assert ear_act(ear_agent, 7, 2) == frame.open_receipt
    for timestamp in range(3, 4000, 2):
        frame = publish(ear_agent, timestamp, dt=0.1, publish_abi=ear_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(ear_agent, timestamp + 1, publish_abi=ear_publish).done
            break
    else:
        raise AssertionError("A By Ear try never reached a verdict")
finally:
    ear_destroy(ear_agent)
print("PASS: native By Ear 13-port agent, a key port, too-slow verdict, receipts, and raster publication")


tune_create = lib.nw_piano_tuner_agent_create
tune_create.argtypes, tune_create.restype = rover_create.argtypes, rover_create.restype
tune_act = lib.nw_piano_tuner_agent_act
tune_act.argtypes, tune_act.restype = agent_act.argtypes, agent_act.restype
tune_destroy = lib.nw_piano_tuner_agent_destroy
tune_destroy.argtypes, tune_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
tune_publish = lib.nw_piano_tuner_agent_publish
tune_publish.argtypes, tune_publish.restype = agent_publish.argtypes, agent_publish.restype

# Five ports: up and down, quickly and slowly, and done.
assert not tune_create(1, 1, 0, 17, 4, False)
tune_agent = tune_create(1, 1, 0, 17, 5, False)
assert tune_agent
try:
    frame = publish(tune_agent, 1, publish_abi=tune_publish)
    assert frame.open_receipt and not frame.done
    assert tune_act(tune_agent, 5, 2) == 0
    assert tune_act(tune_agent, 0, 2) == frame.open_receipt
    # Done at once, far out of tune: judged sharp.
    frame = publish(tune_agent, 3, publish_abi=tune_publish)
    assert frame.open_receipt and not frame.done
    assert tune_act(tune_agent, 4, 4) == frame.open_receipt
    for timestamp in range(5, 400, 2):
        frame = publish(tune_agent, timestamp, dt=0.1, publish_abi=tune_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(tune_agent, timestamp + 1, publish_abi=tune_publish).done
            break
    else:
        raise AssertionError("A Piano Tuner try never reached a verdict")
finally:
    tune_destroy(tune_agent)
print("PASS: native Piano Tuner 5-port agent, the up and done ports, sharp verdict, receipts, and raster publication")


cricket_create = lib.nw_cricket_hunt_agent_create
cricket_create.argtypes, cricket_create.restype = rover_create.argtypes, rover_create.restype
cricket_act = lib.nw_cricket_hunt_agent_act
cricket_act.argtypes, cricket_act.restype = agent_act.argtypes, agent_act.restype
cricket_destroy = lib.nw_cricket_hunt_agent_destroy
cricket_destroy.argtypes, cricket_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
cricket_publish = lib.nw_cricket_hunt_agent_publish
cricket_publish.argtypes, cricket_publish.restype = agent_publish.argtypes, agent_publish.restype

# Seven ports: walk, turn and look, and grab.
assert not cricket_create(1, 1, 0, 17, 6, False)
cricket_agent = cricket_create(1, 1, 0, 17, 7, False)
assert cricket_agent
try:
    frame = publish(cricket_agent, 1, publish_abi=cricket_publish)
    assert frame.open_receipt and not frame.done
    assert cricket_act(cricket_agent, 7, 2) == 0
    assert cricket_act(cricket_agent, 0, 2) == frame.open_receipt
    # Three grabs at nothing, a frame apart.
    for timestamp in (4, 6, 8):
        frame = publish(cricket_agent, timestamp - 1, publish_abi=cricket_publish)
        assert frame.open_receipt and not frame.done
        assert cricket_act(cricket_agent, 6, timestamp) == frame.open_receipt
    for timestamp in range(9, 400, 2):
        frame = publish(cricket_agent, timestamp, dt=0.1, publish_abi=cricket_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(cricket_agent, timestamp + 1, publish_abi=cricket_publish).done
            break
    else:
        raise AssertionError("A Cricket Hunt try never reached a verdict")
finally:
    cricket_destroy(cricket_agent)
print("PASS: native Cricket Hunt 7-port agent, the walking and grab ports, three grabs at nothing, receipts, and raster "
      "publication")


claw_create = lib.nw_claw_machine_agent_create
claw_create.argtypes, claw_create.restype = rover_create.argtypes, rover_create.restype
claw_act = lib.nw_claw_machine_agent_act
claw_act.argtypes, claw_act.restype = agent_act.argtypes, agent_act.restype
claw_destroy = lib.nw_claw_machine_agent_destroy
claw_destroy.argtypes, claw_destroy.restype = agent_destroy.argtypes, agent_destroy.restype
claw_publish = lib.nw_claw_machine_agent_publish
claw_publish.argtypes, claw_publish.restype = agent_publish.argtypes, agent_publish.restype

# Five ports: the trolley left, right, in and out, and the drop.
assert not claw_create(1, 1, 0, 17, 4, False)
claw_agent = claw_create(1, 1, 0, 17, 5, False)
assert claw_agent
try:
    frame = publish(claw_agent, 1, publish_abi=claw_publish)
    assert frame.open_receipt and not frame.done
    assert claw_act(claw_agent, 5, 2) == 0
    assert claw_act(claw_agent, 0, 2) == frame.open_receipt
    # Dropped where it stands: a miss.
    frame = publish(claw_agent, 3, publish_abi=claw_publish)
    assert frame.open_receipt and not frame.done
    assert claw_act(claw_agent, 4, 4) == frame.open_receipt
    for timestamp in range(5, 400, 2):
        frame = publish(claw_agent, timestamp, dt=0.1, publish_abi=claw_publish)
        if frame.outcome_receipt:
            assert frame.outcome_scalar == -1
            assert publish(claw_agent, timestamp + 1, publish_abi=claw_publish).done
            break
    else:
        raise AssertionError("A Claw Machine try never reached a verdict")
finally:
    claw_destroy(claw_agent)
print("PASS: native Claw Machine 5-port agent, the trolley and drop ports, a missed verdict, receipts, and raster "
      "publication")
