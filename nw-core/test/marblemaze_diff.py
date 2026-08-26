"""Drive the real neural_workshop.marblemaze over the same grid as the sweep.

Only the generator and its certificate: the reference's `Simulation` wraps
MuJoCo and is not ported (see the header of src/tasks/marblemaze.elisa). The
import is stubbed so the module loads -- nothing exercised here touches it, and
MuJoCo is not installed on this machine in any case.

The distance field is the thing worth comparing. It is both the certificate
and the coach's yardstick, so a field one ulp out in a few cells is a tray that
still looks entirely reasonable and is not the tray the reference dealt.
"""
import os
import struct
import subprocess
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "original-neural-workshop-enhanced"))
sys.modules.setdefault("mujoco", types.ModuleType("mujoco"))

from neural_workshop import marblemaze as mm

RUNGS = tuple(range(1, 17))
SEEDS = (0, 1, 5, 9)


def bits(value):
    return struct.unpack("<q", struct.pack("<d", value))[0]


def python_lines():
    out = []
    for rung in RUNGS:
        for seed in SEEDS:
            tray = mm.deal(rung, seed=seed)
            row = ["mm", rung, seed, 1, tray.cols, tray.rows,
                   bits(tray.width), bits(tray.depth), bits(tray.cell),
                   bits(tray.thickness), bits(tray.height),
                   bits(tray.home[0]), bits(tray.home[1]), bits(tray.home[2]),
                   bits(tray.route), bits(mm.par_seconds(tray))]
            row += ["w", len(tray.walls)]
            for wall in tray.walls:
                row += [bits(wall.x0), bits(wall.y0), bits(wall.x1),
                        bits(wall.y1)]
            row += ["o", len(tray.holes)]
            for hole in tray.holes:
                row += [bits(hole.x), bits(hole.y), bits(hole.radius),
                        1 if hole.home else 0]
            row += ["s", len(tray.starts)]
            for (x, y) in tray.starts:
                row += [bits(x), bits(y)]
            field = tray.field
            row += ["d", field.cols, field.rows,
                    sum(1 for v in field.dist if v is not None)]
            for i, value in enumerate(field.dist):
                if i % 37 == 0:
                    row.append("n" if value is None else bits(value))
            out.append(",".join(str(v) for v in row))
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:4]:
        fg, fw = g.split(","), w.split(",")
        where = next((j for j, (a, b) in enumerate(zip(fg, fw)) if a != b), -1)
        print(f"MISMATCH line {i} at field {where} "
              f"(elisa {len(fg)} fields, python {len(fw)})")
        print(f"  elisa:  {','.join(fg[max(0, where - 4):where + 5])}")
        print(f"  python: {','.join(fw[max(0, where - 4):where + 5])}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
