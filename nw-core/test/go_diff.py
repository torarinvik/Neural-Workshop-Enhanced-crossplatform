"""Drive the real neural_workshop.go over the same grid as go_sweep.elisa.

Whole problems, never summaries: the full board and the whole target group.
A wrong draw here still yields a *plausible* Go position, so only the complete
structure catches it.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "original-neural-workshop-enhanced"))

from neural_workshop import go as ref

LEVELS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
SEEDS = (0, 1, 2, 3, 4, 5, 6, 7, 11, 19, 23, 42)


def python_lines():
    out = []
    for level in LEVELS:
        for seed in SEEDS:
            try:
                problem = ref.generate_problem(seed, level)
            except RuntimeError:
                out.append("go,%d,%d,0" % (level, seed))
                continue
            size = problem.size
            row = ["go", level, seed, 1, size,
                   problem.winning_move[1] * size + problem.winning_move[0],
                   problem.capture_goal, problem.capture_options,
                   1 if problem.show_target else 0,
                   1 if problem.show_move else 0]
            for y in range(size):
                for x in range(size):
                    row.append(problem.board[y][x])
            row.append("t")
            for cell in sorted(y * size + x for x, y in problem.target):
                row.append(cell)
            out.append(",".join(str(v) for v in row))
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g[:200]}\n  python: {w[:200]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:260]}\n  python: {w[:260]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
