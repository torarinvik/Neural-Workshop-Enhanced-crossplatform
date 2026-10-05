"""Bounded high-precision trig cross-check; not a production libm replacement."""
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path
import math
import struct


def trig_reference(x, precision=120):
    if not math.isfinite(x) or abs(x)>16:
        raise ValueError("finite bounded half-angle required")
    with localcontext() as ctx:
        ctx.prec=precision
        d=Decimal.from_float(x); square=d*d
        sine=st=d;cosine=ct=Decimal(1)
        for n in range(1,300):
            st=-st*square/Decimal((2*n)*(2*n+1))
            ct=-ct*square/Decimal((2*n-1)*(2*n))
            sine+=st;cosine+=ct
            if max(abs(st),abs(ct))<Decimal(10)**(-precision+10):
                return float(sine),float(cosine)
        raise ValueError("Taylor remainder bound not reached")


def bits(x):return struct.pack(">d",x).hex()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("golden",type=Path)
    args=p.parse_args();golden=json.loads(args.golden.read_text());different=[]
    for row in golden["results"]:
        angle=struct.unpack(">d",bytes.fromhex(row["angleBits"][0]))[0]*.5
        sine,cosine=trig_reference(angle)
        if [bits(sine),bits(cosine)]!=[bits(v) for v in trig_reference(angle,240)]:
            raise ValueError("rounded reference changes with precision")
        for name,result in (("sine",sine),("cosine",cosine)):
            expected=row[name+"Bits"][0]
            if bits(result)!=expected:
                different.append(dict(label=row["label"],function=name,halfAngle=angle,
                                      referenceBits=bits(result),originalBits=expected))
    print(json.dumps(dict(calls=len(golden["results"]),precision=120,
                          differentValues=len(different),differences=different,
                          promoted=False),indent=2))


if __name__=="__main__":main()
