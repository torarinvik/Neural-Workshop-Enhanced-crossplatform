"""Compare original quaternion trig outputs with macOS combined sincos ABI."""
import argparse
import ctypes
import json
import math
from pathlib import Path
import struct
import platform


class SinCos(ctypes.Structure):
    _fields_=[("sine",ctypes.c_double),("cosine",ctypes.c_double)]


def bits(x):return struct.pack(">d",x).hex()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("golden",type=Path)
    args=p.parse_args()
    if platform.system()!="Darwin" or platform.machine()!="arm64":
        raise ValueError("qualified macOS arm64 ABI required")
    lib=ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    routine=lib.__sincos_stret;routine.argtypes=[ctypes.c_double];routine.restype=SinCos
    different=[];independent=[]
    golden=json.loads(args.golden.read_text())
    for row in golden["results"]:
        x=struct.unpack(">d",bytes.fromhex(row["angleBits"][0]))[0]*.5
        actual=routine(x)
        for name in ("sine","cosine"):
            expected=row[name+"Bits"][0]
            if bits(getattr(actual,name))!=expected:
                different.append(dict(label=row["label"],function=name,actual=bits(getattr(actual,name)),expected=expected))
            separate=math.sin(x) if name=="sine" else math.cos(x)
            if bits(separate)!=expected:independent.append(dict(label=row["label"],function=name,actual=bits(separate),expected=expected))
    print(json.dumps(dict(calls=len(golden["results"]),combinedDifferences=different,
                          independentDifferences=independent,platform=platform.platform(),
                          promoted=False),indent=2))


if __name__=="__main__":main()
