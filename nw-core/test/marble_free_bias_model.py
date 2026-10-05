"""Diagnostic fused reconstruction; qualification is mandatory, not assumed."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from marble_integrator_readset import named_phase, validated_packet


def dot(a,b):return math.fma(a[2],b[2],math.fma(a[0],b[0],a[1]*b[1]))
def cross(a,b):return [math.fma(a[1],b[2],-(a[2]*b[1])),math.fma(a[2],b[0],-(a[0]*b[2])),math.fma(a[0],b[1],-(a[1]*b[0]))]
def matmul(a,b):return [dot(a[3*r:3*r+3],[b[c],b[3+c],b[6+c]]) for r in range(3) for c in range(3)]
def transpose(a):return [a[3*c+r] for r in range(3) for c in range(3)]


def reconstruct(packet,joint):
    decoded=validated_packet(packet,"checkAcc");a=decoded["arrays"];m=decoded["model"]
    body=joint+1;R=a["xmat"][9*body:9*body+9];Xi=a["ximat"][9*body:9*body+9]
    inertia=m["body_inertia"][3*body:3*body+3];mass=m["body_mass"][body]
    s=[a["xipos"][3*body+i]-a["xpos"][3*body+i] for i in range(3)]
    v=a["qvel"][6*joint+3:6*joint+6];w=[dot(R[3*i:3*i+3],v) for i in range(3)]
    XiI=[Xi[3*r+c]*inertia[c] for r in range(3) for c in range(3)]
    Iw=[0.]*9
    for r in range(3):
        for c in range(r,3):Iw[3*r+c]=Iw[3*c+r]=dot(XiI[3*r:3*r+3],Xi[3*c:3*c+3])
    ws=cross(w,s);Iww=[dot(Iw[3*r:3*r+3],w) for r in range(3)];wdot=dot(w,s)
    K=[math.fma(s[0],w[0],-wdot),math.fma(s[0],w[1],-ws[2]),math.fma(s[0],w[2],ws[1]),
       math.fma(s[1],w[0],ws[2]),math.fma(s[1],w[1],-wdot),math.fma(s[1],w[2],-ws[0]),
       math.fma(s[2],w[0],-ws[1]),math.fma(s[2],w[1],ws[0]),math.fma(s[2],w[2],-wdot)]
    lin=matmul(K,R);C=[0.]*9
    additions=[[0.,Iww[2],-Iww[1]],[-Iww[2],0.,Iww[0]],[Iww[1],-Iww[0],0.]]
    for c in range(3):
        sx=cross(s,[K[c],K[3+c],K[6+c]]);wx=cross(w,[Iw[c],Iw[3+c],Iw[6+c]])
        for r in range(3):C[3*r+c]=math.fma(-mass,sx[r],wx[r])+additions[r][c]
    rot=matmul(matmul(transpose(R),C),R)
    B=[0.]*36
    for r in range(3):
        for c in range(3):B[6*r+3+c]=-mass*lin[3*r+c];B[6*(3+r)+3+c]=rot[3*r+c]
    return B


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("trace",type=Path);p.add_argument("original",type=Path);args=p.parse_args()
    t=json.loads(args.trace.read_text());original=json.loads(args.original.read_text());rows=[]
    if original.get("referenceSha256") != "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c" or original.get("traceSha256") != hashlib.sha256(args.trace.read_bytes()).hexdigest():
        raise ValueError("actual original reference and current trace identity required")
    for boundary in original["boundaries"]:
        packet=named_phase(t["events"][boundary["event"]],boundary["substep"],"checkAcc")["engine"]["integratorReadSet"]
        for stage in boundary["actualOriginal"]["originalPublicLocalStages"]:
            if len(stage["biasBits"])!=36:raise ValueError("complete original public bias output required")
            actual=[struct.pack(">d",v).hex() for v in reconstruct(packet,stage["joint"])]
            differences=[i for i,(a,b) in enumerate(zip(actual,stage["biasBits"])) if a!=b]
            rows.append(dict(event=boundary["event"],substep=boundary["substep"],joint=stage["joint"],differentIndices=differences))
    print(json.dumps(dict(calls=len(rows),differentCalls=sum(bool(r["differentIndices"]) for r in rows),differentValues=sum(len(r["differentIndices"]) for r in rows),qualified=not any(r["differentIndices"] for r in rows),productionChange=False,rows=rows),indent=2))


if __name__=="__main__":main()
