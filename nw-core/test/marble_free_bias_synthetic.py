"""Varied finite owned operands against the guarded original public bias call."""
import argparse
import copy
import ctypes
import json
import random
import struct
from pathlib import Path
from marble_integrator_original import OriginalIntegrator, bits
from marble_integrator_readset import named_phase, validated_packet
from marble_free_bias_model import reconstruct


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("trace",type=Path);p.add_argument("--reference-library",type=Path,required=True);args=p.parse_args()
    trace=json.loads(args.trace.read_text());templates=[]
    for event in trace["events"]:
        for substep in range(len(event.get("engineStep2Phases",[]))):
            packet=named_phase(event,substep,"checkAcc")["engine"]["integratorReadSet"]
            validated_packet(packet,"checkAcc");templates.append(packet)
    if not templates:raise ValueError("complete bias templates required")
    guard=OriginalIntegrator(args.reference_library)
    import mujoco
    from marble_source_play_trace import native_mujoco_provenance
    native=native_mujoco_provenance(mujoco)
    if Path(native["activeEngineLibrary"]["path"]).resolve()!=guard.anchor.path:raise ValueError("owned model image differs")
    model=mujoco.MjModel.from_xml_string('<mujoco><worldbody>'+3*'<body><freejoint/><geom size=".1"/></body>'+'</worldbody></mujoco>')
    data=mujoco.MjData(model);rng=random.Random(0x669f8);rows=[]
    for case in range(1000):
        packet=copy.deepcopy(templates[case%len(templates)])
        def set_values(owner,key,values):
            packet[owner][key]=values
            packet["modelBits" if owner=="model" else "arrayBits"][key]=bits(values)
        draw=lambda:rng.uniform(-2,2)*2**rng.randrange(-8,9)
        set_values("arrays","qvel",[draw() for _ in range(18)])
        set_values("arrays","xpos",[draw() for _ in range(12)])
        set_values("arrays","xipos",[draw() for _ in range(12)])
        set_values("model","body_mass",[0.]+[2**rng.uniform(-8,8) for _ in range(3)])
        set_values("model","body_inertia",[0.]*3+[2**rng.uniform(-8,8) for _ in range(9)])
        operands=validated_packet(packet,"checkAcc")
        for key in ("qvel","xpos","xipos","xmat","ximat"):getattr(data,key).ravel()[:]=operands["arrays"][key]
        for key in ("body_mass","body_inertia"):getattr(model,key).ravel()[:]=operands["model"][key]
        for owner,fields,values in ((data,("qvel","xpos","xipos","xmat","ximat"),operands["arrays"]),(model,("body_mass","body_inertia"),operands["model"])):
            for key in fields:
                if bits(getattr(owner,key).ravel())!=bits(values[key]):raise ValueError("synthetic original operand copy differs: "+key)
        for joint in range(3):
            output=(ctypes.c_double*36)()
            guard.anchor.library.mjd_freeBias_vel(ctypes.c_void_p(int(model._address)),ctypes.c_void_p(int(data._address)),joint,output)
            modeled=bits(reconstruct(packet,joint));expected=bits(output)
            indices=[i for i,(a,b) in enumerate(zip(modeled,expected)) if a!=b]
            rows.append(dict(case=case,joint=joint,differentIndices=indices))
    print(json.dumps(dict(cases=1000,calls=len(rows),differentCalls=sum(bool(r["differentIndices"]) for r in rows),differentValues=sum(len(r["differentIndices"]) for r in rows),qualified=not any(r["differentIndices"] for r in rows),productionChange=False,nativeRuntime=native,rows=rows),indent=2))


if __name__=="__main__":main()
