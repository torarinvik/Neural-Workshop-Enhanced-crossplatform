"""Compare seeded Elisa Inside or Out? deals to the original Python game."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import inside  # noqa: E402


def point(key, offset=0):
    x, y = divmod(key, 33)
    return x - 1 + offset, y - 1 + offset


def main():
    output = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    tested = 0
    for header in output:
        rung, seed, size, answer, first, second, count = map(int, header.split())
        expected = inside.deal(rung, seed)
        context = (rung, seed)
        assert (size, answer) == (expected.size, expected.answer), context
        boundary = [point(int(key)) for key in next(output).split()]
        assert len(boundary) == count and [boundary] == expected.loops, context
        dots = [point(first, 0.5)]
        if expected.level.pair:
            dots.append(point(second, 0.5))
        assert dots == expected.dots, (context, dots, expected.dots)
        for line in expected.decoys:
            got = list(map(float, next(output).split()))
            want = [value for p in line for value in p]
            assert len(got) == len(want) and all(
                math.isclose(a, b, rel_tol=1e-13, abs_tol=1e-13)
                for a, b in zip(got, want)
            ), context
        tested += 1
    assert tested == 742, tested
    print(f"Inside or Out? matched {tested} seeded Python deals")


if __name__ == "__main__":
    main()
