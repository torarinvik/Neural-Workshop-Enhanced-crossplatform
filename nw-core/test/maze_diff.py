#!/usr/bin/env python3
"""Differential harness: tasks/maze.elisa vs the real neural_workshop/maze.py.

The reference imports cleanly and takes its randomness as an argument, so this
drives the ACTUAL module: every row below comes out of `maze.carve`,
`maze.dead_ends`, `maze._deal`, `maze.generate` and friends, seeded the same
way the Elisa side seeds MT19937.

Two things are being checked at once. The obvious one is the algorithm. The
subtle one is the *order the random stream is consumed in* -- and, underneath
that, CPython's set iteration order, which `dead_ends` walks and which the
port reimplements slot for slot. The `set` rows compare a real `set`'s
iteration against the port's table directly, so a divergence there is named
rather than merely showing up as a different maze twenty steps later.
"""
import random
import subprocess
import sys

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import maze as ref  # noqa: E402

# Keyed by hundredths so both sides name the same float literal.
SHARES = {0: 0.0, 20: 0.2, 25: 0.25, 35: 0.35, 40: 0.4, 45: 0.45,
          50: 0.5, 55: 0.55, 60: 0.6}


def row(*values):
    return ",".join(str(v) for v in values)


def maze_fields(maze):
    """The port's emit_maze_fields, on the reference side."""
    if maze is None:
        return [0]
    return ([1, maze.width, maze.height, maze.start, maze.way_out,
             maze.minimum, maze.greedy, len(maze.doors)]
            + list(maze.doors) + list(maze.keys))


def grade_lines(out):
    for level in (-3, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                  16, 40):
        grade = ref.GRADES[max(0, min(len(ref.GRADES) - 1, level - 1))]
        out.append(row("grd", level, grade.rooms, grade.doors,
                       int(grade.braid * 1000), grade.floor,
                       int(grade.planning * 1000)))


def carve_lines(out):
    for rooms in (2, 3, 4, 5, 6, 8, 11, 15):
        for seed in (0, 1, 7, 12345):
            rng = random.Random(seed)
            width, height, cells = ref.carve(rooms, rng)
            # list(cells) is CPython's own table order -- the thing the port's
            # mset_* has to reproduce exactly.
            out.append(row("set", rooms, seed, len(cells), *list(cells)))
            ends = ref.dead_ends(width, height, cells)
            out.append(row("de", rooms, seed, len(ends), *ends))


def shuffle_lines(out):
    for rooms in (4, 6, 9, 13):
        for seed in (0, 3, 99):
            for hundredths in (20, 25, 35, 40, 45, 50, 55, 60):
                share = SHARES[hundredths]
                rng = random.Random(seed)
                width, height, cells = ref.carve(rooms, rng)
                ends = ref.dead_ends(width, height, cells)
                rng.shuffle(ends)
                out.append(row("sh", rooms, seed, hundredths,
                               int(round(len(ends) * share)), *ends))


def braid_lines(out):
    for rooms in (3, 5, 7, 10, 14):
        for seed in (0, 2, 55):
            for hundredths in (0, 20, 35, 50, 60):
                rng = random.Random(seed)
                width, height, cells = ref.carve(rooms, rng)
                ref.braid(width, height, cells, SHARES[hundredths], rng)
                opened = sorted(cells)
                out.append(row("br", rooms, seed, hundredths, len(opened),
                               *opened))


def deal_lines(out):
    for level in (1, 2, 3, 5, 8, 11, 14):
        for seed in (0, 4):
            grade = ref.GRADES[level - 1]
            rng = random.Random(seed)
            for attempt in range(6):
                maze = ref._deal(grade, rng)
                out.append(row("dl", level, seed, attempt,
                               *maze_fields(maze)))


def generate_lines(out):
    for level in range(1, 16):
        for seed in (1, 2):
            try:
                maze = ref.generate(level, seed=seed)
            except ValueError:
                maze = None
            fields = maze_fields(maze)
            if maze is None:
                out.append(row("gn", level, seed, *fields))
                continue
            opened = sorted(maze.open_cells())
            out.append(row("gn", level, seed, *fields, len(opened), *opened))

            walk = ref.route(maze)
            out.append(row("sv", level, seed, ref.solve(maze),
                           ref.greedy_walk(maze),
                           int(ref.planning_share(maze) * 1000000),
                           ref.solve(maze), len(walk), *walk,
                           ref.held_after(maze, walk)))

            links = ref.adjacency(maze.width, maze.height, maze.open_cells())
            beads = ref.separators(links, maze.start, maze.way_out)
            out.append(row("sp", level, seed, len(beads), *beads))


def python_lines():
    out = []
    grade_lines(out)
    carve_lines(out)
    shuffle_lines(out)
    braid_lines(out)
    deal_lines(out)
    generate_lines(out)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g[:180]}\n  python: {w[:180]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
