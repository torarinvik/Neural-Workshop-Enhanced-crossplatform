"""Compare seeded Touching? deals and signed gaps to the Python reference."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import touching  # noqa: E402


def main():
    output = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    tested = 0
    unavailable = 0
    for header in output:
        rung, seed, count, answer, margin = header.split()
        context = int(rung), int(seed)
        assert math.isclose(float(margin), touching.grade(context[0]).margin, abs_tol=1e-14), context
        try:
            expected = touching.deal(*context)
        except RuntimeError:
            assert (int(count), int(answer)) == (0, -1), context
            unavailable += 1
            continue
        assert int(count) == len(expected.shapes) and int(answer) == expected.answer, context
        for i, shape in enumerate(expected.shapes):
            square, filled, *geometry = next(output).split()
            assert int(square) == (shape.kind == "square") and int(filled) == shape.filled, context
            for got, want in zip(map(float, geometry), (shape.x, shape.y, shape.r, shape.turn)):
                assert math.isclose(got, want, rel_tol=1e-12, abs_tol=1e-12), (context, i, got, want)
            for j in range(i):
                got = float(next(output))
                want = touching.gap(shape, expected.shapes[j])
                assert math.isclose(got, want, rel_tol=1e-12, abs_tol=1e-12), (context, i, j, got, want)
        tested += 1
    assert tested + unavailable == 1034, (tested, unavailable)
    print(f"Touching? matched {tested} seeded Python deals and {unavailable} exhausted seeds")


if __name__ == "__main__":
    main()
