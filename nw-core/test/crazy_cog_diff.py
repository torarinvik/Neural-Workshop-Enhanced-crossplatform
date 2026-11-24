"""Compare seeded Crazy Cog candidates, their geometry, and RNG state."""
from random import Random
import subprocess
import sys

from crane_diff import compare
from neural_workshop import crazycog

RUNGS = (0, 1, 4, 7, 10, 13, 16, 19, 20, 24, 28, 32, 40, 80)


def check_machine(lines, machine, draw, where):
    compare(lines, "deal", (len(machine.plan) if machine else 0, draw.random()), where)
    if not machine:
        return
    compare(lines, "machine", (machine.fan_way, *machine.fan_band, machine.chains, machine.lift,
                               machine.seconds, len(machine.walls), len(machine.tray)), where)
    for peg, plane in ((machine.motor, 0), (machine.winch, machine.winch_z), (machine.fan, machine.fan_z)):
        cog = next((c for c in machine.plan if peg == (c.x, c.y) and c.z == plane), (0., 0., 0., 0))
        compare(lines, "cog", cog, where)
    for wall in machine.walls:
        compare(lines, "wall", wall, where)
    for radius in machine.tray:
        compare(lines, "radius", (int(radius),), where)
    for cog in machine.plan:
        compare(lines, "cog", cog, where)
    for link in machine.plan_chains:
        for cog in link:
            compare(lines, "cog", cog, where)


def check_physics(lines, machine, policy, where):
    if policy == 1:
        machine = machine._replace(fan_way=-machine.fan_way)
    if policy == 2:
        machine = machine._replace(seconds=2.0)
    run = crazycog.Run(machine)
    if policy not in (2, 3):
        run.cogs = list(machine.plan)
        run.chains = list(machine.plan_chains)
    run._rewire()
    compare(lines, "rewire", (int(bool(run.ratio)), int(run.jammed)), where)
    tick = 0
    while run.result is None:
        if policy == 3:
            ports = crazycog.autopilot(run)
            port = ports[0] if ports else -1
            if port >= 0:
                crazycog.act(run, port)
            carry = -1 if run.carry == crazycog.CHAIN else int(run.carry or 0)
            compare(lines, "control", (port, run.hand.x, run.hand.y, int(run.hand.down),
                                        run.layer, carry, run.chain_stock, len(run.cogs), len(run.chains)), (where, tick))
        run.step(1 / 60)
        result = 0 if run.result is None else (1 if run.result[0] else
                 (2 if run.height >= machine.lift else 3))
        if tick % 8 == 0 or result:
            compare(lines, "tick", (tick, result, run.t, run.height, run.out, run.motor_speed(), run.fan_speed()), where)
            for cog in run.cogs:
                compare(lines, "turn", (run.ratio.get(cog, 0.), run.angle.get(cog, 0.)), where)
        tick += 1
    for cue in run.notes:
        compare(lines, "cue", (cue.t, cue.dur, cue.freq, cue.voice, cue.gain, cue.pan), where)
    assert next(lines) == "end"
    return tick


def main(binary):
    lines = iter(subprocess.check_output([binary], text=True).splitlines())
    actual_layers = set()
    accepted = ticks = 0
    for rung in RUNGS:
        grade = crazycog.grade(rung)
        compare(lines, "grade", (*grade[:2], int(grade.chains), *grade[3:]), rung)
        sampled = False
        for seed in range(1000):
            draw = Random(seed)
            machine = crazycog.build(grade, draw)
            check_machine(lines, machine, draw, (rung, seed))
            if machine:
                accepted += 1
                actual_layers.add(grade.layers)
                if not sampled:
                    sampled = True
                    ticks += check_physics(lines, machine, 0, (rung, seed, "train"))
                    if grade.rung == 1:
                        ticks += check_physics(lines, machine, 2, (rung, "empty board"))
                    if grade.rung == 20:
                        ticks += check_physics(lines, machine, 1, (rung, "reversed fan"))
        if grade.rung in (1, 10, 20, 32):
            draw = Random(17)
            try:
                machine = crazycog.deal(rung, rng=draw)
            except RuntimeError:
                machine = None
            check_machine(lines, machine, draw, (rung, "screened"))
            if machine is not None:
                ticks += check_physics(lines, machine, 3, (rung, "reference controls"))
    for jammed in (True, False):
        first, last = (30.0, 30.0) if jammed else (52.0, 22.0)
        motor = (130.0, 400.0)
        winch = (130.0 + first + last, 400.0)
        plan = (crazycog.Cog(*motor, first), crazycog.Cog(*winch, last))
        if jammed:
            plan += (crazycog.Cog(160.0, 451.9615242270663, 30.0),)
        machine = crazycog.Machine(crazycog.grade(20), motor, winch, None, 0, (0., 0.),
                                   (), (), 0, plan, (), 190., 1.)
        ticks += check_physics(lines, machine, 0, "jammed" if jammed else "stalled")
    assert next(lines, None) is None
    assert actual_layers == set(range(1, 6)), actual_layers
    print(f"PASS: {len(RUNGS) * 1000:,} Crazy Cog candidates across five planes match Python ({accepted:,} accepted)")


    print(f"PASS: {ticks:,} gear-train simulation ticks and sound cues match Python")


if __name__ == "__main__":
    main(sys.argv[1])
