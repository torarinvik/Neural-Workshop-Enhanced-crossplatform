#!/usr/bin/env python3
"""Differential harness: Elisa scheduling port vs the original bwaccel/scheduling.py.

Runs the compiled Elisa sweep binary (path in argv[1]) and replays the same
deterministic input grid through the reference Python module loaded directly
from the original repo, then diffs the streams line-by-line.
"""
import importlib.util
import subprocess
import sys

REF = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced/bwaccel/scheduling.py")

spec = importlib.util.spec_from_file_location("ref_scheduling", REF)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def python_lines():
    out = []
    for ms in [0, 1, 49, 50, 51, 99, 100, 149, 150, 250, 333, 999, 1000, 1050, 2500, 60000]:
        for tick in [0, 1, 10, 50, 100, 250]:
            out.append(f"m2t,{ms},{tick},0,0,{ref.ms_to_ticks(float(ms), tick)}")
    for ms in [-100, 0, 199, 200, 201, 299, 300, 301, 1000, 1049, 1050, 59999, 60000, 60001, 100000]:
        for tick in [1, 50, 100]:
            for mt in [1, 2, 3, 5]:
                out.append(f"clamp,{ms},{tick},{mt},60000,"
                           f"{ref.clamp_trial_interval_ms(ms, tick, mt, 60000)}")
    for trial in [1, 100, 500, 1000, 2200, 3000, 4500]:
        for stim in [1, 100, 500, 1000, 4000]:
            for fb in [1, 120, 500, 4000]:
                for tick in [1, 100]:
                    p = ref.plan_trial_phases(trial, stim, fb, tick)
                    out.append(
                        f"ph,{trial},{stim},{fb},{tick},{p['total_ticks']},"
                        f"{p['stimulus_ticks']},{p['blank_ticks']},{p['feedback_ticks']},"
                        f"{p['stimulus_ms']},{p['blank_ms']},{p['feedback_ms']}")
    for ms in [0, 1, 20, 21, 99, 100, 101, 500, 501, 1999, 2000, 2001, 50000]:
        out.append(f"step,{ms},0,0,0,{ref.interval_adjust_step(ms)}")
    return out


def main():
    elisa_bin = sys.argv[1]
    elisa = subprocess.run([elisa_bin], capture_output=True, text=True, check=True)
    got = [ln for ln in elisa.stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        return 1
    bad = [(g, w) for g, w in zip(got, want) if g != w]
    for g, w in bad[:20]:
        print(f"MISMATCH\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
