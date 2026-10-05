"""Bounded operation-order model of the original arm64 wheel's mju_dot.

The SDK-26 wheel processes full 32-element chunks using separately rounded
products in four lanes, then fused quads and a fused/scalar tail. New Apple
Clang autovectorization selected 16-element chunks in a diagnostic rebuild.
This model is for qualification, not a production replacement or a claim
about x86/AVX, arbitrary native toolchains, or the browser's complete solver.
"""
import math

from marble_cone_update_oracle import Reader


def wheel_dot(a, b, *, fma=None):
    Reader(a)
    Reader(b)
    n = len(a)
    if n != len(b) or n > 512:
        raise ValueError("dot operands require equal lengths in 0..512")
    fma = fma or getattr(math, "fma", None)
    if not callable(fma):
        raise ValueError("wheel dot requires correctly rounded fma")
    lanes = [0.0]*4
    i = 0
    rounded_end = (n//32)*32
    while i < rounded_end:
        for j in range(4):
            lanes[j] += a[i+j]*b[i+j]
        i += 4
    while i <= n-4:
        for j in range(4):
            lanes[j] = fma(a[i+j], b[i+j], lanes[j])
        i += 4
    result = (lanes[0]+lanes[2])+(lanes[1]+lanes[3])
    if n-i == 3:
        result += fma(a[i+2], b[i+2], fma(a[i], b[i], a[i+1]*b[i+1]))
    elif n-i == 2:
        result += fma(a[i], b[i], a[i+1]*b[i+1])
    elif n-i == 1:
        result = fma(a[i], b[i], result)
    Reader([result])
    return result
