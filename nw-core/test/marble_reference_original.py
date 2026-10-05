"""Complete original referenceConstraint for dense, nonadhesive Marble contacts.

Captured JSON zero signs are not qualified. No ordinary trajectory acceptance.
"""
import argparse
import ctypes
import hashlib
import json
import math
import random
from pathlib import Path
import sys
from marble_cone_update_oracle import Reader
from marble_integrator_original import bits
from marble_primal_eval_oracle import OriginalEval, ORIGINAL_EVAL_OFFSET, DlInfo, REFERENCE_SHA256
from marble_reference_arithmetic import reference_acceleration


def validate(engine):
    if not isinstance(engine,dict) or not isinstance(engine.get("arrays"),dict) or not isinstance(engine.get("model"),dict):raise ValueError("complete reference engine required")
    a=engine["arrays"];n=engine.get("nefc")
    if type(n) is not int or not 0<=n<=4096 or engine["model"].get("sparse_jacobian") is not False:raise ValueError("bounded dense reference rows required")
    for key,width in (("qpos",21),("qvel",18),("efc_J",18*n),("efc_KBIP",4*n),("efc_pos",n),("efc_margin",n),("efc_type",n),("efc_vel",n),("efc_aref",n)):
        Reader(a.get(key))
        if len(a[key])!=width:raise ValueError("complete reference operand required: "+key)
    if any(type(v) is not int or not 5<=v<=7 for v in a["efc_type"]):raise ValueError("only contact reference rows qualified")
    return n


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("trace",type=Path);p.add_argument("--reference-library",type=Path,required=True);p.add_argument("--source-root",type=Path,required=True);args=p.parse_args()
    t=json.loads(args.trace.read_text());rows=[]
    for event,e in enumerate(t["events"]):
        for substep,phases in enumerate(e.get("engineStep1Phases",[])):
            owners={name:[p["engine"] for p in phases if p["phase"]==name] for name in ("probe_passive","probe_referenceConstraint")}
            if any(len(v)!=1 for v in owners.values()):raise ValueError("unique reference call owners required")
            before,after=owners["probe_passive"][0],owners["probe_referenceConstraint"][0]
            validate(before);validate(after)
            for key in ("qpos","qvel","efc_J","efc_KBIP","efc_pos","efc_margin","efc_type"):
                if before["arrays"][key]!=after["arrays"][key]:raise ValueError("reference read-set mutated")
            rows.append((event,substep,before,after))
    anchor=OriginalEval(args.reference_library);routine=anchor.library.mj_referenceConstraint
    address=ctypes.cast(routine,ctypes.c_void_p).value;base=ctypes.cast(anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
    dladdr=ctypes.CDLL(None).dladdr;dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int;info=DlInfo()
    if address!=base+0x49bc8 or not dladdr(address,ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve()!=anchor.path:raise ValueError("original reference image/address differs")
    routine.argtypes=[ctypes.c_void_p,ctypes.c_void_p];routine.restype=None
    import mujoco
    from marble_source_play_trace import native_mujoco_provenance
    native=native_mujoco_provenance(mujoco)
    if Path(native["activeEngineLibrary"]["path"]).resolve()!=anchor.path:raise ValueError("owned original model image differs")
    sys.path.insert(0,str(args.source_root.resolve()))
    from neural_workshop import marblemaze as source
    from marble_source_capture import float32_abi_tray
    sim=source.Simulation(float32_abi_tray(source.deal(t["rung"],seed=t["boardSeed"])));sim._ensure_engine();m=sim._model
    if m.nv!=18 or m.nq!=21 or m.neq or m.nplugin or m.flg_surfacevel or m.flg_adhesion or m.opt.enableflags:
        raise ValueError("unsupported original reference branch")
    results=[]
    synthetic_calls=0;rng=random.Random(0x49bc8)
    for event,substep,before,after in rows:
        d=mujoco.MjData(m);a=before["arrays"];n=validate(before)
        d.qpos[:]=a["qpos"];d.qvel[:]=a["qvel"];mujoco.mj_forward(m,d)
        if d.ne or d.nf or d.nefc!=n or mujoco.mj_isSparse(m) or any(d.contact.adhesion):raise ValueError("owned original reference contact allocation/branch differs")
        for key in ("qvel","efc_J","efc_KBIP","efc_pos","efc_margin"):
            target=getattr(d,key).ravel()
            if target.size!=len(a[key]):raise ValueError("owned reference operand size differs")
        for key in ("qvel","efc_J","efc_KBIP","efc_pos","efc_margin"):
            target=getattr(d,key).ravel();target[:]=a[key]
            if bits(target)!=bits(a[key]):raise ValueError("owned reference copy differs")
        routine(ctypes.c_void_p(int(m._address)),ctypes.c_void_p(int(d._address)))
        for key in ("qvel","efc_J","efc_KBIP","efc_pos","efc_margin"):
            if bits(getattr(d,key).ravel())!=bits(a[key]):raise ValueError("reference mutated read-only operand: "+key)
        actual={k:getattr(d,k).ravel().tolist() for k in ("efc_vel","efc_aref")}
        differences={k:[i for i,(x,y) in enumerate(zip(v,after["arrays"][k])) if x!=y] for k,v in actual.items()}
        modeled=[reference_acceleration(a["efc_KBIP"][4*i:4*i+4],actual["efc_vel"][i],a["efc_pos"][i],a["efc_margin"][i]) for i in range(n)]
        model_differences=[dict(index=i,model=x,original=y) for i,(x,y) in enumerate(zip(bits(modeled),bits(actual["efc_aref"]))) if x!=y]
        results.append(dict(event=event,substep=substep,actualOriginal=actual,actualOriginalBits={k:bits(v) for k,v in actual.items()},differentIndices=differences,modelDifferences=model_differences))
        # Reuse the independently allocated contact branch; perturb all aref
        # operands and Jacobian/qvel, checking complete actual outputs each call.
        for case in range(50):
            draw=lambda:rng.uniform(-2.,2.)*2**rng.randrange(-8,9)
            values={"qvel":[draw() for _ in range(18)],"efc_J":[draw() for _ in range(18*n)],"efc_KBIP":[draw() for _ in range(4*n)],"efc_pos":[draw() for _ in range(n)],"efc_margin":[draw() for _ in range(n)]}
            if case%10==0:values["qvel"]=[-0. if i%2 else 0. for i in range(18)]
            for key,v in values.items():
                getattr(d,key).ravel()[:]=v
                if bits(getattr(d,key).ravel())!=bits(v):raise ValueError("synthetic reference copy differs")
            routine(ctypes.c_void_p(int(m._address)),ctypes.c_void_p(int(d._address)))
            modeled=[reference_acceleration(values["efc_KBIP"][4*i:4*i+4],float(d.efc_vel[i]),values["efc_pos"][i],values["efc_margin"][i]) for i in range(n)]
            if bits(modeled)!=bits(d.efc_aref):raise ValueError("synthetic complete original aref model differs")
            if any(not math.isfinite(float(v)) for v in d.efc_aref):raise ValueError("nonfinite synthetic reference output")
            for key,v in values.items():
                if bits(getattr(d,key).ravel())!=bits(v):raise ValueError("synthetic reference mutated input")
            synthetic_calls+=1
    print(json.dumps(dict(referenceSha256=REFERENCE_SHA256,traceSha256=hashlib.sha256(args.trace.read_bytes()).hexdigest(),boundaries=results,syntheticCalls=synthetic_calls,syntheticModelDifferentValues=0,modelDifferentValues=sum(len(b["modelDifferences"]) for b in results),capturedBrowserZeroSignsQualified=False,ordinaryTrajectoryAcceptance=False,promoted=False),indent=2))


if __name__=="__main__":main()
