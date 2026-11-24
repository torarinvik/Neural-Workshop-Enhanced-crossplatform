"""Compare Python's seeded Glider courses, motion, trails and verdicts."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import glider


def equal(values, expected, context):
    assert len(values) == len(expected), context
    for actual, wanted in zip(map(float, values), expected):
        assert math.isclose(actual, wanted, rel_tol=1e-10, abs_tol=1e-10), (context, actual, wanted)


def check_state(records, run, context):
    result = hit = 0
    if run.result:
        passed, message = run.result
        result = 1 if passed else (2 if message.endswith("floor") else (3 if message.endswith("roof") else 4))
        if result == 4:
            hit = int(message.rsplit(" ", 1)[1])
    equal(next(records).split(), [
        run.t, run.y, run.vy, run.gust(), run.lifting, run.passed, result, hit, len(run.trail)
    ], context)
    for point in run.trail:
        equal(next(records).split(), point, context)
    return result


def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    cases = 0
    outcomes = set()
    for line in records:
        rung, seed, count, gust_seed = map(int, line.split())
        course = glider.deal(rung, seed)
        context = rung, seed
        assert (count, gust_seed) == (len(course.walls), course.gust_seed), context
        for wall in course.walls:
            equal(next(records).split(), wall, context)
        run = glider.Run(course)
        for tick in range(480):
            run.step(1 / 120, glider.UP if tick % 72 < 27 else None)
            if tick % 32 == 31:
                check_state(records, run, (*context, tick))
        run = glider.Run(course)
        while run.result is None:
            ports = glider.autopilot(run)
            run.step(1 / 60, ports[0] if ports else None)
        outcomes.add(check_state(records, run, (*context, "pilot")))
        cases += 1
    assert cases == 202 and 1 in outcomes and len(outcomes) > 1, (cases, outcomes)
    print(f"Glider matched {cases} seeded courses and {cases * 16:,} flight states, including trails and verdicts")


if __name__ == "__main__":
    main()
