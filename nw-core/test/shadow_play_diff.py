"""Compare Shadow Play's rods, projections, controls, and cues with Python."""

import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, shadowplay as model


def compare(binary):
    lines = iter(subprocess.check_output([binary], text=True).splitlines())

    def near(expected, where):
        actual = list(map(float, next(lines).split()))
        assert len(actual) == len(expected) and all(
            math.isclose(a, b, rel_tol=0, abs_tol=2e-11) for a, b in zip(actual, expected)
        ), (where, actual, expected)

    def rod_check(rod, where):
        for point in [rod[0][0], *(segment[1] for segment in rod)]:
            near(point, where)

    def matrix_check(matrix, where):
        for row in matrix:
            near(row, where)

    def run_check(run, where):
        result = (1 if run.result[0] else -1) if run.result else 0
        hold = run.fit_since if run.fit_since is not None else -1.0
        mask = sum(1 << port for port in model.autopilot(run))
        near((run.t, run.fit, run.checked, hold, run.close(), result, run.dirty, len(run.notes), mask), where)
        matrix_check(run.turn, where)

    for bends in range(3, 9):
        rng = random.Random(bends)
        for seed in range(50):
            rod_check(model.make_rod(bends, rng), ("rod", bends, seed))

    cases = [(rung, 17 + rung * 19) for rung in range(34)]
    cases.extend(((3, -17), (7, -(2**63)), (25, 2**63 - 1)))
    for rung, seed in cases:
        setup = model.deal(rung, seed)
        level = setup.level
        near((level.rung, level.bends, level.axes, level.hum, level.floor, level.tol,
              level.turning, level.swing, level.hold, level.seconds), (rung, seed, "grade"))
        rod_check(setup.rod, (rung, seed, "deal rod"))
        matrix_check(setup.target, (rung, seed, "target"))
        matrix_check(setup.start, (rung, seed, "start"))
        run = model.Run(setup)
        run_check(run, (rung, seed, "initial"))
        lamp = model.wall_light(level.swing, 1.37)
        p = setup.rod[0][0]
        near(lamp, "wall lamp")
        near(model.on_wall(p, lamp), "wall projection")
        near(model.on_floor(p), "floor projection")
        for i in range(25):
            run.rotate(2, 0.19)
            mask = (i * 19) % 64
            run.step(1 / 120, [port for port in range(6) if mask & (1 << port)])
        run_check(run, (rung, seed, "manual controls"))
        while run.result is None:
            run.step(1 / 60, model.autopilot(run))
        run_check(run, (rung, seed, "pilot verdict"))
        for note in run.notes:
            near((note.t, note.dur, note.freq, note.pan, note.pan2, note.gain,
                  note.bright, note.voice, note.seed, note.who, note.room), (rung, seed, "cue"))
    rng = random.Random(-17)
    now = last = 10.0
    run = model.Run(model.deal(1, rng=rng))
    heard_to = 0.0
    voices = [drshape.make_patch("sine", random.Random(1)),
              drshape.make_patch("bell", random.Random(2))]

    def session_check(phase, rung, trial, passed, best):
        near((phase, rung, trial, passed, best, last), ("session", phase, trial))
        if phase in (1, 2):
            run_check(run, ("session run", phase, trial))

    def tick(seconds, ports=None):
        nonlocal now, last
        now += seconds
        dt = max(0, min(0.1, now - last))
        last = now
        steps = max(1, math.ceil(dt / (1 / 120)))
        for _ in range(steps):
            run.step(dt / steps, ports)
            if run.result is not None:
                break

    def audio_check():
        nonlocal heard_to
        end = min(run.t, heard_to + 8192 / drshape.RATE)
        recorded = next(lines).split()
        assert len(recorded) == 2 and math.isclose(float(recorded[0]), end, abs_tol=1e-11)
        assert bytes.fromhex(recorded[1]) == drshape.synth(run.notes, heard_to, end, voices)
        heard_to = end

    session_check(1, 1, 1, 0, 0)
    run.rotate(1, 22 * 0.012)
    run.rotate(0, 12 * 0.012)
    tick(0.4, [model.YAW_L])
    for _ in range(12):
        tick(0.05)
    session_check(1, 1, 1, 0, 0)
    audio_check()
    audio_check()
    run.turn = run.setup.target
    while run.result is None:
        tick(0.05)
    assert run.result[0]
    session_check(2, 2, 1, 1, 1)
    audio_check()
    audio_check()
    now += 2.5
    last = now
    run = model.Run(model.deal(2, rng=rng))
    session_check(1, 2, 2, 1, 1)
    while run.result is None:
        tick(0.05)
    assert not run.result[0]
    session_check(2, 1, 2, 1, 1)
    session_end = now + 0.05
    last = session_end
    session_check(3, 1, 2, 1, 1)
    last = now + 1.0
    run = model.Run(model.deal(1, rng=rng))
    session_check(1, 1, 1, 0, 0)

    assert next(lines, None) is None
    print(f"PASS: {301 + len(cases)} Shadow Play cases match Python (300 rods, {len(cases)} seeded trials, and an adaptive session with PCM)")


if __name__ == "__main__":
    compare(sys.argv[1])
