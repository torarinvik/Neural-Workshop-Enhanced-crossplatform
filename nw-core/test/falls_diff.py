"""Replay the Python Will It Fall? model and a scored adaptive run."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import falls


KINDS = ("stand", "lever", "land", "first", "bounce")


def numbers(rows, convert=int):
    return tuple(map(convert, next(rows).split()))


def close(actual, expected):
    assert len(actual) == len(expected)
    assert all(isclose(a, b, rel_tol=2e-13, abs_tol=2e-13)
               for a, b in zip(actual, expected)), (actual, expected)


def compare_puzzle(rows, puzzle):
    assert numbers(rows) == (KINDS.index(puzzle.kind), len(puzzle.choices), puzzle.answer)
    if puzzle.blocks:
        first = falls.first_to_fall(puzzle.blocks)
        assert numbers(rows) == (len(puzzle.blocks), -1 if first is None else first)
        for index, block in enumerate(puzzle.blocks):
            lean = falls.lean(puzzle.blocks, index) if index else 0.0
            close(numbers(rows, float), (*block, lean))
    elif puzzle.lever:
        _, pivot, _, piles = puzzle.lever
        assert numbers(rows) == (pivot,)
        piles = dict(piles)
        assert tuple(numbers(rows)[0] for _ in range(11)) == tuple(piles.get(at, 0) for at in range(-5, 6))
    else:
        height, edge, speed, lo, hi, dots, bounces = puzzle.flight
        close(numbers(rows, float), (height, edge, speed, lo, hi, falls.landing(height, speed, edge, bounces)))
        for dot in dots:
            close(numbers(rows, float), dot)


def main(executable):
    rows = iter(subprocess.check_output([executable], text=True).splitlines())
    cases = [(rung, seed) for rung in range(-1, 43) for seed in range(-11, 13)]
    cases += [(24, -(1 << 63)), (24, (1 << 63) - 1)]
    observed = set()
    for rung, seed in cases:
        try:
            fields = next(rows).split()
            grade = falls.grade(rung)
            assert tuple(map(int, fields[:5])) == (rung, seed, grade.rung, KINDS.index(grade.kinds[-1]), grade.blocks)
            close((float(fields[5]),), (grade.margin,))
            assert tuple(map(int, fields[6:])) == (grade.bins, grade.dots, int(grade.offset_pivot))
            puzzle = falls.deal(rung, seed=seed)
            observed.add(puzzle.kind)
            compare_puzzle(rows, puzzle)
        except AssertionError as error:
            raise AssertionError(f"rung={rung}, seed={seed}") from error
    assert observed == set(KINDS)

    rng = Random(-17)
    rung = 16
    for at in range(5):
        assert numbers(rows) == (rung, at + 1)
        compare_puzzle(rows, falls.deal(rung, rng=rng))
        rung += 1 if at % 2 == 0 else -1
    assert numbers(rows) == (5, 3, 16, 17)
    assert next(rows, None) is None
    print(f"PASS: {len(cases)} Will It Fall? scenes across five puzzle kinds and a scored adaptive replay")


if __name__ == "__main__":
    main(sys.argv[1])
