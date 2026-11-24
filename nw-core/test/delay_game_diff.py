"""Replay Delay's original session methods with the same virtual clock."""

import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))

from neural_workshop.ui.delay import Delay


def expected():
    for index, rung in enumerate([1, 10, 16, 25]):
        now = 0
        game = Delay.__new__(Delay)
        game.rng = random.Random(17)
        game.clock = lambda: now
        game.start_rung = rung
        game.total_trials = 2
        game.adaptive = index != 2
        game.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        game._redraw = lambda: None
        game.start_run()
        for tick in range(528):
            now = tick / 4
            game.update(0)
            score = game.score()
            if game.phase == "done":
                yield f"done {score['passed']} {score['best_rung']}"
                break
            if tick % 2 == 0:
                game.steer(int(index == 0 or tick % 6 != 0))
            phase = ("ready", "playing", "judged").index(game.phase)
            mode = ("offer", "waiting", "pause", "over").index(game.mode)
            yield (f"{phase} {mode} {game.rung} {game.trial} {game.k} {game.coins} "
                   f"{score['passed']} {game.par:.9f}")


def main():
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    reference = list(expected())
    assert len(actual) == len(reference), (len(actual), len(reference))
    for index, (line, wanted) in enumerate(zip(actual, reference)):
        assert line == wanted, (index, line, wanted)
    assert sum(line.startswith("done ") for line in actual) == 4
    print(f"PASS: {len(actual)} Delay session states match Python across eight rounds")


if __name__ == "__main__":
    main()
