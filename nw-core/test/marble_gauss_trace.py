"""Bounded initialized Gauss calls paired to every S2 constraint update."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path

from marble_cone_update_oracle import Reader
from marble_constraint_update_oracle import captured_difference
from marble_gauss_oracle import OriginalGauss, wheel_order
from marble_iteration_constraint_oracle import captures, active_original
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_neutral_pair
from marble_qcqp_kernel_trace import comparison_scope


def decode_gauss(values,calls):
    if type(calls) is not int or not 0<=calls<=1000000:
        raise ValueError("Gauss count must be a bounded integer")
    r=Reader(values)
    if len(values)>300000:raise ValueError("Gauss recorder exceeds capacity")
    result=[]
    while r.offset<len(values):
        r.integer("Gauss schema",1,1)
        ordinal=r.integer("Gauss ordinal",0,999999)
        if ordinal!=len(result):raise ValueError("Gauss calls must be contiguous")
        island=r.integer("Gauss island",-1,65536)
        n=r.integer("Gauss dofs",0,512)
        nefc=r.integer("Gauss constraint count",0,65536)
        r.integer("initialized Ma/cost validity",3,3)
        before,after,gauss=r.take(3,"assigned costs")
        arrays={k:r.take(n,k) for k in ("Ma","qfrc_smooth","qacc","qacc_smooth","partial")}
        if gauss!=(arrays["partial"][-1] if n else 0.) or after!=before+gauss:
            raise ValueError("Gauss assigned final sum/cost-addition relation differs")
        result.append(dict(ordinal=ordinal,island=island,nv=n,nefc=nefc,
            costBefore=before,costAfter=after,gauss=gauss,**arrays))
    r.finish()
    if len(result)!=calls:raise ValueError("Gauss actual call count differs")
    return result


def capture_gauss(trace):
    if (not isinstance(trace,dict) or type(trace.get("gaussSchema")) is not int or
            trace["gaussSchema"]!=1 or trace.get("gaussOverflow") is not False or
            trace.get("gaussInvalid") is not False):
        raise ValueError("explicit assigned Gauss schema/overflow/validity required")
    rows=decode_gauss(trace.get("gaussTrace"),trace.get("gaussCalls"))
    pairs=captures(trace)
    if len(rows)!=len(pairs):raise ValueError("every S2 call needs an actual Gauss owner")
    for row,pair in zip(rows,pairs):
        if (row["nv"]!=pair["before"]["nv"] or row["nefc"]!=pair["before"]["nefc"] or
                row["costBefore"]!=pair["after"]["cost"]):
            raise ValueError("Gauss cost/dimensions do not match their actual primal call")
    return rows,pairs


def capture_native_gauss(library):
    if not hasattr(library,"mj_solver_gauss_schema"):return {}
    result={}
    for field in ("schema","calls","overflow","invalid","size"):
        routine=getattr(library,"mj_solver_gauss_"+field)
        routine.argtypes,routine.restype=[],ctypes.c_int
        value=routine()
        result[field]=bool(value) if field in ("overflow","invalid") else int(value)
    if (result["schema"]!=1 or result["overflow"] or result["invalid"] or
            not 0<=result["size"]<=300000):
        raise ValueError("invalid/overflowed/unbounded native Gauss recorder")
    array=(ctypes.c_double*result["size"])()
    copy=library.mj_solver_gauss_copy
    copy.argtypes,copy.restype=[ctypes.POINTER(ctypes.c_double)],None
    copy(array)
    return dict(gaussTrace=list(array),gaussSchema=result["schema"],
        gaussCalls=result["calls"],gaussOverflow=result["overflow"],gaussInvalid=result["invalid"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path)
    p.add_argument("--control",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    p.add_argument("--arithmetic-candidate",action="store_true",
        help="explicit changed-physics diagnosis, never neutral recorder or game acceptance")
    args=p.parse_args();document=json.loads(args.trace.read_text())
    neutrality=comparison_scope(document,json.loads(args.control.read_text()),args.arithmetic_candidate)
    selected=[(event,substep,g,c) for event,e in enumerate(document["events"])
        for substep,t in enumerate(e.get("newtonTraces",[]))
        for g,c in zip(*capture_gauss(t))]
    if not selected:raise ValueError("no initialized Gauss calls captured")
    original=OriginalGauss(args.reference_library);kernels=active_original(args.reference_library)
    counts=dict(calls=0,originalGaussModelDifferent=0,gaussDifferent=0,
        constraintCostDifferent=0,totalCostDifferent=0,partialModelDifferentCalls=0)
    witnesses=[]
    for event,substep,g,c in selected:
        inputs=[g[k] for k in ("Ma","qfrc_smooth","qacc","qacc_smooth")]
        value=original.solve(*inputs);model=wheel_order(*inputs)
        before=kernels.update(c["capture"])["cost"][0]
        diff=captured_difference([value],[g["gauss"]])
        partial=captured_difference(model["partial"],g["partial"])
        counts["calls"]+=1
        counts["originalGaussModelDifferent"]+=value!=model["gauss"]
        counts["gaussDifferent"]+=value!=g["gauss"]
        counts["constraintCostDifferent"]+=before!=g["costBefore"]
        counts["totalCostDifferent"]+=before+value!=g["costAfter"]
        counts["partialModelDifferentCalls"]+=partial["nonzeroDifferenceCount"]>0
        if (value!=g["gauss"] or before!=g["costBefore"]) and len(witnesses)<6:
            witnesses.append(dict(event=event,substep=substep,ordinal=g["ordinal"],
                captured=g,actualOriginalGauss=value,actualOriginalConstraintCost=before,
                composedOriginalTotalCost=before+value,referenceModel=model,
                gaussDifference=diff,partialDifference=partial))
    if counts["originalGaussModelDifferent"]:
        raise ValueError("Gauss reference order fails actual original producer qualification")
    identity=lambda path:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-gauss-boundary.v1",
        trace=identity(args.trace),control=identity(args.control),runtime=document["runtimeProvenance"],
        referenceSha256=REFERENCE_SHA256,neutrality=neutrality,
        counts=counts,witnesses=witnesses,capturedBrowserZeroSigns=False,
        scope="actual guarded original Gauss via zero-constraint private routine plus actual original constraintUpdate impl; partial original sums are reconstructed/final-qualified, not private-state captures; not complete solver/trajectory acceptance"),
        indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
