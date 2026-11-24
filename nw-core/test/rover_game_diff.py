"""Replay Rover's original 120 Hz controller against Elisa."""
from math import ceil
from random import Random
import subprocess
import sys

from rover_diff import compare, rover


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    draw = Random(17)
    run = rover.Run(rover.deal(4, rng=draw))
    phase, rung, trial, total, wins, best, start, adaptive = 1, 4, 1, 3, 0, 0, 4, 1
    result = 0
    last = 0.0
    snapshots = 0

    def emit():
        nonlocal snapshots
        if phase in (1, 2):
            seen = run.seen()
            metrics = (run.reached, run.level.flags, len(run.queue),
                       *(round(v * 1000) for v in (run.t, rover.delay_at(run.g, run.t),
                                                   run.state.x, run.state.z, *seen)))
        else:
            metrics = (0,) * 11
        compare(rows, "state", (phase, rung, trial, total, wins, best, start, adaptive, result, *metrics),
                (phase, trial, snapshots))
        snapshots += 1

    def tick(now, port=None):
        nonlocal last, phase, result, rung, wins, best
        dt = min(0.1, now - last)
        last = now
        substeps = max(1, ceil(dt / (1 / 120)))
        for _ in range(substeps):
            run.step(dt / substeps, port)
            if run.result is not None:
                passed, message = run.result
                result = 1 if passed else 2 if message == "Hit a rock" else 4
                if passed:
                    wins += 1
                    best = max(best, rung)
                rung = max(1, rung + (1 if passed else -1)) if adaptive else rung
                phase = 2
                break
        emit()

    emit()
    for index in range(1, 121):
        port = (rover.DRIVE if index < 11 else rover.BRAKE if index == 17 else
                rover.RIGHT if index < 21 else None)
        tick(index * 0.125, port)
    for x, z in run.g.flags:
        run.state = rover.State(x, z, 0.0, 0.0)
        tick(15.0)
    assert phase == 2 and result == 1
    phase, trial, result, last = 1, 2, 0, 17.5
    run = rover.Run(rover.deal(rung, rng=draw))
    emit()
    run.t = run.g.seconds + 1.0
    tick(17.5)
    assert result == 4
    phase, trial, result = 1, 3, 0
    run = rover.Run(rover.deal(rung, rng=draw))
    emit()
    x, z, _ = run.g.rocks[0]
    run.state = rover.State(x, z, 0.0, 0.0)
    tick(17.5)
    assert result == 2
    phase = 3
    emit()
    phase, rung, trial, total, wins, best, start, adaptive, result = 1, 1, 1, 1, 0, 0, 1, 0, 0
    run = rover.Run(rover.deal(rung, rng=draw))
    emit()
    assert next(rows, None) is None
    print(f"PASS: {snapshots} Rover session snapshots match Python, including restart and three terminal verdicts")


if __name__ == "__main__":
    main(sys.argv[1])
