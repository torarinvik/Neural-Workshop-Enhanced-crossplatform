"""Compare Rover's terrain candidates and fractional-thrust state updates."""
from random import Random
import subprocess
import sys
from unittest.mock import patch

from crane_diff import compare
from neural_workshop import rover


def terrain(rows, g, where):
    level = g.level
    compare(rows, "ground", (*level[:5], *map(float, level[5:]), g.seconds, len(g.delays)), where)
    for wave in g.waves:
        compare(rows, "wave", wave, where)
    for flag in g.flags:
        compare(rows, "flag", flag, where)
    for rock in g.rocks:
        compare(rows, "rock", rock, where)
    for delay in g.delays:
        compare(rows, "delay", (delay,), where)
    compare(rows, "edges", (rover.delay_at(g, -5), rover.delay_at(g, g.seconds + 100)), where)


def replay(rows, g, where):
    state = rover.State(0.0, 0.0, 0.0, 0.0)
    for i in range(480):
        pattern = i // 40 % 6
        controls = {
            rover.DRIVE: 1.0 if pattern < 2 else 0.3 if pattern == 3 else 0.0,
            rover.BRAKE: 1.0 if pattern == 4 else 0.4 if pattern == 3 else 0.0,
            rover.LEFT: 0.6 if pattern in (1, 5) else 0.0,
            rover.RIGHT: 0.5 if pattern == 3 else 0.0,
        }
        state = rover.advance(g, state, controls, 1 / (30 if i % 2 == 0 else 120))
        height = rover.height(g, state.x, state.z)
        slope = rover.slope(g, state.x, state.z, state.heading)
        compare(rows, "tick", (*state, float(height), slope), (*where, i))


def compare_run(rows, run, port, where):
    result = 0
    if run.result is not None:
        passed, message = run.result
        result = 1 if passed else {"Hit a rock": 2, "Tipped over on a slope": 3}.get(message, 4)
    cue_time = run.notes[-1].t if run.notes else -1.0
    compare(rows, "run", (port, run.t, *run.state, *run.seen(), len(run.queue), len(run.history),
                          run.reached, result, len(run.notes), cue_time), (*where, run.t))
    return result



def delayed(rows, g, mode):
    compare(rows, "delayed", (mode,), mode)
    run = rover.Run(g)

    def step(dt, port):
        run.step(dt, port if port >= 0 else None)
        return compare_run(rows, run, port, (mode,))

    if mode == 0:
        for i in range(5100):
            port = (i // 29) % 5 - 1
            if step(0.012 if i % 3 == 0 else 1 / 120, port):
                break
        assert i == 5099 and len(run.history) < 4000
        return i + 1
    if mode == 1:
        for x, z in g.flags:
            run.state = rover.State(x, z, 0.0, 0.0)
            result = step(0, -1)
        assert result == 1
        return len(g.flags)
    if mode == 2:
        x, z, _ = g.rocks[0]
        run.state = rover.State(x, z, 0.0, 0.0)
    elif mode == 3:
        run.state = rover.State(5.0, -17.0, 2.0, 0.5)
    else:
        run.t = g.seconds + 0.1
    assert step(0, -1) == mode
    return 1


def route(rows, g, where):
    path = rover.route(g)
    compare(rows, "route", (len(path),), where)
    for point in path:
        compare(rows, "waypoint", point, where)


def deal_trace(rows, rung):
    where = (rung, "deal")
    compare(rows, "deal", (rung,), where)
    draw = Random(17)
    ground = rover.deal(rung, rng=draw)
    terrain(rows, ground, where)
    compare(rows, "draw", (draw.random(),), where)
    route(rows, ground, where)
    run = rover.Run(ground)
    ticks = 0
    while run.result is None:
        ports = rover.autopilot(run)
        port = ports[0] if ports else -1
        run.step(1 / 30, ports[0] if ports else None)
        compare_run(rows, run, port, (*where, ticks))
        ticks += 1
    assert run.result[0], where
    return ticks


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in (0, 1, 2, 4, 6, 7, 10, 12, 13, 20, 30, 40, 60):
        for seed in (0, 17, 42):
            draw = Random(seed)
            compare(rows, "case", (rung, seed), (rung, seed))
            for index in range(3):
                # Read each candidate straight from Python's generator without screening it.
                with patch.object(rover, "play", side_effect=[(True, ""), (False, "")]):
                    g = rover.deal(rung, rng=draw)
                terrain(rows, g, (rung, seed, index))
                if index == 0:
                    replay(rows, g, (rung, seed))
                    if seed == 17:
                        route(rows, g, (rung, seed))
    with patch.object(rover, "play", side_effect=[(True, ""), (False, "")]):
        ground = rover.deal(13, seed=17)
    delayed_ticks = sum(delayed(rows, ground, mode) for mode in range(5))
    pilot_ticks = sum(deal_trace(rows, rung) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30))
    with patch.object(rover, "play", side_effect=[(True, ""), (False, "")]):
        ground = rover.deal(4, seed=17)
    blocked = ground._replace(rocks=((0.0, 0.0, 5.0), *ground.rocks[1:]))
    assert not rover.route(blocked)
    route(rows, blocked, ("blocked",))
    assert next(rows, None) is None
    print(f"PASS: 117 Rover terrains, 18,720 motion updates, and {delayed_ticks:,} delayed-control ticks match Python. "
          f"23 routes and {pilot_ticks:,} pilot ticks match, including nine screened deals.")


if __name__ == "__main__":
    main(sys.argv[1])
