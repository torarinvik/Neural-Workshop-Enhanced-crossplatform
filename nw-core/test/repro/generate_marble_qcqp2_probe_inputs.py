#!/usr/bin/env python3
"""Actual original public QCQP2 goldens; not a gameplay acceptance oracle."""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from marble_qcqp_small_original import OriginalQCQPSmall,synthetic_inputs,wheel_qcqp2
from marble_qcqp_trace import capture_qcqp,validate_runtime_pair
from marble_primal_eval_oracle import REFERENCE_SHA256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace",required=True,type=Path)
    p.add_argument("--reference-library",required=True,type=Path)
    args=p.parse_args();trace=json.loads(args.trace.read_text())
    # Retained runtime only. Gauss arithmetic control is not a neutral-observer claim.
    validate_runtime_pair(trace,trace)
    selected=[(event,step,c) for event,e in enumerate(trace["events"])
        for step,t in enumerate(e.get("newtonTraces",[])) for c in capture_qcqp(t) if c["route"]==2]
    if len(selected)!=18:raise ValueError("expected retained 18-call two-tangent selection")
    original=OriginalQCQPSmall(args.reference_library)
    def emit(kind,label,inputs):
        actual=original.solve(*inputs,2);model=wheel_qcqp2(*inputs)
        bits=lambda values:[struct.pack("!d",v).hex() for v in values]
        if actual["active"]!=model["active"] or bits(actual["rawForce"])!=bits(model["rawForce"]):
            raise ValueError("small QCQP2 model fails actual original qualification")
        matrix,rhs,mu,radius=inputs
        print(json.dumps(dict(kind=kind,label=label,values=[1,2,radius]+matrix+rhs+mu,
            active=actual["active"],expectedBits=bits(actual["rawForce"]),
            referenceSha256=REFERENCE_SHA256),separators=(",",":"),allow_nan=False))
    for event,step,c in selected:
        emit("captured",f"{event}:{step}:{c['ordinal']}",(c["matrix"],c["rhs"],c["mu"],c["normal"]))
    for case,inputs in enumerate(synthetic_inputs(2)):emit("synthetic",str(case),inputs)


if __name__=="__main__":main()
