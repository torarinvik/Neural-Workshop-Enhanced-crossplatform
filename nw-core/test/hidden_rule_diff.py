"""Compare Elisa's Hidden Rule world and seeded deals with the Python source."""

import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

from neural_workshop import hiddenrule


def world_digest(world):
    digest = 1
    for rule in world.rules:
        for offset in range(0, 384, 64):
            word = (rule.mask >> offset) & ((1 << 64) - 1)
            digest = ((digest * 16777619) ^ word ^ (word >> 32)) & 0xFFFFFFFF
    return digest


def expected():
    for rung in range(1, 23):
        world = hiddenrule.space(hiddenrule.grade(rung))
        yield (rung, len(world.items), len(world.rules), world_digest(world))
        for seed in range(5):
            dealt = hiddenrule.deal(rung, rng=random.Random(seed))
            yield (
                seed, world.rules.index(dealt.rule), *(item for item, _ in dealt.seeds),
                *map(int, dealt.lies), *dealt.exam,
            )
            played = hiddenrule.Round(dealt)
            assert played.test(-1) is None and played.question is None
            readings = [played.test((index * 19) % len(world.items)) for index in range(dealt.level.budget)]
            assert all(reading is not None for reading in readings)
            assert played.test(0) is None and played.start_exam()
            for index in range(dealt.level.exam):
                assert played.answer(index % 3 == 0)
            assert played.question is None
            yield (-1, -1, *map(int, readings), -1, played.wrong, int(played.cost), -1)
            reference = hiddenrule.reference_round(dealt)
            yield (
                reference.wrong, int(reference.cost), round(hiddenrule.par(dealt) * 1e9),
                *(value for item, shown in reference.tests for value in (item, int(shown))),
                *map(int, reference.answers),
            )


def main():
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30)
    rows = [tuple(map(int, line.split())) for line in output.splitlines()]
    reference = list(expected())
    assert len(rows) == len(reference), (len(rows), len(reference))
    for index, (actual, wanted) in enumerate(zip(rows, reference)):
        if actual != wanted:
            raise AssertionError(f"Hidden Rule row {index}: Elisa {actual}, Python {wanted}")
    print("PASS: 110 Hidden Rule round replays and all rule worlds match Python across rungs 1–22")


if __name__ == "__main__":
    main()
