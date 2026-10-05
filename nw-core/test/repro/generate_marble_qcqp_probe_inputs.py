#!/usr/bin/env python3
"""Emit actual-original generic QCQP goldens, not projection or trajectory goldens."""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from marble_qcqp_original import OriginalQCQP5,probe_packet,synthetic_inputs
from marble_qcqp_kernel_trace import capture_kernel
from marble_qcqp_trace import validate_neutral_pair
from marble_primal_eval_oracle import REFERENCE_SHA256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace",type=Path,required=True)
    p.add_argument("--control",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args()
    trace=json.loads(args.trace.read_text())
    validate_neutral_pair(trace,json.loads(args.control.read_text()))
    captures=[(event,substep,g) for event,d in enumerate(trace["events"])
        for substep,t in enumerate(d.get("newtonTraces",[])) for g in capture_kernel(t)]
    if len(captures)!=114:
        raise ValueError("expected qualified 114-call bounded generic capture")
    original=OriginalQCQP5(args.reference_library)
    def emit(kind,label,inputs):
        output=original.solve(*inputs)
        model=original.decomposed(*inputs)
        if any(output[k]!=model[k] for k in ("rawForce","active")):
            raise ValueError("reference driver no longer qualifies against actual original")
        print(json.dumps(dict(kind=kind,label=label,values=probe_packet(*inputs),
            expectedBits=[struct.pack("!d",v).hex() for v in output["rawForce"]],
            active=output["active"],referenceSha256=REFERENCE_SHA256,
            goldenScope="actual original generic QCQP raw vector and active flag; excludes projection"),
            separators=(",",":"),allow_nan=False))
    for event,substep,g in captures:
        c=g["contact"]
        emit("captured",f"{event}:{substep}:{g['parent']}",
             (c["matrix"],c["rhs"],c["mu"],c["normal"]))
    for case,inputs in enumerate(synthetic_inputs()):
        emit("synthetic",str(case),inputs)


if __name__=="__main__":main()
