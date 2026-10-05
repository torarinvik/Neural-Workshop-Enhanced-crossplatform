"""Compare complete compiled free-solve stages to qualified original public calls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from marble_integrator_readset import named_phase, validated_packet


def compare(trace, original):
    if original.get("referenceSha256") != "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c":
        raise ValueError("actual original reference identity required")
    rows=[];counts=dict(matrix=0,lu=0,pivots=0,solution=0)
    for boundary in original["boundaries"]:
        phase=named_phase(trace["events"][boundary["event"]],boundary["substep"],"checkAcc")
        packet=phase["engine"]["integratorReadSet"]
        validated_packet(packet,"checkAcc")
        actual=boundary["actualOriginal"]
        if actual.get("originalPublicLocalSolveAdvanceQualified") is not True:
            raise ValueError("enclosing original velocity qualification required")
        probe=phase.get("freeJointSolveProbe")
        nj=packet["dimensions"]["njnt"]
        if not isinstance(probe,list) or len(probe)!=84*nj or any(type(v) not in (int,float) or not math.isfinite(v) for v in probe):
            raise ValueError("complete finite compiled free-solve probe required")
        if len(actual["originalPublicLocalStages"])!=nj:raise ValueError("complete original solve stages required")
        differences={}
        for joint,stage in enumerate(actual["originalPublicLocalStages"]):
            if stage["joint"]!=joint:raise ValueError("ordered original solve ownership required")
            for field,key,start,width in (("matrix","matrixBits",0,36),("lu","luBits",36,36),("pivots","pivots",72,6),("solution","solutionBits",78,6)):
                values=probe[84*joint+start:84*joint+start+width]
                browser=values if field=="pivots" else [struct.pack(">d",float(v)).hex() for v in values]
                expected=stage[key]
                if len(expected)!=width:raise ValueError("complete original stage width required")
                diff=[dict(joint=joint,index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(expected,browser)) if x!=y]
                if diff: differences.setdefault(field,[]).extend(diff);counts[field]+=len(diff)
        rows.append(dict(event=boundary["event"],substep=boundary["substep"],differences=differences))
    return dict(boundaries=rows,differentValues=counts,ordinaryTrajectoryAcceptance=False,promoted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace",type=Path);parser.add_argument("original",type=Path)
    args=parser.parse_args()
    raw=args.original.read_bytes();original=json.loads(raw)
    if original["traceSha256"]!=hashlib.sha256(args.trace.read_bytes()).hexdigest():raise ValueError("original report trace identity differs")
    result=compare(json.loads(args.trace.read_text()),original)
    result.update(traceSha256=original["traceSha256"],originalReportSha256=hashlib.sha256(raw).hexdigest())
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":main()
