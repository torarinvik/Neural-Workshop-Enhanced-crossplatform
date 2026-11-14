"""Compare Go kernel rule fixtures with the original Go implementation."""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "original-neural-workshop-enhanced"))
from neural_workshop import go  # noqa: E402


def cases():
    edge = [[0] * 5 for _ in range(5)]
    edge[2][0], edge[2][1], edge[1][0] = 2, 1, 1

    corner = [[0] * 5 for _ in range(5)]
    corner[0][0], corner[0][1] = 2, 1

    occupied = [[0] * 5 for _ in range(5)]
    occupied[2][2] = 1

    suicide = [[0] * 5 for _ in range(5)]
    for x, y in ((1, 2), (3, 2), (2, 1), (2, 3)):
        suicide[y][x] = 2

    ko = [[0] * 5 for _ in range(5)]
    for x, y in ((1, 1), (3, 1), (2, 0), (2, 2)):
        ko[y][x] = 2
    for x, y in ((1, 2), (3, 2), (2, 3)):
        ko[y][x] = 1
    ko_after_capture = go.play(ko, (2, 1), 1)
    assert ko_after_capture is not None

    return (
        ("edge_capture", edge, (0, 3), 1),
        ("corner_capture", corner, (0, 1), 1),
        ("occupied", occupied, (2, 2), 1),
        ("suicide", suicide, (2, 2), 1),
        ("ko_capture", ko, (2, 1), 1),
        # The original helper is intentionally stateless: ko has no prior-board
        # argument in these generated one-move positions, so immediate recapture
        # is legal at this boundary and reproduces the original board.
        ("ko_recapture", [list(row) for row in ko_after_capture], (2, 2), 2),
    )


def expected_line(name, board, point, colour):
    result = go.play(board, point, colour)
    if result is None:
        return f"{name},0"
    flat = (str(value) for row in result for value in row)
    return ",".join((name, "1", *flat))


def main() -> int:
    got = [line for line in subprocess.run(
        [sys.argv[1]], check=True, capture_output=True, text=True,
    ).stdout.splitlines() if line.strip()]
    wanted = [expected_line(name, board, point, colour)
              for name, board, point, colour in cases()]
    if got != wanted:
        for index, (actual, expected) in enumerate(zip(got, wanted)):
            if actual != expected:
                print(f"MISMATCH case {index}:\n  elisa:  {actual}\n  python: {expected}")
        if len(got) != len(wanted):
            print(f"MISMATCH line count: {len(got)} vs {len(wanted)}")
        return 1
    print("PASS: 6 Go rules fixtures identical (edge/corner capture, occupied, suicide, ko capture and stateless recapture)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
