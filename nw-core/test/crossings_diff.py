"""Compare seeded Crossings geometry and outcomes to the Python reference."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import crossings  # noqa: E402


def main():
    output = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    tested = 0
    exhausted = 0
    for header in output:
        rung, seed, answer, bends, most, decoys = map(int, header.split())
        context = rung, seed
        grade = crossings.grade(rung)
        assert (bends, most, decoys) == (grade.bends, grade.most, grade.decoys), context
        try:
            oracle = crossings.deal(*context)
        except RuntimeError:
            assert answer == -1, context
            exhausted += 1
            continue
        assert answer == oracle.answer, context
        for points in (oracle.red, oracle.blue, *oracle.decoys, oracle.crossings):
            got = list(map(float, next(output).split()))
            want = [c for p in points for c in p]
            assert len(got) == len(want), (context, len(got), len(want))
            assert all(math.isclose(a, b, abs_tol=1e-11, rel_tol=1e-12) for a, b in zip(got, want)), context
        tested += 1
    assert tested + exhausted == 69, (tested, exhausted)
    print(f"Crossings matched {tested} seeded Python deals and {exhausted} exhausted seeds")


if __name__ == "__main__":
    main()
