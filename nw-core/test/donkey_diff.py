#!/usr/bin/env python3
"""Differential harness: tasks/donkey.elisa vs the real
neural_workshop/donkey.py.

Drives the ACTUAL module: GRADES, `feasible`, `generate`, `survivable`, and a
driven replay through `steer` and `beat`.

The generator's dice sit behind a SHORT-CIRCUITING `and`:

    if (blocked[at] is None and at >= free_from and at + SPAN <= length
            and rng.random() < chance):

so `random()` is not called unless the three cheap tests already pass. Drawing
first and testing after spends a value on every sub-row instead of a few, and
lays a completely different road that still looks entirely like a road. Only a
sub-row-by-sub-row comparison of the whole road shows it, which is what the
`road` rows are.

`feasible` is compared as a BITMASK. The port keeps the surviving states packed
into one integer rather than as a set, which is safe precisely because the
reference never iterates those sets for order -- it only tests them for
emptiness and rebuilds them. Encoding the reference's frozenset the same way
makes that equivalence checkable rather than assumed.
"""
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/"
       "Neural-Workshop-Enhanced-crossplatform/original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import donkey as ref  # noqa: E402


def row(*values):
    return ",".join(str(v) for v in values)


def mask_of(alive, crossing):
    """The port's packing: bit (lane * (crossing + 1) + owed)."""
    mask = 0
    for lane, owed in alive:
        mask |= 1 << (lane * (crossing + 1) + owed)
    return mask


def grade_lines(out):
    for level in (-2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 40):
        g = ref.GRADES[max(0, min(len(ref.GRADES) - 1, level - 1))]
        out.append(row("grd", level, g.rows, round(g.density * 10000),
                       g.swerve, g.crossing))


def feasible_lines(out):
    for swerve in (1, 2, 3):
        crossing = swerve * ref.SUB
        for lane_start in (0, 1):
            for lane in (-1, 0, 1):
                alive = ref.states(lane_start)
                masks = []
                for _step in range(8):
                    alive = ref.feasible(alive, None if lane < 0 else lane,
                                         crossing)
                    masks.append(mask_of(alive, crossing))
                out.append(row("feas", swerve, lane_start, lane, *masks))


def road_lines(out):
    for level in range(1, 11):
        for seed in (0, 1, 7, 42, 1234):
            road = ref.generate(level, seed=seed)
            flat = []
            for at, lane in road.beasts:
                flat += [at, lane]
            flat += [-1 if lane is None else lane for lane in road.blocked]
            out.append(row("road", level, seed, road.start, road.length,
                           len(road.beasts), int(ref.survivable(road)), *flat))


def drive_lines(out):
    for level in (1, 3, 5, 6, 8, 10):
        for seed in (1, 7, 1234):
            for style in (0, 1, 2):
                road = ref.generate(level, seed=seed)
                car = ref.Car(road.start, road.grade.swerve)
                ends = road.ends
                trace = []
                tick = 0
                while tick < road.length and not ref.over(car, road):
                    if style == 0:
                        port = ref.SWITCH
                    elif style == 1:
                        port = ref.SWITCH if tick % 4 == 0 else ref.HOLD
                    else:
                        port = ref.SWITCH if tick % 9 == 0 else ref.HOLD
                    ref.steer(car, port)
                    ref.beat(car, road, ends)
                    trace += [car.lane, car.crossing]
                    tick += 1
                out.append(row("drive", level, seed, style, *trace, car.at,
                               car.passed, int(car.hit),
                               int(ref.cleared(car, road))))


def plan_lines(out):
    for level in (1, 6, 10):
        for seed in (0, 1, 7, 42, 1234):
            road = ref.generate(level, seed=seed)
            plan = ref.line(road)
            out.append(row("line", level, seed, int(plan is not None),
                           len(plan or []), *(plan or [])))
            for look in (ref.SUB, road.grade.crossing):
                presses = ref.dodge(road, look)
                car = ref.drive(road, presses)
                out.append(row("dodge", level, seed, look, 1,
                               len(presses), *presses, car.at, car.passed,
                               int(car.hit), int(ref.cleared(car, road))))


def python_lines():
    out = []
    grade_lines(out)
    feasible_lines(out)
    road_lines(out)
    drive_lines(out)
    plan_lines(out)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g[:180]}\n  python: {w[:180]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
