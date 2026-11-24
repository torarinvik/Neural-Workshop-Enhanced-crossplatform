"""Compare Keep the Beat schedules, curtain transitions, and scoring to Python."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import beat  # noqa: E402


def verdict(run):
    hits, strays = run.score()
    passed, message = run.result
    kind = 1 if passed else (2 if message.endswith("needed") else 3)
    return hits, strays, kind, len(run.taps), message


def main():
    records = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    schedules = cases = 0
    outcomes = set()
    for header in records:
        rung, seed, cycle, count, window, end = header.split()
        context = int(rung), int(seed)
        song = beat.deal(*context)
        assert (int(cycle), int(count), float(window), float(end)) == (
            len(song.level.pattern), len(song.beats), song.level.window, song.end
        ), context
        probe = beat.Run(song)
        for index, expected in enumerate(song.beats):
            time, heard, before, after = next(records).split()
            assert float(time) == expected and bool(int(heard)) == song.heard[index], (context, index)
            probe.t = expected - 0.01
            assert bool(int(before)) == probe.curtain(), (context, index, "before")
            probe.t = expected
            assert bool(int(after)) == probe.curtain(), (context, index, "after")
        for mode in ("pilot", "mash", "idle"):
            run = beat.Run(song)
            if mode == "idle":
                run.step(song.end)
            else:
                tick = 0
                while run.result is None:
                    if beat.autopilot(run) if mode == "pilot" else tick % 7 == 0:
                        run.tap()
                    run.step(1 / 60)
                    tick += 1
            *numbers, message = next(records).split(" ", 4)
            actual = (*map(int, numbers), message)
            assert actual == verdict(run), (context, mode, actual, verdict(run))
            outcomes.add(actual[2])
            cases += 1
        schedules += 1
    assert schedules == 324 and outcomes == {1, 2, 3}, (schedules, outcomes)
    print(f"Keep the Beat matched {schedules} Python song schedules and {cases} scored runs")


if __name__ == "__main__":
    main()
