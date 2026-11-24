#!/usr/bin/env python3
"""Replay hidden Python OpenGL and native SDL spatial task frames.

Run with the original application's Python environment and the built
libnw-agent path. Pass which_is_nearer, same_or_mirror, point_of_view, inside_or_out, touching, crossings, time_it, balance, juggler, lander, keep_the_beat, glider, catch, echo_cave, drone_hoops, field_manual, safecracker, stagehand, loading_dock, or gunslinger to replay another spatial task.
NumPy is used only by this differential.
"""
import ctypes
import os
from pathlib import Path
import struct
import sys
import tempfile
from unittest.mock import patch

import numpy as np


WIDTH, HEIGHT = 912, 684
HEADER_BYTES = 36
STEP = 1 / 60


class Publication(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int64) for name in (
        "frame_seq", "timestamp_ns", "done", "open_receipt", "outcome_receipt"
    )] + [("outcome_scalar", ctypes.c_double)] + [(name, ctypes.c_int64) for name in (
        "action_port", "receipt_frame_seq", "receipt_timestamp_ns", "trial"
    )] + [("digest", ctypes.c_char * 64), ("stimulus_digest", ctypes.c_char * 64)]


def dilate(mask, radius):
    padded = np.pad(mask, radius)
    height, width = mask.shape
    near = np.zeros_like(mask)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            near |= padded[dy:dy + height, dx:dx + width]
    return near


def compare(source, packet, board, label, interior_limit=0.005, floor_grid=False, paper_outline=False,
            crossings_grid=False, striped_tent=False, frame_limit=0.055):
    assert (source["width"], source["height"]) == (WIDTH, HEIGHT)
    shape = (HEIGHT, WIDTH, 4)
    reference = np.frombuffer(source["rgba"], np.uint8).reshape(shape)[:, :, :3]
    native = np.frombuffer(packet, np.uint8, offset=HEADER_BYTES).reshape(shape)[:, :, :3]
    delta = np.abs(reference.astype(np.int16) - native.astype(np.int16))
    different = delta.max(axis=2) > 12

    # Check the whole frame and weight the playing area separately so the
    # background cannot hide a moved or missing object. Ignore the button
    # label in the interior comparison because the two hosts use different fonts.
    assert different.mean() < frame_limit, (label, "frame", different.mean())
    if board is not None:
        colour_area = reference[board]
        board_difference = different[board]
        interior = np.ones(colour_area.shape[:2], dtype=bool)
        for dy, dx in ((0, 2), (0, -2), (2, 0), (-2, 0), (2, 2), (2, -2), (-2, 2), (-2, -2)):
            interior &= np.all(colour_area == np.roll(colour_area, (dy, dx), (0, 1)), axis=2)
        if floor_grid or crossings_grid:
            # The perspective grid has subpixel lines. Require both
            # rasterizers' grid pixels to land near the other grid, then
            # compare the remaining board at the usual interior tolerance.
            if crossings_grid:
                grid = (223, 232, 241)
                source_grid = np.all(colour_area == grid, axis=2)
                native_grid = np.all(np.abs(native[board].astype(np.int16) - grid) <= 1, axis=2)
                for colour in ((226, 58, 70), (40, 110, 230), (40, 168, 90), (250, 180, 30)):
                    source_line = np.all(colour_area == colour, axis=2)
                    native_line = np.all(native[board] == colour, axis=2)
                    assert source_line.any() == native_line.any(), (label, colour)
                    if source_line.any():
                        assert dilate(source_line, 2)[native_line].mean() > 0.98, (label, colour)
                        assert dilate(native_line, 2)[source_line].mean() > 0.98, (label, colour)
                        assert 0.85 < native_line.sum() / source_line.sum() < 1.15, (label, colour)
            else:
                source_grid = np.all(colour_area == (150, 144, 132), axis=2)
                native_grid = np.all(native[board] == (150, 144, 132), axis=2)
            source_near = dilate(source_grid, 3)
            native_near = dilate(native_grid, 3)
            assert source_grid.any() and native_grid.any(), label
            assert source_near[native_grid].mean() > 0.88, label
            assert native_near[source_grid].mean() > 0.88, label
            away_from_grid = ~(source_near | native_near)
            assert board_difference[away_from_grid].mean() < 0.04, label
            interior &= away_from_grid
        elif paper_outline:
            # Thin maze strokes expose rasterizer rounding. Check both ink
            # masks geometrically, then check paper and verdict wash separately.
            source_ink = np.all(colour_area == (40, 46, 70), axis=2)
            native_ink = np.all(native[board] == (40, 46, 70), axis=2)
            assert source_ink.any() and native_ink.any(), label
            source_near = dilate(source_ink, 2)
            native_near = dilate(native_ink, 2)
            assert source_near[native_ink].mean() > 0.995, label
            assert native_near[source_ink].mean() > 0.995, label
            assert 0.85 < native_ink.sum() / source_ink.sum() < 1.15, label
            for colour in ((236, 72, 80), (60, 140, 240)):
                source_dot = np.all(colour_area == colour, axis=2)
                native_dot = np.all(native[board] == colour, axis=2)
                assert source_dot.any() == native_dot.any(), (label, colour)
                if source_dot.any():
                    assert dilate(source_dot, 2)[native_dot].mean() > 0.95, (label, colour)
                    assert dilate(native_dot, 2)[source_dot].mean() > 0.95, (label, colour)
            away = ~(source_near | native_near)
            assert board_difference[away].mean() < 0.025, label
            interior &= away
        elif striped_tent:
            # The tent's closely spaced stripes create many high-contrast
            # edges. Compare the interior and require the tray, cart, and
            # roof scallops to align within two pixels in both directions.
            for colour in ((250, 206, 70), (60, 80, 170), (250, 200, 60)):
                source_shape = np.all(colour_area == colour, axis=2)
                native_shape = np.all(native[board] == colour, axis=2)
                assert source_shape.any() and native_shape.any(), (label, colour)
                assert dilate(source_shape, 2)[native_shape].mean() > 0.98, (label, colour)
                assert dilate(native_shape, 2)[source_shape].mean() > 0.98, (label, colour)
                assert 0.65 < native_shape.sum() / source_shape.sum() < 1.35, (label, colour)
        else:
            assert board_difference.mean() < 0.04, (label, "board", board_difference.mean())
        assert board_difference[interior].mean() < interior_limit, (label, "interior", board_difference[interior].mean())
    return float(np.mean(np.all(delta == 0, axis=2)))


def rooms_actions(puzzle, correct, expected):
    assert puzzle.change == expected
    answer = puzzle.answer[0] if correct else next(
        cell for cell in range(puzzle.cols * puzzle.rows) if cell not in puzzle.answer)
    return [30] * len(puzzle.rooms) + [answer]


def nearer_actions(puzzle, correct, expected):
    assert puzzle.cue == expected
    if not correct:
        picks = [puzzle.order[1]]
    else:
        picks = list(puzzle.order if puzzle.ask_order else puzzle.order[:1])
    return [None] * 36 + picks if puzzle.cue == "motion" else picks


def mirror_actions(puzzle, correct, expected):
    assert (len(puzzle.others), puzzle.lit) == expected
    choices = len(puzzle.choices)
    chosen = puzzle.answer if correct else (puzzle.answer + 1) % choices
    return [chosen]


def pov_actions(puzzle, correct, expected):
    count, mirrored, monochrome = expected
    assert len(puzzle.views) == count
    assert any(view[2] for view in puzzle.views) == mirrored
    assert (len({solid.colour for solid in puzzle.solids}) == 1) == monochrome
    return [puzzle.answer if correct else (puzzle.answer + 1) % count]


def inside_actions(puzzle, correct, expected):
    assert (puzzle.level.kind, puzzle.level.pair, len(puzzle.decoys)) == expected
    return [puzzle.answer if correct else 1 - puzzle.answer]


def touching_actions(puzzle, correct, expected):
    assert (any(s.kind == "square" for s in puzzle.shapes), len(puzzle.shapes), puzzle.level.thick) == expected
    return [puzzle.answer if correct else (puzzle.answer + 1) % len(puzzle.choices)]


def crossings_actions(puzzle, correct, expected):
    assert (puzzle.level.smooth, len(puzzle.decoys), len(puzzle.crossings)) == expected
    return [puzzle.answer if correct else (puzzle.answer + 1) % len(puzzle.choices)]


def replay(agent, env_class, rung, seed, black, correct, expected, task):
    env = env_class(seed=seed, rung=rung, trials=1, visible=False)
    rooms = task == "where_was_it"
    nearer = task == "which_is_nearer"
    ports = {"where_was_it": 31, "inside_or_out": 2, "touching": 6, "crossings": 7}.get(task, 5)
    start_args = (6, False) if nearer else (0, 0, ports, False)
    handle = agent.create(rung, 1, 1, seed, *start_args)
    try:
        assert handle
        source = env.observe()
        puzzle = env.task.puzzle
        play = {
            "where_was_it": rooms_actions, "which_is_nearer": nearer_actions,
            "same_or_mirror": mirror_actions, "point_of_view": pov_actions,
            "inside_or_out": inside_actions, "touching": touching_actions, "crossings": crossings_actions,
        }[task]
        inputs = [None, *play(puzzle, correct, expected), None]
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        output = Publication()
        scores = []
        verdict_frame = len(inputs) - 2
        for index, action in enumerate(inputs):
            if index:
                source = env.step(action)[0]
                if action is not None:
                    assert agent.act(handle, action, index * 2)
            timestamp = index * 2 + 1
            size = agent.publish(
                handle, STEP, timestamp, packet, len(packet), WIDTH, HEIGHT, black, ctypes.byref(output))
            assert size == len(packet)
            assert struct.unpack_from("<4sIQQIII", packet) == (b"NWFB", 1, index + 1, timestamp, WIDTH, HEIGHT, 0)
            assert bool(output.done) == source["done"] == (index == len(inputs) - 1)
            if index == verdict_frame:
                assert output.outcome_receipt and output.outcome_scalar == (1 if correct else -1)
                assert source["outcome"]["scalar"] == output.outcome_scalar
            else:
                assert not output.outcome_receipt
            if index >= verdict_frame:
                colour = (64, 255, 64) if correct else (255, 64, 64)
                for rgba in (source["rgba"], memoryview(packet)[HEADER_BYTES:]):
                    band = np.frombuffer(rgba, np.uint8).reshape(HEIGHT, WIDTH, 4)[HEIGHT * 3 // 4:, :, :3]
                    assert np.count_nonzero(np.all(band == colour, axis=2)) >= 25, (rung, black, index)
            if nearer and 0 < index < 36 and action is None and index not in (9, 18, 27):
                continue  # Compare four intermediate sway positions plus picks and verdicts.
            board = None
            if not output.done:
                if rooms:
                    bottom = 454 if index < len(puzzle.rooms) else 505
                    board = np.s_[116:bottom, 28:884]
                elif nearer:
                    board = np.s_[116:443, 192:720]
                else:
                    board = np.s_[116:505, 28:884]
            scores.append(compare(source, packet, board, (rung, seed, black, index),
                                  interior_limit=0.005 if rooms else 0.015,
                                  floor_grid=nearer and expected in ("size", "floor"),
                                  paper_outline=task == "inside_or_out",
                                  crossings_grid=task == "crossings"))
        return scores
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def timed_replay(agent, env_class, rung, seed, dark, press):
    env = env_class(seed=seed, rung=rung, trials=1, visible=False, frame_hz=40)
    handle = agent.create(rung, 1, 1, seed, 1, False)
    try:
        assert handle
        source = env.observe()
        shot = env.task.run.shot
        action_frame = int(shot.when * 40) + 1 if press == "mark" else 35 if press == "early" else None
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        pcm = ctypes.create_string_buffer(2500)
        frames = []
        verdict = False
        for index in range(200):
            action = 0 if index == action_frame else None
            if index:
                source = env.step(action)[0]
            if action is not None:
                assert agent.act(handle, action, index * 2)
            size = agent.publish(handle, 0.025 if index else 1e-12, index * 2 + 1,
                                 packet, len(packet), WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"]
            length = agent.audio(handle, pcm, len(pcm))
            if "audio_pcm" in source:
                assert length == len(source["audio_pcm"]), (rung, index, length)
                got = np.frombuffer(pcm.raw[:length], dtype="<i2").astype(np.int32)
                want = np.frombuffer(source["audio_pcm"], dtype="<i2")
                assert np.max(np.abs(got - want)) <= 1, (rung, index)
            else:
                assert length == 0, (rung, index, length)
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar == (1 if press == "mark" else -1)
                verdict = True
            if index in (0, 22, 70) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[116:505, 67:845]
                frames.append(compare(source, packet, board, (rung, seed, dark, index), interior_limit=0.025))
            if publication.done:
                assert verdict
                return frames
        raise AssertionError(("did not complete", rung, seed, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def balance_replay(agent, env_class, rung, dark, pilot_mode):
    from neural_workshop import balance

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 2, False)
    try:
        assert handle
        source = env.observe()
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        verdict = False
        saw_length_change = False
        for index in range(2600):
            action = None
            if index:
                trial = env.task.run
                if trial and trial.result is None and (pilot_mode == "pass" or (
                    pilot_mode == "change" and trial.t <= trial.course.lengths[1][0] + 0.6
                )):
                    ports = balance.autopilot(trial)
                    action = ports[0] if ports else None
                source = env.step(action)[0]
            if action is not None:
                assert agent.act(handle, action, index * 2)
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"]
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar == (1 if pilot_mode == "pass" else -1)
                verdict = True
            near_change = False
            if pilot_mode == "change" and not saw_length_change and env.task.run:
                when = env.task.run.course.lengths[1][0]
                if env.task.run.t >= when:
                    near_change = saw_length_change = True
            if index in (0, 15, 60, 300) or near_change or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[136:505, 27:885]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.025))
            if publication.done:
                assert verdict
                assert pilot_mode != "change" or saw_length_change
                return scores
        raise AssertionError(("Balance did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def juggler_replay(agent, env_class, rung, dark):
    from neural_workshop import juggler

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 2, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        caught_at = None
        verdict = False
        for index in range(500):
            if index:
                trial = env.task.run
                if trial and trial.result is None:
                    controls = juggler.autopilot(trial) if not trial.flashes else [juggler.LEFT]
                    if controls:
                        assert agent.act(handle, controls[0], index * 2)
                    source = env.step(controls[0] if controls else None)[0]
                else:
                    source = env.step()[0]
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"]
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar == -1
                verdict = True
            if caught_at is None and env.task.run and env.task.run.flashes:
                caught_at = index
            sample = caught_at is not None and index in (caught_at, caught_at + 12)
            if index in (0, 120) or sample or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[116:505, 212:700]
                scores.append(compare(source, packet, board, (rung, 17, dark, index),
                                      interior_limit=0.003, striped_tent=True))
            if publication.done:
                assert verdict and caught_at is not None
                return scores
        raise AssertionError(("Juggler did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def lander_replay(agent, env_class, rung, dark):
    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 5, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        verdict = False
        for index in range(1400):
            if index:
                port = 0 if index <= 15 else None
                if port is not None:
                    assert agent.act(handle, port, index * 2)
                source = env.step(port)[0]
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, dark, index)
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar == -1
                verdict = True
            if index in (0, 15, 120, 300) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[130:580, 120:792]
                scores.append(compare(source, packet, board, (rung, 17, dark, index)))
            if publication.done:
                assert verdict
                return scores
        raise AssertionError(("Lander did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def beat_replay(agent, env_class, rung, dark):
    from neural_workshop import beat

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 1, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        verdict = False
        for index in range(2400):
            tapped = False
            if index:
                trial = env.task.run
                ports = beat.autopilot(trial) if trial and trial.result is None else []
                tapped = bool(ports)
                if tapped:
                    assert agent.act(handle, ports[0], index * 2)
                source = env.step(ports[0] if tapped else None)[0]
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, dark, index)
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar == 1
                verdict = True
            if index in (0, 52) or tapped or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[124:503, 30:882]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.012))
            if publication.done:
                assert verdict
                return scores
        raise AssertionError(("Keep the Beat did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def glider_replay(agent, env_class, rung, dark, pilot):
    from neural_workshop import glider

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 1, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        verdict = False
        for index in range(1700):
            if index:
                trial = env.task.run
                ports = glider.autopilot(trial) if pilot and trial and trial.result is None else []
                if ports:
                    assert agent.act(handle, ports[0], index * 2)
                source = env.step(ports[0] if ports else None)[0]
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, dark, index)
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar
                assert publication.outcome_scalar == (1 if pilot else -1)
                verdict = True
            if index in (0, 20, 78, 320, 600) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[124:495, 137:775]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.009))
            if publication.done:
                assert verdict
                return scores
        raise AssertionError(("Glider did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def catch_replay(agent, env_class, rung, dark, pilot):
    from neural_workshop import catch

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 8, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        verdict = False
        for index in range(1800):
            if index:
                trial = env.task.run
                ports = []
                if trial and trial.result is None:
                    if pilot:
                        ports = catch.autopilot(trial)
                    elif index <= 8:
                        ports = [0, 3, 5, 6]
                if ports:
                    mask = sum(1 << port for port in ports)
                    assert agent.act_mask(handle, mask, index * 2)
                # TaskEnv receipts accept a single port. Feed simultaneous input
                # through the Python controller's existing held-control path.
                if len(ports) > 1:
                    env.task.control = set(ports)
                    source = env.step()[0]
                else:
                    source = env.step(ports[0] if ports else None)[0]
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, dark, index)
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar
                assert publication.outcome_scalar == (1 if pilot else -1)
                verdict = True
            if index in (0, 30, 90, 165, 250, 440) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[124:492, 36:876]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.012))
            if publication.done:
                assert verdict
                return scores
        raise AssertionError(("Catch did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def echo_cave_replay(agent, env_class, rung, dark, pilot):
    from neural_workshop import echocave

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 9, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        verdict = False
        for index in range(1800):
            if index:
                trial = env.task.run
                ports = []
                if trial and trial.result is None:
                    if pilot:
                        ports = echocave.autopilot(trial)
                    elif index == 1:
                        ports = [5, 8]
                if ports:
                    mask = sum(1 << port for port in ports)
                    assert agent.act_mask(handle, mask, index * 2)
                # TaskEnv receipts accept a single port. Feed simultaneous input
                # through the Python controller's existing held-control path.
                if len(ports) > 1:
                    if echocave.CLICK in ports:
                        env.task.run.click()
                    env.task.control = set(ports) - {echocave.CLICK}
                    source = env.step()[0]
                else:
                    source = env.step(ports[0] if ports else None)[0]
            size = agent.publish(handle, STEP, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, dark, index)
            if publication.outcome_receipt:
                assert not verdict and source["outcome"]["scalar"] == publication.outcome_scalar
                assert publication.outcome_scalar == (1 if pilot else -1)
                verdict = True
            if index in (0, 1, 10, 16, 170, 540) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[124:492, 36:876]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.012))
            if publication.done:
                assert verdict
                return scores
        raise AssertionError(("Echo Cave did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def drone_hoops_replay(agent, env_class, rung, dark):
    from neural_workshop import dronehoops
    from nwenv.outcome import derive_public_outcome

    frame_hz = 10 if dark else 60
    env = env_class(seed=17, rung=rung, trials=1, visible=False, frame_hz=frame_hz)
    handle = agent.create(rung, 1, 1, 17, 10, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        source_verdict = None
        native_verdict = None
        compared_verdict = False
        native_done = False
        for index in range(5000):
            if index:
                trial = env.task.run
                ports = []
                if trial and trial.result is None:
                    if not dark:
                        ports = dronehoops.autopilot(trial)
                    elif index == 1:
                        ports = [dronehoops.DOWN]
                if ports:
                    assert agent.act_mask(handle, sum(1 << port for port in ports), index * 2)
                if len(ports) > 1:
                    env.task.control = set(ports)
                    source = env.step()[0]
                else:
                    source = env.step(ports[0] if ports else None)[0]
            if not native_done:
                size = agent.publish(handle, 1 / frame_hz if index else 1e-12, index * 2 + 1, packet, len(packet),
                                     WIDTH, HEIGHT, dark, ctypes.byref(publication))
                assert size == len(packet)
                native_done = bool(publication.done)
            if source_verdict is None and env.task.phase == "judged":
                # The original can report an early outcome from scenery pixels.
                # Read the actual judged frame directly from its pixels.
                outcome = derive_public_outcome(source["rgba"], WIDTH, HEIGHT, [], None)
                assert outcome["scalar"] == (-1 if dark else 1)
                source_verdict = index
            if publication.outcome_receipt:
                assert native_verdict is None
                assert publication.outcome_scalar == (-1 if dark else 1)
                native_verdict = index
            both_verdicts = source_verdict is not None and native_verdict is not None
            if both_verdicts:
                assert abs(source_verdict - native_verdict) <= 1, (rung, source_verdict, native_verdict)
            settled = bool(publication.done) and source["done"]
            if index in (0, 10, 170, 450) or (both_verdicts and not compared_verdict) or settled:
                board = None if settled else np.s_[124:492, 36:876]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.012))
                compared_verdict |= both_verdicts
            if settled:
                assert compared_verdict
                return scores
        raise AssertionError(("Drone Hoops did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def field_manual_replay(agent, env_class, rung, dark):
    from neural_workshop import fieldmanual

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 25, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        judged = False
        for index in range(1000):
            if index:
                choices = fieldmanual.autopilot(env.task.run) if env.task.run else []
                port = choices[0] if choices else None
                if dark and index == 65:
                    order = env.task.run.order
                    digit = (int(order.value[env.task.run.typed]) + 1) % 10 if order.kind == "type" else 0
                    port = fieldmanual.DIGIT + digit
                if port is not None:
                    assert agent.act(handle, port, index * 2)
                source = env.step(port)[0]
            size = agent.publish(handle, STEP if index else 1e-12, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, index)
            if publication.outcome_receipt:
                assert not judged and source["outcome"]["scalar"] == publication.outcome_scalar == (-1 if dark else 1), (
                    rung, index, source["outcome"]["scalar"], publication.outcome_scalar, env.task.run.result)
                judged = True
            if index in (0, 4, 8, 15, 60, 64) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[168:486, 168:744]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.017))
            if publication.done:
                assert judged
                return scores
        raise AssertionError(("Field Manual did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def safecracker_replay(agent, env_class, rung, dark):
    from neural_workshop import safecracker

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 41, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        judged = False
        for index in range(1000):
            if index:
                choices = safecracker.autopilot(env.task.run) if not dark and env.task.run else []
                port = choices[0] if choices else None
                if dark and 65 <= index and env.task.phase == "playing":
                    port = safecracker.LETTER + 25
                if port is not None:
                    assert agent.act(handle, port, index * 2)
                source = env.step(port)[0]
            size = agent.publish(handle, STEP if index else 1e-12, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, index)
            if publication.outcome_receipt:
                assert not judged and source["outcome"]["scalar"] == publication.outcome_scalar == (-1 if dark else 1), (
                    rung, index, source["outcome"]["scalar"], publication.outcome_scalar, env.task.run.result if env.task.run else None)
                judged = True
            if index in (0, 4, 15, 20, 40, 64) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[168:486, 168:744]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.017))
            if publication.done:
                assert judged
                return scores
        raise AssertionError(("Safecracker did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def stagehand_replay(agent, env_class, rung, dark):
    from neural_workshop import stagehand

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 19, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        judged = False
        for index in range(1000):
            if index:
                choices = stagehand.autopilot(env.task.run) if env.task.run else []
                port = choices[0] if choices else None
                if dark and index == 220:
                    port = stagehand.KEY
                if port is not None:
                    assert agent.act(handle, port, index * 2)
                source = env.step(port)[0]
            size = agent.publish(handle, STEP if index else 1e-12, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, index)
            if publication.outcome_receipt:
                assert not judged and source["outcome"]["scalar"] == publication.outcome_scalar == (-1 if dark else 1), (
                    rung, index, source["outcome"]["scalar"], publication.outcome_scalar, env.task.run.result if env.task.run else None)
                judged = True
            if index in (0, 4, 8, 12, 73, 155, 195, 219) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[168:486, 168:744]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.017))
            if publication.done:
                assert judged
                return scores
        raise AssertionError(("Stagehand did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def loading_dock_replay(agent, env_class, rung, dark):
    from neural_workshop import hand, loadingdock

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 20, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        judged = False
        for index in range(2000):
            if index:
                run = env.task.run
                port = None
                if run is not None and run.result is None:
                    if not dark:
                        ports = loadingdock.autopilot(run)
                        port = ports[0] if ports else None
                    elif index >= 460:
                        x, y, _ = run.view().see(run.lamp(run.waiting()[0]))
                        if run.hand.down:
                            port = hand.RELEASE
                        else:
                            port = hand.toward(run.hand, x, y, tol=5)
                            if port is None:
                                port = hand.PRESS
                if port is not None:
                    assert agent.act(handle, port, index * 2)
                source = env.step(port)[0]
            size = agent.publish(handle, STEP if index else 1e-12, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, index)
            if publication.outcome_receipt:
                assert not judged and source["outcome"]["scalar"] == publication.outcome_scalar == (-1 if dark else 1), (
                    rung, index, source["outcome"]["scalar"], publication.outcome_scalar)
                judged = True
            if index in (0, 60, 101, 140, 235, 453, 467) or publication.outcome_receipt or publication.done:
                board = None if publication.done else np.s_[168:486, 168:744]
                scores.append(compare(source, packet, board, (rung, 17, dark, index), interior_limit=0.017))
            if publication.done:
                assert judged
                return scores
        raise AssertionError(("Loading Dock did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


def compare_gunslinger(source, packet, label, active):
    score = compare(source, packet, None, label, frame_limit=0.065)
    if active:
        shape = (HEIGHT, WIDTH, 4)
        area = np.s_[168:486, 168:744, :3]
        reference = np.frombuffer(source["rgba"], np.uint8).reshape(shape)[area].astype(np.int16)
        actual = np.frombuffer(packet, np.uint8, offset=HEADER_BYTES).reshape(shape)[area].astype(np.int16)
        # Plank edges and narrow telegraph wires can land on adjacent pixels.
        # Check their colours against a one-pixel neighbourhood in both views.
        for left, right in ((reference, actual), (actual, reference)):
            padded = np.pad(right, ((1, 1), (1, 1), (0, 0)), mode="edge")
            height, width, _ = left.shape
            miss = np.ones((height, width), dtype=bool)
            for dy in range(3):
                for dx in range(3):
                    neighbour = padded[dy:dy + height, dx:dx + width]
                    miss &= np.abs(left - neighbour).max(axis=2) > 12
            assert miss.mean() < 0.022, (label, "unmatched street pixels", miss.mean())
    return score


def gunslinger_replay(agent, env_class, rung, dark):
    from neural_workshop import gunslinger

    env = env_class(seed=17, rung=rung, trials=1, visible=False)
    handle = agent.create(rung, 1, 1, 17, 15, False)
    try:
        assert handle
        packet = ctypes.create_string_buffer(WIDTH * HEIGHT * 4 + HEADER_BYTES)
        publication = Publication()
        scores = []
        source = env.observe()
        judged = False
        reach = False
        for index in range(1200):
            if index:
                run = env.task.run
                ports = gunslinger.autopilot(run) if run is not None and not dark else []
                port = ports[0] if ports else None
                if port is not None:
                    assert agent.act(handle, port, index * 2)
                source = env.step(port)[0]
            size = agent.publish(handle, STEP if index else 1e-12, index * 2 + 1, packet, len(packet),
                                 WIDTH, HEIGHT, dark, ctypes.byref(publication))
            assert size == len(packet)
            assert bool(publication.done) == source["done"], (rung, index)
            if publication.outcome_receipt:
                assert not judged and source["outcome"]["scalar"] == publication.outcome_scalar == (-1 if dark else 1), (
                    rung, index, source["outcome"]["scalar"], publication.outcome_scalar)
                judged = True
            run = env.task.run
            reached = bool(run and run.drawn())
            if index in (0, 4, 90, 180, 280) or (reached and not reach) or publication.outcome_receipt or publication.done:
                scores.append(compare_gunslinger(source, packet, (rung, 17, dark, index), not publication.done))
            reach |= reached
            if publication.done:
                assert judged
                return scores
        raise AssertionError(("Gunslinger did not complete", rung, dark))
    finally:
        env.close()
        if handle:
            agent.destroy(handle)


class Agent:
    def __init__(self, lib, task):
        prefix = "nw_" + ("beat" if task == "keep_the_beat" else task) + "_agent_"
        self.create = getattr(lib, prefix + "create")
        self.act = getattr(lib, prefix + "act")
        self.destroy = getattr(lib, prefix + "destroy")
        self.publish = getattr(lib, prefix + "publish")
        self.create.argtypes = [ctypes.c_int64] * 4 + ([] if task in ("which_is_nearer", "time_it", "balance", "juggler", "lander", "keep_the_beat", "glider", "catch", "echo_cave", "drone_hoops", "field_manual", "safecracker", "stagehand", "loading_dock", "gunslinger") else [ctypes.c_double] * 2) + [
            ctypes.c_int64, ctypes.c_bool]
        self.create.restype = ctypes.c_int64
        self.act.argtypes = [ctypes.c_int64] * 3
        self.act.restype = ctypes.c_int64
        self.destroy.argtypes = [ctypes.c_int64]
        self.destroy.restype = None
        self.publish.argtypes = [
            ctypes.c_int64, ctypes.c_double, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
            ctypes.c_int32, ctypes.c_int32, ctypes.c_int64, ctypes.POINTER(Publication)]
        self.publish.restype = ctypes.c_int64
        if task in ("catch", "echo_cave", "drone_hoops"):
            self.act_mask = getattr(lib, prefix + "act_mask")
            self.act_mask.argtypes = self.act.argtypes
            self.act_mask.restype = self.act.restype
        if task == "time_it":
            self.audio = getattr(lib, prefix + "audio")
            self.audio.argtypes = [ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64]
            self.audio.restype = ctypes.c_int64


def main(library, task="where_was_it"):
    path = Path(library).resolve(strict=True)
    dll_directory = os.add_dll_directory(str(path.parent)) if sys.platform == "win32" else None
    try:
        lib = ctypes.CDLL(str(path))
        return run(lib, task)
    finally:
        if dll_directory is not None:
            dll_directory.close()


def run(lib, task):
    assert task in ("where_was_it", "which_is_nearer", "same_or_mirror", "point_of_view", "inside_or_out", "touching", "crossings", "time_it", "balance", "juggler", "lander", "keep_the_beat", "glider", "catch", "echo_cave", "drone_hoops", "field_manual", "safecracker", "stagehand", "loading_dock", "gunslinger")
    rooms = task == "where_was_it"
    nearer = task == "which_is_nearer"
    agent = Agent(lib, task)

    original = Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"
    os.chdir(original)
    sys.path.insert(0, str(original))
    os.environ["NW_HEADLESS"] = "1"
    import nwenv   # Sets pyglet's headless options before the application imports it.
    import pyglet

    pyglet.options.dpi_scaling = "real"
    from neural_workshop import bootstrap, state
    from neural_workshop.window import MyWindow

    constructor = MyWindow.__init__

    def hidden(self, *args, **kwargs):
        kwargs["visible"] = False
        return constructor(self, *args, **kwargs)

    with tempfile.TemporaryDirectory() as temporary:
        config = Path(temporary) / "config.ini"
        config.write_text("[DEFAULT]\nWINDOW_WIDTH = 912\nWINDOW_HEIGHT = 684\nWINDOW_FULLSCREEN = False\n")
        with patch.object(sys, "argv", [sys.argv[0], "--configfile", str(config)]), patch.object(MyWindow, "__init__", hidden):
            bootstrap.build_application()
        try:
            # Cocoa may allocate the initial hidden buffer at Retina scale.
            state.window.set_size(WIDTH, HEIGHT)
            scores = []
            for dark in (0, 1):
                state.cfg.BLACK_BACKGROUND = bool(dark)
                clear = float(not dark)
                pyglet.gl.glClearColor(clear, clear, clear, 1.0)
                if task == "gunslinger":
                    scores.extend(gunslinger_replay(agent, nwenv.GunslingerEnv, 25 if dark else 1, dark))
                    continue
                if task == "loading_dock":
                    scores.extend(loading_dock_replay(agent, nwenv.LoadingDockEnv, 16 if dark else 1, dark))
                    continue
                if task == "stagehand":
                    scores.extend(stagehand_replay(agent, nwenv.StagehandEnv, 30 if dark else 1, dark))
                    continue
                if task == "safecracker":
                    scores.extend(safecracker_replay(agent, nwenv.SafecrackerEnv, 13 if dark else 1, dark))
                    continue
                if task == "field_manual":
                    scores.extend(field_manual_replay(agent, nwenv.FieldManualEnv, 16 if dark else 1, dark))
                    continue
                if task == "drone_hoops":
                    scores.extend(drone_hoops_replay(agent, nwenv.DroneHoopsEnv, 10 if dark else 1, dark))
                    continue
                if task == "echo_cave":
                    scores.extend(echo_cave_replay(agent, nwenv.EchoCaveEnv, 10 if dark else 1, dark, not dark))
                    continue
                if task == "catch":
                    scores.extend(catch_replay(agent, nwenv.CatchEnv, 20 if dark else 1, dark, not dark))
                    continue
                if task == "glider":
                    scores.extend(glider_replay(agent, nwenv.GliderEnv, 16 if dark else 1, dark, not dark))
                    continue
                if task == "keep_the_beat":
                    for rung in (1, 16):
                        scores.extend(beat_replay(agent, nwenv.KeepTheBeatEnv, rung, dark))
                    continue
                if task == "lander":
                    for rung in (1, 20):
                        scores.extend(lander_replay(agent, nwenv.LanderEnv, rung, dark))
                    continue
                if task == "juggler":
                    for rung in (1, 7, 13, 20):
                        scores.extend(juggler_replay(agent, nwenv.JugglerEnv, rung, dark))
                    continue
                if task == "balance":
                    for rung, mode in ((1, "pass"), (10, "coast"), (16, "change")):
                        scores.extend(balance_replay(agent, nwenv.BalanceEnv, rung, dark, mode))
                    continue
                if task == "time_it":
                    for rung, press in ((1, "mark"), (7, "early"), (10, "mark"), (13, "miss")):
                        scores.extend(timed_replay(agent, nwenv.TimeItEnv, rung, 17, dark, press))
                    continue
                cases = (
                    (1, 0, True, "moved"), (7, 0, False, "recoloured"),
                    (16, 2, True, "swapped"), (20, 17, True, "gone"),
                ) if rooms else (
                    (1, 17, True, "size"), (7, 23, True, "floor"),
                    (10, 17, True, "shadow"), (13, 6, False, "hiding"),
                    (20, 17, True, "motion"), (20, 17, False, "motion"),
                ) if nearer else (
                    (1, 17, True, (1, True)), (10, 17, False, (1, True)),
                    (13, 17, True, (3, True)), (25, 17, False, (5, False)),
                ) if task == "same_or_mirror" else (
                    (1, 17, True, (3, False, False)), (7, 17, False, (4, True, False)),
                    (16, 17, True, (5, True, True)), (20, 17, True, (5, True, True)),
                    (30, 17, False, (5, True, True)),
                ) if task == "point_of_view" else (
                    (1, 17, True, ("blob", False, 0)),
                    (4, 17, False, ("fingers", False, 0)),
                    (13, 17, True, ("maze", True, 0)),
                    (25, 17, True, ("maze", True, 7)),
                    (30, 17, False, ("maze", False, 10)),
                ) if task == "inside_or_out" else (
                    (1, 17, True, (False, 2, False)), (7, 17, False, (True, 2, False)),
                    (10, 17, True, (False, 3, False)), (13, 17, True, (True, 4, True)),
                    (25, 17, False, (True, 6, True)),
                ) if task == "touching" else (
                    (1, 17, True, (False, 0, 2)), (7, 17, False, (True, 0, 2)),
                    (10, 17, True, (True, 1, 2)), (16, 17, False, (True, 2, 5)),
                    (20, 17, True, (True, 3, 5)),
                )
                env_class = {
                    "where_was_it": nwenv.WhereWasItEnv, "which_is_nearer": nwenv.WhichIsNearerEnv,
                    "same_or_mirror": nwenv.SameOrMirrorEnv, "point_of_view": nwenv.PointOfViewEnv,
                    "inside_or_out": nwenv.InsideOrOutEnv, "touching": nwenv.TouchingEnv,
                    "crossings": nwenv.CrossingsEnv,
                }[task]
                for rung, seed, correct, expected in cases:
                    scores.extend(replay(agent, env_class, rung, seed, dark, correct, expected, task))
        finally:
            state.window.close()
    label = {
        "where_was_it": "Where Was It?", "which_is_nearer": "Which Is Nearer?",
        "same_or_mirror": "Same or Mirror?", "point_of_view": "Point of View",
        "inside_or_out": "Inside or Out?", "touching": "Touching?", "crossings": "Crossings", "time_it": "Time It", "balance": "Balance", "juggler": "Juggler", "lander": "Lander", "keep_the_beat": "Keep the Beat", "glider": "Glider", "catch": "Catch", "echo_cave": "Echo Cave", "drone_hoops": "Drone Hoops", "field_manual": "Field Manual", "safecracker": "Safecracker", "stagehand": "Stagehand", "loading_dock": "Loading Dock", "gunslinger": "Gunslinger",
    }[task]
    print(f"PASS: {len(scores)} Python/SDL {label} frames, "
          f"{min(scores):.2%} minimum exact RGB agreement, matching verdicts through completion")


if __name__ == "__main__":
    main(*sys.argv[1:])
