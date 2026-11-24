"""Replay the original Triage UI's session methods without a window."""

import os
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))

from neural_workshop import triage
from neural_workshop.ui.triage import Triage


def snapshot(game, deadline):
    score = game.score()
    phase = ("ready", "playing", "judged", "done").index(game.phase)
    fields = [phase, game.rung, game.trial, score["passed"], score["best_rung"], deadline]
    play = game.round
    if play is None:
        return [*map(str, fields), "0", "0", "0", "-1", "0.000000000"]
    return [*map(str, fields), str(play.deal.budget), str(play.used), str(play.value),
            str(-1 if play.open is None else play.open), f"{game.par:.9f}",
            *(str(card.pays) for card in play.deal.cards)]


def expected():
    for rung, trials, adaptive, seed in [
        (1, 5, True, 17), (12, 5, True, 17), (25, 5, False, 17),
        (4, 2, False, -17), (-5, 0, True, 8), (35, 1, True, -29),
    ]:
        now = 0
        game = Triage.__new__(Triage)
        game.rng = random.Random(seed)
        game.clock = lambda: now / 1000
        game.start_rung = rung
        game.total_trials = trials
        game.adaptive = adaptive
        game.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        game._redraw = lambda: None
        for _ in range(2):
            game.start_run()
            yield snapshot(game, 0)
            for trial in range(trials):
                now = 10000 * trial + 1234
                if trial % 2:
                    game.done()
                else:
                    while game.phase == game.PLAY:
                        kind, index = triage.reference_move(game.round)
                        game.steer({"open": index, "swap": index + 8, "done": 16}[kind])
                deadline = round(game.feedback_until * 1000)
                yield snapshot(game, deadline)
                now = deadline - 1
                game.update(0)
                yield snapshot(game, deadline)
                now = deadline
                game.update(0)
                yield snapshot(game, 0)


def main():
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    reference = list(expected())
    assert len(actual) == len(reference), (len(actual), len(reference))
    for index, (line, wanted) in enumerate(zip(actual, reference)):
        assert line.split() == wanted, (index, line, wanted)
    print("PASS: 36 Triage rounds match Python across adaptive, fixed-rung, timer, restart, and environment dial paths")


if __name__ == "__main__":
    main()
