"""Compare cave geometry, flight, lighting, and live notes against Python."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import echocave


def compare(values, wanted, case):
    assert len(values) == len(wanted), case
    for actual, expected in zip(map(float, values), wanted):
        assert math.isclose(actual, expected, abs_tol=1e-10, rel_tol=1e-10), (case, actual, expected)


def state(run):
    result = 0 if run.result is None else (1 if run.result[0] else (2 if run.result[1] == "Hit the rock" else 3))
    return [run.t, run.z, run.x, run.y, run.vx, run.vy, run.lit(), sum(run.caught),
            sum(1 << index for index, caught in enumerate(run.caught) if caught), result]


def main():
    rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    count = notes = 0
    verdicts = set()
    for header in rows:
        rung, seed, moths, flutter = map(int, header.split())
        case = rung, seed
        cave = echocave.deal(*case)
        assert (moths, flutter) == (len(cave.moths), cave.flutter), case
        for wave in (*cave.waves, *cave.waves_y, (0.18, *cave.width)):
            compare(next(rows).split(), wave, case)
        for moth in cave.moths:
            compare(next(rows).split(), moth, case)
        run = echocave.Run(cave)
        for tick in range(1440):
            if tick % 9 == 0:
                run.click()
            run.aim = (-1.4, 0.6) if tick % 60 < 25 else None
            run.step(1 / 120, [] if tick % 60 < 40 else [tick // 37 % 8, tick // 81 % 8])
            if tick % 96 == 95:
                compare(next(rows).split(), state(run), (*case, tick))
        verdicts.add(state(run)[-1])
        run = echocave.Run(cave)
        while run.result is None:
            ports = echocave.autopilot(run)
            if echocave.CLICK in ports:
                run.click()
            run.step(1 / 60, [port for port in ports if port != echocave.CLICK])
        compare(next(rows).split(), state(run), (*case, "pilot"))
        verdicts.add(state(run)[-1])
        assert int(next(rows)) == len(run.notes), case
        for n in run.notes:
            compare(next(rows).split(), [n.t, n.dur, n.freq, n.pan, n.gain, n.bright, n.voice], (*case, n.seed))
        count += 1
        notes += len(run.notes)
    assert count == 107 and {1, 2} <= verdicts, (count, verdicts)
    print(f"Echo Cave matched {count} Python caves, {count * 16:,} flight states, and {notes:,} sound cues")


if __name__ == "__main__":
    main()
