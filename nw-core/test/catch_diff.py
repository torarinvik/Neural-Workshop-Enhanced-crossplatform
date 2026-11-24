"""Compare Catch's generated courts, trajectories and basket control to Python."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import catch
from neural_workshop.ui.lens import Lens


def check(values, expected, context):
    assert len(values) == len(expected), context
    for actual, wanted in zip(map(float, values), expected):
        assert math.isclose(actual, wanted, rel_tol=1e-10, abs_tol=1e-10), (context, actual, wanted)


def state(run):
    result = 0 if run.result is None else (1 if run.result[0] else 2)
    baskets = [coordinate for basket in run.baskets for coordinate in basket]
    fate = [0 if caught is None else (1 if caught else 2) for caught in run.fate]
    return [run.t, run.caught, run.missed, result, *baskets, *fate]



def projection(level, time):
    def camera(swing):
        eye = (-math.sin(swing) * 26.0, 12.0, 14.0 - math.cos(swing) * 26.0)
        return Lens(eye, (0.0, 0.0, 19.0), 1.0, 0.0, 0.0)

    points = ((-10, 0, 0), (10, 0, 0), (-10, 0, 40), (10, 0, 40),
              (0, 10.5, 22), (0, 3, 41))
    wide = math.radians(level.swing)
    frame = [point for angle in {-wide, wide, 0.0} for point in points if camera(angle).see(point)]
    lens = camera(wide * math.sin(0.3 * time)).fit(frame, 27.36, 179.0, 857.28, 389.0)
    return [lens.focal, lens.cx, lens.cy, *lens.see((-3.5, 0.6, 12.0))]

def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    courts = balls = 0
    outcomes = set()
    for row in records:
        rung, seed, count = map(int, row.split())
        context = rung, seed
        court = catch.deal(*context)
        assert len(court.balls) == count, context
        for ball in court.balls:
            check(next(records).split(), [ball.t0, ball.x0, *ball.v, ball.ax, ball.flight, *ball.land, ball.colour], context)
            for step in range(5):
                time = ball.t0 + ball.flight * step / 4
                check(next(records).split(), catch.where(ball, time, court.level.walls), context)
            balls += 1
        run = catch.Run(court)
        for index in range(3):
            check(next(records).split(), projection(court.level, index * 2.3), (*context, "camera", index))
        for tick in range(1440):
            if tick % 90 == 0:
                run.aim[run.mouse_basket()] = ((tick // 90 % 9 - 4) * 2.5, (tick // 90 % 8) * 2.5)
            run.step(1 / 120, tick // 20 % 8)
            if tick % 80 == 79:
                check(next(records).split(), state(run), (*context, tick))
        outcomes.add(run.result[0])
        run = catch.Run(court)
        while run.result is None:
            run.step(1 / 60, catch.autopilot(run))
        outcomes.add(run.result[0])
        check(next(records).split(), state(run), (*context, "pilot"))
        courts += 1
    assert courts == 110 and outcomes == {False, True}, (courts, outcomes)
    print(f"Catch matched {courts} seeded courts, {balls * 5:,} ball positions, and {courts * 19:,} basket and verdict states, plus {courts * 3} camera samples")


if __name__ == "__main__":
    main()
