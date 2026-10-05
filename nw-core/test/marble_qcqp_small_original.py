"""Exact original exported QCQP2/3 routines, independent of generic QCQP5."""
import ctypes
import math
from pathlib import Path
import random

from marble_cone_update_oracle import Reader
from marble_primal_eval_oracle import OriginalEval, ORIGINAL_EVAL_OFFSET, DlInfo

OFFSETS={2:0x1203e8,3:0x1204f0}


def validated(matrix,rhs,scaling,radius,n):
    if type(n) is not int or n not in (2,3):
        raise ValueError("small QCQP needs exactly two or three tangent dimensions")
    for values,length in ((matrix,n*n),(rhs,n),(scaling,n),([radius],1)):
        Reader(values)
        if len(values)!=length:raise ValueError("small QCQP complete operand width differs")
    if radius<0 or any(v<=0 for v in scaling):
        raise ValueError("small QCQP needs nonnegative radius and positive scaling")


def synthetic_inputs(n,count=1000):
    if n not in (2,3):raise ValueError("small QCQP dimension differs")
    rng=random.Random(1203+n)
    for case in range(count):
        v=[rng.uniform(-1.,1.) for _ in range(n)]
        matrix=[v[i]*v[j]+(2.**rng.randrange(-8,8) if i==j else 0.)
                for i in range(n) for j in range(n)]
        rhs=[rng.uniform(-1.,1.)*2.**rng.randrange(-8,8) for _ in range(n)]
        scaling=[2.**rng.randrange(-5,5) for _ in range(n)]
        radius=2.**rng.randrange(-6,8)
        if case%50==0:matrix=[0.]*(n*n)
        if case%25==1:rhs=[0.]*n
        yield matrix,rhs,scaling,radius


def wheel_qcqp2(matrix,rhs,scaling,radius):
    """Disassembly-order model. Intermediates reconstructed, not captured."""
    validated(matrix,rhs,scaling,radius,2)
    if not callable(getattr(math,"fma",None)):
        raise ValueError("QCQP2 order requires correctly rounded fma")
    fma=math.fma
    a=matrix[0]*scaling[0]*scaling[0]
    d=matrix[3]*scaling[1]*scaling[1]
    c=matrix[1]*scaling[0]*scaling[1]
    b1=rhs[0]*scaling[0];b2=rhs[1]*scaling[1]
    lam=0.;steps=[]
    for iteration in range(20):
        a1=a+lam;d1=d+lam
        det=fma(a1,d1,-(c*c))
        row=dict(iteration=iteration,lambdaBefore=lam,determinant=det)
        steps.append(row)
        if det<1e-10:
            row["reason"]="rank"
            return dict(active=False,rawForce=[0.,0.],steps=steps)
        inv=1./det
        P11=d1*inv;P22=a1*inv;P12=(-c)*inv
        v1=fma(-P11,b1,(-P12)*b2)
        v2=fma(-P12,b1,(-P22)*b2)
        norm=fma(v1,v1,v2*v2)
        value=fma(-radius,radius,norm)
        row.update(inverse=[P11,P12,P12,P22],solved=[v1,v2],norm=norm,value=value)
        if value<1e-10:
            row["reason"]="value";break
        cross=((P12+P12)*v1)*v2
        derivativeHalf=fma(P22*v2,v2,fma(P11*v1,v1,cross))
        delta=value/(derivativeHalf+derivativeHalf)
        row.update(derivativeHalf=derivativeHalf,delta=delta)
        if delta<1e-10:
            row["reason"]="delta";break
        lam+=delta
        row.update(lambdaAfter=lam,reason="update" if iteration<19 else "limit")
    result=dict(active=lam!=0.,rawForce=[v1*scaling[0],v2*scaling[1]],steps=steps)
    Reader(result["rawForce"])
    return result


class OriginalQCQPSmall:
    def __init__(self,path):
        self.anchor=OriginalEval(path)
        base=ctypes.cast(self.anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
        dladdr=ctypes.CDLL(None).dladdr
        dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int
        ptr=ctypes.POINTER(ctypes.c_double);self.routines={}
        for n,offset in OFFSETS.items():
            routine=getattr(self.anchor.library,"mju_QCQP"+str(n))
            address=ctypes.cast(routine,ctypes.c_void_p).value;info=DlInfo()
            if (address!=base+offset or not dladdr(address,ctypes.byref(info)) or
                    not info.filename or Path(info.filename.decode()).resolve()!=self.anchor.path):
                raise ValueError("original small QCQP symbol/image/address differs")
            # engine_util_solve.h at pinned 13827e9: four number pointers, radius.
            routine.argtypes=[ptr,ptr,ptr,ptr,ctypes.c_double];routine.restype=ctypes.c_int
            self.routines[n]=routine

    def solve(self,matrix,rhs,scaling,radius,n):
        validated(matrix,rhs,scaling,radius,n)
        make=lambda values:(ctypes.c_double*len(values))(*values)
        A,b,d=make(matrix),make(rhs),make(scaling);out=(ctypes.c_double*n)()
        active=self.routines[n](out,A,b,d,radius)
        raw=list(out);Reader(raw)
        if active not in (0,1) or list(A)!=matrix or list(b)!=rhs or list(d)!=scaling:
            raise ValueError("original small QCQP postconditions differ")
        return dict(active=bool(active),rawForce=raw)
