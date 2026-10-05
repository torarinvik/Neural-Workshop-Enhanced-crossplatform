"""Assigned elliptic no-slip cost producers with actual original primitives.

The quadratic/dot routines are original exported boundaries. Composed final
cost is a reconstruction, never a private original costChange capture.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path

from marble_cone_update_oracle import Reader
from marble_constraint_update_oracle import captured_difference
from marble_primal_eval_oracle import OriginalEval,DlInfo,REFERENCE_SHA256
from marble_qcqp_trace import capture_qcqp,validate_neutral_pair
from marble_qcqp_kernel_trace import comparison_scope


def decode_cost(values,calls):
    if type(calls) is not int or not 0<=calls<=1000000:
        raise ValueError("costChange calls must be a bounded integer")
    r=Reader(values)
    if len(values)>300000:raise ValueError("costChange capture exceeds capacity")
    result=[]
    while r.offset<len(values):
        r.integer("cost schema",1,1)
        ordinal=r.integer("cost ordinal",0,999999)
        if ordinal!=len(result):raise ValueError("cost calls must be contiguous")
        island=r.integer("cost island",-1,65536)
        iteration=r.integer("no-slip iteration",0,1000000)
        row=r.integer("contact row",0,65536)
        contact=r.integer("contact id",0,65536)
        n=r.integer("tangent dimension",2,5)
        if n not in (2,3,5):raise ValueError("only actual elliptic cost dimensions are supported")
        r.integer("assigned delta/quadratic/dot/final validity",7,7)
        restored=bool(r.integer("restoration branch",0,1))
        quadratic,dot,before,final=r.take(4,"actual assigned scalar returns")
        matrix=r.take(n*n,"cost matrix")
        old=r.take(n,"old force");proposed=r.take(n,"pre-restoration force")
        residual=r.take(n,"residual");delta=r.take(n,"actual subtracted delta")
        retained=r.take(n,"post-restoration force")
        if delta!=[a-b for a,b in zip(proposed,old)]:
            raise ValueError("cost delta does not match actual before/old force")
        if restored!=(before>1e-10):raise ValueError("restoration branch does not match pre-change threshold")
        if (final!=(0. if restored else before) or retained!=(old if restored else proposed)):
            raise ValueError("actual final change/force differs from restoration branch")
        # Do NOT impose fused/rounded recomposition on the assigned before-change.
        result.append(dict(ordinal=ordinal,island=island,iteration=iteration,row=row,
            contact=contact,n=n,restored=restored,quadratic=quadratic,dot=dot,
            beforeChange=before,finalChange=final,matrix=matrix,oldForce=old,
            beforeForce=proposed,residual=residual,delta=delta,finalForce=retained))
    r.finish()
    if len(result)!=calls:raise ValueError("cost call count differs from assigned capture")
    return result


def capture_cost(trace):
    if (not isinstance(trace,dict) or type(trace.get("costChangeSchema")) is not int or
            trace["costChangeSchema"]!=1 or trace.get("costChangeOverflow") is not False or
            trace.get("costChangeInvalid") is not False):
        raise ValueError("explicit cost schema/nonoverflowed/valid metadata required")
    rows=decode_cost(trace.get("costChangeTrace"),trace.get("costChangeCalls"))
    owners=capture_qcqp(trace)
    if len(rows)!=len(owners):raise ValueError("every cost needs its actual elliptic outer owner")
    for c,q in zip(rows,owners):
        for field in ("ordinal","island","iteration","row","contact","restored",
                      "matrix","oldForce","residual"):
            if c[field]!=q[field]:raise ValueError("cost owner input/metadata differs: "+field)
        if (c["n"]!=q["dim"]-1 or c["finalChange"]!=q["costChange"] or
                c["finalForce"]!=q["retainedForce"] or
                c["beforeForce"]!=(q["projectedForce"] if q["valid"]==7 else [0.]*c["n"])):
            raise ValueError("cost force/dimension/final output differs from actual outer branch")
    return rows


def capture_native_cost(library):
    if not hasattr(library,"mj_solver_costchange_schema"):return {}
    meta={}
    for field in ("schema","size","calls","overflow","invalid"):
        routine=getattr(library,"mj_solver_costchange_"+field)
        routine.argtypes,routine.restype=[],ctypes.c_int
        value=routine();meta[field]=bool(value) if field in ("overflow","invalid") else int(value)
    if (meta["schema"]!=1 or meta["overflow"] or meta["invalid"] or
            not 0<=meta["size"]<=300000 or not 0<=meta["calls"]<=1000000):
        raise ValueError("unbounded/invalid native costChange capture")
    output=(ctypes.c_double*meta["size"])()
    routine=library.mj_solver_costchange_copy
    routine.argtypes,routine.restype=[ctypes.POINTER(ctypes.c_double)],None
    routine(output)
    return dict(costChangeTrace=list(output),costChangeSchema=1,
        costChangeCalls=meta["calls"],costChangeOverflow=False,costChangeInvalid=False)


class OriginalCostPrimitives:
    def __init__(self,path):
        self.anchor=OriginalEval(path)
        dladdr=ctypes.CDLL(None).dladdr
        dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int
        ptr=ctypes.POINTER(ctypes.c_double)
        for name in ("mju_mulVecMatVec","mju_dot"):
            routine=getattr(self.anchor.library,name);info=DlInfo()
            if (not dladdr(ctypes.cast(routine,ctypes.c_void_p),ctypes.byref(info)) or
                    not info.filename or Path(info.filename.decode()).resolve()!=self.anchor.path):
                raise ValueError("cost primitive loaded from another original image")
            routine.argtypes=([ptr,ptr,ptr,ctypes.c_int] if name=="mju_mulVecMatVec" else
                             [ptr,ptr,ctypes.c_int]);routine.restype=ctypes.c_double
            setattr(self,name,routine)

    def evaluate(self,delta,matrix,residual):
        return self.evaluate_operands(delta,matrix,delta,residual)

    def evaluate_operands(self,left,matrix,right,residual):
        for values in (left,matrix,right,residual):Reader(values)
        n=len(left)
        if n not in (2,3,5) or len(matrix)!=n*n or len(right)!=n or len(residual)!=n:
            raise ValueError("actual cost primitives need complete elliptic operands")
        make=lambda v:(ctypes.c_double*len(v))(*v)
        d,A,b,r=make(left),make(matrix),make(right),make(residual)
        quadratic=self.mju_mulVecMatVec(d,A,b,n);dot=self.mju_dot(d,r,n)
        Reader([quadratic,dot])
        if list(d)!=left or list(A)!=matrix or list(b)!=right or list(r)!=residual:
            raise ValueError("original cost primitives mutated immutable input")
        return dict(quadratic=quadratic,dot=dot)


def existing_diagnostic_difference(control,candidate):
    if len(control["events"])!=len(candidate["events"]):
        return dict(field="event count")
    for event,(a,b) in enumerate(zip(control["events"],candidate["events"])):
        aa=a.get("newtonTraces",[]);bb=b.get("newtonTraces",[])
        if len(aa)!=len(bb):return dict(event=event,field="newton trace count")
        for substep,(x,y) in enumerate(zip(aa,bb)):
            for field,value in x.items():
                if field=="traceKeys" and field in y:
                    # Inventory is metadata, not an assigned solver result. The
                    # additive observer may advertise ONLY its five new fields;
                    # all old keys and every old payload still have to survive.
                    added={"costChangeTrace","costChangeSchema","costChangeCalls",
                           "costChangeOverflow","costChangeInvalid"}
                    other=y[field]
                    if (isinstance(value,list) and isinstance(other,list) and
                            all(isinstance(k,str) for k in value+other) and
                            value==sorted(set(value)) and other==sorted(set(other)) and
                            set(value)<=set(other) and set(other)-set(value)<=added):
                        continue
                if field not in y or value!=y[field]:
                    return dict(event=event,substep=substep,field=field)
    return None


def compare(trace,original):
    # Decode ALL selected branches before the first native primitive call.
    selected=[(e,s,c) for e,event in enumerate(trace["events"])
        for s,t in enumerate(event.get("newtonTraces",[])) for c in capture_cost(t)]
    if not selected:raise ValueError("no assigned costChange calls captured")
    if not hasattr(math,"fma"):raise ValueError("explicit fused reference reconstruction requires fma")
    counts=dict(calls=0,quadraticDifferent=0,dotDifferent=0,
        composedBeforeDifferent=0,composedFinalDifferent=0,composedRestoredDifferent=0,
        capturedRestoredCalls=0,twoTangentCalls=0,threeTangentCalls=0,fiveTangentCalls=0)
    witnesses=[]
    for event,substep,c in selected:
        actual=original.evaluate(c["delta"],c["matrix"],c["residual"])
        # Reconstruction ONLY: public original producers + explicit fused add.
        composed=math.fma(.5,actual["quadratic"],actual["dot"])
        restored=composed>1e-10;final=0. if restored else composed
        counts["calls"]+=1;counts["capturedRestoredCalls"]+=c["restored"]
        counts[{2:"twoTangentCalls",3:"threeTangentCalls",5:"fiveTangentCalls"}[c["n"]]]+=1
        for name in ("quadratic","dot"):counts[name+"Different"]+=actual[name]!=c[name]
        counts["composedBeforeDifferent"]+=composed!=c["beforeChange"]
        counts["composedFinalDifferent"]+=final!=c["finalChange"]
        counts["composedRestoredDifferent"]+=restored!=c["restored"]
        if (any(actual[k]!=c[k] for k in actual) or composed!=c["beforeChange"]) and len(witnesses)<8:
            witnesses.append(dict(event=event,substep=substep,ordinal=c["ordinal"],captured=c,
                actualOriginalPublic=actual,composedOriginalBefore=composed,
                composedOriginalFinal=final,composedRestored=restored,
                differences={k:captured_difference([actual[k]],[c[k]]) for k in actual}))
    return counts,witnesses


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path)
    p.add_argument("--control",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    p.add_argument("--arithmetic-candidate",action="store_true",
        help="explicit changed-physics diagnosis, not observer neutrality or game acceptance")
    args=p.parse_args();trace=json.loads(args.trace.read_text());control=json.loads(args.control.read_text())
    if args.arithmetic_candidate:
        neutrality=comparison_scope(trace,control,True)
    else:
        validate_neutral_pair(trace,control)
        existing=existing_diagnostic_difference(control,trace)
        if existing:raise ValueError("observer changed existing assigned diagnostic output: "+str(existing))
        neutrality=dict(exact=True,events=len(trace["events"]),existingAssignedDiagnosticsExact=True)
    counts,witnesses=compare(trace,OriginalCostPrimitives(args.reference_library))
    identity=lambda path:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-costchange-boundary.v1",
        trace=identity(args.trace),control=identity(args.control),runtime=trace["runtimeProvenance"],
        referenceSha256=REFERENCE_SHA256,counts=counts,witnesses=witnesses,
        neutrality=neutrality,
        capturedBrowserZeroSigns=False,originalPrivateCostChangeCaptured=False,
        scope="actual original exported quadratic/dot on initialized matched operands; composed cost/restoration are reconstructions, not private original outputs; neutral observer is not full original trajectory acceptance"),
        indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
