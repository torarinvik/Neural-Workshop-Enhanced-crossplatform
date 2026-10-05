#!/usr/bin/env python3
"""Compare captured RNE inertia products with the original native library.

Uses each captured WASM cacc/cvel operand, not a separately reconstructed
trajectory. This is a routine diagnostic, never a full-play acceptance gate.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path


def compare_event(event, library):
    routine = library.mju_mulInertVec
    scalar = ctypes.c_double
    routine.argtypes = [ctypes.POINTER(scalar)] * 3
    routine.restype = None
    traces = event.get("rneTraces", [])
    phases = event.get("engineStep1Phases", [])
    if not traces or len(traces) != len(phases):
        raise ValueError("missing or mismatched RNE and phase substeps")
    for substep, (trace, checkpoints) in enumerate(zip(traces, phases)):
        matches = [p["engine"] for p in checkpoints
                   if p["phase"] == "probe_rneBias"]
        if len(matches) != 1:
            raise ValueError("expected one RNE bias checkpoint")
        engine = matches[0]
        arrays = engine["arrays"]
        bodies = len(engine["model"]["body_parentid"])
        nv = len(arrays["qvel"])
        if (len(trace) != 36*bodies + 13*nv or
                len(arrays["cinert"]) != 10*bodies or
                len(arrays["cvel"]) != 6*bodies):
            raise ValueError("invalid captured operand dimensions")
        for body in range(1, bodies):
            inertia = arrays["cinert"][10*body:10*body+10]
            for stage, vector, offset in (
                    ("acceleration", trace[36*body:36*body+6], 6),
                    ("velocity", arrays["cvel"][6*body:6*body+6], 12)):
                wasm = trace[36*body+offset:36*body+offset+6]
                if not all(math.isfinite(x) for x in inertia + vector + wasm):
                    raise ValueError("non-finite captured operand or result")
                original = (scalar*6)()
                routine(original, (scalar*10)(*inertia), (scalar*6)(*vector))
                differences = [[i, original[i], wasm[i]] for i in range(6)
                               if original[i] != wasm[i]]
                yield {"substep": substep, "body": body, "stage": stage,
                       "differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--event", type=int, action="append", required=True)
    parser.add_argument("--reference-library", type=Path, required=True)
    args = parser.parse_args()
    events = json.loads(args.trace.read_text())["events"]
    library = ctypes.CDLL(str(args.reference_library.resolve()))
    mismatches = 0
    for index in args.event:
        if not 0 <= index < len(events):
            parser.error("event outside trace")
        for row in compare_event(events[index], library):
            mismatches += bool(row["differences"])
            print(json.dumps({"event": index, **row}, allow_nan=False))
    return int(bool(mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
