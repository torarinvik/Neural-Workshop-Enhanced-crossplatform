#!/usr/bin/env python3
"""Differential harness for tasks/hanoi.elisa against neural_workshop.ui.hanoi.

Tower of Hanoi has no core module in the reference -- its rules live in the UI
file beside the drawing -- so the reference side here calls those module-level
functions directly and re-derives the adaptive ladder and the scoring from the
same constants the class uses.

Importing ui/hanoi.py drags in pyglet, so the four rule functions are taken by
reading the module's source and executing just them. That keeps the reference
the REAL one rather than a restatement of it: if the file's `can_move` changes,
this picks the change up.
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "hanoi.py")

WANTED = {"minimum_moves", "fresh_pegs", "can_move", "solved",
          "SMALLEST_TOWER", "LARGEST_TOWER", "GROW_AT", "SHRINK_AT"}


def reference_module():
    """The rule half of ui/hanoi.py, without importing pyglet."""
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in WANTED:
            keep.append(node)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if WANTED.intersection(names + tuples):
                keep.append(node)
    space = {"List": list, "Tuple": tuple, "Optional": object}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = WANTED - set(space)
    if missing:
        raise SystemExit("hanoi_diff: could not lift %s from %s"
                         % (sorted(missing), SOURCE))
    return space


REF = reference_module()


def clamped(disks):
    return max(REF["SMALLEST_TOWER"], min(REF["LARGEST_TOWER"], disks))


def solve_moves(disks, source, spare, target, out):
    if disks <= 0:
        return
    solve_moves(disks - 1, source, target, spare, out)
    out.append((source, target))
    solve_moves(disks - 1, spare, source, target, out)


def apply_move(pegs, source, target):
    if not REF["can_move"](pegs, source, target):
        return False
    pegs[target].append(pegs[source].pop())
    return True


def top_of(pegs, peg):
    return pegs[peg][-1] if pegs[peg] else -1


def next_disks(disks, eff):
    if eff >= REF["GROW_AT"]:
        return clamped(disks + 1)
    if eff < REF["SHRINK_AT"]:
        return clamped(disks - 1)
    return clamped(disks)


def efficiency(par, moves):
    worst = max(par, moves)
    return 0.0 if worst <= 0 else par / worst


def reference():
    out = []
    for disks in range(0, 16):
        out.append(["par", disks, clamped(disks),
                    REF["minimum_moves"](clamped(disks))])
    for disks in range(3, 11):
        pegs = REF["fresh_pegs"](disks)
        moves = []
        solve_moves(disks, 0, 1, 2, moves)
        walked, legal = 0, True
        for source, target in moves:
            if apply_move(pegs, source, target):
                walked += 1
            else:
                legal = False
                break
        row = ["solve", disks, len(moves), walked, 1 if legal else 0,
               1 if REF["solved"](pegs, disks) else 0]
        row.extend(len(peg) for peg in pegs)
        out.append(row)
    pegs = REF["fresh_pegs"](5)
    apply_move(pegs, 0, 2)
    apply_move(pegs, 0, 1)
    for source in range(3):
        for target in range(3):
            out.append(["legal", source, target,
                        1 if REF["can_move"](pegs, source, target) else 0,
                        top_of(pegs, source), top_of(pegs, target)])
    for disks in range(2, 14):
        for hundredth in range(0, 21):
            out.append(["adapt", disks, hundredth,
                        next_disks(disks, hundredth * 0.05)])
    for par in range(1, 40):
        for moves in range(1, 40):
            eff = efficiency(par, moves)
            out.append(["eff", par, moves, int(round(eff * 1000000.0)),
                        int(round(100 * eff))])
    return [",".join(str(one) for one in row) for row in out]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True,
                         check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            print("MISMATCH line %d\n  elisa:  %s\n  python: %s" % (index, a, b))
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
