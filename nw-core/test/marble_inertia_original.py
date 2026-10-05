"""Guarded actual original 6D inertia products on complete captured operands.

The RNE mirror's assigned public inertia products are captured; the original
public routine returns are actual. The ordered scalar model is reconstructed,
not a private original RNE intermediate recorder or full-game acceptance.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct

from marble_cone_update_oracle import Reader
from marble_constraint_update_oracle import captured_difference
from marble_primal_eval_oracle import (OriginalEval,ORIGINAL_EVAL_OFFSET,DlInfo,
    REFERENCE_SHA256)
from marble_qcqp_trace import validate_runtime_pair
from marble_trace_neutrality import first_physics_difference

OFFSET=0x12ba10


def validated(inertia,vector):
    Reader(inertia);Reader(vector)
    if len(inertia)!=10 or len(vector)!=6:raise ValueError("complete10/6 inertia operands required")


class OriginalInertia:
    def __init__(self,path):
        self.anchor=OriginalEval(path)
        base=ctypes.cast(self.anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
        routine=self.anchor.library.mju_mulInertVec
        address=ctypes.cast(routine,ctypes.c_void_p).value
        dladdr=ctypes.CDLL(None).dladdr
        dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int
        info=DlInfo()
        if (address!=base+OFFSET or not dladdr(address,ctypes.byref(info)) or
                not info.filename or Path(info.filename.decode()).resolve()!=self.anchor.path):
            raise ValueError("original inertia symbol/image/address differs")
        routine.argtypes=[ctypes.POINTER(ctypes.c_double)]*3;routine.restype=None
        self.routine=routine

    def multiply(self,inertia,vector):
        validated(inertia,vector)
        make=lambda v:(ctypes.c_double*len(v))(*v)
        i,v,out=make(inertia),make(vector),(ctypes.c_double*6)()
        self.routine(out,i,v);result=list(out);Reader(result)
        if list(i)!=inertia or list(v)!=vector:raise ValueError("original inertia mutated input")
        return result


def wheel_inertia(i,v):
    validated(i,v)
    fma=getattr(math,"fma",None)
    if not callable(fma):raise ValueError("requires correctly rounded fma")
    result=[
        fma(i[7],v[5],fma(-i[8],v[4],fma(i[4],v[2],fma(i[0],v[0],i[3]*v[1])))),
        fma(-i[6],v[5],fma(i[8],v[3],fma(i[5],v[2],fma(i[3],v[0],i[1]*v[1])))),
        fma(i[6],v[4],fma(-i[7],v[3],fma(i[2],v[2],fma(i[4],v[0],i[5]*v[1])))),
        fma(i[9],v[3],fma(i[8],v[1],(-i[7])*v[2])),
        fma(i[9],v[4],fma(i[6],v[2],(-i[8])*v[0])),
        fma(i[9],v[5],fma(i[7],v[0],(-i[6])*v[1]))]
    Reader(result);return result


def captures(trace):
    if not isinstance(trace,dict) or not isinstance(trace.get("events"),list):
        raise ValueError("RNE trace needs an events array")
    selected=[]
    for e,event in enumerate(trace["events"]):
        if not isinstance(event,dict):raise ValueError("RNE event must be an object")
        raw=event.get("rneTraces",[])
        if not isinstance(raw,list):raise ValueError("RNE substeps must be an array")
        if not raw:continue
        phases=event.get("engineStep1Phases",[])
        if not isinstance(phases,list):raise ValueError("RNE phases must be an array")
        if len(raw)!=len(phases) or len(raw)>4:raise ValueError("RNE/phase substep counts differ")
        for s,(values,checkpoints) in enumerate(zip(raw,phases)):
            if not isinstance(checkpoints,list) or any(not isinstance(p,dict) for p in checkpoints):
                raise ValueError("RNE checkpoints must be objects in an array")
            matches=[p.get("engine") for p in checkpoints if p.get("phase")=="probe_rneBias"]
            if len(matches)!=1:raise ValueError("one assigned RNE bias owner required")
            engine=matches[0]
            if not isinstance(engine,dict):raise ValueError("RNE owner must contain engine state")
            model=engine.get("model");arrays=engine.get("arrays")
            if not isinstance(model,dict) or not isinstance(arrays,dict):
                raise ValueError("RNE model and arrays must be objects")
            parents=model.get("body_parentid");Reader(parents)
            qvel=arrays.get("qvel");Reader(qvel)
            nbody=len(parents);nv=len(qvel)
            if not 1<=nbody<=1000 or nv>512:raise ValueError("bounded RNE model dimensions required")
            if parents[0]!=0 or any(p!=int(p) or not 0<=p<b for b,p in enumerate(parents[1:],1)):
                raise ValueError("invalid topologically ordered body ownership")
            options=model.get("options")
            if not isinstance(options,dict):raise ValueError("explicit RNE options object required")
            flags=options.get("enableflags")
            if type(flags) is not int or not 0<=flags<=2147483647 or flags&(1<<4):
                raise ValueError("explicit sleep-disabled RNE mirror required; no unassigned asleep bodies")
            for a,width in ((values,36*nbody+13*nv),(arrays.get("cinert"),10*nbody),
                            (arrays.get("cvel"),6*nbody),(qvel,nv)):
                Reader(a)
                if len(a)!=width:raise ValueError("complete assigned RNE operand dimensions required")
            for b in range(1,nbody):
                inertia=arrays["cinert"][10*b:10*b+10]
                for stage,vector,offset in (("acceleration",values[36*b:36*b+6],6),
                        ("velocity",arrays["cvel"][6*b:6*b+6],12)):
                    selected.append(dict(event=e,substep=s,body=b,stage=stage,inertia=inertia,
                        vector=vector,result=values[36*b+offset:36*b+offset+6]))
    if not selected:raise ValueError("no assigned inertia products")
    return selected


def synthetic_inputs(count=1000):
    if type(count) is not int or not 12<=count<=10000:raise ValueError("bounded synthetic count required")
    rng=random.Random(0x12BA10)
    for case in range(count):
        if case<12:
            inertia=[0.]*10;inertia[case%10]=1.
            vector=[(-1. if case%2 else 1.)*(j+1.) for j in range(6)]
            if case>=10:inertia=[-0. if case%2 else 0.]*10
        else:
            draw=lambda:math.ldexp(rng.uniform(-2.,2.),rng.randrange(-15,16))
            inertia=[draw() for _ in range(10)];vector=[draw() for _ in range(6)]
            if case%4==0:
                inertia[:3]=[abs(x)+1. for x in inertia[:3]]
                inertia[9]=abs(inertia[9])+1.
            if case%7==0:vector[1]=-vector[0]
            if case%9==0:inertia[6:9]=[0.]*3
        yield inertia,vector


def qualified_row(original,i,v,kind,label):
    actual=original.multiply(i,v);model=wheel_inertia(i,v)
    bits=lambda a:[struct.pack("!d",x).hex() for x in a]
    if bits(actual)!=bits(model):raise ValueError("inertia model differs from original: "+label)
    return dict(kind=kind,label=label,referenceSha256=REFERENCE_SHA256,
        values=[1]+i+v,expected=actual,expectedBits=bits(actual))


def compare(trace,original):
    # Every selected packet is decoded before invoking any native routine.
    rows=captures(trace);counts=dict(calls=len(rows),accelerationCalls=0,velocityCalls=0,
        differentCalls=0,nonzeroDifferentValues=0,zeroSignOnlyCalls=0,modelDifferentCalls=0)
    witnesses=[]
    for c in rows:
        actual=original.multiply(c["inertia"],c["vector"])
        model=wheel_inertia(c["inertia"],c["vector"])
        diff=captured_difference(actual,c["result"])
        counts[c["stage"]+"Calls"]+=1
        counts["differentCalls"]+=bool(diff["nonzeroDifferenceCount"])
        counts["nonzeroDifferentValues"]+=diff["nonzeroDifferenceCount"]
        counts["zeroSignOnlyCalls"]+=bool(diff["zeroSignOnlyCount"])
        counts["modelDifferentCalls"]+=any(struct.pack("!d",a)!=struct.pack("!d",b)
            for a,b in zip(model,actual))
        if diff["nonzeroDifferenceCount"] and len(witnesses)<8:
            witnesses.append(dict(captured=c,actualOriginal=actual,model=model,difference=diff))
    if counts["modelDifferentCalls"]:raise ValueError("model fails actual original final-bit qualification")
    return counts,witnesses


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path);p.add_argument("--control",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    p.add_argument("--golden",action="store_true")
    args=p.parse_args();trace=json.loads(args.trace.read_text());control=json.loads(args.control.read_text())
    validate_runtime_pair(trace,control);selected=captures(trace)
    original=OriginalInertia(args.reference_library)
    if args.golden:
        for c in selected:
            label=f"event{c['event']}-step{c['substep']}-body{c['body']}-{c['stage']}"
            print(json.dumps(qualified_row(original,c["inertia"],c["vector"],"captured",label),allow_nan=False))
        for i,operands in enumerate(synthetic_inputs()):
            print(json.dumps(qualified_row(original,*operands,"synthetic",f"synthetic{i}"),allow_nan=False))
        return
    counts,witnesses=compare(trace,original);difference=first_physics_difference(control,trace)
    identity=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-original-inertia.v1",trace=identity(args.trace),
        control=identity(args.control),runtime=trace["runtimeProvenance"],referenceSha256=REFERENCE_SHA256,
        counts=counts,witnesses=witnesses,capturedBrowserZeroSigns=False,
        originalPrivateRneIntermediatesCaptured=False,
        physicsComparison=dict(claimedRecorderNeutrality=False,events=len(trace["events"]),
            exactlyUnchanged=difference is None,firstDifference=difference),
        scope="actual original public inertia return on initialized captured RNE-mirror operands; scalar model reconstructed/final-qualified; shared helper also has mass/derivative callers; not original private RNE intermediates or full-game acceptance"),
        indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
