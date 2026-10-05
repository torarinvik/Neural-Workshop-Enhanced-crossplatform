"""Pinned macOS small-angle combined trig model; rejects range reduction."""
import math

SMALL_LIMIT = float.fromhex("0x1.921fb54442d18p-1")

SIN=tuple(float.fromhex(x) for x in (
    "0x1.5d8fd1fd19ccdp-33","-0x1.ae5e5a9291f5dp-26",
    "0x1.71de3567d48a1p-19","-0x1.a01a019bfdf03p-13",
    "0x1.111111110f7d0p-7","-0x1.5555555555548p-3"))
COS=tuple(float.fromhex(x) for x in (
    "-0x1.8fa49a0861a9bp-37","0x1.1ee9d7b4e3f05p-29",
    "-0x1.27e4f7eac4bc6p-22","0x1.a01a019c844f5p-16",
    "-0x1.6c16c16c14f91p-10","0x1.555555555554bp-5","-0x1.0000000000000p-1"))


def small_sine(x):
    if not math.isfinite(x) or abs(x)>SMALL_LIMIT:
        raise ValueError("qualified small-angle domain required")
    if x==0:return x
    square=x*x
    polynomial=SIN[0]
    for coefficient in SIN[1:]:polynomial=math.fma(square,polynomial,coefficient)
    return math.fma(x,square*polynomial,0.)+x


def small_cosine(x):
    if not math.isfinite(x) or abs(x)>SMALL_LIMIT:
        raise ValueError("qualified small-angle domain required")
    square=math.fma(x,x,0.)
    polynomial=COS[0]
    for coefficient in COS[1:]:polynomial=math.fma(square,polynomial,coefficient)
    return math.fma(square,polynomial,1.)
