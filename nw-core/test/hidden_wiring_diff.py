"""Compare Elisa's Hidden Wiring gate order and rounds with Python."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import wiring


def expected():
    for rung in range(1, 31):
        level = wiring.grade(rung)
        world = wiring.space(level)
        count = 1 << level.switches
        digest = 2166136261
        for _, mask in world:
            for setting in range(count):
                digest = ((digest ^ ((mask >> setting) & 1)) * 16777619) & 0xFFFFFFFF
        yield (rung, level.switches, len(world), digest)
        indices = {gate: index for index, (gate, _) in enumerate(world)}
        for seed in range(5):
            dealt = wiring.deal(rung, seed=seed)
            yield (seed, *(indices[gate] for gate in dealt.lamps), *dealt.lies, *dealt.exam)
            played = wiring.Round(dealt)
            readings = [played.look((look * 19) % count) for look in range(wiring.budget(level))]
            assert played.look(0) is None
            played.start_exam()
            for index in range(len(dealt.exam)):
                played.answer((index * 5) % count)
            assert played.over
            yield (*readings, -1, played.wrong, int(played.cost), -1)
            reference = wiring.reference_round(dealt)
            yield (reference.wrong, int(reference.cost), round((reference.cost * level.factor + level.slack) * 1e9),
                   *(value for observation in reference.looks for value in observation), *reference.answers)


def main():
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30)
    actual = [tuple(map(int, line.split())) for line in output.splitlines()]
    reference = list(expected())
    assert len(actual) == len(reference), (len(actual), len(reference))
    for index, (row, wanted) in enumerate(zip(actual, reference)):
        assert row == wanted, f"Hidden Wiring row {index}: Elisa {row}, Python {wanted}"
    print("PASS: 150 Hidden Wiring round replays and ordered truth tables match Python across rungs 1–30")


if __name__ == "__main__":
    main()
