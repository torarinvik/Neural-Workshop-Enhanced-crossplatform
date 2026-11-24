"""Compare the Elisa Sonar deal and action boundary against Python."""
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import sonar


def python312_sum(values):
    """Float sum used by the source app on CPython 3.12 and later."""
    total = correction = 0.0
    for term in values:
        next_total = total + term
        if abs(total) >= abs(term):
            correction += (total - next_total) + term
        else:
            correction += (term - next_total) + total
        total = next_total
    return total + correction


if sys.version_info < (3, 12):
    sonar.sum = python312_sum


LEVELS = (0, 1, 2, 3, 5, 7, 8, 10, 15, 23, 100)


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())

    def read(kind):
        row, *fields = next(rows).split()
        assert row == kind, (kind, row, fields)
        return fields

    actions = 0
    for rung in LEVELS:
        rng = random.Random(1729)
        for trial in range(2):
            dealt = sonar.deal(rung, rng=rng)
            level = dealt.level
            side = level.side

            def index(cell):
                return cell[1] * side + cell[0]

            grade = read("deal")
            assert tuple(map(int, grade[:5])) == (rung, trial, side, level.width, level.bands)
            assert math.isclose(float(grade[5]), level.noise, abs_tol=1e-15)
            assert math.isclose(float(grade[6]), level.drift, abs_tol=1e-15)
            assert int(grade[7]) == level.penalty
            assert float(grade[8]) == level.slack
            assert int(grade[9]) == dealt.budget
            for cell, lie in zip(dealt.path, dealt.lies):
                assert tuple(map(int, read("path"))) == (index(cell), lie)
            assert read("last") == [str(index(dealt.path[-1]))]
            run = sonar.Round(dealt)
            for at in range(dealt.budget):
                cell, reading, cost, target, over = map(int, read("act"))
                point = cell % side, cell // side
                if at % 3 == 0:
                    assert not run.dig(point)
                    assert reading == -1
                else:
                    assert run.ping(point) == reading
                assert (cost, target, bool(over)) == (run.cost, index(run.target), run.over)
                actions += 1
            assert read("over") == ["-1", "0"]
            won = sonar.Round(dealt)
            assert won.dig(won.target)
            assert tuple(map(int, read("win"))) == (won.over, won.found, won.actions, won.cost)
            reference = sonar.Round(dealt)
            belief = sonar.Belief(level)
            solver_rng = random.Random(0)
            while not reference.over:
                expected = sonar.reference_move(belief, solver_rng)
                row = tuple(map(int, read("ref")))
                assert row == (int(expected[0] == "dig"), index(expected[1])), (rung, trial, reference.actions, row, expected)
                kind, point = expected
                if kind == "dig":
                    if not reference.dig(point):
                        belief.missed(point)
                else:
                    belief.heard(point, reference.ping(point))
            cost = reference.cost if reference.found else dealt.budget * sonar.PING
            assert float(read("par")[0]) == cost + level.slack
    rng = random.Random(-1729)
    first = sonar.deal(1, rng=rng)
    assert list(map(float, read("survey"))) == [1, 1, 7, sonar.par(first)]
    assert list(map(int, read("judged"))) == [2, 1, 1, 100, 0]
    second = sonar.deal(2, rng=rng)
    assert list(map(float, read("survey"))) == [1, 2, 21, sonar.par(second)]
    assert list(map(int, read("loss"))) == [2, 1, second.budget, 2010 + second.budget - 1 + 1800]
    assert list(map(float, read("done"))) == [3, 1, second.budget / 2]
    restart = sonar.deal(1, rng=rng)
    x, y = restart.path[0]
    assert list(map(float, read("restart"))) == [1, 1, 0, y * 5 + x, sonar.par(restart)]
    assert next(rows, None) is None
    print(f"PASS: {len(LEVELS) * 2} Sonar deals and {actions:,} actions, solver choices, and par scores matched Python. Controller replay passed")


if __name__ == "__main__":
    compare(sys.argv[1])
