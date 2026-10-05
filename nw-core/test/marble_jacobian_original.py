"""Actual original public point Jacobians on complete identical copied operands."""
import argparse
import ctypes
import hashlib
import json
import math
import random
import copy
from pathlib import Path
import sys
from marble_cone_update_oracle import Reader
from marble_integrator_original import OriginalIntegrator,bits
from marble_primal_eval_oracle import ORIGINAL_EVAL_OFFSET,DlInfo


def reconstruct(engine,body,point):
    m,a=engine["model"],engine["arrays"];nv=18
    Reader(point);Reader(a["cdof"]);Reader(a["subtree_com"])
    if len(point)!=3 or len(a["cdof"])!=108 or len(a["subtree_com"])!=12 or type(body)is not int or not 0<=body<4:
        raise ValueError("bounded complete Jacobian reconstruction operands required")
    parents=m["dof_parentid"]
    if len(parents)!=18 or any(type(p)is not int or not -1<=p<i for i,p in enumerate(parents)):
        raise ValueError("acyclic ordered Jacobian DOF parents required")
    if len(m["body_rootid"])!=4 or any(type(v)is not int or not 0<=v<4 for v in m["body_rootid"]):raise ValueError("bounded Jacobian roots required")
    if len(m["body_dofnum"])!=4 or len(m["body_dofadr"])!=4:raise ValueError("complete Jacobian body ownership required")
    for adr,width in zip(m["body_dofadr"],m["body_dofnum"]):
        if type(adr)is not int or type(width)is not int or not 0<=width<=6 or (width and not 0<=adr<=18-width):raise ValueError("bounded Jacobian body DOFs required")
    jp=[0.]*54;jr=[0.]*54
    root=m["body_rootid"][body]
    offset=[point[k]-a["subtree_com"][3*root+k] for k in range(3)]
    if not m["body_dofnum"][body]:return dict(jacp=jp,jacr=jr)
    i=m["body_dofadr"][body]+m["body_dofnum"][body]-1
    while i>=0:
        c=a["cdof"][6*i:6*i+6]
        cross=[math.fma(c[1],offset[2],-(c[2]*offset[1])),math.fma(c[2],offset[0],-(c[0]*offset[2])),math.fma(c[0],offset[1],-(c[1]*offset[0]))]
        for k in range(3):jp[k*nv+i]=c[k+3]+cross[k];jr[k*nv+i]=c[k]
        i=m["dof_parentid"][i]
    return dict(jacp=jp,jacr=jr)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("trace",type=Path);p.add_argument("--reference-library",type=Path,required=True);p.add_argument("--source-root",type=Path,required=True);args=p.parse_args()
    trace=json.loads(args.trace.read_text());rows=[];uncaptured=[]
    for event,e in enumerate(trace["events"]):
        for substep,phases in enumerate(e.get("engineStep1Phases",[])):
            owners=[p["engine"] for p in phases if p["phase"]=="comPos"]
            if len(owners)!=1:raise ValueError("unique comPos owner required")
            engine=owners[0];a=engine["arrays"];m=engine["model"]
            if engine["contacts"] and not any(k.endswith("_jacp") for k in a):
                uncaptured.append(dict(event=event,substep=substep,reason="no browser Jacobian outputs recorded"));continue
            for key,width in (("cdof",108),("subtree_com",12)):
                Reader(a.get(key))
                if len(a[key])!=width:raise ValueError("complete Jacobian read-set required")
            for key in ("body_rootid","body_parentid","body_dofadr","body_dofnum","dof_parentid","geom_bodyid"):
                Reader(m.get(key))
                if any(type(x)is not int for x in m[key]):raise ValueError("integral Jacobian topology required")
            for index,contact in enumerate(engine["contacts"]):
                Reader(contact.get("pos"))
                if len(contact["pos"])!=3:raise ValueError("complete Jacobian point required")
                for side in range(2):
                    geom=contact["geom1" if side==0 else "geom2"]
                    if type(geom)is not int or not 0<=geom<len(m["geom_bodyid"]):raise ValueError("bounded Jacobian geom required")
                    body=m["geom_bodyid"][geom]
                    if not 0<=body<4:raise ValueError("bounded Jacobian body required")
                    for suffix in ("jacp","jacr"):
                        Reader(a.get(f"contact{index}_side{side}_{suffix}"))
                        if len(a[f"contact{index}_side{side}_{suffix}"])!=54:raise ValueError("complete captured Jacobian required")
                    rows.append((event,substep,index,side,engine,body,contact["pos"]))
    guard=OriginalIntegrator(args.reference_library);anchor=guard.anchor;routine=anchor.library.mj_jac
    address=ctypes.cast(routine,ctypes.c_void_p).value;base=ctypes.cast(anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
    dladdr=ctypes.CDLL(None).dladdr;dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int;info=DlInfo()
    if address!=base+0x4bc88 or not dladdr(address,ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve()!=anchor.path:raise ValueError("original Jacobian image/address differs")
    ptr=ctypes.POINTER(ctypes.c_double);routine.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ptr,ptr,ptr,ctypes.c_int];routine.restype=None
    import mujoco
    from marble_source_play_trace import native_mujoco_provenance
    if Path(native_mujoco_provenance(mujoco)["activeEngineLibrary"]["path"]).resolve()!=anchor.path:raise ValueError("owned original Jacobian image differs")
    sys.path.insert(0,str(args.source_root.resolve()))
    from neural_workshop import marblemaze as source
    from marble_source_capture import float32_abi_tray
    sim=source.Simulation(float32_abi_tray(source.deal(trace["rung"],seed=trace["boardSeed"])));sim._ensure_engine();m,d=sim._model,sim._data
    if (m.nbody,m.nv)!=(4,18) or m.body_weldid.tolist()!=list(range(4)):raise ValueError("qualified standalone Jacobian layout required")
    results=[];synthetic_calls=0;rng=random.Random(0x4bc88)
    for event,substep,index,side,engine,body,point in rows:
        for key in ("body_rootid","body_parentid","body_dofadr","body_dofnum","dof_parentid","geom_bodyid"):
            if getattr(m,key).tolist()!=engine["model"][key]:raise ValueError("owned Jacobian topology differs")
        for key in ("cdof","subtree_com"):
            getattr(d,key).ravel()[:]=engine["arrays"][key]
            if bits(getattr(d,key).ravel())!=bits(engine["arrays"][key]):raise ValueError("Jacobian copy differs")
        jp=(ctypes.c_double*54)();jr=(ctypes.c_double*54)();position=(ctypes.c_double*3)(*point)
        routine(ctypes.c_void_p(int(m._address)),ctypes.c_void_p(int(d._address)),jp,jr,position,body)
        if bits(position)!=bits(point):raise ValueError("Jacobian mutated point")
        for key in ("cdof","subtree_com"):
            if bits(getattr(d,key).ravel())!=bits(engine["arrays"][key]):raise ValueError("Jacobian mutated input")
        differences={suffix:[i for i,(x,y) in enumerate(zip(values,engine["arrays"][f"contact{index}_side{side}_{suffix}"])) if x!=y] for suffix,values in (("jacp",jp),("jacr",jr))}
        modeled=reconstruct(engine,body,point)
        if bits(modeled["jacp"])!=bits(jp) or bits(modeled["jacr"])!=bits(jr):raise ValueError("complete Jacobian reconstruction differs from original")
        results.append(dict(event=event,substep=substep,contact=index,side=side,differences=differences,actualOriginalBits=dict(jacp=bits(jp),jacr=bits(jr))))
        for case in range(10):
            stress=copy.deepcopy(engine);draw=lambda:rng.uniform(-2.,2.)*2**rng.randrange(-8,9)
            for key in ("cdof","subtree_com"):
                stress["arrays"][key]=[draw() for _ in stress["arrays"][key]]
                getattr(d,key).ravel()[:]=stress["arrays"][key]
                if bits(getattr(d,key).ravel())!=bits(stress["arrays"][key]):raise ValueError("synthetic Jacobian copy differs")
            pt=[draw() for _ in range(3)];position=(ctypes.c_double*3)(*pt)
            routine(ctypes.c_void_p(int(m._address)),ctypes.c_void_p(int(d._address)),jp,jr,position,body)
            expected=reconstruct(stress,body,pt)
            if bits(jp)!=bits(expected["jacp"]) or bits(jr)!=bits(expected["jacr"]):raise ValueError("synthetic complete Jacobian reconstruction differs")
            synthetic_calls+=1
    print(json.dumps(dict(traceSha256=hashlib.sha256(args.trace.read_bytes()).hexdigest(),calls=len(results),syntheticCalls=synthetic_calls,modelDifferentValues=0,uncapturedBoundaries=uncaptured,differentValues={key:sum(len(r["differences"][key]) for r in results) for key in ("jacp","jacr")},results=results,capturedBrowserZeroSignsQualified=False,ordinaryTrajectoryAcceptance=False,promoted=False),indent=2))


if __name__=="__main__":main()
