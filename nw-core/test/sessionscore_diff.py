#!/usr/bin/env python3
"""Differential harness for src/sessionscore.elisa against bwaccel.

`bwaccel.analyze_session` is called here -- the same entry point AnalysisLabel
calls, so whichever implementation the accelerator loaded is the one under
test. Nothing restates the scoring.

The session is not shipped across the boundary; both sides build it from the
spec by the same arithmetic, which is what lets a sweep of seventy-two sessions
be a dozen integers per spec.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
VENV = os.path.join(ORIGINAL, ".venv", "bin", "python")

if not os.environ.get("NW_SCENE_REEXEC") and os.path.exists(VENV):
    if len(sys.argv) > 1:
        sys.argv[1] = os.path.abspath(sys.argv[1])
    os.environ["NW_SCENE_REEXEC"] = "1"
    os.execv(VENV, [VENV] + sys.argv)
sys.path.insert(0, HERE)
# bwaccel is a package inside the reference checkout, imported by its own
# modules as a bare name; the reference's tests reach it the same way.
sys.path.insert(0, ORIGINAL)
os.chdir(ORIGINAL)

import bwaccel                                                      # noqa: E402

#: Stream keys, in the port's own numbering (src/sessionscore.elisa).
NAMES = ["position1", "position2", "position3", "position4", "color", "image",
         "vis1", "vis2", "vis3", "vis4", "visvis", "visaudio", "audiovis",
         "audio", "audio2", "arithmetic", "vis"]
STREAM_KEY_COUNT = len(NAMES)
SESSION_KEY_COUNT = STREAM_KEY_COUNT + 16

MODALITY_SETS = {
    0: ["position1", "audio"],
    1: ["position1", "color", "image", "audio", "audio2"],
    2: ["visvis", "visaudio", "audiovis"],
    3: ["position1", "arithmetic"],
    4: ["position1", "position2", "position3", "position4",
        "vis1", "vis2", "vis3", "vis4"],
    5: ["visvis", "image", "arithmetic", "audio"],
}
CODES = {name: index for index, name in enumerate(NAMES[:16])}


def build_session(spec):
    session = {}
    for key, name in enumerate(NAMES):
        if key == spec["drop"]:
            continue
        session[name] = [(trial * spec["mult"] + key) % spec["modulus"]
                         for trial in range(spec["trials"])]
    for code in range(16):
        if STREAM_KEY_COUNT + code == spec["drop"]:
            continue
        session["%s_input" % NAMES[code]] = [
            1 if (trial + code) % spec["stride"] == 0 else 0
            for trial in range(spec["input_trials"])]
    return session


def frame(spec):
    modalities = MODALITY_SETS[spec["which"]]
    variable = ([1 + trial % 3 for trial in range(spec["trials"])]
                if spec["variable"] else None)
    scored = bwaccel.analyze_session(spec["nback"], bool(spec["crab"]),
                                     bool(spec["jaeggi"]), variable,
                                     modalities, build_session(spec))
    rows = []
    for name in modalities:
        if name not in scored:
            rows.append("mod|%d|2|0|0" % CODES[name])
            continue
        pair = scored[name]
        if pair is None:
            rows.append("mod|%d|1|0|0" % CODES[name])
            continue
        rows.append("mod|%d|0|%d|%d" % (CODES[name], pair[0], pair[1]))
    return rows


def parse(binary):
    got = subprocess.run([binary], capture_output=True, text=True, check=True)
    names, specs, frames, current = None, [], [], None
    for line in got.stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith("names|"):
            names = line.split("|")[1:]
        elif line.startswith("spec|"):
            specs.append(dict(zip(names, (int(one) for one in line.split("|")[1:]))))
            current = []
        elif line == "end":
            frames.append(current)
            current = None
        elif current is not None:
            current.append(line)
    if not specs:
        raise SystemExit("sweep printed no specs at all")
    return specs, frames


def main():
    specs, mine = parse(sys.argv[1])
    bad = 0
    for spec, ours in zip(specs, mine):
        theirs = frame(spec)
        if ours == theirs:
            continue
        bad += 1
        if bad > 3:
            continue
        print("MISMATCH spec %s" % (
            " ".join("%s=%s" % pair for pair in sorted(spec.items())),))
        print("    elisa:  %s" % " ".join(ours))
        print("    python: %s" % " ".join(theirs))
    if bad:
        print("FAIL: %d differences" % bad)
        return 1
    print("PASS: %d sessions identical" % len(mine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
