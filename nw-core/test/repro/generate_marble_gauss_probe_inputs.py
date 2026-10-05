#!/usr/bin/env python3
"""Actual original private Gauss producer goldens, not full-game goldens."""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from marble_gauss_oracle import OriginalGauss,synthetic_inputs,wheel_order
from marble_gauss_trace import capture_gauss
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_neutral_pair


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace",type=Path,required=True)
    p.add_argument("--control",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();trace=json.loads(args.trace.read_text())
    validate_neutral_pair(trace,json.loads(args.control.read_text()))
    rows=[(event,step,g) for event,e in enumerate(trace["events"])
        for step,t in enumerate(e.get("newtonTraces",[])) for g in capture_gauss(t)[0]]
    if len(rows)!=125:raise ValueError("expected retained 125-call Gauss selection")
    original=OriginalGauss(args.reference_library)
    def emit(kind,label,arrays):
        actual=original.solve(*arrays)
        if struct.pack("!d",actual)!=struct.pack("!d",wheel_order(*arrays)["gauss"]):
            raise ValueError("reference Gauss model does not qualify against actual original")
        print(json.dumps(dict(kind=kind,label=label,
            values=[1,len(arrays[0])]+[v for a in arrays for v in a],
            expectedBits=struct.pack("!d",actual).hex(),referenceSha256=REFERENCE_SHA256,
            scope="actual exact original PrimalUpdateConstraint isolated zero-constraint Gauss output"),
            separators=(",",":"),allow_nan=False))
    for event,step,g in rows:
        emit("captured",f"{event}:{step}:{g['ordinal']}",
            [g[k] for k in ("Ma","qfrc_smooth","qacc","qacc_smooth")])
    for case,arrays in enumerate(synthetic_inputs()):emit("synthetic",str(case),arrays)


if __name__=="__main__":main()
