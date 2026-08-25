#!/usr/bin/env python3
"""Differential harness: Elisa nback port vs the original bwaccel/fallback.py."""
import importlib.util
import math
import subprocess
import sys

REF = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced/bwaccel/fallback.py")

spec = importlib.util.spec_from_file_location("ref_fallback", REF)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def token_at(seed, index, span):
    mixed = (seed * 1103515245 + index * 12345 + 7) % 2147483647
    return 1 + abs(mixed) % span


def python_lines():
    out = []
    variable = [1 + s % 5 for s in range(12)]
    for nback in (1, 2, 3, 5):
        for crab in (0, 1):
            for has_var in (0, 1):
                for x in range(14):
                    vl = variable if has_var else None
                    back = ref._resolve_back(x, nback, bool(crab), vl)
                    out.append(f"rb,{nback},{crab},{has_var},{x},{back}")

    history = [token_at(11, s, 4) for s in range(8)]
    for current in (1, 2, 3, 4):
        for trial in (-2, -1, 0, 1, 3, 7, 8, 12):
            got = ref._is_nback_match_py(current, history, trial)
            code = -1 if got is None else int(got)
            out.append(f"m,{current},{trial},{code}")

    variable40 = [1 + s % 4 for s in range(40)]
    for seed in (3, 17):
        for span in (2, 3):
            for length in (6, 12, 25):
                data = [token_at(seed, i, span) for i in range(length)]
                inputs = [token_at(seed + 1, i, 2) - 1 for i in range(length)]
                for nback in (1, 2, 3):
                    for crab in (0, 1):
                        for jaeggi in (0, 1):
                            for has_var in (0, 1):
                                vl = variable40 if has_var else None
                                r, w = ref._score_direct(data, inputs, nback, bool(crab),
                                                         bool(jaeggi), vl)
                                out.append(f"sc,{seed},{span},{length},{nback},{crab},"
                                           f"{jaeggi},{has_var},{r},{w}")

    for length in (0, 1, 4, 9):
        values = [float(10 * i + 3) for i in range(length)]
        for tail in (0, 1, 2, 5, 20):
            scaled = ref._mean_tail_py(values, tail) * 1000.0
            out.append(f"mt,{length},{tail},{int(math.trunc(scaled))}")
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
