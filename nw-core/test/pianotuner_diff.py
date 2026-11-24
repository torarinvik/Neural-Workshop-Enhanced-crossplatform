"""Replay Piano Tuner's grades, jobs and tries against Python, bit for bit.

Every dealt job, every step of a try -- the pitch, the string, the error,
the pin -- the verdict, the notes, and both sound tracks' settings and
phases must match exactly.
"""
from pathlib import Path
from random import Random
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import pianotuner as model

NAMES = ("unison", "octave", "fifth", "fourth", "third")
LIVE, IN_TUNE, SHARP, FLAT, OUT_OF_TIME = range(5)


def same(actual, expected):
    actual = list(actual)
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        if isinstance(b, float):
            assert struct.pack("<d", float(a)) == struct.pack("<d", b), (a, b)
        else:
            assert int(a) == int(b), (a, b)


def outcome(run):
    if run.result is None:
        return LIVE
    ok, text = run.result
    if ok:
        return IN_TUNE
    if text.startswith("Out of time"):
        return OUT_OF_TIME
    return SHARP if text.endswith("sharp") else FLAT


def player(run, mode, n):
    ports = model.autopilot(run)
    auto = ports[0] if ports else -1
    if mode == 0:
        return auto
    if mode == 1:
        return -1
    if mode == 2:
        return model.DONE if n == 300 else (auto if auto != model.DONE else -1)
    if mode == 3:
        return (n // 40) % 4 if n < 640 else auto
    return model.UP if n < 150 else (model.DONE if n == 150 else -1)


def replay(rows, rung, seed, mode, dt):
    draw = Random(seed)
    job = model.deal(rung, rng=draw)
    marker, *values = next(rows).split()
    assert marker == "job"
    same(values, [mode, rung, seed, draw.getrandbits(32), job.ref])
    for interval, off, pin in job.plan:
        marker, *values = next(rows).split()
        assert marker == "plan"
        same(values, [NAMES.index(interval), off, pin])
    if mode < 0:
        return None, 0
    run = model.Run(job)
    marker, *values = next(rows).split()
    assert marker == "begin"
    same(values, [run.pitch, run.end])
    n = 0
    while run.result is None:
        port = player(run, mode, n)
        if port == model.DONE:
            model.act(run, port)
        run.step(dt, None if port in (-1, model.DONE) else port)
        try:
            same(next(rows).split(), [port, outcome(run), run.t, run.pitch, run.k, len(run.tuned), run.error(), run.pin(),
                                      len(run.ref_track.t)])
        except AssertionError as error:
            raise AssertionError((rung, seed, mode, n, error)) from error
        n += 1
    said = run.result[1]
    marker, *values = next(rows).split()
    assert marker == "end"
    assert int(values[0]) == outcome(run)
    for note in run.notes:
        same(next(rows).split(), [note.seed, note.voice, note.t, float(note.freq), note.dur, note.gain])
    a, b = run.ref_track, run.string_track
    assert a.t == b.t and a.l == a.r == b.l == b.r and set(a.b) | set(b.b) <= {1.0}
    for k in range(len(a.t)):
        same(next(rows).split(), [a.t[k], a.f[k], b.f[k], a.l[k], a.ph[k], b.ph[k]])
    return outcome(run), n


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(41):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = model.grade(rung)
        same(values, (g.rung, len(g.intervals), g.strings, float(g.tol), float(g.stiff), float(g.seconds),
                      *(NAMES.index(i) for i in g.intervals)))
    jobs = 0
    for rung in range(1, 41):
        for seed in range(1, 11):
            replay(rows, rung, seed, -1, 0.0)
            jobs += 1
    endings = set()
    steps = tries = 0
    for rung in (1, 2, 4, 5, 7, 8, 10, 13, 16, 20, 30):
        for mode in range(4):
            result, n = replay(rows, rung, 17 + mode, mode, 1 / 120.0)
            endings.add(result)
            steps += n
            tries += 1
            if mode == 0:
                assert result == IN_TUNE, (rung, result)
    for rung, seed, mode in ((1, 5, 1), (25, 9, 0), (1, 3, 4)):
        result, n = replay(rows, rung, seed, mode, 1 / 30.0)
        endings.add(result)
        steps += n
        tries += 1
    assert next(rows, None) is None
    assert endings == {IN_TUNE, SHARP, FLAT, OUT_OF_TIME}, endings
    print(f"PASS: 41 Piano Tuner grades, {jobs} jobs and {tries} tries ending {sorted(endings)} over {steps} steps, "
          f"with their notes and both tracks' settings and phases, bit for bit match Python")


if __name__ == "__main__":
    check(sys.argv[1])
