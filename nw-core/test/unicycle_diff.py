"""Replay Python's seeded tracks, contact physics, and reference rider."""
from random import Random
import subprocess
import sys

from crane_diff import compare
from neural_workshop import unicycle


FAILURES = {"Head over heels": 2, "Fell off": 3}


def terrain(rows, track, where):
    g = track.level
    compare(rows, "track", (*g, len(track.xs), track.finish, track.seconds, track.best), where)
    for x, y in zip(track.xs, track.ys):
        compare(rows, "height", (x, y, unicycle.ground(track, x + 0.125)), where)


def state(rows, run, where):
    result = 0 if run.result is None else 1 if run.result[0] else FAILURES.get(run.result[1], 4)
    compare(rows, "tick", (run.last if run.last is not None else -1, run.t, *run.body,
                          *unicycle.head(run.body), unicycle.tilt(run.body), result), where)
    return result


def replay(rows, track, where, pilot):
    run = unicycle.Run(track)
    tick = 0
    while run.result is None and (pilot or tick < 720):
        port = unicycle.steer(track, run.body) if pilot else tick // 5 % 9 - 1
        run.step(1 / (30 if pilot else 120), None if port == -1 else port)
        state(rows, run, (*where, tick))
        tick += 1
    compare(rows, "end", (tick,), where)
    if pilot:
        assert run.result[0], where
    return tick


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    ticks = 0
    for rung in (0, 1, 2, 4, 6, 7, 10, 12, 13, 16, 20, 30, 60):
        for seed in (0, 17, 42):
            where = rung, seed
            compare(rows, "candidate", where, where)
            draw = Random(seed)
            g = unicycle.grade(rung)
            for index in range(3):
                xs, ys, finish = unicycle._shape(g, draw)
                track = unicycle.Track(g, tuple(xs), tuple(ys), finish, 600.0, 0.0)
                terrain(rows, track, (*where, index))
                if index == 0:
                    ticks += replay(rows, track, where, False)
    for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30):
        where = (rung, 17)
        compare(rows, "deal", where, where)
        draw = Random(17)
        track = unicycle.deal(rung, rng=draw)
        terrain(rows, track, where)
        compare(rows, "draw", (draw.random(),), where)
        ticks += replay(rows, track, where, True)
    for mode in (2, 3, 4):
        compare(rows, "edge", (mode,), mode)
        run = unicycle.Run(unicycle.deal(1, seed=17))
        if mode == 2:
            run.body = run.body._replace(qy=0.1)
        elif mode == 3:
            run.body = run.body._replace(py=-0.4, qy=0.08)
        else:
            run.t = 600.1
        run.step(0)
        assert state(rows, run, ("edge", mode)) == mode
        ticks += 1
    assert next(rows, None) is None
    print(f"PASS: 117 Unicycle track candidates, nine screened deals, and {ticks:,} ticks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
