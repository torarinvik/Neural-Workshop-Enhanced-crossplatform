#!/usr/bin/env python3
"""Differential harness: tasks/sokoban.elisa vs the real
neural_workshop/sokoban.py.

Drives the ACTUAL module: GRADES, `_carve_room`, `_blob_goals` and all three
backwards walks.

`_native` is forced to None, and that is a finding rather than a convenience.
The `bwcore` built in this tree carries the nback and stats kernels but NOT
`sokoban_min_pushes`, so `solve_bounded` raises AttributeError and `generate`
cannot run at all as installed. The module's own docstring calls the pure search
the contract and says the tests hold the two to identical answers, so the pure
path is what this port targets.

The orderings that had to be right, each found the hard way:

  * the anti-undo filter is CROSSED. The reference keeps `last = (box, near)`
    and rejects the next pull when `(near, box) == last`. Comparing uncrossed
    never rejects anything, and the walk then oscillates one box in and out of
    its goal until the pull budget runs out.
  * the goal set is built in the blob's APPEND order, not by scanning cells.
    Sokoban's three goal cells 27, 35 and 43 all hash to slot 3 under mask 7, so
    insertion order decides the whole layout.
  * `boxes = set(goals)` follows CPython's set_merge, which has TWO paths: copy
    the table wholesale when the masks match after a pre-resize, else re-insert
    one by one. Three goals take the copy path and keep their order; five goals
    take the re-insert path and come out reordered. Assuming either path alone
    gets one of the two wrong.
"""
import random
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/"
       "Neural-Workshop-Enhanced-crossplatform/original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import sokoban as ref  # noqa: E402

ref._native = None


def row(*values):
    return ",".join(str(v) for v in values)


def grade_at(rung):
    return ref.GRADES[max(0, min(len(ref.GRADES) - 1, rung - 1))]


def grade_lines(out):
    for rung in (-3, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 99):
        g = grade_at(rung)
        out.append(row("grd", rung, g.width, g.height, g.boxes,
                       int(g.floor_share * 100), g.pulls, g.floor,
                       int(g.trap_share * 100), int(g.deceit * 100)))


def room_lines(out):
    for level in range(1, 17):
        for seed in (0, 1, 7, 42):
            g = grade_at(level)
            rng = random.Random(seed)
            walls = ref._carve_room(g, rng)
            goals = ref._blob_goals(g.width, g.height, walls, g.boxes, rng)
            cells = g.width * g.height
            cells_row = ["room", level, seed, 0 if goals is None else 1]
            cells_row += [1 if c in walls else 0 for c in range(cells)]
            if goals is not None:
                cells_row += [1 if c in goals else 0 for c in range(cells)]
            out.append(row(*cells_row))


def walk_cells(got, cells):
    if got is None:
        return [0]
    boxes, player, pulls = got
    return [1, player, pulls] + [1 if c in boxes else 0 for c in range(cells)]


def walk_lines(out):
    for level in (1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16):
        for seed in (0, 1, 7):
            g = grade_at(level)
            rng = random.Random(seed)
            walls = ref._carve_room(g, rng)
            goals = ref._blob_goals(g.width, g.height, walls, g.boxes, rng)
            cells = g.width * g.height
            line = ["wlk", level, seed]
            if goals is None:
                line.append(-1)
            elif g.boxes >= 9:
                line += walk_cells(ref._convoy_walk(g, walls, goals, rng), cells)
                line += walk_cells(ref._climbing_walk(g, walls, goals, rng), cells)
            else:
                line += walk_cells(ref._pull_walk(g, walls, goals, rng), cells)
            out.append(row(*line))


def python_lines():
    out = []
    grade_lines(out)
    room_lines(out)
    walk_lines(out)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:4]:
            print(f"  elisa:  {g[:160]}\n  python: {w[:160]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:5]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:200]}\n  python: {w[:200]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
