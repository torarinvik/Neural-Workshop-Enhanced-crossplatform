"""Drive the real neural_workshop.syllogism over the same grid as the sweep.

The whole printed page, not the verdict. A syllogism generator that has
diverged still prints a readable question with a plausible answer, so nothing
short of the full text catches it: the question, every premise line in the
order shown, every option, every working step, and the four measured numbers.

The reference imports mujoco only through its sibling modules, but the word
index it names things from is real and is read from the machine. The port
compiles in two distilled tables instead (see scripts/words.py); this driver
uses the reference exactly as it stands, so the two agreeing is what says the
distillation lost nothing.
"""
import os
import subprocess
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "original-neural-workshop-enhanced"))
sys.modules.setdefault("mujoco", types.ModuleType("mujoco"))

from neural_workshop import syllogism as sy

LEVELS = tuple(range(1, 13))
SEEDS = (0, 1, 2, 3, 4, 5, 6, 7, 11, 19)


def python_lines():
    out = []
    for made_up in (0, 1):
        for level in LEVELS:
            for seed in SEEDS:
                q = sy.generate(level, seed=seed, made_up=made_up == 1)
                row = ["sy", made_up, level, seed, 1 if q else 0]
                if not q:
                    out.append(",".join(str(v) for v in row))
                    continue
                row += [q.answer, q.surface, q.steps, q.decoys,
                        len(q.options), len(q.lines), len(q.working)]
                parts = ([q.asked] + list(q.lines) + list(q.options)
                         + list(q.working))
                out.append(",".join(str(v) for v in row) + "|"
                           + "|".join(parts))
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
        fg, fw = g.split("|"), w.split("|")
        where = next((j for j, (a, b) in enumerate(zip(fg, fw)) if a != b), -1)
        print(f"MISMATCH line {i} at field {where}")
        print(f"  elisa:  {fg[where][:160] if where >= 0 else ''}")
        print(f"  python: {fw[where][:160] if where >= 0 else ''}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
