"""Qualify original quaternion multiplication ordering, without runtime edits.

Normalization and axis-angle are actual original public calls, not reconstructed
private intermediates. Their composition is checked against complete original
quatIntegrate returns on captured inputs and synthetic finite inputs.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path
import random
import struct

from marble_primal_eval_oracle import OriginalEval, REFERENCE_SHA256
from marble_integrator_readset import validated_packet, named_phase


def multiply(a,b):
    f=math.fma
    return [f(-a[3],b[3],f(-a[2],b[2],f(a[0],b[0],-(a[1]*b[1])))),
            f(-a[3],b[2],f(a[2],b[3],f(a[0],b[1],a[1]*b[0]))),
            f(a[3],b[1],f(a[2],b[0],f(a[0],b[2],-(a[1]*b[3])))),
            f(a[3],b[0],f(-a[2],b[1],f(a[0],b[3],a[1]*b[2])))]


def bits(values): return [struct.pack(">d",float(x)).hex() for x in values]


def normalize4_model(q):
    if len(q)!=4 or not all(math.isfinite(x) for x in q):
        raise ValueError("complete finite quaternion required")
    n=math.sqrt(math.fma(q[3],q[3],math.fma(q[2],q[2],math.fma(q[0],q[0],q[1]*q[1]))))
    return n, ([1.,0.,0.,0.] if n<1e-15 else
               [x*(1./n) for x in q] if abs(n-1)>1e-15 else list(q))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path);p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();trace=json.loads(args.trace.read_text())
    cases=[]
    for e,event in enumerate(trace["events"]):
        for s in range(len(event.get("engineStep2Phases",[]))):
            before=named_phase(event,s,"checkAcc")["engine"]["integratorReadSet"]
            after=named_phase(event,s,"implicit")["engine"]["integratorReadSet"]
            a=validated_packet(before,"checkAcc");b=validated_packet(after,"implicit")
            for joint in range(before["dimensions"]["njnt"]):
                cases.append(dict(label=f"event{e}/step{s}/joint{joint}",q=a["arrays"]["qpos"][7*joint+3:7*joint+7],v=b["outputs"]["qvel"][6*joint+3:6*joint+6],dt=a["options"]["timestep"],browser=after["outputBits"]["qpos"][7*joint+3:7*joint+7]))
    captured_count=len(cases)
    if not captured_count:raise ValueError("no captured quaternion operands")
    anchor=OriginalEval(args.reference_library);lib=anchor.library
    ptr=ctypes.POINTER(ctypes.c_double)
    for name,signature,result in (("mju_quatIntegrate",[ptr,ptr,ctypes.c_double],None),("mju_normalize3",[ptr],ctypes.c_double),("mju_normalize4",[ptr],ctypes.c_double),("mju_axisAngle2Quat",[ptr,ptr,ctypes.c_double],None),("mju_mulQuat",[ptr,ptr,ptr],None)):
        routine=getattr(lib,name);routine.argtypes=signature;routine.restype=result
    rng=random.Random(0x12a96c)
    for i in range(1000):
        cases.append(dict(label=f"synthetic{i}",q=[rng.uniform(-2,2) for _ in range(4)],v=[rng.uniform(-100,100) for _ in range(3)],dt=rng.uniform(.0001,.1)))
    make=lambda v:(ctypes.c_double*len(v))(*v)
    results=[]
    for case in cases:
        q,v,dt=case["q"],case["v"],case["dt"]
        actual=make(q);velocity=make(v);lib.mju_quatIntegrate(actual,velocity,dt)
        if bits(velocity)!=bits(v):raise ValueError("original quaternion call mutated velocity")
        axis=make(v);norm=lib.mju_normalize3(axis);angle=dt*norm
        modeled_norm=math.sqrt(math.fma(v[2],v[2],math.fma(v[0],v[0],v[1]*v[1])))
        modeled_axis=([1.,0.,0.] if modeled_norm<1e-15 else
                      [x*(1./modeled_norm) for x in v])
        if bits([norm])!=bits([modeled_norm]) or bits(axis)!=bits(modeled_axis):
            raise ValueError("complete normalize3 reconstruction differs: "+case["label"])
        rotation=make([0.]*4);lib.mju_axisAngle2Quat(rotation,axis,angle)
        unit_rotation=make([0.]*4)
        lib.mju_axisAngle2Quat(unit_rotation,make([1.,0.,0.]),angle)
        if bits(rotation)!=bits([unit_rotation[0],
                                 *[x*unit_rotation[1] for x in axis]]):
            raise ValueError("axis-angle component product differs: "+case["label"])
        normalized=make(q);norm4=lib.mju_normalize4(normalized)
        modeled_norm4,modeled_q=normalize4_model(q)
        if bits([norm4])!=bits([modeled_norm4]) or bits(normalized)!=bits(modeled_q):
            raise ValueError("complete normalize4 reconstruction differs: "+case["label"])
        product=make([0.]*4);lib.mju_mulQuat(product,normalized,rotation)
        reconstructed=multiply(list(normalized),list(rotation))
        if bits(product)!=bits(reconstructed):raise ValueError("machine-order multiplication differs: "+case["label"])
        if bits(actual)!=bits(reconstructed):raise ValueError("complete original quaternion composition differs: "+case["label"])
        differences=[j for j,(x,y) in enumerate(zip(bits(actual),case.get("browser",bits(actual)))) if x!=y]
        results.append(dict(label=case["label"],q=q,v=v,dt=dt,originalBits=bits(actual),
                            axisBits=bits(axis),normalizedBits=bits(normalized),rotationBits=bits(rotation),
                            normBits=bits([norm]),angleBits=bits([angle]),
                            sineBits=bits([unit_rotation[1]]),cosineBits=bits([unit_rotation[0]]),
                            browserDifferentIndices=differences))
    print(json.dumps(dict(referenceSha256=REFERENCE_SHA256,captured=captured_count,synthetic=1000,completeOriginalCompositionDifferences=0,multiplicationModelDifferences=0,capturedBrowserDifferentValues=sum(len(x["browserDifferentIndices"]) for x in results),normalizationAndAxisAngleAreOriginalPublicCalls=True,originalPrivateIntermediateCapture=False,ordinaryTrajectoryAcceptance=False,promoted=False,results=results),indent=2))


if __name__=="__main__":main()
