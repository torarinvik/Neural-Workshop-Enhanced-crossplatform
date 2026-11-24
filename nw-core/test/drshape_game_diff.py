"""Replay Dr Shape's clock, audio cursor, and adaptive run against Python."""
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape


def check_view(lines):
    def row(values):
        actual = tuple(map(float, next(lines).split()))
        assert len(actual) == len(values) and all(
            math.isclose(a, b, abs_tol=1e-12) for a, b in zip(actual, values)
        ), (actual, values)

    left, bottom, width, height = 27.36, 179.0, 857.28, 389.0
    for count in range(3, 7):
        panel = count == 3
        x0, w = (left + width * 0.28, width * 0.72) if panel else (left, width)
        top = bottom + height * 0.93
        cols, rows = (count, 1) if count <= 4 else (3, 2)
        gap = min(w, height) * 0.03
        cw = (w - gap * (cols + 1)) / cols
        ch = (top - bottom - gap * (rows + 1)) / rows
        cw = min(cw, ch * 1.25)
        ch = min(ch, cw)
        for k in range(count):
            r, c = divmod(k, cols)
            span_w = cols * cw + (cols - 1) * gap
            span_h = rows * ch + (rows - 1) * gap
            row((x0 + (w - span_w) / 2 + c * (cw + gap),
                 bottom + (top - bottom - span_h) / 2 + (rows - 1 - r) * (ch + gap), cw, ch))

    clamp = lambda x: max(0, min(1, x))
    view = drshape.matmul(drshape.axis_turn((0, 1, 0), 0.12 * math.sin(1.2 * 0.9 + 2)),
                          drshape.axis_turn((1, 0, 0), 0.3))

    def orbit(point):
        x, y, z = drshape.apply(view, point)
        f = 3.4 / (3.4 - z)
        return 400 + x * 100 * f, 220 + y * 100 * f, -z, clamp((z + 1) / 2), x, y, -z

    probe = (0.45, 0.15, -0.34)
    row(orbit(probe))
    x, y, z = drshape.apply(view, probe)
    fx, fy, fz = x * 0.85 + 0.3, y * 0.85 + 0.6, max(0.3, z * 0.85 + 3.4)
    row((left + width / 2 + height * 0.9 * fx / fz,
         bottom + height * 0.62 + height * 0.9 * (fy - drshape.FLOOR_EYE) / fz,
         fz, clamp(1 - (fz - 1.8) / 6), fx, fy, fz))
    c = drshape.seen_from(0.8, (x * drshape.OBJECT - 0.7, y * drshape.OBJECT + 0.5, z * drshape.OBJECT + 0.85))
    z = max(0.5, c[2])
    row((300 + 120 * c[0] / z, 260 + 120 * c[1] / z, z, clamp(1 - (z - drshape.ORBIT + 2.5) / 5), *c))

    form = drshape.build("prism", drshape.draw_params("prism", random.Random(17)))
    a, b = form.segs[2]
    pen = orbit(tuple(x + (y - x) * (2.4 - 2) for x, y in zip(a, b)))
    jitter = random.Random(29)
    for _ in range(10):
        jitter.uniform(-1, 1)
    row((pen[0] + jitter.uniform(-1, 1) * 0.12, pen[1] + jitter.uniform(-1, 1) * 0.12, *pen[2:]))
    items = [(1, (orbit(a)[2] + orbit(b)[2]) / 2) for a, b in form.segs]
    items += [(0, sum(orbit(v)[2] for v in face) / len(face) + 0.05) for face, _ in form.faces]
    for item in sorted(items, key=lambda it: (-it[1], it[0])):
        row(item)


def compare(binary):
    rng = random.Random(-17)
    now = 10.0
    rung, passed, best = 1, 0, 0
    with subprocess.Popen([binary], stdout=subprocess.PIPE, text=True) as process:
        lines = iter(process.stdout)

        def deal():
            return drshape.Run(drshape.deal(rung, rng=rng))

        def tick(increment):
            nonlocal now
            last = now
            now += increment
            dt = max(0.0, min(0.1, now - last))
            steps = max(1, math.ceil(dt / (1 / 30.0)))
            for _ in range(steps):
                run.step(dt / steps)
                if run.result is not None:
                    break

        def state(phase, trial, verdict=0):
            row = next(lines).split()
            if phase == 3:
                assert tuple(map(float, row)) == (3, 0, rung, 3, -1, 0, 0, 0, passed, best), row
                return
            assert tuple(map(int, row[:6])) == (
                phase, run.puzzle.seed, rung, trial,
                -1 if run.choice is None else run.choice, verdict,
            ), row
            assert tuple(map(int, row[8:])) == (passed, best)
            assert math.isclose(float(row[6]), run.t, abs_tol=1e-12)
            assert math.isclose(float(row[7]), run.strokes(), abs_tol=1e-12)

        run = deal()
        assert not run.choosing
        run.pick(0)
        state(1, 1)
        tick(0.4)
        state(1, 1)
        for _ in range(9):
            tick(0.05)
        state(1, 1)
        heard = 0.0
        for stop in (2500 / drshape.RATE, run.t, run.t):
            row = next(lines).split()
            assert math.isclose(float(row[0]), stop, abs_tol=1e-12)
            actual = bytes.fromhex(row[1]) if len(row) == 2 else b""
            assert actual == drshape.synth(run.puzzle.notes, heard, stop, run.puzzle.patches)
            heard = stop

        for i, verdict in enumerate((1, -1, -2), 1):
            if verdict != -2:
                while not run.choosing:
                    tick(0.05)
                answer = run.puzzle.answer
                run.pick(answer if verdict == 1 else (answer + 1) % len(run.puzzle.candidates))
                state(1, i, verdict)
                tick(0.05)
            else:
                while run.result is None:
                    tick(0.05)
            assert run.result is not None and run.result[0] == (verdict == 1)
            if verdict == 1:
                passed += 1
                best = max(best, rung)
                rung += 1
            else:
                rung = max(1, rung - 1)
            state(2, i, verdict)
            now += 2.5 if i == 1 else 0.05
            if i < 3:
                run = deal()
                state(1, i + 1)
            else:
                state(3, i)

        run = deal()
        passed = best = 0
        state(1, 1)
        check_view(lines)
        for mode in range(6):
            for stage in range(4):
                m, frame, rims, turtles, tubes = map(int, next(lines).split())
                assert (m, frame) == (mode, stage)
                if stage == 0:
                    assert rims == (2 if mode == 4 else 0)
                    assert turtles == (1 if mode in (0, 2) else 0)
                    if mode in (1, 3, 5):
                        assert tubes == 0
                else:
                    assert rims == (12 if mode in (4, 5) else 0) and turtles == 0
                    assert bool(tubes) == (stage >= 2 or mode != 3)
        assert next(lines, None) is None
        assert process.wait() == 0
    print("PASS: Dr Shape timing, win/loss/timeout, adaptive replay, restart, byte-exact audio windows, three camera projections, and all six rendered modes")


if __name__ == "__main__":
    compare(sys.argv[1])
