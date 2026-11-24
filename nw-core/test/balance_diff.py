"""Compare the Balance course selector and integrator with Python."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import balance  # noqa: E402


def values(actual, expected, context, tolerance=2e-10):
    assert len(actual) == len(expected), context
    for got, want in zip(actual, expected):
        assert math.isclose(got, want, rel_tol=tolerance, abs_tol=tolerance), (context, got, want)


def state(line, run, context, tolerance=2e-10):
    result = 0
    if run.result:
        passed, msg = run.result
        result = 1 if passed else {"The pole fell": 2, "The cart hit the buffers": 3, "Out of time": 4}[msg]
    values(list(map(float, line.split())), [run.t, run.x, run.v, run.theta, run.omega,
           run.flag, run.still, result, run.pushing], context, tolerance)


def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    tested = 0
    largest_finish_delta = 0.0
    for header in records:
        rung, seed, count, gust_seed, *grade = header.split()
        context = int(rung), int(seed)
        course = balance.deal(*context)
        assert int(count) == len(course.flags) and int(gust_seed) == course.gust_seed, context
        when, after = course.lengths[-1]
        values(list(map(float, grade)), [course.level.length, course.level.gusts, course.level.seconds, when, after], context)
        values(list(map(float, next(records).split())), course.flags, context)
        run = balance.Run(course)
        for tick in range(120):
            control = balance.RIGHT if tick % 17 < 8 else None if tick % 17 < 12 else balance.LEFT
            run.step(1 / 120, control)
            state(next(records), run, (context, tick))
        run = balance.Run(course)
        while not run.result:
            ports = balance.autopilot(run)
            run.step(1 / 60, ports[0] if ports else None)
        time, _x, _velocity, _theta, _omega, flags, _still, verdict, _pushing = map(float, next(records).split())
        passed, message = run.result
        expected = 1 if passed else {"The pole fell": 2, "The cart hit the buffers": 3, "Out of time": 4}[message]
        assert (int(flags), int(verdict)) == (run.flag, expected), (context, flags, verdict, run.flag, expected)
        largest_finish_delta = max(largest_finish_delta, abs(time - run.t))
        assert abs(time - run.t) < 0.35, (context, time, run.t)
        tested += 1
    assert tested == 177, tested
    print(f"Balance matched {tested} seeded courses, {tested * 120:,} control frames, and reference-pilot outcomes (max finish delta {largest_finish_delta:.4f} s)")


if __name__ == "__main__":
    main()
