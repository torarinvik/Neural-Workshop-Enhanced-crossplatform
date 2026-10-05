"""Original-wheel qualified quadratic order, not private costChange output.

Only n=2/3/5 are modeled. Each row uses the qualified original dot order,
then the arm64 wheel's outer FMADD in increasing row order. Rows and final
cost reconstruction are models; only the original exported return is actual.
"""
import argparse
import json
import math
from pathlib import Path
import random
import struct

from marble_cone_update_oracle import Reader
from marble_costchange_trace import OriginalCostPrimitives,capture_cost
from marble_native_dot_oracle import wheel_dot
from marble_primal_eval_oracle import REFERENCE_SHA256


def wheel_quadratic(left,matrix,right):
    for values in (left,matrix,right):Reader(values)
    n=len(left)
    if n not in (2,3,5) or len(right)!=n or len(matrix)!=n*n:
        raise ValueError("quadratic model requires complete n=2/3/5 operands")
    if not hasattr(math,"fma"):raise ValueError("requires correctly rounded fma")
    result=0.
    for i in range(n):
        row=wheel_dot(matrix[i*n:(i+1)*n],right)
        result=math.fma(left[i],row,result)
    Reader([result])
    return result


def synthetic_inputs(count=1000):
    if type(count) is not int or not 6<=count<=10000:raise ValueError("bounded synthetic count required")
    rng=random.Random(0xC057CA11)
    for i in range(count):
        n=(2,3,5)[i%3]
        if i<6:
            sign=-1. if i>=3 else 1.
            left=[math.copysign(0.,sign)]*n
            right=[sign*(j+1.) for j in range(n)]
            matrix=[float(r==c) for r in range(n) for c in range(n)]
            residual=[sign]*n
        else:
            draw=lambda:math.ldexp(rng.uniform(-2.,2.),rng.randrange(-15,16))
            left=[draw() for _ in range(n)];right=[draw() for _ in range(n)]
            residual=[draw() for _ in range(n)]
            matrix=[draw() for _ in range(n*n)]
            # Cover SPD and asymmetric matrices, correlated vectors and
            # cancellation as well as scale imbalance. No nonfinite operands.
            if i%4==0:
                matrix=[sum(matrix[k*n+r]*matrix[k*n+c] for k in range(n))+
                        float(r==c) for r in range(n) for c in range(n)]
                right=list(left)
            elif i%4==1:
                matrix[n]=-matrix[1]
                left[-1]=-left[0]
        yield left,matrix,right,residual


def qualified_row(original,left,matrix,right,residual,kind,label):
    actual=original.evaluate_operands(left,matrix,right,residual)
    model=wheel_quadratic(left,matrix,right)
    bits=lambda v:struct.pack("!d",v).hex()
    if bits(model)!=bits(actual["quadratic"]):
        raise ValueError("quadratic model differs from actual original: "+label)
    if bits(wheel_dot(left,residual))!=bits(actual["dot"]):
        raise ValueError("dot model differs from actual original: "+label)
    n=len(left)
    return dict(kind=kind,label=label,referenceSha256=REFERENCE_SHA256,
        values=[1,n]+left+matrix+right+residual,
        quadratic=actual["quadratic"],dot=actual["dot"],
        expectedBits={k:bits(v) for k,v in actual.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();trace=json.loads(args.trace.read_text())
    selected=[(e,s,c) for e,event in enumerate(trace["events"])
        for s,t in enumerate(event.get("newtonTraces",[])) for c in capture_cost(t)]
    if not selected:raise ValueError("no captured assigned cost operands")
    original=OriginalCostPrimitives(args.reference_library)
    for e,s,c in selected:
        print(json.dumps(qualified_row(original,c["delta"],c["matrix"],c["delta"],
            c["residual"],"captured",f"event{e}-step{s}-ordinal{c['ordinal']}"),allow_nan=False))
    for i,values in enumerate(synthetic_inputs()):
        print(json.dumps(qualified_row(original,*values,"synthetic",f"synthetic{i}"),allow_nan=False))


if __name__=="__main__":main()
