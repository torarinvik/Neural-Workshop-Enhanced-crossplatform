"""Drive the real neural_workshop.twohands over the same grid as the sweep.

Whole roads and whole plays, never verdicts: a policy that diverges by one
tick still comes back with a perfectly plausible ride, and a solved line that
differs only in WHICH of several shortest lines it picked has the same length.
"""
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "original-neural-workshop-enhanced"))

from neural_workshop import twohands as th

LEVELS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
SEEDS = (0, 1, 2, 3, 4, 5, 6, 7, 11, 19, 23, 42)


def bits(value):
    return struct.unpack("<q", struct.pack("<d", value))[0]


def ride_cells(ride):
    return [ride.at, ride.lane, ride.to, ride.cross, ride.air, ride.speed,
            ride.ticks, 1 if ride.hit else 0, ride.passed, ride.clipped,
            ride.points]


def play_cells(tag, road, **kwargs):
    done = th.play(road, **kwargs)
    return ([tag] + ride_cells(done.ride)
            + [1 if done.home else 0, done.shot, len(done.ports)]
            + list(done.ports))


def python_lines():
    out = []
    for level in LEVELS:
        for seed in SEEDS:
            road = th.generate(level, seed=seed)
            row = ["road", level, seed, road.length, road.start, road.clock,
                   road.par, len(road.hazards)]
            for haz in road.hazards:
                row += [haz.at, haz.lane, haz.kind]
            row += ["s", len(road.sky)]
            for target in road.sky:
                row += [target.at, bits(target.across), bits(target.up),
                        bits(target.drift)]
            ports = th.line(road) or []
            row += ["p", len(ports)] + list(ports)
            row += ["x"] + ride_cells(th.drive(road, ports))
            row += play_cells("c", road, want=1)
            row += play_cells("r", road, look=0.34)
            row += play_cells("a", road)
            row += play_cells("g", road, shoot="spare")
            row += play_cells("n", road, shoot="always")
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
        print(f"MISMATCH line {i} at field {where}")
        print(f"  elisa:  {','.join(fg[max(0, where - 4):where + 5])}")
        print(f"  python: {','.join(fw[max(0, where - 4):where + 5])}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
