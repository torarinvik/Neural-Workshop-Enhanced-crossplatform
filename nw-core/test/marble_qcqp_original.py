"""Exact-wheel-only generic five-tangent QCQP test bridge.

The original generic kernel is a local (not dlsym-exported) symbol. Reuse the
strict loaded-image/ABI/public-dot anchor checks, then guard its own entry
bytes. This is not a portable API and does not include projectEllipsoid.
"""
import ctypes
import math
import random
from pathlib import Path

from marble_cone_update_oracle import Reader
from marble_primal_eval_oracle import OriginalEval, ORIGINAL_EVAL_OFFSET, DlInfo

QCQP_OFFSET=0x120704
QCQP_ENTRY=bytes.fromhex("ef3bb66ded33016deb2b026de923036d")

def synthetic_inputs():
    """Same bounded 1,000-case qualification matrix used by the native tests."""
    rng=random.Random(42002111)
    for case in range(1000):
        v=[rng.uniform(-1.,1.) for _ in range(5)]
        matrix=[v[i]*v[j]+(2.**rng.randrange(-8,8) if i==j else 0.)
                for i in range(5) for j in range(5)]
        rhs=[rng.uniform(-1.,1.)*2.**rng.randrange(-8,8) for _ in range(5)]
        scaling=[2.**rng.randrange(-5,5) for _ in range(5)]
        radius=2.**rng.randrange(-6,8)
        if case%50==0:matrix=[0.]*25
        if case%25==1:rhs=[0.]*5
        yield matrix,rhs,scaling,radius


def probe_packet(matrix,rhs,scaling,radius):
    validated(matrix,rhs,scaling,radius)
    return [1,5,radius]+matrix+rhs+scaling


def validated(matrix,rhs,scaling,radius):
    for values,length in ((matrix,25),(rhs,5),(scaling,5),([radius],1)):
        Reader(values)
        if len(values)!=length:
            raise ValueError("generic QCQP bridge requires exactly five tangent dimensions")
    if radius<0 or any(v<=0 for v in scaling):
        raise ValueError("QCQP scaling must be positive and radius nonnegative")


class OriginalQCQP5:
    def __init__(self,path):
        self.anchor=OriginalEval(path)
        base=ctypes.cast(self.anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET
        address=base+QCQP_OFFSET
        if ctypes.string_at(address,len(QCQP_ENTRY))!=QCQP_ENTRY:
            raise ValueError("original generic QCQP entry bytes differ")
        ptr=ctypes.POINTER(ctypes.c_double)
        self.routine=ctypes.CFUNCTYPE(ctypes.c_int,ptr,ptr,ptr,ptr,ctypes.c_double,ctypes.c_int)(address)

    def decomposed(self,matrix,rhs,scaling,radius):
        """Diagnostic wheel-order driver using actual original public primitives.

        The exact-wheel generic kernel inlines factorization/dots but calls
        cholSolve. This driver is independently checked against that actual
        generic kernel; matching final output alone does not validate every
        reconstructed intermediate or qualify a browser trajectory.
        """
        validated(matrix,rhs,scaling,radius)
        if not callable(getattr(math,"fma",None)):
            raise ValueError("decomposed original QCQP needs correctly rounded fma")
        library=self.anchor.library
        dladdr=ctypes.CDLL(None).dladdr
        dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)]
        dladdr.restype=ctypes.c_int
        for name in ("mju_cholFactor","mju_cholSolve","mju_dot"):
            info=DlInfo();address=ctypes.cast(getattr(library,name),ctypes.c_void_p).value
            if not dladdr(address,ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve()!=self.anchor.path:
                raise ValueError("QCQP public primitive loaded from another image")
        ptr=ctypes.POINTER(ctypes.c_double)
        factor=library.mju_cholFactor
        factor.argtypes=[ptr,ctypes.c_int,ctypes.c_double];factor.restype=ctypes.c_int
        solve=library.mju_cholSolve
        solve.argtypes=[ptr,ptr,ptr,ctypes.c_int];solve.restype=None
        dot=library.mju_dot
        dot.argtypes=[ptr,ptr,ctypes.c_int];dot.restype=ctypes.c_double
        make=lambda values:(ctypes.c_double*len(values))(*values)
        A=[matrix[i*5+j]*scaling[i]*scaling[j] for i in range(5) for j in range(5)]
        b=[rhs[i]*scaling[i] for i in range(5)]
        Reader(A);Reader(b)
        lam=0.;steps=[]
        for iteration in range(20):
            ala=A.copy()
            for i in range(5):ala[i*6]+=lam
            Reader(ala)
            matrix_buffer=make(ala)
            rank=factor(matrix_buffer,5,1e-10)
            if not 0<=rank<=5:raise ValueError("original Cholesky rank out of bounds")
            row=dict(iteration=iteration,lambdaBefore=lam,rank=rank,
                     scaledMatrix=A,scaledRhs=b,factor=list(matrix_buffer))
            steps.append(row)
            if rank<5:
                row["reason"]="rank"
                return dict(active=False,rawForce=[0.]*5,steps=steps)
            vec=(ctypes.c_double*5)()
            solve(vec,matrix_buffer,make(b),5)
            x=[-v for v in vec]
            Reader(x)
            norm=dot(make(x),make(x),5)
            value=math.fma(-radius,radius,norm)
            Reader([norm,value])
            row.update(solved=x,norm=norm,value=value)
            if value<1e-10:
                row["reason"]="value"
                break
            tmp=(ctypes.c_double*5)()
            solve(tmp,matrix_buffer,make(x),5)
            Reader(list(tmp))
            product=dot(make(x),tmp,5)
            if product==0:raise ValueError("QCQP model has zero Newton derivative")
            # Actual wheel 0x121390..0x1213b0: dot, double, divide.
            delta=value/(product+product)
            Reader([product,delta])
            row.update(inverseSolved=list(tmp),derivative=-2.*product,delta=delta)
            if delta<1e-10:
                row["reason"]="delta"
                break
            lam+=delta
            Reader([lam])
            row.update(lambdaAfter=lam,reason="update" if iteration<19 else "limit")
        raw=[x[i]*scaling[i] for i in range(5)]
        Reader(raw)
        return dict(active=lam!=0.,rawForce=raw,steps=steps)

    def solve(self,matrix,rhs,scaling,radius):
        # Validate everything before allocation or native pointer access.
        validated(matrix,rhs,scaling,radius)
        make=lambda values:(ctypes.c_double*len(values))(*values)
        A,b,d=make(matrix),make(rhs),make(scaling)
        result=(ctypes.c_double*5)()
        active=self.routine(result,A,b,d,radius,5)
        values=list(result)
        Reader(values)
        if active not in (0,1) or list(A)!=matrix or list(b)!=rhs or list(d)!=scaling:
            raise ValueError("original QCQP bridge postcondition differs")
        return dict(active=bool(active),rawForce=values)
