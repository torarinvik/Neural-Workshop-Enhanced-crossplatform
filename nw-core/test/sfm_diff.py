"""Compare seeded Shape from Motion deals and projected dots with Python."""
import math
import random
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import sfm

TIMES = (0.0, 0.017, 0.249, 0.5, 3.333, 0.017)


def compare(binary):
    cases = [(rung, seed) for rung in range(-1, 31) for seed in range(-8, 9)]
    cases.extend((12, seed) for seed in (9, 11, 14, 23, 71))
    cases.extend(((16, -(2**63)), (25, 2**63 - 1), (24, 2**30 - 1)))
    kinds = set()
    dot_count = 0
    with subprocess.Popen([binary], stdout=subprocess.PIPE, text=True) as process:
        lines = iter(process.stdout)
        for rung, seed in cases:
            puzzle = sfm.deal(rung, seed)
            grade = puzzle.level
            spin = int(puzzle.kind == "spin")
            record = next(lines).split()
            assert tuple(map(int, record[:9])) == (
                rung, seed, grade.rung, sfm.SOLIDS.index(puzzle.solid), spin,
                puzzle.way, len(puzzle.choices), puzzle.answer, grade.dots,
            ), (rung, seed, record, puzzle)
            assert len(record) == 12 and all(
                math.isclose(float(actual), expected, rel_tol=0, abs_tol=1e-12)
                for actual, expected in zip(record[9:], (grade.life or 0.0, grade.eye, grade.period))
            ), (rung, seed, record, grade)
            options = tuple(int(next(lines)) for _ in puzzle.choices)
            assert options == ((-1, -1) if spin else tuple(map(sfm.SOLIDS.index, puzzle.options))), (
                rung, seed, options, puzzle.options,
            )
            kinds.add((puzzle.solid, puzzle.kind))
            for t in TIMES:
                for index, expected in enumerate(sfm.dots(puzzle, t)):
                    dot = tuple(map(float, next(lines).split()))
                    assert len(dot) == 3 and all(
                        math.isclose(a, b, rel_tol=0, abs_tol=1e-12)
                        for a, b in zip(dot, expected)
                    ), (rung, seed, puzzle.solid, puzzle.kind, t, index, dot, expected)
                    dot_count += 1
        rng = random.Random(17)
        for rung in (12, 13):
            seed = rng.randrange(1 << 30)
            assert tuple(map(int, next(lines).split())) == (seed, sfm.deal(rung, seed).answer)
        assert next(lines, None) is None
        assert process.wait() == 0
    assert kinds == {(solid, kind) for solid in sfm.SOLIDS for kind in ("shape", "spin")}
    print(f"PASS: Shape from Motion Python parity across {len(cases)} deals and {dot_count} dots")


if __name__ == "__main__":
    compare(sys.argv[1])
