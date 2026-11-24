"""Compare seeded Drone Hoops courses, cameras and flight physics."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import dronehoops


def compare(row, expected, case):
    values = list(map(float, row.split()))
    assert len(values) == len(expected), case
    for got, want in zip(values, expected):
        assert math.isclose(got, want, abs_tol=2e-9, rel_tol=2e-9), (case, got, want)


def state(run):
    result = 0 if run.result is None else (1 if run.result[0] else (3 if run.result[1] == "Out of time" else 2))
    return [run.t, run.cam, run.next, run.bumps, result, *run.p, *run.v, *run.thrust, *run.eye, *run.look]


def main():
    rows = iter(subprocess.check_output([sys.argv[1]], text=True, timeout=120).splitlines())
    count = 0
    verdicts = set()
    for row in rows:
        rung, seed, valid = map(int, row.split())
        course = dronehoops.deal(rung, seed)
        case = rung, seed
        assert bool(valid) == bool(course), case
        if course is None:
            continue
        compare(next(rows), [len(course.hoops), len(course.gusts), len(course.birds),
                             len(course.flashes), len(course.cuts), course.decoy, course.seed, *course.circle], case)
        for hoop in course.hoops:
            compare(next(rows), [*hoop.centre, hoop.yaw, hoop.radius, *hoop.bob, hoop.spin], case)
        for gust in course.gusts:
            compare(next(rows), gust, case)
        for bird in course.birds:
            compare(next(rows), [bird.t, bird.dur, *bird.a, *bird.b], case)
        for flash in course.flashes:
            compare(next(rows), [flash], case)
        for cut in course.cuts:
            compare(next(rows), cut, case)
        run = dronehoops.Run(course)
        for i in range(720):
            run.aim = (4.0, 2.0) if i % 70 < 15 else None
            run.aim_y = 6.0 if i % 70 < 15 else None
            run.step(1 / 60, [] if i % 70 < 25 else [i // 23 % 10, i // 71 % 10])
            if i % 60 == 59:
                compare(next(rows), state(run), (*case, i))
        run = dronehoops.Run(course)
        while run.result is None:
            run.step(1 / 30, dronehoops.autopilot(run))
        compare(next(rows), state(run), (*case, "pilot"))
        verdicts.add(state(run)[4])
        run = dronehoops.Run(course)
        while run.result is None:
            run.step(1 / 30)
        compare(next(rows), state(run), (*case, "idle"))
        verdicts.add(state(run)[4])
        count += 1
    assert count == 48 and {1, 3} <= verdicts, (count, verdicts)
    print(f"Drone Hoops matched {count} Python courses and {count * 14} flight states")


if __name__ == "__main__":
    main()
