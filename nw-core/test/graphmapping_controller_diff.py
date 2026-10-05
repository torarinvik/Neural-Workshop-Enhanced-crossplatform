#!/usr/bin/env python3
"""Differential test for the Graph Mapping controller boundary.

The lower-level graph sweep already compares the Elisa graph kernel with the
original Python helpers.  This test adds the stateful boundary that the
browser and native shells actually use: the source RNG/deck stream, pair
edges, ring coordinates, exposure/feedback transitions, grading, and
adaptive node changes.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "nw-core" / "build" / "pymod"))
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))
sys.path.insert(0, str(ROOT / "nw-core" / "test"))

import nwcore  # noqa: E402
from graphmapping_diff import MAX_NODES, REF, Run, SAME, DIFFERENT, code  # noqa: E402

PHASE_READY = 0
PHASE_ASKING = 1
PHASE_HIDDEN = 2
PHASE_FEEDBACK = 3
PHASE_DONE = 4

INFO_PHASE = 0
INFO_NODES = 2
INFO_TRIAL = 4
INFO_TOTAL_TRIALS = 5
INFO_CORRECT = 6
INFO_SAME_TOTAL = 7
INFO_SAME_RIGHT = 8
INFO_DIFFERENT_TOTAL = 9
INFO_DIFFERENT_RIGHT = 10
INFO_SETTLED_FOR = 17
INFO_ANSWERED = 18
INFO_MEAN_MS = 19
INFO_ASKED_AT_MS = 20
INFO_REALLY_SAME = 21

VALUE_LEFT_EDGE = 0
VALUE_RIGHT_EDGE = 1
VALUE_LEFT_X = 2
VALUE_LEFT_Y = 3
VALUE_RIGHT_X = 4
VALUE_RIGHT_Y = 5


def info(handle: int, field: int) -> int:
    return nwcore.graph_mapping_info(handle, field)


def value(handle: int, field: int, at: int) -> int:
    return nwcore.graph_mapping_value(handle, field, at)


def micro(value_: float) -> int:
    return int(value_ * 1_000_000.0)


def source_edges(graph):
    return [code(edge) for edge in graph.edges]


def controller_edges(handle: int, field: int, count: int):
    return [value(handle, field, at) for at in range(count)]


def compare_trial(handle: int, reference: Run, label: str) -> None:
    assert info(handle, INFO_PHASE) == {"asking": PHASE_ASKING,
                                       "hidden": PHASE_HIDDEN,
                                       "feedback": PHASE_FEEDBACK,
                                       "done": PHASE_DONE}[reference.phase], label
    assert info(handle, INFO_NODES) == reference.nodes, label
    assert info(handle, INFO_TRIAL) == reference.trial, label
    assert info(handle, INFO_REALLY_SAME) == int(reference.really_same), label
    assert info(handle, INFO_SETTLED_FOR) == reference.settled_for, label
    assert controller_edges(handle, VALUE_LEFT_EDGE, len(reference.pair.first.edges)) == source_edges(reference.pair.first), label
    assert controller_edges(handle, VALUE_RIGHT_EDGE, len(reference.pair.second.edges)) == source_edges(reference.pair.second), label
    for panel, spots in enumerate(reference.spots):
        x_field = VALUE_LEFT_X if panel == 0 else VALUE_RIGHT_X
        y_field = VALUE_LEFT_Y if panel == 0 else VALUE_RIGHT_Y
        for at, (x, y) in enumerate(spots):
            assert value(handle, x_field, at) == micro(x), f"{label}: x {panel}/{at}"
            assert value(handle, y_field, at) == micro(y), f"{label}: y {panel}/{at}"


def compare_score(handle: int, reference: Run, label: str) -> None:
    score = reference.score()
    expected = {
        INFO_CORRECT: score["correct"],
        INFO_SAME_TOTAL: score["same_total"],
        INFO_SAME_RIGHT: score["same_right"],
        INFO_DIFFERENT_TOTAL: score["different_total"],
        INFO_DIFFERENT_RIGHT: score["different_right"],
        INFO_ANSWERED: score["trials"],
        INFO_MEAN_MS: int(round(score["mean_seconds"] * 1000)),
    }
    for field, want in expected.items():
        assert info(handle, field) == want, f"{label}: info {field}"


def run_case(start_nodes: int, density: int, subtle: bool, exposure_ms: int,
             adaptive: bool, seed: int) -> None:
    total_trials = 5
    handle = nwcore.graph_mapping_create(
        start_nodes, density, total_trials, exposure_ms,
        int(adaptive), int(subtle), seed,
    )
    assert handle > 0
    density_name = {0: "sparse", 1: "medium", 2: "dense"}[density]
    reference = Run(
        random.Random(seed), start_nodes, density_name, total_trials,
        subtle, exposure_ms, adaptive, True,
    )
    now_ms = 1000
    now = now_ms / 1000.0
    try:
        assert info(handle, INFO_PHASE) == PHASE_READY
        assert info(handle, INFO_TOTAL_TRIALS) == total_trials
        assert nwcore.graph_mapping_action(handle, 0, now_ms) == 1
        reference.start_run(now)
        compare_trial(handle, reference,
                      f"start={start_nodes} density={density} subtle={subtle} "
                      f"exposure={exposure_ms} adaptive={adaptive} seed={seed}")

        # Exercise the exact boundaries: exposure is hidden only at the
        # deadline, answers are accepted in both asking and hidden, and the
        # feedback deadline advances exactly at its timestamp.
        if exposure_ms:
            before = now_ms + exposure_ms - 1
            assert nwcore.graph_mapping_advance(handle, before) == 2
            assert info(handle, INFO_PHASE) == PHASE_ASKING
            reference.update(before / 1000.0)
            assert nwcore.graph_mapping_advance(handle, now_ms + exposure_ms) == 1
            reference.update((now_ms + exposure_ms) / 1000.0)
            assert info(handle, INFO_PHASE) == PHASE_HIDDEN
        answer = SAME if reference.really_same else DIFFERENT
        answer_ms = now_ms + max(exposure_ms, 3000) + 200
        reference.answer(answer, answer_ms / 1000.0)
        assert nwcore.graph_mapping_action(handle, 1 if answer == SAME else 2, answer_ms) == 1
        compare_score(handle, reference, "after first answer")
        assert info(handle, INFO_PHASE) == PHASE_FEEDBACK
        deadline = info(handle, 16)
        assert nwcore.graph_mapping_advance(handle, deadline - 1) == 2
        assert nwcore.graph_mapping_advance(handle, deadline) == 1
        # The controller's integer millisecond deadline is exact.  CPython's
        # decimal conversion can represent 6.1 as 6.1000000000000005, while
        # the reference's accumulated 6.1000000000000005 may compare just
        # above or below it; the source clock is never guaranteed to land on
        # the mathematical boundary exactly, so advance by one microsecond.
        reference.update(deadline / 1000.0 + 0.000001)
        # Keep the replay clock on the controller's integer-ms timeline for
        # latency accounting; the generated state is independent of this
        # one-microsecond boundary nudge.
        reference.asked_at = deadline / 1000.0
        compare_trial(handle, reference, "after feedback")

        # A deliberate wrong answer exercises the opposite adaptive branch,
        # duplicate-answer suppression, and the controller's persistent pair.
        wrong = DIFFERENT if reference.really_same else SAME
        answer_ms = deadline + 400
        reference.answer(wrong, answer_ms / 1000.0)
        assert nwcore.graph_mapping_action(handle, 1 if wrong == SAME else 2, answer_ms) == 1
        assert nwcore.graph_mapping_action(handle, 1 if wrong == SAME else 2, answer_ms + 1) == 2
        compare_score(handle, reference, f"after wrong answer start={start_nodes} density={density} subtle={subtle} exposure={exposure_ms} adaptive={adaptive} seed={seed}")
    finally:
        assert nwcore.graph_mapping_destroy(handle) == 0


def restart_after_done_case() -> None:
    """Keep the lifecycle edge explicit rather than relying on destruction."""
    handle = nwcore.graph_mapping_create(4, 0, 5, 0, 0, 0, 314159)
    assert handle > 0
    now = 1000
    try:
        assert nwcore.graph_mapping_action(handle, 0, now) == 1
        for _trial in range(5):
            same = info(handle, INFO_REALLY_SAME)
            assert nwcore.graph_mapping_action(handle, 1 if same else 2, now + 100) == 1
            deadline = info(handle, 16)
            assert nwcore.graph_mapping_advance(handle, deadline) == 1
            now = deadline + 1
        assert info(handle, INFO_PHASE) == PHASE_DONE
        assert nwcore.graph_mapping_action(handle, 0, now) == 1
        assert info(handle, INFO_PHASE) == PHASE_ASKING
        assert info(handle, INFO_TRIAL) == 1
    finally:
        assert nwcore.graph_mapping_destroy(handle) == 0


for start_nodes in (4, 8, 12, 16):
    for density in (0, 1, 2):
        for subtle in (False, True):
            for adaptive in (False, True):
                for exposure_ms in (0, 3000, 5000, 8000, 12000, 20000):
                    for seed in (1, 17, 73):
                        run_case(start_nodes, density, subtle, exposure_ms,
                                 adaptive, seed)

restart_after_done_case()

print("PASS: Graph Mapping controller matches original source RNG, pair state, coordinates, timing, grading, and adaptation")
