#!/usr/bin/env python3
"""Differential harness: tasks/tetris.elisa vs the real
neural_workshop/tetris.py.

Drives the ACTUAL module: GRADES, `Board.skyline`, `holes`,
`perfect_placements` and `carve`.

Two tie-breaks in this module both keep the FIRST minimum -- `min(cut, key=...)`
choosing the window to cut from, and `min(range(cols), key=sky)` choosing the
bar column. Scanning with `<=` instead of `<` takes the last instead, which
yields a perfectly legal piece cut from a different window. On a level board,
where many windows sit equally low, that is most of the time. Pieces are
therefore compared cell by cell rather than by cell count.

The other trap is the level-top draw: `[rng.randint(lowest, highest)] * width`
is ONE value replicated across every column. Drawing per column spends `width`
values instead of one and gives a top already ragged before the dents are cut.
"""
from pathlib import Path
import random
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import tetris as ref  # noqa: E402


def row(*values):
    return ",".join(str(v) for v in values)


def piece_cells(piece):
    """The port's canonical spelling: sorted by (x, y)."""
    return sorted(piece)


def grade_lines(out):
    for rung in (-2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 40):
        g = ref.grade_at(rung)
        out.append(row("grd", rung, g.cells[0], g.cells[1], g.span[0],
                       g.span[1], g.step, g.roughness))


def make_board(cols, rows, pattern):
    board = ref.Board(cols, rows)
    for x in range(cols):
        height = (x * x + pattern * 3) % 5 + (pattern % 2)
        for y in range(height):
            board.fill(x, y, 1)
    return board


SHAPES = (
    frozenset({(0, 0), (0, 1), (1, 0)}),
    frozenset({(0, 0), (0, 1), (0, 2)}),
    frozenset({(0, 0), (0, 1), (1, 0), (1, 1)}),
)


def geometry_lines(out):
    for pattern in (0, 1, 2, 3):
        board = make_board(12, 10, pattern)
        flat = list(board.skyline())
        for shape in SHAPES:
            piece = ref.normalise(shape)
            found = ref.perfect_placements(board, piece)
            flat.append(len(found))
            for place in found:
                flat += [place.quarter, place.col, place.row]
        out.append(row("geom", pattern, board.holes(), *flat))


def carve_lines(out):
    for rung in range(1, 9):
        for seed in (0, 1, 7, 42, 1234):
            board = ref.Board(14, 12)
            for x in range(14):
                for y in range((x * 5 + seed) % 4):
                    board.fill(x, y, 1)
            rng = random.Random(seed)
            grade = ref.grade_at(rung)
            flat = []
            for _round in range(4):
                piece = ref.carve(board, grade, rng, attempts=24, shortlist=6)
                cells = piece_cells(piece)
                flat.append(len(cells))
                for x, y in cells:
                    flat += [x, y]
            out.append(row("carve", rung, seed, *flat))


def python_lines():
    out = []
    grade_lines(out)
    geometry_lines(out)
    carve_lines(out)
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
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
