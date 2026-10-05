"""Replay EVERY initialized primal update, not only the first-call recorder.

S2 phase pairs contain all inputs consumed by mj_constraintUpdate_impl.
They do not contain input contact Hessians, generalized-force multiplication,
or subsequent Gauss addition; none of those outputs are compared here.
"""
import argparse
import ctypes
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path

from marble_constraint_update_oracle import (
    Kernels, captured_updates, captured_difference, wheel_order_update)
from marble_iteration_trace import decode_iteration_updates
from marble_primal_eval_oracle import OriginalEval, DlInfo, REFERENCE_SHA256
from marble_qcqp_trace import validate_runtime_pair


def captures(trace):
    if (not isinstance(trace,dict) or
            type(trace.get("constraintIterationTraceSchema")) is not int or
            trace["constraintIterationTraceSchema"]!=2 or
            trace.get("constraintIterationTraceOverflow") is not False):
        raise ValueError("all-call replay requires explicit nonoverflowed S2")
    values=trace.get("constraintIterationTrace")
    if not isinstance(values,list) or len(values)>300000:
        raise ValueError("iteration capture must be a bounded array")
    rows,error=decode_iteration_updates(values,2)
    if error or len(rows)%2:
        raise ValueError("invalid or incomplete initialized phase pairs")
    result=[]
    for index in range(0,len(rows),2):
        before,after=rows[index:index+2]
        if before["phase"]!=0 or after["phase"]!=1 or not after["validity"]["cost"]:
            raise ValueError("primal update needs input/output phase ordering and assigned cost")
        for key in ("ne","nf","nefc","nv","ncontact","hessian"):
            if before[key]!=after[key]:raise ValueError("phase-pair dimensions differ")
        static=("efc_D","efc_R","frictionloss","Jaref","efc_type","efc_id",
                "contact_dim_mu_friction")
        if any(before["fields"][key]!=after["fields"][key] for key in static):
            raise ValueError("constraint-update input operands changed during the call")
        a,b=before["fields"],after["fields"];n=before["nefc"];nv=before["nv"]
        # Reuse the existing full ABI operand validator. Its aref and qfrc
        # transport slots are not consumed by Kernels.update. Discard the
        # placeholders below so they cannot masquerade as captured inputs.
        packet=[before["ne"],before["nf"],n,before["ncontact"],before["hessian"],1,nv]
        for key in ("Jaref","efc_D","efc_R","frictionloss"):packet+=a[key]
        packet += [0.]*n+a["efc_type"]+a["efc_id"]+a["efc_state"]+a["efc_force"]
        packet += a["contact_dim_mu_friction"]+b["efc_force"]+b["efc_state"]+[after["cost"]]+[0.]*nv
        c=captured_updates(packet)[0]
        c.aref=[];c.qfrc_after=[]
        result.append(dict(pair=index//2,before=before,after=after,capture=c))
    return result


def active_original(path):
    anchor=OriginalEval(path)  # exact wheel/hash/image/ABI guard
    kernels=Kernels(anchor.path)
    dladdr=ctypes.CDLL(None).dladdr
    dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)]
    dladdr.restype=ctypes.c_int
    for routine in (kernels.routine,kernels.norm_routine):
        info=DlInfo();address=ctypes.cast(routine,ctypes.c_void_p).value
        if (not dladdr(address,ctypes.byref(info)) or not info.filename or
                Path(info.filename.decode()).resolve()!=anchor.path):
            raise ValueError("constraint-update primitive loaded from another image")
    return kernels


def compare(capture,kernels):
    original=kernels.update(capture)
    browser=dict(force=capture.force_after,state=capture.state_after,cost=capture.cost_after)
    if not hasattr(math,"fma"):raise ValueError("original constraint model requires correctly rounded fma")
    model=wheel_order_update(capture,kernels.norm,math.fma)
    return dict(original=original,browser=browser,
        differences={k:captured_difference(original[k],browser[k]) for k in original},
        referenceModelDifferences={k:captured_difference(original[k],model[k]) for k in original})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path)
    p.add_argument("--reference-library",required=True,type=Path)
    p.add_argument("--event",action="append",type=int,required=True)
    args=p.parse_args();document=json.loads(args.trace.read_text())
    # Retained byte validation only. This self-pair does NOT claim neutrality.
    validate_runtime_pair(document,document)
    selected=[]
    if len(set(args.event))!=len(args.event):raise ValueError("duplicate selected event")
    for event in args.event:
        if not 0<=event<len(document["events"]):raise ValueError("event outside trace")
        for substep,trace in enumerate(document["events"][event].get("newtonTraces",[])):
            selected.extend((event,substep,c) for c in captures(trace))
    if not selected:raise ValueError("no initialized primal calls selected")
    # Validate every selected packet before loading or invoking native code.
    kernels=active_original(args.reference_library)
    counts=dict(calls=0,laterCalls=0,nonzeroDifferentCalls=0,forceDifferences=0,
        stateDifferences=0,costDifferences=0,referenceModelDifferentCalls=0,zeroSignOnlyCalls=0)
    witnesses=[]
    for event,substep,row in selected:
        result=compare(row["capture"],kernels)
        d=result["differences"];m=result["referenceModelDifferences"]
        counts["calls"]+=1;counts["laterCalls"]+=row["pair"]>0
        counts["nonzeroDifferentCalls"]+=any(v["nonzeroDifferenceCount"] for v in d.values())
        counts["referenceModelDifferentCalls"]+=any(v["nonzeroDifferenceCount"] for v in m.values())
        counts["zeroSignOnlyCalls"]+=any(v["zeroSignOnlyCount"] for v in d.values())
        for name in ("force","state","cost"):
            counts[name+"Differences"]+=d[name]["nonzeroDifferenceCount"]
        if any(v["nonzeroDifferenceCount"] for v in d.values()) and len(witnesses)<6:
            inputs=asdict(row["capture"])
            for key in ("aref","qfrc_after"):inputs.pop(key)
            witnesses.append(dict(event=event,substep=substep,pair=row["pair"],
                inputs=inputs,**result))
    identity=lambda path:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-all-primal-updates.v1",
        trace=identity(args.trace),runtime=document["runtimeProvenance"],
        referenceSha256=REFERENCE_SHA256,counts=counts,witnesses=witnesses,
        originalPrivateIntermediatesCaptured=False,
        scope="actual original constraintUpdate impl on every selected initialized S2 pair; excludes Gauss addition, J-transpose multiplication, input contact Hessians and full trajectory acceptance"),
        indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
