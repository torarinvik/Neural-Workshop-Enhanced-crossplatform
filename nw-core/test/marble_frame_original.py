"""Qualify complete makeFrame results on the pinned original image."""
import argparse
import ctypes
import json
import math
import random
from pathlib import Path
from marble_integrator_original import OriginalIntegrator, bits
from marble_primal_eval_oracle import ORIGINAL_EVAL_OFFSET, DlInfo


def dot(a,b):
    return math.fma(a[2],b[2],math.fma(a[0],b[0],a[1]*b[1]))


def normalize(a):
    n=math.sqrt(dot(a,a))
    return ([1.,0.,0.] if n<1e-15 else [v*(1./n) for v in a]),n


def frame_model(frame):
    if len(frame)!=9 or not all(math.isfinite(v) for v in frame):
        raise ValueError("complete finite frame required")
    x,n=normalize(frame[:3])
    if n<.5:raise ValueError("undefined contact normal")
    y=frame[3:6]
    if dot(y,y)<.25:
        y=[0.,1.,0.] if -.5<x[1]<.5 else [0.,0.,1.]
    projection=dot(x,y)
    y,_=normalize([y[i]-x[i]*projection for i in range(3)])
    z=[math.fma(x[1],y[2],-(x[2]*y[1])),
       math.fma(x[2],y[0],-(x[0]*y[2])),
       math.fma(x[0],y[1],-(x[1]*y[0]))]
    return x+y+z


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw_report",type=Path)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args()
    guard=OriginalIntegrator(args.reference_library)
    base=ctypes.cast(guard.anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
    address=base+0x12bc0c;info=DlInfo()
    dladdr=ctypes.CDLL(None).dladdr
    dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int
    if not dladdr(address,ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve()!=guard.anchor.path:
        raise ValueError("original frame image differs")
    routine=ctypes.CFUNCTYPE(None,ctypes.POINTER(ctypes.c_double))(address)
    report=json.loads(args.raw_report.read_text());cases=[]
    for row in report["results"]:
        cases.append((row["label"],row["originalNormal"]+[0.]*6,row["capturedNormal"]))
    rng=random.Random(0x12bc0c)
    for i in range(1000):
        x=[rng.uniform(-2.,2.) for _ in range(3)]
        if math.sqrt(dot(x,x))<.5:x[0]+=2.
        y=[0.]*3 if i%2 else [rng.uniform(-2.,2.) for _ in range(3)]
        cases.append((f"synthetic{i}",x+y+[0.]*3,None))
    for label,values,captured in cases:
        expected=frame_model(values)  # Validate before a native error can abort.
        out=(ctypes.c_double*9)(*values);routine(out)
        if bits(out)!=bits(expected):
            raise ValueError(f"complete frame model differs: {label}: "
                             f"{[(i,a,b) for i,(a,b) in enumerate(zip(out,frame_model(values))) if bits([a])!=bits([b])]}")
        if captured is not None and bits(out[:3])!=bits(captured):
            raise ValueError("original rebuilt normal differs from captured contact")
    print(json.dumps(dict(captured=len(report["results"]),synthetic=1000,
                          completeDifferentValues=0,promoted=False)))


if __name__=="__main__":main()
