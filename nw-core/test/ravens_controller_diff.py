#!/usr/bin/env python3
"""Compare the Matrix Reasoning run controller with the original UI source.

The Ravens kernel differential already checks the generator in isolation.  This
test checks the boundary the browser/native shells actually use: the original
UI's per-trial sampled-seed stream, durable panel copies, answer permutation,
feedback deadline, adaptive level, and next-trial transition.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "nw-core" / "build" / "pymod"))
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

import nwcore  # noqa: E402
from neural_workshop.ravens import GRADES, generate  # noqa: E402
from neural_workshop.ravens.figures import SHAPES  # noqa: E402
from neural_workshop.ravens.palette import PALETTES  # noqa: E402


INFO_PHASE = 0
INFO_LEVEL = 1
INFO_TRIAL = 2
INFO_ACROSS = 4
INFO_CHOICES = 5
INFO_ANSWER = 6
INFO_CORRECT = 8
INFO_VERDICT = 9
INFO_TRIAL_LEVEL = 15
INFO_ANSWERED = 18
INFO_FEEDBACK_UNTIL = 21

VALUE_GRID_COUNT = 0
VALUE_CHOICE_COUNT = 1
VALUE_SHAPE = 2
VALUE_FILL = 3
VALUE_ANGLE = 4
VALUE_PART = 5
VALUE_CX = 6
VALUE_CY = 7
VALUE_RADIUS = 8
VALUE_CHOICE_SHAPE = 13
VALUE_CHOICE_FILL = 14
VALUE_CHOICE_ANGLE = 15
VALUE_CHOICE_PART = 16
VALUE_CHOICE_CX = 17
VALUE_CHOICE_CY = 18
VALUE_CHOICE_RADIUS = 19

FILL_ID = {
    "white": 0, "grey-light": 1, "grey-mid": 2, "grey-dark": 3,
    "black": 4, "yellow": 5, "sky": 6, "vermilion": 7, "blue": 8,
}
SHAPE_ID = {name: index for index, name in enumerate(SHAPES)}
MAX_FIGURES = 27  # three components × nine source layout slots


def micro(value: float) -> int:
    # The Elisa controller stores the same decimal values as the kernel and
    # converts them to the diagnostic integer with a truncating i64 cast.
    return int(value * 1_000_000.0)


def source_figure(figure):
    return (
        SHAPE_ID[figure.shape], micro(figure.centre.x), micro(figure.centre.y),
        micro(figure.radius), FILL_ID[figure.fill.name], figure.angle,
        figure.component,
    )


def source_panels(puzzle):
    grid = [panel for row in puzzle.panels for panel in row]
    return grid, puzzle.choices


def info(handle, field):
    return nwcore.matrix_reasoning_info(handle, field)


def value(handle, field, at):
    return nwcore.matrix_reasoning_value(handle, field, at)


def controller_panel(handle, panel, choice=False):
    count_field = VALUE_CHOICE_COUNT if choice else VALUE_GRID_COUNT
    shape_field = VALUE_CHOICE_SHAPE if choice else VALUE_SHAPE
    fill_field = VALUE_CHOICE_FILL if choice else VALUE_FILL
    angle_field = VALUE_CHOICE_ANGLE if choice else VALUE_ANGLE
    part_field = VALUE_CHOICE_PART if choice else VALUE_PART
    cx_field = VALUE_CHOICE_CX if choice else VALUE_CX
    cy_field = VALUE_CHOICE_CY if choice else VALUE_CY
    radius_field = VALUE_CHOICE_RADIUS if choice else VALUE_RADIUS
    base = panel * MAX_FIGURES
    count = value(handle, count_field, panel)
    return [
        (
            value(handle, shape_field, base + figure),
            value(handle, cx_field, base + figure),
            value(handle, cy_field, base + figure),
            value(handle, radius_field, base + figure),
            value(handle, fill_field, base + figure),
            value(handle, angle_field, base + figure),
            value(handle, part_field, base + figure),
        )
        for figure in range(count)
    ]


def compare_trial(handle, puzzle, label):
    expected_grid, expected_choices = source_panels(puzzle)
    assert info(handle, INFO_ACROSS) == puzzle.across, label
    assert info(handle, INFO_CHOICES) == len(expected_choices), label
    assert info(handle, INFO_ANSWER) == puzzle.answer, label
    for panel, expected in enumerate(expected_grid):
        got = controller_panel(handle, panel)
        want = [source_figure(figure) for figure in expected]
        assert got == want, f"{label}: grid panel {panel}: {got!r} != {want!r}"
    for panel, expected in enumerate(expected_choices):
        got = controller_panel(handle, panel, choice=True)
        want = [source_figure(figure) for figure in expected]
        assert got == want, f"{label}: choice panel {panel}: {got!r} != {want!r}"


def run_case(start_level: int, seed: int) -> None:
    # flags: feedback on, explanation off; colour selects the two source
    # palettes.  Adaptive is on so the next-trial level is exercised too.
    handle = nwcore.matrix_reasoning_create(start_level, 5, 0, 1, 1, 1, seed)
    assert handle > 0
    source_rng = random.Random(seed)
    level = start_level
    try:
        for trial in range(2):
            if trial == 0:
                assert nwcore.matrix_reasoning_action(handle, 0, 0, 1000) == 1
            else:
                assert info(handle, INFO_PHASE) == 1
            sampled_seed = source_rng.randrange(1 << 30)
            puzzle = generate(level=level, seed=sampled_seed, palettes=PALETTES)
            compare_trial(handle, puzzle, f"level={start_level} seed={seed} trial={trial}")
            assert info(handle, INFO_TRIAL) == trial + 1
            assert info(handle, INFO_TRIAL_LEVEL) == level
            answer = info(handle, INFO_ANSWER)
            assert nwcore.matrix_reasoning_action(
                handle, 1, answer, 1100 + trial * 2000
            ) == 1
            assert info(handle, INFO_PHASE) == 3
            assert info(handle, INFO_VERDICT) == 1
            deadline = info(handle, INFO_FEEDBACK_UNTIL)
            assert nwcore.matrix_reasoning_advance(handle, deadline - 1) == 2
            assert nwcore.matrix_reasoning_advance(handle, deadline) == 1
            assert info(handle, INFO_CORRECT) == trial + 1
            assert info(handle, INFO_ANSWERED) == trial + 1
            level = min(len(GRADES), level + 1)
    finally:
        assert nwcore.matrix_reasoning_destroy(handle) == 0


for level in (1, 2, 4, 7, 10, 12):
    for seed in (1, 17, 73):
        run_case(level, seed)

print("PASS: Matrix Reasoning controller matches original source seed stream, panels, choices, grading, feedback, and adaptation")
