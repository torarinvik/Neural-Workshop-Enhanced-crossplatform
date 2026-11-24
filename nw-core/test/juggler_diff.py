"""Compare seeded Juggler acts and physics against the original Python model."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import juggler  # noqa: E402


def compare(line, expected, context):
    values = list(map(float, line.split()))
    assert len(values) == len(expected), context
    for got, want in zip(values, expected):
        assert math.isclose(got, want, rel_tol=2e-11, abs_tol=2e-11), (context, got, want)


def state(run):
    verdict = 0 if run.result is None else (1 if run.result[0] else 2)
    fields = [run.t, run.x, run.v, verdict, len(run.flashes)]
    for ball in run.balls:
        fields += [ball.x, ball.y, ball.vx, ball.vy, ball.live, ball.catches, len(ball.trail)]
    return fields


def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    count = 0
    catches = 0
    results = set()
    for row in records:
        rung, seed, balls, gust, *params = row.split()
        context = int(rung), int(seed)
        act = juggler.deal(*context)
        assert (int(balls), int(gust)) == (act.level.balls, act.draught_seed), context
        compare(" ".join(params), (act.level.tray, act.level.draught, act.level.seconds), context)
        for (onset, x), weight in zip(act.drops, act.weights):
            compare(next(records), (onset, x, weight), context)
        run = juggler.Run(act)
        for frame in range(640):
            port = juggler.LEFT if frame % 40 < 12 else (juggler.RIGHT if frame % 40 < 24 else None)
            run.step(1 / 120, port)
            if frame % 16 == 15:
                compare(next(records), state(run), (context, frame))
        run = juggler.Run(act)
        while run.result is None:
            controls = juggler.autopilot(run)
            run.step(1 / 60, controls[0] if controls else None)
        compare(next(records), state(run), (context, "pilot"))
        catches += sum(ball.catches for ball in run.balls)
        results.add(run.result[0])
        count += 1
    assert count == 12 and catches > 0 and True in results
    print(f"Juggler matched {count} Python acts, {count * 40} scripted states, and pilot results with {catches} catches")


if __name__ == "__main__":
    main()
