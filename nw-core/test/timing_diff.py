#!/usr/bin/env python3
"""Differential harness for neural_workshop.timing's state wrapper."""
import subprocess
import sys
import types

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import state, timing  # noqa: E402
from neural_workshop.config import DotDict  # noqa: E402


def emit(tag, *values):
    return "|".join([tag] + [str(v) for v in values])


def install(st):
    state.cfg = DotDict(TICK_DURATION_MS=st[0], TRIAL_INTERVAL_MS=st[1],
                        STIMULUS_DURATION_MS=st[2],
                        FEEDBACK_DURATION_MS=st[3])
    state.mode = types.SimpleNamespace(ticks_per_trial=st[4])


def rows(spec, st):
    install(st)
    plan = timing.plan_current_trial_phases()
    before = emit("before", spec, timing.tick_duration_ms(),
                  timing.trial_interval_ms(), state.mode.ticks_per_trial,
                  plan["total_ticks"], plan["stimulus_ticks"],
                  plan["blank_ticks"], plan["feedback_ticks"],
                  plan["stimulus_ms"], plan["blank_ms"],
                  plan["feedback_ms"], timing.feedback_tick())

    wanted = (spec - 20) * 211
    snapped = timing.set_trial_interval_ms(wanted)
    setting = emit("set", spec, wanted, snapped,
                   state.cfg.TRIAL_INTERVAL_MS,
                   state.mode.ticks_per_trial)

    if spec % 2 == 0:
        state.cfg.TRIAL_INTERVAL_MS = 0
    timing.apply_trial_interval_override()
    plan = timing.plan_current_trial_phases()
    after = emit("after", spec, timing.tick_duration_ms(),
                 timing.trial_interval_ms(), state.mode.ticks_per_trial,
                 plan["total_ticks"], plan["stimulus_ticks"],
                 plan["blank_ticks"], plan["feedback_ticks"],
                 plan["stimulus_ms"], plan["blank_ms"],
                 plan["feedback_ms"], timing.feedback_tick())
    return [before, setting, after]


def python_lines():
    out = []
    for spec in range(48):
        out += rows(spec, ((spec % 7) - 1, (spec % 9 - 3) * 137,
                           (spec % 8) * 83, (spec % 6) * 117,
                           1 + spec % 12))
    return out


def main():
    got = [line for line in subprocess.run(
        [sys.argv[1]], capture_output=True, text=True, check=True
    ).stdout.splitlines() if line and not line.startswith("names|")]
    want = python_lines()
    if got != want:
        for index, (a, b) in enumerate(zip(got, want)):
            if a != b:
                print(f"FAIL: first mismatch at {index}\n  elisa:  {a}\n  python: {b}")
                break
        if len(got) != len(want):
            print(f"FAIL: line count {len(got)} vs {len(want)}")
        return 1
    print(f"PASS: {len(want)} timing cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
