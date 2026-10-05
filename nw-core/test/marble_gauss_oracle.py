"""Exact-wheel guarded Gauss producer, isolated through zero constraints.

The original private PrimalUpdateConstraint is invoked with nefc=0 so only
its dof/Gauss path is observed. This is not a full solver/context replay.
"""
import ctypes
import math
import random

from marble_cone_update_oracle import Reader
from marble_primal_eval_oracle import OriginalEval, ORIGINAL_EVAL_OFFSET, MjContact312

UPDATE_OFFSET=0x104a9c
UPDATE_ENTRY=bytes.fromhex("ff0302d1fa6703a9f85f04a9f65705a9")


def synthetic_inputs():
    rng=random.Random(1044972)
    widths=list(range(35))+[63,64,65,511,512]
    for case in range(1000):
        n=widths[case%len(widths)]
        yield [[rng.uniform(-1,1)*2.**rng.randrange(-80,80) for _ in range(n)] for _ in range(4)]


class GaussContext(ctypes.Structure):
    _fields_=[("header",ctypes.c_int*8),("contact",ctypes.c_void_p),
        ("qfrc_smooth",ctypes.c_void_p),("qacc_smooth",ctypes.c_void_p),
        ("qfrc_constraint",ctypes.c_void_p),("qacc",ctypes.c_void_p),
        ("unused48",ctypes.c_byte*0x30),("D",ctypes.c_void_p),
        ("R",ctypes.c_void_p),("frictionloss",ctypes.c_void_p),
        ("aref",ctypes.c_void_p),("ids",ctypes.c_void_p),("types",ctypes.c_void_p),
        ("force",ctypes.c_void_p),("state",ctypes.c_void_p),
        ("unusedB8",ctypes.c_byte*0x20),("J",ctypes.c_void_p),
        ("unusedE0",ctypes.c_byte*0x28),("jaref",ctypes.c_void_p),
        ("unused110",ctypes.c_void_p),("Ma",ctypes.c_void_p),
        ("unused120",ctypes.c_byte*0x110),("cost",ctypes.c_double),
        ("gauss",ctypes.c_double*3),("unused250",ctypes.c_byte*0x28)]


def check_layout():
    offsets=dict(header=0,contact=0x20,qfrc_smooth=0x28,qacc_smooth=0x30,
        qfrc_constraint=0x38,qacc=0x40,D=0x78,R=0x80,frictionloss=0x88,
        ids=0x98,types=0xa0,force=0xa8,state=0xb0,J=0xd8,jaref=0x108,
        Ma=0x118,cost=0x230,gauss=0x238)
    if (ctypes.sizeof(GaussContext)!=0x278 or
            any(getattr(GaussContext,k).offset!=v for k,v in offsets.items())):
        raise ValueError("exact-original Gauss context layout differs")


def validated(Ma,qfrc_smooth,qacc,qacc_smooth):
    for values in (Ma,qfrc_smooth,qacc,qacc_smooth):Reader(values)
    n=len(Ma)
    if n>512 or any(len(v)!=n for v in (qfrc_smooth,qacc,qacc_smooth)):
        raise ValueError("Gauss producer needs equal bounded dof arrays")
    return n


def wheel_order(Ma,qfrc_smooth,qacc,qacc_smooth,*,fma=None):
    n=validated(Ma,qfrc_smooth,qacc,qacc_smooth)
    fma=fma or getattr(math,"fma",None)
    if not callable(fma):raise ValueError("original Gauss order requires correctly rounded fma")
    # Disassembly 0x104d80..0x104e2c: rounded products, ordered additions,
    # not horizontal/reassociated vector reduction. Tail 0x104e78 is fmadd.
    prefix=n//8*8 if n>=8 else 0
    value=0.;partial=[]
    for i in range(n):
        left=(Ma[i]-qfrc_smooth[i])*.5
        right=qacc[i]-qacc_smooth[i]
        value=value+left*right if i<prefix else fma(left,right,value)
        partial.append(value)
    Reader([value]+partial)
    return dict(gauss=value,partial=partial,roundedPrefix=prefix)


class OriginalGauss:
    def __init__(self,path):
        self.anchor=OriginalEval(path)
        check_layout()
        address=ctypes.cast(self.anchor.routine,ctypes.c_void_p).value-ORIGINAL_EVAL_OFFSET+UPDATE_OFFSET
        if ctypes.string_at(address,len(UPDATE_ENTRY))!=UPDATE_ENTRY:
            raise ValueError("original PrimalUpdateConstraint entry differs")
        self.routine=ctypes.CFUNCTYPE(None,ctypes.POINTER(GaussContext),ctypes.c_int)(address)

    def solve(self,Ma,qfrc_smooth,qacc,qacc_smooth):
        n=validated(Ma,qfrc_smooth,qacc,qacc_smooth)
        ctx=GaussContext();ctx.header[:]=[0,0,-1,n,0,0,0,0]
        keep=[]
        inputs=[]
        def assign(name,values,scalar=ctypes.c_double):
            buffer=(scalar*max(1,len(values)))(*values);keep.append(buffer)
            setattr(ctx,name,ctypes.cast(buffer,ctypes.c_void_p).value)
            return buffer
        for name,values in (("Ma",Ma),("qfrc_smooth",qfrc_smooth),
                ("qacc",qacc),("qacc_smooth",qacc_smooth)):
            inputs.append((assign(name,values),values))
        output=assign("qfrc_constraint",[0.]*n)
        for name in ("D","R","frictionloss","aref","force","J","jaref"):
            assign(name,[0.])
        for name in ("ids","types","state"):assign(name,[0],ctypes.c_int)
        contact=(MjContact312*1)();keep.append(contact)
        ctx.contact=ctypes.cast(contact,ctypes.c_void_p).value
        self.routine(ctypes.byref(ctx),0)
        if any(list(buffer)[:n]!=values for buffer,values in inputs) or any(output):
            raise ValueError("isolated original Gauss mutated inputs or nonzero constraint force")
        Reader([ctx.gauss[0],ctx.cost])
        if ctx.gauss[0]!=ctx.cost:
            raise ValueError("zero-constraint original Gauss did not match final cost")
        return ctx.gauss[0]
