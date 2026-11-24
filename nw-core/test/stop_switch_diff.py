"""Compare Stop & Switch deals and timed session states with Python."""
import os
import random
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

os.environ.setdefault("PYGLET_SHADOW_WINDOW", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))

from neural_workshop import stopswitch
from neural_workshop.ui.stopswitch import StopAndSwitch


def deals():
    for rung in range(1, 36):
        for seed in range(-4, 4):
            block = stopswitch.deal(rung, seed)
            level = block.level
            yield (f"{rung} {seed} {level.count} {level.window:.9f} {level.stops:.9f} "
                   f"{level.ssd:.9f} {len(level.rules)} {int(level.prepared)} "
                   f"{level.incongruent:.9f} {level.needed:.9f}")
            for item in block.stimuli:
                rule = ("shape", "colour", "opposite").index(item.rule)
                yield (f"{int(item.shape == 'square')} {int(item.colour == 'orange')} "
                       f"{item.side} {rule} {int(item.stop)} {stopswitch.answer(item)}")


def sessions():
    for scenario, rung in enumerate((1, 7, 13, 25)):
        now = 0.0
        game = StopAndSwitch.__new__(StopAndSwitch)
        game.rng = random.Random(17)
        game.clock = lambda: now
        game.start_rung = rung
        game.total_trials = 2
        game.adaptive = scenario != 2
        game.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
        game._redraw = lambda: None
        game.start_run()
        for tick in range(3200):
            now = tick / 32.0
            game.update(0)
            if game.phase == "done":
                score = game.score()
                yield f"done {score['passed']} {score['best_rung']}"
                break
            if game.showing and tick % 7 == 0:
                stimulus = game.stimulus
                if not stimulus.stop or scenario % 2:
                    game.steer(stopswitch.answer(stimulus) if scenario != 3 else tick % 2)
            phase = {"playing": 1, "judged": 2}[game.phase]
            marks = sum(1 << index for index, correct in enumerate(game.marks) if correct)
            yield (f"{phase} {game.trial} {game.rung} {game.k} {sum(game.marks)} {marks} "
                   f"{int(game.showing)} {int(game.ring_up)} {game.shown_at:.9f}")


def main():
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    deal_rows = list(deals())
    session_rows = list(sessions())
    expected = deal_rows + session_rows
    for index, (line, wanted) in enumerate(zip(actual, expected)):
        assert line == wanted, (index, line, wanted)
    assert len(actual) == len(expected), (len(actual), len(expected))
    assert sum(row.startswith("done ") for row in actual) == 4
    print(f"PASS: 280 Stop & Switch deals and {len(session_rows)} clocked states match Python")


if __name__ == "__main__":
    main()
