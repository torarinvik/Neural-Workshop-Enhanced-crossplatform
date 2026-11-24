"""Compare Ferry's Python seeds, reference skipper, and clocked state."""
from pathlib import Path
from random import Random
import subprocess
import sys

from crane_diff import compare

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import ferry

FAILURES = {
    "The ferry ran hard aground": 2,
    "Swept out of the harbour": 3,
    "The ferry struck a barge": 4,
    "Out of time": 5,
}


def compare_river(rows, river, where):
    compare(rows, "river", (*river.level, river.gust_seed), where)
    for pier in river.piers:
        compare(rows, "pier", pier, where)
    for barge in river.barges:
        compare(rows, "lane", barge, where)


def replay(rows, river, mode, where):
    run = ferry.Run(river)
    if mode == 4:
        run.x = ferry.WORLD_W - 1.01
        run.heading = 0.0
    tick = result = 0
    while run.result is None and (mode != 3 or tick < 1200):
        if mode == 3:
            port = tick // 59 % 7 - 1
        elif mode == 4:
            port = ferry.AHEAD
        else:
            commands = ferry.autopilot(run)
            port = commands[0] if commands else -1
        run.step(1 / 30, port if port >= 0 else None)
        result = 0 if run.result is None else 1 if run.result[0] else FAILURES[run.result[1]]
        docked = -1.0 if run.docked_since is None else run.docked_since
        state = [port, run.t, run.x, run.y, run.heading, run.speed, *run.ground_velocity(),
                 run.gust(), run.leg, docked, run.thrusting, result, len(run.wake)]
        if run.wake:
            state.extend((*run.wake[0], *run.wake[-1]))
        state.extend(x for x, _, _ in run.barge_positions())
        compare(rows, "tick", state, (*where, tick))
        tick += 1
    return tick, result


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    ticks = candidates = runs = 0
    verdicts = set()
    for header in rows:
        label, *numbers = header.split()
        assert label == "case", header
        rung, seed, mode = where = tuple(map(int, numbers))
        draw = Random(seed)
        if mode == 0:
            for attempt in range(3):
                compare_river(rows, ferry._build(ferry.grade(rung), draw), (*where, attempt))
                candidates += 1
        else:
            river = ferry.deal(rung, seed=seed) if mode == 2 else ferry._build(ferry.grade(rung), draw)
            compare_river(rows, river, where)
            count, result = replay(rows, river, mode, where)
            ticks += count
            runs += 1
            verdicts.add(result)
        assert next(rows) == "end", where
    assert candidates == 99 and runs == 21 and verdicts == {1, 2, 3, 4, 5}
    print(f"PASS: {candidates + runs} Ferry cases match Python ({candidates} candidates, {ticks:,} ticks, verdicts {sorted(verdicts)})")


if __name__ == "__main__":
    main(sys.argv[1])
