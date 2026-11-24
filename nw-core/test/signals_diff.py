"""Check the deal stream, hidden codes, partner, reference learner and par."""

import math
import random
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import signals


def value_index(value):
    return -1 if value is None else signals.VALUES.index(value)


def compare_session(rows):
    rng = random.Random(17)
    first = signals.deal(12, rng=rng)
    second = signals.deal(13, rng=rng)
    restart = signals.deal(12, rng=rng)
    first_speak = signals.partner_says(first, 1)[0]
    expected = [
        (1, 1, 12, 1, 0, -1, 0, first.seed, 0, 0, 0, 0),
        (0, 1, 12, 1, 0, -1, 0, first.seed, 0, 0, 0, 0),
        (1, 1, 12, 1, 1, first_speak, 1, first.seed, 0, 0, 100, 0),
        (1, 2, 13, 1, 16, -1, 16, first.seed, 1, 12, 100, 2900),
        (0, 2, 13, 1, 16, -1, 16, first.seed, 1, 12, 100, 2900),
        (1, 1, 13, 2, 0, -1, 0, second.seed, 1, 12, 2900, 2900),
        (1, 2, 12, 2, 16, -1, 0, second.seed, 1, 12, 3000, 5800),
        (1, 3, 12, 2, 0, 0, 0, 0, 1, 12, 5800, 5800),
        (1, 1, 12, 1, 0, -1, 0, restart.seed, 0, 0, 6000, 5800),
    ]
    for state in expected:
        actual = tuple(map(int, next(rows).split()))
        assert actual == state, (actual, state)


def compare(binary):
    transcript = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(1, 36):
        for seed in range(-10, 11):
            deal = signals.deal(rung, seed)
            level = deal.level
            reference = signals.reference_game(deal)
            floor = signals.guessing(deal)
            ref = reference.score
            if rung <= 20:
                par = ref - (0.5 * (20 - rung) / 19) * max(0, ref - floor)
            else:
                par = ref + min(0.8, 0.08 * (rung - 20)) * ((ref + len(deal.exchanges)) / 2 - ref)
            row = next(transcript).split()
            expected = (rung, level.objects, level.exchanges, ("listen", "speak", "both").index(level.roles),
                        int(level.shapes), level.length, level.swaps, deal.change_at, ref)
            assert tuple(map(int, row[:9])) == expected, (rung, seed, row, expected)
            assert math.isclose(float(row[9]), floor, abs_tol=1e-12, rel_tol=0), (rung, seed, row, floor)
            assert math.isclose(float(row[10]), par, abs_tol=1e-12, rel_tol=0), (rung, seed, row, par)
            for initial, changed in zip(deal.meaning, deal.changed):
                actual = tuple(map(int, next(transcript).split()))
                assert actual == (value_index(initial), value_index(changed)), (rung, seed, actual)
            for at, (exchange, signal, picked, right) in enumerate(reference.history):
                said = signals.partner_says(deal, at)
                actual = tuple(map(int, next(transcript).split()))
                expected = (int(exchange.role == "player"), exchange.target, exchange.coin,
                            said[0], said[1] if len(said) == 2 else -1,
                            signal[0], signal[1] if len(signal) == 2 else -1, picked, int(right),
                            signals.partner_picks(deal, at, said),
                            *(colour * 4 + shape for colour, shape in exchange.objects))
                assert actual == expected, (rung, seed, at, actual, expected)
    compare_session(transcript)
    assert next(transcript, None) is None
    print("PASS: 736 Signals cases match Python (735 games and an adaptive session)")


if __name__ == "__main__":
    compare(sys.argv[1])
