"""Actual original complete RNE bias on owned, identical captured operands.

This diagnostic calls the original public mj_rne, not a newer-SDK mirror or
guessed inline ABI. Intermediate scalar reconstructions are separately checked
against its final return. Captured JSON zero signs remain unqualified.
"""
import argparse
import copy
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

from marble_cone_update_oracle import Reader
from marble_inertia_original import OriginalInertia,captures as inertia_captures
from marble_primal_eval_oracle import ORIGINAL_EVAL_OFFSET,REFERENCE_SHA256,DlInfo
from marble_qcqp_trace import validate_runtime_pair

OFFSET=0x60ef8
FIELDS=("cinert","cvel","cdof","cdof_dot","qvel")
LAYOUTS=(
    '<mujoco><worldbody><body><freejoint/><geom size=".1"/></body></worldbody></mujoco>',
    '<mujoco><worldbody><body><freejoint/><geom size=".1"/></body><body><freejoint/><geom size=".1"/></body><body><freejoint/><geom size=".1"/></body></worldbody></mujoco>',
    '<mujoco><worldbody><body><freejoint/><geom size=".1"/><body pos="0 0 1"><joint type="hinge"/><geom size=".1"/></body></body></worldbody></mujoco>')


def validated_engine(engine):
    if not isinstance(engine,dict) or not isinstance(engine.get("model"),dict) or not isinstance(engine.get("arrays"),dict):
        raise ValueError("complete RNE engine/model/arrays objects required")
    m,a=engine["model"],engine["arrays"]
    parents=m.get("body_parentid");Reader(parents)
    qvel=a.get("qvel");Reader(qvel)
    nb,nv=len(parents),len(qvel)
    if not 1<=nb<=1000 or not 1<=nv<=512:raise ValueError("bounded nonempty RNE dimensions required")
    if parents[0]!=0 or any(p!=int(p) or not 0<=p<b for b,p in enumerate(parents[1:],1)):
        raise ValueError("RNE parents must be topologically ordered")
    adr,num=m.get("body_dofadr"),m.get("body_dofnum");Reader(adr);Reader(num)
    if len(adr)!=nb or len(num)!=nb or num[0]!=0:raise ValueError("complete body DOF ownership required")
    owned=[]
    for b,(start,count) in enumerate(zip(adr,num)):
        if count!=int(count) or not 0<=count<=6 or start!=int(start):
            raise ValueError("bounded integral Marble body DOFs required")
        if count:
            if start<0 or start+count>nv:raise ValueError("body DOF range out of bounds")
            owned.extend(range(int(start),int(start+count)))
        elif start not in (-1,0):raise ValueError("explicit empty body DOF address required")
    if sorted(owned)!=list(range(nv)):raise ValueError("complete nonoverlapping DOF ownership required")
    options=m.get("options")
    if not isinstance(options,dict):raise ValueError("explicit RNE options required")
    for flag in ("disableflags","enableflags"):
        value=options.get(flag)
        if type(value) is not int or not 0<=value<=2147483647:raise ValueError("explicit bounded flags required")
    if options["enableflags"]&(1<<4):raise ValueError("sleep-enabled RNE not qualified")
    if type(m.get("disableflags")) is not int or m["disableflags"]!=options["disableflags"]:
        raise ValueError("inconsistent duplicate RNE disable flags")
    gravity=m.get("gravity");Reader(gravity)
    if len(gravity)!=3:raise ValueError("complete gravity required")
    for name,width in (("cinert",10*nb),("cvel",6*nb),("cdof",6*nv),("cdof_dot",6*nv),("qvel",nv),("qfrc_bias",nv)):
        values=a.get(name);Reader(values)
        if len(values)!=width:raise ValueError("complete RNE array required: "+name)
    return nb,nv


def selected_inputs(trace):
    # Prevalidate every assigned mirror packet and complete original RNE input
    # before constructing models or invoking any original routine.
    inertia_captures(trace);rows=[]
    for e,event in enumerate(trace["events"]):
        if not event.get("rneTraces"):continue
        for s,phases in enumerate(event["engineStep1Phases"]):
            owners={name:[p.get("engine") for p in phases if p.get("phase")==name]
                for name in ("probe_referenceConstraint","probe_rneBias")}
            if any(len(v)!=1 for v in owners.values()):raise ValueError("unique before/after RNE owners required")
            before,after=(owners[n][0] for n in ("probe_referenceConstraint","probe_rneBias"))
            nb,nv=validated_engine(before);validated_engine(after)
            if before["model"]!=after["model"] or any(before["arrays"][f]!=after["arrays"][f] for f in FIELDS):
                raise ValueError("captured RNE input operands mutated across call")
            raw=event["rneTraces"][s]
            if raw[36*nb:36*nb+nv]!=after["arrays"]["qfrc_bias"]:
                raise ValueError("assigned actual RNE return differs from captured phase output")
            rows.append(dict(event=e,substep=s,engine=before,captured=after["arrays"]["qfrc_bias"]))
    if not rows:raise ValueError("no selected RNE input/output boundaries")
    return rows


class OriginalRNE:
    def __init__(self,path):
        self.guard=OriginalInertia(path)
        anchor=self.guard.anchor;base=ctypes.cast(anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
        self.routine=anchor.library.mj_rne;address=ctypes.cast(self.routine,ctypes.c_void_p).value
        dladdr=ctypes.CDLL(None).dladdr
        dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int
        info=DlInfo()
        if address!=base+OFFSET or not dladdr(address,ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve()!=anchor.path:
            raise ValueError("original RNE symbol/image/address differs")
        self.routine.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_double)]
        self.routine.restype=None

    def evaluate(self,model,data,engine):
        nb,nv=validated_engine(engine);m,a=engine["model"],engine["arrays"]
        if (model.nbody,model.nv)!=(nb,nv):raise ValueError("owned original model dimensions differ")
        for name in ("body_parentid","body_dofadr","body_dofnum"):
            if getattr(model,name).tolist()!=m[name]:raise ValueError("owned original model topology differs: "+name)
        expected_body=[b for b in range(nb) for _ in range(int(m["body_dofnum"][b]))]
        if model.dof_bodyid.tolist()!=expected_body:raise ValueError("owned original DOF bodies differ")
        # No sleep state is copied or guessed. This qualified context explicitly
        # disables sleep and reads only the RNE bias inputs, not constraint data.
        model.opt.enableflags=m["options"]["enableflags"]
        model.opt.disableflags=m["options"]["disableflags"]
        model.opt.gravity[:]=m["gravity"]
        for field in FIELDS:
            target=getattr(data,field).ravel()
            if target.size!=len(a[field]):raise ValueError("owned data shape differs")
            target[:]=a[field]
        if any(getattr(data,f).ravel().tolist()!=a[f] for f in FIELDS) or model.opt.gravity.tolist()!=m["gravity"]:
            raise ValueError("owned original RNE input copy differs")
        out=(ctypes.c_double*nv)()
        self.routine(ctypes.c_void_p(int(model._address)),ctypes.c_void_p(int(data._address)),0,out)
        result=list(out);Reader(result)
        if any(getattr(data,f).ravel().tolist()!=a[f] for f in FIELDS):raise ValueError("RNE mutated input arrays")
        return result


def main():
    from marble_source_play_trace import native_mujoco_provenance,reconstruct_rne_bias
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path);p.add_argument("--control",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True);p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--golden",action="store_true")
    args=p.parse_args();trace=json.loads(args.trace.read_text());control=json.loads(args.control.read_text())
    validate_runtime_pair(trace,control);rows=selected_inputs(trace)
    original=OriginalRNE(args.reference_library)
    import mujoco
    runtime=native_mujoco_provenance(mujoco)
    if runtime["activeEngineLibrary"]["sha256"]!=REFERENCE_SHA256 or Path(runtime["activeEngineLibrary"]["path"]).resolve()!=original.guard.anchor.path:
        raise ValueError("owned objects must come from the exact original wheel")
    sys.path.insert(0,str(args.source_root.resolve()))
    from neural_workshop import marblemaze as source
    from marble_source_capture import float32_abi_tray
    sim=source.Simulation(float32_abi_tray(source.deal(trace["rung"],seed=trace["boardSeed"])));sim._ensure_engine()
    bits=lambda v:[struct.pack("!d",x).hex() for x in v]
    if args.golden:
        native_models=[mujoco.MjModel.from_xml_string(xml) for xml in LAYOUTS]
        native_data=[mujoco.MjData(m) for m in native_models]
        def emit(engine,kind,label,layout):
            m,d=native_models[layout],native_data[layout]
            result=original.evaluate(m,d,engine)
            small=dict(model={f:engine["model"][f] for f in
                ("body_parentid","body_dofadr","body_dofnum","gravity","disableflags","options")},
                arrays={f:engine["arrays"][f] for f in FIELDS+("qfrc_bias",)})
            print(json.dumps(dict(kind=kind,label=label,layout=layout,xml=LAYOUTS[layout],input=small,
                referenceSha256=REFERENCE_SHA256,expected=result,expectedBits=bits(result)),allow_nan=False))
        for row in rows:emit(row["engine"],"captured",f"event{row['event']}-step{row['substep']}",1)
        rng=random.Random(0x60EF8)
        for case in range(1000):
            layout=case%3;m=native_models[layout]
            draw=lambda:math.ldexp(rng.uniform(-2.,2.),rng.randrange(-12,13))
            a={f:[draw() for _ in range(getattr(native_data[layout],f).size)] for f in FIELDS}
            a["qfrc_bias"]=[0.]*m.nv
            if case%7==0:a["qvel"]=[0.]*m.nv
            if case%9==0:a["cvel"]=[0.]*len(a["cvel"])
            if case%11==0:a["cdof_dot"]=[-0. if j%2 else 0. for j in range(len(a["cdof_dot"]))]
            flags=(1<<7) if case%5==0 else 0
            model=dict(body_parentid=m.body_parentid.tolist(),body_dofadr=m.body_dofadr.tolist(),
                body_dofnum=m.body_dofnum.tolist(),gravity=[draw() for _ in range(3)],
                disableflags=flags,options=dict(disableflags=flags,enableflags=0))
            emit(dict(model=model,arrays=a),"synthetic",f"synthetic{case}",layout)
        return
    counts=dict(boundaries=len(rows),differentBoundaries=0,differentValues=0,modelDifferentBoundaries=0,modelDifferentValues=0)
    boundaries=[]
    for row in rows:
        result=original.evaluate(sim._model,sim._data,row["engine"])
        modeled_engine=copy.deepcopy(row["engine"])
        if modeled_engine["model"]["disableflags"]&(1<<7):modeled_engine["model"]["gravity"]=[0.,0.,0.]
        model=reconstruct_rne_bias(modeled_engine,fma=math.fma,fused_kernels=frozenset(("dof","inert","cross","dot")))["qfrc_bias"]
        d=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(result,row["captured"])) if x!=y]
        md=[dict(index=i,original=x,model=y) for i,(x,y) in enumerate(zip(result,model)) if bits([x])!=bits([y])]
        counts["differentBoundaries"]+=bool(d);counts["differentValues"]+=len(d)
        counts["modelDifferentBoundaries"]+=bool(md);counts["modelDifferentValues"]+=len(md)
        boundaries.append(dict(event=row["event"],substep=row["substep"],actualOriginal=result,
            actualOriginalBits=bits(result),captured=row["captured"],differences=d,modelDifferences=md))
    identity=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-original-rne.v1",referenceSha256=REFERENCE_SHA256,
        trace=identity(args.trace),control=identity(args.control),runtime=trace["runtimeProvenance"],nativeRuntime=runtime,
        originalSource=identity(Path(source.__file__)),counts=counts,boundaries=boundaries,
        originalPrivateIntermediatesCaptured=False,capturedBrowserZeroSignsQualified=False,
        matchedInputs=True,ordinaryTrajectoryAcceptance=False,promoted=False,
        scope="actual original complete public RNE bias on owned copied finite sleep-disabled Marble operands; full model reconstruction separately checked, not original private intermediates or uninterrupted-game acceptance"),indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
