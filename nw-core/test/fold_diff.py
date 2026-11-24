"""Compare Fold It nets, hinge frames, marks and every offered cube to Python."""

from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import fold, space

AXES = {
    (1, 0, 0): 1, (0, 1, 0): 2, (0, 0, 1): 3,
    (-1, 0, 0): -1, (0, -1, 0): -2, (0, 0, -1): -3,
}
GLYPHS = ("none", "arrow", "triangle", "half", "tee", "bar", "dot", "ell", "flag")
COLOURS = fold.COLOURS + (fold.PLAIN,)


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())

    def read():
        return tuple(map(int, next(rows).split()))

    nets = set()
    for rung in range(1, 31):
        for seed in range(-5, 20):
            puzzle = fold.deal(rung, seed)
            nets.add(puzzle.net)
            assert fold.check(puzzle), (rung, seed)
            assert read() == (rung, seed, puzzle.asked, puzzle.answer, len(puzzle.choices))
            frames = fold.fold(puzzle.net)
            for (x, y), (glyph, colour, quarter) in zip(puzzle.net, puzzle.marks):
                expected = (10 * x + y, GLYPHS.index(glyph), COLOURS.index(colour), quarter,
                            *(AXES[axis] for axis in frames[(x, y)]))
                actual = read()
                assert actual == expected, (rung, seed, (x, y), actual, expected)
            if puzzle.kind == "opposite":
                assert read() == tuple(fold.LETTERS.index(letter) for letter in puzzle.choices)
            for cube, turn in puzzle.cubes:
                assert read() == (space.GRID_TURNS.index(turn),), (rung, seed)
                expected = {
                    (AXES[normal], AXES[mark.up], GLYPHS.index(mark.glyph),
                     COLOURS.index(mark.colour), int(mark.mirrored))
                    for normal, mark in cube
                }
                actual = {read() for _ in range(6)}
                assert actual == expected, (rung, seed, actual, expected)
    first = fold.deal(3, rng=Random(17))
    rng = Random(17)
    fold.deal(3, rng=rng)
    second = fold.deal(4, rng=rng)
    clock_rng = Random(17)
    fold.deal(4, rng=clock_rng)
    after_flag = fold.deal(4, rng=clock_rng)
    expected_states = (
        (1, 1, 3, 1, -1, 0, 0, 0, 0, -1, 0.0),
        (0, 1, 3, 1, -1, 0, 0, 0, 0, -1, 0.0),
        (1, 2, 4, 1, first.answer, 1, 3, 1, 0, 2600, 0.0),
        (0, 2, 4, 1, first.answer, 1, 3, 1, 0, 2600, 0.0),
        (1, 1, 4, 2, -1, 1, 3, 1, 0, -1, 0.0),
        (1, 2, 3, 2, second.answer, 1, 3, 2, 0, 5200, 0.0),
        (1, 3, 3, 2, -1, 1, 3, 2, 0, -1, 0.0),
        (1, 1, 3, 1, -1, 0, 0, 0, 0, -1, 0.0),
        (1, 1, 4, 1, -1, 0, 0, 0, 0, -1, 0.5),
        (1, 4, 4, 1, -1, 0, 0, 0, 1, -1, 0.0),
        (1, 1, 4, 2, -1, 0, 0, 0, 1, -1, 0.25),
        (1, 2, 5, 2, after_flag.answer, 1, 4, 1, 1, 2600, 0.25),
        (1, 2, 5, 2, after_flag.answer, 1, 4, 1, 1, 2600, 0.25),
        (1, 3, 5, 2, -1, 1, 4, 1, 1, -1, 0.25),
    )
    for expected in expected_states:
        *fields, bank = next(rows).split()
        actual = (*map(int, fields), float(bank))
        assert actual == expected, (actual, expected)
    assert next(rows, None) is None
    assert nets == set(fold.NETS)
    print("PASS: 750 Fold It puzzles, all 11 nets, exact Python distractors, and 2 controller sessions")


if __name__ == "__main__":
    compare(sys.argv[1])
