#!/usr/bin/env python3
"""Differential harness: Elisa menu row text vs the ORIGINAL's Menu._label_text.

Every menu screen in the game formats its rows the same way -- name padded to a
fixed column, value right-aligned in seven -- so this covers all of them at
once. The reference strings come out of a real Menu instance holding the real
value objects (Cycler, PercentCycler, AllCycler), not a restatement of the
format, because PercentCycler's one-decimal / two-decimal rule is exactly the
sort of thing a paraphrase gets subtly wrong.

Rows are bracketed on the Elisa side so trailing spaces survive: a row's
padding IS what is under test.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
EXTRACTOR = os.path.join(ROOT, "scripts", "extract_menurow.py")
PYTHON = os.path.join(ORIGINAL, ".venv", "bin", "python")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: menurow_diff.py <menurow_sweep binary>")
    if not os.path.exists(PYTHON):
        raise SystemExit("the original's interpreter is missing: %s" % PYTHON)

    out = subprocess.run([sys.argv[1]], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("sweep exited %d: %s" % (out.returncode, out.stderr.strip()))
    got = []
    for line in out.stdout.splitlines():
        if not line:
            continue
        if not (line.startswith("[") and line.endswith("]")):
            raise SystemExit("unbracketed sweep line: %r" % line)
        got.append(line[1:-1])

    proc = subprocess.run([PYTHON, EXTRACTOR], cwd=ORIGINAL,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("cannot read the original's rows: %s"
                         % (proc.stderr.strip() or proc.returncode,))
    want = json.loads(proc.stdout)

    if len(got) != len(want):
        raise SystemExit("FAILED: %d rows emitted, original produced %d"
                         % (len(got), len(want)))

    problems = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    if problems:
        for index, g, w in problems[:10]:
            print("MISMATCH row %d:\n  elisa    %r\n  original %r" % (index, g, w))
        raise SystemExit("FAILED: %d row(s) differ" % len(problems))
    print("PASS: %d menu rows identical" % len(got))


if __name__ == "__main__":
    main()
