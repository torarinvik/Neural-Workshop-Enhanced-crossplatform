"""Compare seeded Triage deals and reference move transcripts with Python."""

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import triage


def expected():
    ports = {"open": 0, "swap": 1, "done": 2}
    for rung in range(1, 36):
        for seed in range(16):
            dealt = triage.deal(rung, seed)
            cards = [field for card in dealt.cards
                     for field in (len(card.row), card.cost, card.pays, *card.row)]
            yield [str(rung), str(seed), str(dealt.budget), str(triage.best(dealt)),
                   f"{triage.par(dealt):.9f}", *map(str, cards)]
            play = triage.Round(dealt)
            transcript = []
            while not play.over:
                kind, at = triage.reference_move(play)
                triage.act(play, (kind, at))
                transcript.extend((ports[kind], at, play.used, play.value,
                                   sum(1 << i for i in play.turned),
                                   sum(1 << i for i in play.solved)))
            yield list(map(str, transcript))


def main():
    output = subprocess.check_output([sys.argv[1]], text=True, timeout=30)
    actual = [line.split() for line in output.splitlines()]
    reference = list(expected())
    assert len(actual) == len(reference), (len(actual), len(reference))
    for index, (row, wanted) in enumerate(zip(actual, reference)):
        rung, seed = divmod(index // 2, 16)
        assert row == wanted, f"rung {rung + 1}, seed {seed}, row {index % 2}: Elisa {row}, Python {wanted}"
    print("PASS: 560 Triage deals and complete reference transcripts match Python across rungs 1–35")


if __name__ == "__main__":
    main()
