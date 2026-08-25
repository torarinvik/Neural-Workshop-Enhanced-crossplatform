#!/usr/bin/env python3
"""Differential harness: stimulus.elisa vs bwaccel/fallback.py's random kernels."""
import importlib.util
import random
import subprocess
import sys

REF = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced/bwaccel/fallback.py")

spec = importlib.util.spec_from_file_location("ref_fallback", REF)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def python_lines():
    out = []
    for seed in (1, 42, 9999):
        for back in (2, 3, 4, 7, 10):
            random.seed(seed)
            levels = ref._variable_nback_list_py(15, back)
            out.append(",".join(str(v) for v in ["vnl", seed, back] + levels))

    for seed in (8, 4242):
        for high in (6, 20, 25, 64):
            for k in (1, 3, 6):
                random.seed(seed)
                picked = ref._sample_unique_py(1, high, k)
                out.append(",".join(str(v) for v in ["su", seed, high, k] + picked))

    for seed in (2, 1234):
        for nback in (1, 2, 3):
            for trials in (12, 20, 30):
                for both in (0, 2, 4):
                    random.seed(seed)
                    try:
                        pos, audio = ref._compute_bt_sequence_py(
                            trials, nback, 6, 6, both, 8, 8)
                    except ValueError:
                        pos, audio = [], []
                    out.append(",".join(str(v) for v in
                                        ["bt", seed, nback, trials, both, len(pos)]
                                        + list(pos) + list(audio)))
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
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
