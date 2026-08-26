"""Drive the real neural_workshop.buzzwire over the same grid as the sweep.

Every port and the complete hand state every sixteenth tick, as raw IEEE bits.
Everything in this module is a float, and a float one ulp out does not
announce itself: it steers the loop a nanometre wide, and two hundred ticks
later that is a buzz that did not happen in the reference.
"""
import os
import random
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "original-neural-workshop-enhanced"))

from neural_workshop import buzzwire as bw

RUNGS = tuple(range(1, 13))
SEEDS = (0, 3, 17)
# The rung's own budget, as the bench flies it.
HZ = 60.0

TWIST = {'tilt up': (1.0, 0.0), 'tilt down': (-1.0, 0.0),
         'tilt left': (0.0, 1.0), 'tilt right': (0.0, -1.0)}


def bits(value):
    return struct.unpack("<q", struct.pack("<d", value))[0]


def vec_cells(v):
    return [bits(v[0]), bits(v[1]), bits(v[2])]


def hand_cells(hand):
    return (vec_cells(hand.centre) + vec_cells(hand.velocity)
            + vec_cells(hand.drift)
            + [bits(hand.yaw), bits(hand.pitch), bits(hand.yaw_rate),
               bits(hand.pitch_rate), bits(hand.arc), bits(hand.quiet),
               hand.touches, 1 if hand.scraping else 0,
               1 if hand.home else 0])


def python_lines():
    out = []
    for rung in RUNGS:
        for seed in SEEDS:
            wire = bw.deal(rung, seed=seed)
            grade = bw.grade_of(rung)
            row = ["bz", rung, seed, len(wire.points), wire.beads,
                   bits(wire.length)]
            for i in range(len(wire.points)):
                if i % 23 == 0:
                    p = wire.points[i]
                    row += [bits(p[0]), bits(p[1]), bits(p[2]),
                            bits(wire.arcs[i])]
            row.append("f")
            hand = bw.Hand(wire, grade, random.Random(seed + 1))
            dt = 1.0 / 60.0
            tick = 0
            limit = int(grade.seconds * HZ)
            while tick < limit and not hand.home:
                port = bw.pilot_port(hand)
                row.append(port)
                name = bw.PORTS[port]
                push = bw.push_vector(grade, name) if name in bw.PUSHES else None
                twist = TWIST.get(name, (0.0, 0.0))
                hand.advance(dt, push=push, twist=twist,
                             grip=(name == bw.GRIP))
                if tick % 16 == 0:
                    row.append("h")
                    row += hand_cells(hand)
                tick += 1
            row.append("e")
            row.append(tick)
            row += hand_cells(hand)
            row.append(hand.beads_left())
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
