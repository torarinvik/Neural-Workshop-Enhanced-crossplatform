"""Original machine-order aref core; full public-call qualification still required."""
import math


def reference_acceleration(kbip, velocity, position, margin):
    if not isinstance(kbip,list) or len(kbip)!=4:
        raise ValueError("complete reference coefficients required")
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in kbip+[velocity,position,margin]):
        raise ValueError("finite reference operands required")
    # Original SIMD and scalar loops: rounded spring product, fused damping.
    spring=(-kbip[0]*kbip[2])*(position-margin)
    # FMSUB/FMLS result is the negation of fused (B*vel - spring),
    # including its exact-zero sign; fma(-B, vel, spring) loses that sign.
    return -math.fma(kbip[1],velocity,-spring)
