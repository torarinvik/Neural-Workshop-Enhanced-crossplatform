"""Replay the Python Safecracker pilot against the Elisa port."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import safecracker


def check(actual, expected, label):
    fields = list(map(float, actual.split()))
    assert len(fields) == len(expected), label
    for got, want in zip(fields, expected):
        assert math.isclose(got, want, rel_tol=2e-9, abs_tol=2e-9), (label, got, want)


def compare(executable):
    rows = iter(subprocess.check_output([executable], text=True, timeout=120).splitlines())
    machines = states = cues = 0
    for header in rows:
        rung, seed, valid = map(int, header.split())
        case = rung, seed
        try:
            safe = safecracker.deal(rung, seed)
        except RuntimeError:
            assert not valid, case
            continue
        assert valid, case
        check(next(rows), [*safe.lamps, safe.bolts, safe.seed, safe.level.seconds], case)
        assert tuple(map(int, next(rows).split())) == safe.combo, case
        assert tuple(map(int, next(rows).split())) == safe.decoys, case
        assert next(rows) == safe.clue and next(rows) == safe.answer, case
        run = safecracker.Run(safe)
        frame = 0
        while run.result is None:
            ports = safecracker.autopilot(run)
            port = ports[0] if ports else -1
            if port >= 0:
                safecracker.act(run, port)
            run.step(1 / 60)
            if frame % 19 == 0 or run.result is not None:
                result = 1 if run.result else 0
                grab = {None: 0, "dial": 1, "lever": 2}[run.grab]
                check(next(rows), [frame, port, result, run.set, grab, run.last_way, len(run.typed),
                                   run.strikes, run.t, run.reading, run.travel, run.hand.x, run.hand.y,
                                   run.lever], (case, frame))
                states += 1
            frame += 1
        assert next(rows).split() == ["cues", str(len(run.notes))], case
        for note in run.notes:
            check(next(rows), [note.t, note.dur, note.freq, note.voice, note.gain, note.seed], case)
            cues += 1
        machines += 1
    assert machines == 65
    print(f"Safecracker matched {machines} Python safes, {states} pilot states and {cues} audio cues")


if __name__ == "__main__":
    compare(sys.argv[1])
