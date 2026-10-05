"""Qualify the bounded model against the pinned macOS arm64 combined ABI.

This is a local arithmetic qualification, not full Marble Maze acceptance.
"""
import ctypes
import hashlib
import json
import math
import platform
import random

from marble_platform_sincos import SinCos, bits
from marble_small_sincos_model import SMALL_LIMIT, small_cosine, small_sine


REGIONS = (
    (-736, 16, "c5ebbec1d24f658b078269886bb3938f337dcdf307fc062fb83d87d5c7fb64d3"),
    (0, 416, "79c768005a3e106c74bcac4013d634998a6baf2875d03c258dfbeb746b855b73"),
    (904, 48, "6abb4e27b972daa25032afa046fb814807b5ffcd6fcf5beb551e31b673ac7043"),
    (1176, 56, "e874aeba59eebdebdf68d18b1196d1ca6aeee12b110985a856f8fe404e0c76ee"),
    (1104, 68, "74ad10239204f5a6543a503dac44bf9db85ccabe090f3f10303bf749d66b9ffe"),
    (1276, 68, "6db6bce7b43dfc54ea0db4dcb37d9f5d9dbace6d74c9e96f353ae1d4338e8911"),
    (1344, 36, "5c5f0cbef56817d200a59008b5986c317ef8342f3a8545b4b0974aa4563f6d86"),
)


def qualify():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Pinned macOS arm64 ABI required")
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    routine = library.__sincos_stret
    routine.argtypes = [ctypes.c_double]
    routine.restype = SinCos
    address = ctypes.cast(routine, ctypes.c_void_p).value
    regions = []
    for offset, length, expected in REGIONS:
        actual = hashlib.sha256(ctypes.string_at(address + offset, length)).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Unqualified platform image at offset {offset}: {actual}")
        regions.append(dict(offset=offset, length=length, sha256=actual))
    values = [0., -0., SMALL_LIMIT, -SMALL_LIMIT, math.nextafter(SMALL_LIMIT, 0.),
              math.nextafter(-SMALL_LIMIT, 0.), math.ulp(0.), -math.ulp(0.),
              0.019710379478423627, 0.6849294978512117]
    rng = random.Random(565)
    values.extend(rng.uniform(-SMALL_LIMIT, SMALL_LIMIT) for _ in range(10000))
    for exponent in range(-1074, 0):
        value = math.ldexp(1., exponent)
        values.extend((value, -value))
    mismatches = []
    for value in values:
        reference = routine(value)
        for name, model in (("sine", small_sine), ("cosine", small_cosine)):
            actual, expected = bits(model(value)), bits(getattr(reference, name))
            if actual != expected:
                mismatches.append(dict(input=bits(value), function=name,
                                       actual=actual, expected=expected))
    rejected = [math.nextafter(SMALL_LIMIT, math.inf), math.nextafter(-SMALL_LIMIT, -math.inf),
                math.inf, -math.inf, math.nan]
    for value in rejected:
        for model in (small_sine, small_cosine):
            try:
                model(value)
            except ValueError:
                continue
            raise AssertionError("Model accepted an unsupported input")
    result = dict(platform=platform.platform(), regions=regions,
                  pairs=len(values), mismatches=mismatches,
                  rejectedInputs=len(rejected), promoted=False,
                  domain="finite abs(x) <= 0x1.921fb54442d18p-1; no range reduction")
    print(json.dumps(result, indent=2))
    if mismatches:
        raise AssertionError(f"{len(mismatches)} complete-bit differences")


if __name__ == "__main__":
    qualify()
