"""Compare seeded Gamble deals, every payout slot, and played rounds."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import gamble


LEVELS = (1, 5, 6, 6, 7, 10, 14, 18, 19, 21, 25, 50, 512)


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())

    def read(kind):
        header, *values = next(rows).split()
        assert header == kind, (kind, header, values)
        return values

    def close(actual, expected, where):
        assert isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-12), (where, actual, expected)

    outcomes = 0
    covered = set()
    for index in range(3):
        rng = Random(index * 421 + 17)
        for rung in LEVELS:
            dealt = gamble.deal(rung, rng=rng)
            level = dealt.level
            fields = read("level")
            assert tuple(map(int, fields[:3])) == (rung, level.arms, level.pulls)
            close(fields[3], level.spread, (rung, "spread"))
            close(fields[4], level.drift, (rung, "drift"))
            assert tuple(map(int, fields[5:9])) == (level.biters, level.jumps, level.price, level.bankroll)
            close(fields[9], level.allow, (rung, "allow"))
            assert int(fields[10]) == dealt.seed
            for machine in dealt.machines:
                pays, rate, bite = read("machine")
                assert (int(pays), int(bite)) == (machine.pays, machine.bite)
                close(rate, machine.bite_rate, (rung, "bite rate"))
            for jump in dealt.jumps:
                assert int(read("jump")[0]) == jump
            for t in range(level.pulls):
                for arm in range(level.arms):
                    odds, draw, paid, worth = read("turn")
                    close(odds, dealt.odds[t][arm], (rung, t, arm, "odds"))
                    assert float(draw) == dealt.draws[t][arm], (rung, t, arm)
                    assert int(paid) == gamble.payout(dealt, t, arm)
                    close(worth, gamble.worth(dealt, t, arm), (rung, t, arm, "worth"))
                    outcomes += 1
            for policy in range(2):
                round = gamble.Round(dealt)
                for t in range(level.pulls):
                    if round.over or (policy == 1 and t == 2 and round.stop()):
                        break
                    assert round.pull((t * 3 + policy) % level.arms) is not None
                    total, score = read("pull")
                    assert int(total) == round.total
                    close(score, round.value, (rung, policy, t, "score"))
                assert tuple(map(int, read("end"))) == (round.t, round.stopped, round.bust)
                covered.add("bust" if round.bust else ("stop" if round.stopped else "exhaustion"))
            reference = gamble.reference_round(dealt)
            fields = read("reference")
            assert tuple(map(int, fields[:3])) == (reference.t, reference.stopped, reference.total), (rung, index, fields)
            for actual, expected in zip(fields[3:], (reference.value, gamble.guessing(dealt), gamble.knowing(dealt), gamble.par(dealt))):
                close(actual, expected, (rung, "reference"))
            for expected in reference.history:
                assert tuple(map(int, read("move"))) == expected, (rung, index, expected)
    assert covered == {"bust", "stop", "exhaustion"}
    rng = Random(-17)
    rung, wins = 1, 0
    for trial, select in enumerate((max, min), start=1):
        dealt = gamble.deal(rung, rng=rng)
        par = gamble.par(dealt)
        live_rung, live_trial, live_par = read("live")
        assert (int(live_rung), int(live_trial)) == (rung, trial)
        close(live_par, par, "controller par")
        round = gamble.Round(dealt)
        while not round.over:
            arm = select(range(round.level.arms), key=lambda arm: gamble.worth(dealt, round.t, arm))
            round.pull(arm)
        passed = not round.bust and round.value >= par - 1e-9
        assert passed == (trial == 1)
        wins += passed
        rung = rung + 1 if passed else max(1, rung - 1)
        phase, next_rung, passed_count, score, coins, early = read("scored")
        assert tuple(map(int, (phase, next_rung, passed_count, coins, early))) == (2, rung, wins, round.total, 0)
        close(score, round.value, "controller score")
    assert list(map(int, read("done"))) == [3, 1, 1, 0]
    assert list(map(int, read("restart"))) == [1, 1, 0, gamble.deal(1, rng=rng).seed]
    paid = gamble.deal(18, seed=17)
    assert list(map(int, read("stopped"))) == [2, 1, 0, int(gamble.par(paid) <= 1e-9)]
    assert list(map(int, read("released"))) == [3, 0]
    assert next(rows, None) is None
    print(f"PASS: {len(LEVELS) * 3} Gamble deals and {outcomes:,} payout slots matched Python. Reference choices, par, and controller replay passed")


if __name__ == "__main__":
    compare(sys.argv[1])
