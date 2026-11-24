"""Compare Lander terrain, integration, and verdicts with Python."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import lander  # noqa: E402


def equal(values, expected, context, tolerance=2e-10):
    assert len(values) == len(expected), context
    for got, want in zip(map(float, values), expected):
        assert math.isclose(got, want, rel_tol=tolerance, abs_tol=tolerance), (context, got, want)


def state(craft):
    verdict = 0
    if craft.result:
        text = craft.result[1]
        verdict = next(code for code, label in enumerate((
            "", "Landed", "Flew off", "Out of time", "Came down", "Too fast down", "Too fast across", "Tilted"
        )) if label and text.startswith(label))
    return [craft.t, craft.x, craft.y, craft.vx, craft.vy, craft.angle,
            craft.fuel if craft.fuel is not None else -1, craft.firing, verdict]


def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    courses = 0
    outcomes = set()
    for header in records:
        rung, seed, count, *values = header.split()
        context = int(rung), int(seed)
        flight = lander.deal(*context)
        equal(values, [flight.gravity, flight.ratio, flight.pad_x, flight.pad_y, flight.start[0],
                       flight.start[2], flight.wind, flight.wind_phase], context)
        assert len(flight.ground) == int(count), context
        for point in flight.ground:
            equal(next(records).split(), point, context)
        craft = lander.Craft(flight)
        for tick in range(720):
            port = (tick // 40) % 6 - 1
            craft.step(1 / 120, port if port >= 0 else None)
            if tick % 16 == 15:
                equal(next(records).split(), state(craft), (context, tick))
        craft = lander.Craft(flight)
        while not craft.result:
            craft.step(1 / 60, lander.autopilot(craft))
        expected = state(craft)
        equal(next(records).split(), expected, (context, "pilot"), tolerance=1e-8)
        outcomes.add(expected[-1])
        courses += 1
    assert courses == 254 and 1 in outcomes and len(outcomes) > 1, (courses, outcomes)
    print(f"Lander matched {courses} seeded flights, {courses * 45:,} scripted states, and {len(outcomes)} reference-pilot outcomes")


if __name__ == "__main__":
    main()
