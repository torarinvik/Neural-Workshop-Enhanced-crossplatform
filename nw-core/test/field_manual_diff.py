"""Compare seeded Field Manual machine layouts and written instructions."""
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import fieldmanual

KINDS = ("press", "flip", "dial", "slide", "type", "facenum", "listen", "except", "match")


RESULTS = {
    None: 0, "Every order carried out": 1, "That was the wrong control": 2, "Too soon": 3,
    "Shift was not held": 4, "That was the wrong key": 5, "Out of time": 6,
}


def equal_floats(actual, expected, label):
    parsed = list(map(float, actual))
    assert len(parsed) == len(expected), label
    for got, want in zip(parsed, expected):
        assert math.isclose(got, want, abs_tol=3e-9, rel_tol=3e-9), (label, got, want)


def replay(rows, job, case):
    run = fieldmanual.Run(job)
    frame = snapshots = 0
    while run.result is None:
        ports = fieldmanual.autopilot(run)
        port = ports[0] if ports else -1
        control = None
        if port in fieldmanual.EVENTS:
            fieldmanual.act(run, port)
        elif port >= 0:
            control = port
        run.step(1 / 60, control)
        if frame % 59 == 0 or run.result is not None:
            result = RESULTS[run.result[1] if run.result is not None else None]
            grab = -2 if run.grab == "turn" else (-1 if run.grab is None else run.grab)
            row = next(rows).split()
            state = list(map(int, row[:8]))
            assert state == [frame, port, run.step_no, result, run.typed, grab, run.beeped,
                             sum(1 << target for target in run.done)], (case, frame, state, run.result)
            equal_floats(row[8:], [run.t, run.hand.x, run.hand.y, run.yaw, run.pitch, run.hand.down], (case, frame))
            equal_floats(next(rows).split(), run.state, (case, frame))
            snapshots += 1
        frame += 1
    assert next(rows).split() == ["audio", str(len(run.notes))], case
    for note in run.notes:
        equal_floats(next(rows).split(), [note.t, note.dur, note.freq, note.voice, note.gain, note.pan, note.seed], case)
    return snapshots, len(run.notes)


def compare(executable):
    rows = iter(subprocess.check_output([executable], text=True).splitlines())
    cases = orders = snapshots = cues = 0
    for row in rows:
        rung, seed, valid, count, noise_seed, seconds = row.split()
        case = int(rung), int(seed)
        job = fieldmanual._build(fieldmanual.grade(case[0]), random.Random(case[1]))
        assert bool(int(valid)) == (job is not None), case
        assert job is not None, case
        assert len(job.parts) == int(count) and job.seed == int(noise_seed), case
        assert math.isclose(float(seconds), job.seconds, rel_tol=1e-12), case
        assert list(map(int, next(rows).split())) == [int(job.numbers.get(face, '0')) for face in range(6)], case
        for i, part in enumerate(job.parts):
            line = next(rows).split()
            assert list(map(int, line[:6])) == [*part, job.secrets[i]], (case, i, part, line)
            assert float(line[6]) == job.start[i], (case, i, job.start[i], line)
        for i, order in enumerate(job.steps):
            kind, targets, value, digits, shift, wait, tone, *beeps = next(rows).split()
            assert KINDS[int(kind)] == order.kind, (case, i, order)
            assert int(targets) == sum(1 << target for target in order.targets), (case, i, order)
            assert float(value) == (0 if order.kind == "type" or order.value is None else order.value), (case, i, order)
            assert int(digits) == (int(order.value) if order.kind == "type" else 0), (case, i, order)
            assert (int(shift), int(wait), int(tone), tuple(map(int, beeps))) == (order.shift, order.wait, order.tone, order.beeps), (case, i, order)
            text = next(rows)
            assert text == order.text, (case, i, text, order.text)
            orders += 1
        if case[1] < 2:
            states, notes = replay(rows, job, case)
            snapshots += states
            cues += notes
        if case[1] == 6:
            try:
                seed = fieldmanual.deal(case[0], seed=17).seed
            except RuntimeError:
                seed = -1
            assert next(rows).split() == ["dealt", rung, str(seed)], (case, seed)
        cases += 1
    assert cases == 120
    print(f"Field Manual matched {cases} seeded Python machines and {orders} written orders")
    print(f"Field Manual matched {snapshots} hand and order states and {cues} audio cues")


if __name__ == "__main__":
    compare(sys.argv[1])
