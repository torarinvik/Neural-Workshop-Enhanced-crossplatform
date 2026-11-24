#!/usr/bin/env python3
"""Differential harness: Elisa board port vs the original bwaccel/board.py."""
from pathlib import Path
import importlib.util
import subprocess
import sys

REF = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced" / "bwaccel/board.py")

spec = importlib.util.spec_from_file_location("ref_board", REF)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def python_lines():
    out = []
    for dim in (2, 3):
        for n in (2, 3, 4, 5, 6, 7):
            for center in (0, 1):
                cells = ref.grid_layout(n, bool(center), dim=dim)
                row = ["lay", dim, n, center, len(cells)]
                for c in cells:
                    row += [c[0], c[1], c[2], c[3] if len(c) > 3 else 0]
                out.append(",".join(str(v) for v in row))
    for n in (2, 3, 4, 5, 7):
        for center in (0, 1):
            for position in (-1, 0, 1, 2, 5, 8, 9, 10, 25, 50):
                flat = ref.position_col_row(position, n, bool(center))
                cube = ref.position_col_row_depth(position, n, bool(center))
                f = (0, 0, 0) if flat is None else (position, flat[0], flat[1])
                c = (0, 0, 0, 0) if cube is None else (position, cube[0], cube[1], cube[2])
                out.append(",".join(str(v) for v in
                                    ["pos", n, center, position, f[0], f[1], f[2],
                                     c[0], c[1], c[2], c[3]]))
    for dim in (2, 3):
        for n in (2, 3, 4, 5, 6, 7):
            for center in (0, 1):
                ids = ref.grid_center_out_ids(n, bool(center), dim=dim)
                out.append(",".join(str(v) for v in ["cout", dim, n, center] + list(ids)))
    for dim in (2, 3):
        for n in (2, 3, 4, 5, 6):
            for center in (0, 1):
                for limit in (-5, 0, 1, 2, 3, 6, 8, 20, 500):
                    ids = ref.active_position_ids(n, bool(center), limit, dim=dim)
                    out.append(",".join(str(v) for v in
                                        ["act", dim, n, center, limit] + list(ids)))
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:5]:
            print(f"  elisa:  {g}\n  python: {w}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:10]:
        print(f"MISMATCH line {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
