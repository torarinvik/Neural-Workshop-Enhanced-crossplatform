"""Replay the screened Morning Round deals, pilots, verdicts, and cues."""
from random import Random
import subprocess
import sys

from morning_round_diff import compare, morninground as model


def result_code(result):
    if result is None:
        return 0
    passed, message = result
    if passed:
        return 1
    if message.startswith("Out of time"):
        return 2
    if message.startswith("Too many complaints"):
        return 3
    assert message == "Three falls: the round is off"
    return 4


def compare_tick(rows, run, port, where):
    compare(rows, "tick", (port, run.t, run.s, run.x, run.v, run.papers, len(run.flying),
                           run.passed, run.mistakes, run.falls, result_code(run.result),
                           run.down_until, run.last_throw, len(run.known), len(run.notes)), where)
    for paper in run.flying:
        compare(rows, "paper", paper, where)


def replay(rows, rung, policy):
    where = (rung, policy)
    compare(rows, "case", where, where)
    draw = Random(17)
    street = model.deal(rung, rng=draw)
    compare(rows, "deal", (street.papers, street.seconds, len(street.things), draw.random()), where)
    run = model.Run(street)
    ticks = 0
    if policy in (3, 4):
        if policy == 3:
            run.t = run.end
        else:
            run.t = run.level.brief
            thing = street.things[0]
            run.s, run.x, run.falls = run.thing_d(thing), thing.x, 2
        run.step(0.0)
        compare_tick(rows, run, -1, where)
        assert result_code(run.result) == (2 if policy == 3 else 4)
        ticks = 1
    else:
        pilot = (model.autopilot, model.every_house, model.stubborn)[policy]
        while run.result is None:
            ports = pilot(run)
            port = ports[0] if ports else None
            if port in model.EVENTS:
                model.act(run, port)
            run.step(1 / 60, port)
            compare_tick(rows, run, -1 if port is None else port, (*where, ticks))
            if ticks % 60 == 0:
                weights = model.believed(run, run.block_at(run.s))
                for index in range(len(street.deck)):
                    compare(rows, "belief", (weights.get(index, 0.0),), (*where, ticks, index))
            ticks += 1
        assert run.result[0] == (policy == 0)
    for h in street.houses:
        compare(rows, "house", ((None, "ok", "wrong", "missed").index(run.got.get(h.i)),
                                int(h.i in run.known)), where)
    for index in range(len(street.things)):
        compare(rows, "hit", (int(index in run.hit),), where)
    for cue in run.notes:
        compare(rows, "cue", (cue.t, cue.dur, cue.freq, cue.voice, cue.gain, cue.pan), where)
    return ticks


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = [(rung, 0) for rung in (1, 3, 5, 7, 9, 11, 12, 16, 20, 25, 30)]
    cases += [(12, policy) for policy in (1, 2, 3, 4)]
    ticks = sum(replay(rows, *case) for case in cases)
    assert next(rows, None) is None
    print(f"PASS: {len(cases)} Morning Round replays match Python across {ticks:,} ticks")


if __name__ == "__main__":
    main(sys.argv[1])
