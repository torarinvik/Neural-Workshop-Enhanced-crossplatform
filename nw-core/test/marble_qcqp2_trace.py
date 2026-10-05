"""Direct small-QCQP outer raw outputs; not a private-iteration recorder."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from marble_qcqp_small_original import OriginalQCQPSmall,wheel_qcqp2
from marble_qcqp_trace import capture_qcqp,validate_runtime_pair
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_trace_neutrality import first_physics_difference


def compare(trace,original):
    # Decode all branches and validate every packet before native invocation.
    selected=[(e,s,c) for e,event in enumerate(trace["events"])
        for s,t in enumerate(event.get("newtonTraces",[])) for c in capture_qcqp(t)
        if c["route"] in (2,3)]
    counts=dict(calls=0,twoTangentCalls=0,threeTangentCalls=0,
        rawDifferent=0,activeDifferent=0,twoTangentModelDifferent=0)
    witnesses=[]
    for e,s,c in selected:
        n=c["route"];inputs=(c["matrix"],c["rhs"],c["mu"],c["normal"])
        actual=original.solve(*inputs,n)
        counts["calls"]+=1;counts["twoTangentCalls" if n==2 else "threeTangentCalls"]+=1
        different=actual["rawForce"]!=c["rawForce"]
        counts["rawDifferent"]+=different;counts["activeDifferent"]+=actual["active"]!=c["active"]
        model=wheel_qcqp2(*inputs) if n==2 else None
        if model:
            bits=lambda v:[struct.pack("!d",x) for x in v]
            counts["twoTangentModelDifferent"]+=(model["active"]!=actual["active"] or
                bits(model["rawForce"])!=bits(actual["rawForce"]))
        if (different or actual["active"]!=c["active"]) and len(witnesses)<6:
            witnesses.append(dict(event=e,substep=s,ordinal=c["ordinal"],captured=c,
                actualOriginal=actual,referenceModel=model))
    if not selected:raise ValueError("no actual small-QCQP branches captured")
    if counts["twoTangentModelDifferent"]:raise ValueError("QCQP2 model fails actual original qualification")
    return counts,witnesses


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path)
    p.add_argument("--control",required=True,type=Path)
    p.add_argument("--reference-library",required=True,type=Path)
    args=p.parse_args();trace=json.loads(args.trace.read_text());control=json.loads(args.control.read_text())
    validate_runtime_pair(trace,control)
    # Validate all selected packets before loading guarded native routines.
    for e in trace["events"]:
        for t in e.get("newtonTraces",[]):capture_qcqp(t)
    counts,witnesses=compare(trace,OriginalQCQPSmall(args.reference_library))
    identity=lambda path:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    difference=first_physics_difference(control,trace)
    print(json.dumps(dict(schema="neural-workshop.marble-small-qcqp-boundary.v1",
        trace=identity(args.trace),control=identity(args.control),runtime=trace["runtimeProvenance"],
        referenceSha256=REFERENCE_SHA256,counts=counts,witnesses=witnesses,
        physicsComparison=dict(claimedRecorderNeutrality=False,events=len(trace["events"]),
            exactlyUnchanged=difference is None,firstDifference=difference),
        capturedBrowserZeroSigns=False,originalPrivateIntermediatesCaptured=False,
        scope="actual original exported two/three-tangent raw output and flags on captured operands; two-tangent intermediate model reconstructed/final-qualified; projection/costChange/restoration and full trajectory acceptance excluded"),
        indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
