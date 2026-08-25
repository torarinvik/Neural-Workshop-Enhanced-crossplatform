#!/usr/bin/env python3
"""Differential harness: matching.elisa vs the real neural_workshop/matching.py.

The reference reads mutable module singletons (state.mode, state.cfg), so the
harness builds stand-ins with exactly the attributes the module touches and
assigns them onto the imported `state` module. That drives the ACTUAL scoring
code rather than a transcription of it.
"""
import subprocess
import sys
import types

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import matching, state  # noqa: E402

VERDICT_CODE = {matching.CORRECT: 0, matching.INCORRECT: 1,
                matching.MISSED: 2, matching.UNKNOWN: 3}


def token_at(seed, index, span):
    mixed = (seed * 1103515245 + index * 12345 + 7) % 2147483647
    return 1 + abs(mixed) % span


class FakeMode:
    """Only the attributes matching.py actually reads."""

    def __init__(self, back, crab, trial_number, variable_list):
        self.back = back
        self.trial_number = trial_number
        self.mode = 0
        self.flags = {0: {'crab': 1 if crab else 0}}
        self.variable_list = variable_list
        self.current_stim = {}


def install(back, crab, trial_number, variable_nback, variable_list,
            history, positions, current):
    state.mode = FakeMode(back, crab, trial_number, variable_list)
    state.mode.current_stim = {'vis': current}
    state.cfg = types.SimpleNamespace(VARIABLE_NBACK=variable_nback)
    fake_stats = types.SimpleNamespace()
    fake_stats.session = {'position1': [0] * positions, 'vis': history}
    state.stats = fake_stats


def python_lines():
    out = []
    for back in (1, 2, 3, 5):
        for crab in (0, 1):
            for trial in range(1, 13):
                install(back, bool(crab), trial, False, [], [], 0, 0)
                out.append(f"eb,{back},{crab},{trial},{matching.effective_back()}")

    history = [token_at(5, i, 3) for i in range(20)]
    variable = [1 + i % 4 for i in range(20)]
    for back in (1, 2, 3):
        for crab in (0, 1):
            for varnb in (0, 1):
                for trial in (1, 2, 3, 5, 8, 12):
                    for current in (1, 2, 3):
                        for missed in (0, 1):
                            for positions in (0, 1, 3, 10):
                                install(back, bool(crab), trial, bool(varnb),
                                        variable, history, positions, current)
                                try:
                                    verdict = matching.check_match('visvis', bool(missed))
                                    code = VERDICT_CODE[verdict]
                                except IndexError:
                                    # The reference indexes variable_list
                                    # unguarded and raises here. Code 9 records
                                    # that as an outcome both sides agree on,
                                    # rather than hiding the row.
                                    code = 9
                                out.append(f"cm,{back},{crab},{varnb},{trial},{current},"
                                           f"{missed},{positions},{code}")

    channel_code = {'vis': 0, 'audio': 1}
    for code, name in enumerate(('visvis', 'visaudio', 'audiovis', 'image')):
        state.mode = FakeMode(2, False, 3, [])
        state.mode.current_stim = {'vis': 11, 'audio': 22}
        current, key = matching._current_and_history(name)
        out.append(f"ch,{code},{0 if current == 11 else 1},{channel_code[key]}")
    out.append("ch,4,2,2")  # Direct: caller supplies both streams
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
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
