"""Compare live Drone Hoops cue times, spatial parameters and instrument seeds."""
from pathlib import Path
import subprocess
import sys

from drone_hoops_diff import compare

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import dronehoops


def main():
    rows = iter(subprocess.check_output([sys.argv[1]], text=True, timeout=60).splitlines())
    flights = cues = 0
    voices = set()
    for row in rows:
        rung, guided, count = map(int, row.split())
        run = dronehoops.Run(dronehoops.deal(rung, 17))
        while run.result is None:
            run.step(1 / 30, dronehoops.autopilot(run) if guided else dronehoops.FORWARD)
        assert count == len(run.notes), (rung, count, len(run.notes))
        for index, note in enumerate(run.notes):
            compare(next(rows), [note.t, note.dur, note.freq, note.pan, note.gain,
                                 note.bright, note.voice, note.seed], (rung, index))
            voices.add(note.voice)
        flights += 1
        cues += count
    assert flights == 4 and voices == set(range(7)), (flights, voices)
    print(f"Drone Hoops matched {cues:,} Python sound cues across all seven voices")


if __name__ == "__main__":
    main()
