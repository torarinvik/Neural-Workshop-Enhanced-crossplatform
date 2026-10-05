"""Bounded dense no-slip residual order for the original arm64 wheel.

The dot order is independently qualified against the original public kernel.
The final addition/FMA are a compound operation model, not a private residual
function invocation. Sparse residuals and QCQP are outside this model's scope.
"""
import math

from marble_cone_update_oracle import Reader
from marble_native_dot_oracle import wheel_dot


def validated(a, b, bias, regularizer, force):
    Reader(a)
    Reader(b)
    Reader([bias, regularizer, force])
    if len(a) != len(b) or len(a) > 512:
        raise ValueError("dense residual operands must have equal lengths in 0..512")


def packet(a, b, bias=0., regularizer=0., force=0.):
    validated(a, b, bias, regularizer, force)
    return [1, bias, regularizer, force, len(a), *a, *b]


def residual(a, b, bias, regularizer, force, *, fma=None):
    validated(a, b, bias, regularizer, force)
    fma = fma or getattr(math, "fma", None)
    if not callable(fma):
        raise ValueError("residual requires correctly rounded fma")
    value = fma(-regularizer, force, bias+wheel_dot(a, b, fma=fma))
    Reader([value])
    return value


def rejected_dot(a, b):
    """Historical browser-specific rounded-product kernel; diagnostic only."""
    validated(a, b, 0., 0., 0.)
    lanes = [0.]*4
    i = 0
    while i <= len(a)-4:
        for j in range(4):
            lanes[j] += a[i+j]*b[i+j]
        i += 4
    value = (lanes[0]+lanes[2])+(lanes[1]+lanes[3])
    tail = [a[j]*b[j] for j in range(i, len(a))]
    if len(tail)==3:
        value += (tail[0]+tail[1])+tail[2]
    elif len(tail)==2:
        value += tail[0]+tail[1]
    elif len(tail)==1:
        value += tail[0]
    return value
