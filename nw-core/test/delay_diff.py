"""Compare seeded Delay offers and published scoring rules with Python."""

import math
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))

from neural_workshop import delay


def main():
    replay = subprocess.check_output([sys.argv[1]], text=True, timeout=30)
    rows = iter(replay.splitlines())
    for rung in range(1, 36):
        for seed in range(-8, 8):
            source = delay.deal(rung, seed)
            header = next(rows).split()
            assert list(map(int, header[:-1])) == [
                rung, seed, delay.floor(source), delay.reference(source), delay.best(source)
            ], header
            assert math.isclose(float(header[-1]), delay.par(source), abs_tol=1e-9), header
            for index, offer in enumerate(source.offers):
                small, large, wait = next(rows).split()
                expected_wait = -1.0 if offer.wait == delay.NEVER else offer.wait
                assert (int(small), int(large)) == (offer.small, offer.large), (rung, seed, index)
                assert math.isclose(float(wait), expected_wait, rel_tol=1e-13, abs_tol=1e-13), (
                    rung, seed, index, wait, expected_wait
                )
    assert next(rows, None) is None
    print("PASS: 112,000 Delay offers and 560 reference runs match Python across rungs 1–35")


if __name__ == "__main__":
    main()
