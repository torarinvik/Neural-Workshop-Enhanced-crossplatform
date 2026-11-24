"""Compare Docking approach generation, simultaneous thrust, and pilot traces."""
from math import pi
from random import Random
import subprocess
import sys

from crane_diff import compare
from neural_workshop import docking


def build(level, draw):
    x, y = (draw.choice((-1, 1)) * magnitude * draw.uniform(0.7, 1)
            for magnitude in level.lateral)
    angles = tuple(draw.choice((-1, 1)) * level.nose * draw.uniform(0.6, 1)
                   for _ in range(2))
    roll = draw.uniform(-0.3, 0.3) if level.station else 0.0
    spin = tuple(draw.uniform(-1, 1) * level.spin for _ in range(3))
    roll0 = draw.uniform(0, 2 * pi) if level.station else 0.0
    return docking.Approach(level, (x, y, -level.far), (0.0, 0.0, level.drift),
                            (*angles, roll), spin, roll0)


def compare_approach(rows, ap, where):
    g = ap.level
    compare(rows, "grade", (g.rung, *g.lateral, *map(float, g[2:7]), int(g.readouts), *g[8:]), where)
    fields = (*ap.pos, *ap.vel, *ap.att, *ap.spin, ap.roll0, ap.fuel)
    compare(rows, "approach", tuple(map(float, fields)), where)


def replay(rows, ap, mode, where):
    run = docking.Run(ap)
    if mode == 3:
        run.pos[:] = [1.0, 0.0, 0.0]
        run.vel[:] = [0.0, 0.0, 2.0]
        run.att[:] = [0.3, 0.0, run.station_roll() + 0.3]
    if mode == 4:
        run.pos[:] = [0.0, 0.0, -ap.level.far - 16.0]
    tick, result, problems = 0, 0, 0
    while run.result is None and (mode != 2 or tick < 600):
        mask = 0
        if mode == 1:
            mask = sum(1 << port for port in docking.autopilot(run))
        if mode == 2:
            mask = (0, 1041, 288, 4095)[tick // 37 % 4]
        run.step(1 / 30, [port for port in range(docking.PORTS) if mask & (1 << port)])
        if run.result is not None:
            success, message = run.result
            result = 1 if success else 3 if message == "Drifted away" else 2
            problems = sum(1 << index for index, clue in enumerate(("off centre", "too fast", "nose", "rolled"))
                           if clue in message)
        compare(rows, "tick", (mask, run.t, *run.pos, *run.vel, *run.att, *run.spin, run.fuel,
                              run.station_roll(), run.roll_error(), result, problems), (*where, tick))
        tick += 1
    if mode in (1, 3, 4):
        assert (result, problems) == {1: (1, 0), 3: (2, 15), 4: (3, 0)}[mode], where
    return tick


def main():
    rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    cases = [(rung, seed, 0) for rung in (0, 1, 2, 4, 6, 7, 10, 12, 13, 16, 20, 30, 60)
             for seed in (0, 17, 42)]
    cases += [(rung, 17, 1) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    cases += [(rung, 42, 2) for rung in (1, 7, 16, 30)] + [(16, 17, 3), (16, 17, 4)]
    total_ticks = 0
    for where in cases:
        rung, seed, mode = where
        compare(rows, "case", where, where)
        if mode == 0:
            draw = Random(seed)
            for _ in range(3):
                compare_approach(rows, build(docking.grade(rung), draw), where)
            continue
        ap = docking.deal(rung, seed=seed) if mode == 1 else build(docking.grade(rung), Random(seed))
        compare_approach(rows, ap, where)
        total_ticks += replay(rows, ap, mode, where)
    assert next(rows, None) is None
    print(f"PASS: {len(cases)} Docking cases, 117 candidates, and {total_ticks:,} ticks")


if __name__ == "__main__":
    main()
