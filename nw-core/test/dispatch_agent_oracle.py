"""Derive a clocked Dispatch replay from the windowless Python UI."""
from functools import lru_cache
import json
from random import Random

from dispatch_diff import Screen
from neural_workshop.ui.dispatch import FIRST_REFIT, FIRST_SLOT, FIRST_STATION


@lru_cache(maxsize=2)
def fixture(coach):
    screen = Screen()
    screen.rng = Random(17)
    screen.total_trials = 1
    screen.adaptive = False
    screen.coach = coach
    screen.start_run()
    orders = {1: 0, 2: FIRST_REFIT, 3: 1, 4: FIRST_STATION + 2,
              40: 1, 41: FIRST_SLOT}
    ticks = []
    while screen.phase == "running":
        tick = len(ticks) + 1
        assert tick < 1200
        # The default port targets the last incident slot and leaves the
        # simulation running whenever no unit is selected.
        port = orders.get(tick, FIRST_SLOT + 7)
        screen.press(port)
        screen.now += 100
        screen.update(0.1)
        verdict = screen.verdict_shown
        if screen.phase == "judged":
            ticks.append((port, 1 if verdict[0] else -1, verdict[1], True))
        elif verdict:
            ticks.append((port, 1 if verdict[0] else -1, verdict[1], False))
        else:
            ticks.append((port, 0, "", False))
    assert any(words == "Saved one" for _, _, words, _ in ticks) == coach
    assert any(words == "Lost one" for _, _, words, _ in ticks) == coach
    return ticks


if __name__ == "__main__":
    print(json.dumps({"sparse": fixture(False), "coached": fixture(True)}))
