#!/usr/bin/env python3
"""Replay Notebook with CPython's deterministic zero hash secret."""
import os
from pathlib import Path
import subprocess
import sys
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import notebook


def cases():
    keys = [f"{thing} {name}" for thing in (*notebook.THINGS, "Spare") for name in notebook.NAMES]
    key_ids = {key: index for index, key in enumerate(keys)}
    for key in keys[:160]:
        yield str(hash(key) & ((1 << 64) - 1))
    for rung in range(1, 41):
        for seed in range(-12, 12):
            deal = notebook.deal(rung, seed)
            play = notebook.Round(deal)
            yield " ".join(map(str, (rung, seed, *deal.level[1:])))
            for card in deal.cards:
                row = [("fact", "update", "noise", "question").index(card.kind),
                       key_ids[card.key], card.code, card.answer, *card.offered]
                if card.kind == "question":
                    choice = (card.answer + (seed % 2 != 0)) % deal.level.choices
                    row.append(int(play.answer(choice)))
                else:
                    line = play.at % deal.level.lines
                    assert play.write(line) and play.next()
                    key, code = play.lines[line].rsplit(" ", 1)
                    row.extend((key_ids[key], int(code)))
                yield " ".join(map(str, row))
            final = []
            for note in play.lines:
                if note:
                    key, code = note.rsplit(" ", 1)
                    final.extend((key_ids[key], int(code)))
                else:
                    final.extend((0, 0))
            yield " ".join(map(str, ("done", len(play.answers), play.right, *final)))


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.execve(sys.executable, [sys.executable, *sys.argv], dict(os.environ, PYTHONHASHSEED="0"))
    rng = Random(-17)
    first_seed, second_seed = (rng.randrange(1 << 30) for _ in range(2))
    controller = [
        f"round {first_seed} 13", "scored 1 14 16 1",
        f"round {second_seed} 14", "scored 2 13 0 1",
    ]
    assert sys.hash_info.algorithm == "siphash13" and sys.hash_info.hash_bits == 64
    expected = list(cases())
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    for index, (got, want) in enumerate(zip(actual, expected + controller)):
        assert got == want, (index, got, want)
    assert len(actual) == len(expected) + len(controller)
    print(f"PASS: 160 Python string hashes, 960 Notebook deals, and {len(expected) - 160 - 960 * 2} card actions")
