"""Probe the pinned original sphere/box kernel on pre-sync copied operands.

This is a private-symbol diagnostic for the exact guarded original image,
not a portable ABI or ordinary trajectory acceptance test.
"""
import argparse
import ctypes
import hashlib
import json
import math
import random
from pathlib import Path
from marble_integrator_original import OriginalIntegrator, bits
from marble_primal_eval_oracle import ORIGINAL_EVAL_OFFSET, DlInfo


class PreContact(ctypes.Structure):
    _fields_ = [("dist", ctypes.c_double), ("pos", ctypes.c_double * 3),
                ("normal", ctypes.c_double * 3), ("tangent", ctypes.c_double * 3)]


def outside_model(operands):
    p1, _, s1, p2, m, s2 = operands
    delta = [p1[i]-p2[i] for i in range(3)]
    dot = lambda a,b: math.fma(a[2], b[2], math.fma(a[0], b[0], a[1]*b[1]))
    center = [dot([m[i],m[i+3],m[i+6]],delta) for i in range(3)]
    clamped = [max(-s2[i],min(s2[i],center[i])) if s2[i]>0 else center[i] for i in range(3)]
    diff = [clamped[i]-center[i] for i in range(3)]
    length = math.sqrt(dot(diff,diff))
    if length <= 1e-15:
        raise ValueError("outside-only model does not qualify inside branch")
    normal = [x*(1./length) for x in diff]
    deepest = [math.fma(normal[i],s1[0],center[i]) for i in range(3)]
    midpoint = [math.fma(deepest[i],.5,math.fma(clamped[i],.5,0.)) for i in range(3)]
    worldnormal = [dot(m[3*i:3*i+3],normal) for i in range(3)]
    position = [dot(m[3*i:3*i+3],midpoint)+p2[i] for i in range(3)]
    return [length-s1[0],*position,*worldnormal,0.,0.,0.]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("log", type=Path)
    p.add_argument("--reference-library", type=Path, required=True)
    p.add_argument("--label", help="exact pre-sync boundary label to probe")
    args = p.parse_args()
    guard = OriginalIntegrator(args.reference_library)
    anchor = guard.anchor
    base = ctypes.cast(anchor.routine, ctypes.c_void_p).value - ORIGINAL_EVAL_OFFSET
    address = base + 0x142b4
    info = DlInfo()
    dladdr = ctypes.CDLL(None).dladdr
    dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
    dladdr.restype = ctypes.c_int
    if not dladdr(address, ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve() != anchor.path:
        raise ValueError("original sphere/box image differs")
    ptr = ctypes.POINTER(ctypes.c_double)
    routine = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(PreContact), ctypes.c_double,
                              ptr, ptr, ptr, ptr, ptr)(address)
    rows = []
    synthetic_calls = 0
    rng = random.Random(0x142b4)
    for line in args.log.read_text().splitlines():
        if not line.startswith("PRE-SYNC COLLISION GEOMETRY "):
            continue
        label, raw = line.split(": ", 1)
        if args.label is not None and label != args.label:
            continue
        packet = json.loads(raw)
        for index, contact in enumerate(packet["source"]):
            geoms = [contact["geom1"], contact["geom2"]]
            if [packet["geomTypes"][g] for g in geoms] != [2, 6]:
                continue
            operands = []
            for g in geoms:
                for key, width in (("geom_xpos", 3), ("geom_xmat", 9), ("geom_size", 3)):
                    a = packet["sourceOperands"][key][g*width:(g+1)*width]
                    b = packet["wasmOperands"][key][g*width:(g+1)*width]
                    if len(a) != width or bits(a) != bits(b):
                        raise ValueError("sphere/box copied operands differ")
                    operands.append((ctypes.c_double * width)(*a))
            saved = [bits(a) for a in operands]
            output = PreContact()
            # Existing penetrating contact: zero margin selects the same hit.
            # Private optimized symbol omits unused sphere orientation (mat1).
            # Qualified from the pinned image's x1..x5 operand loads.
            count = routine(ctypes.byref(output), 0., operands[0], operands[2],
                            operands[3], operands[4], operands[5])
            if count != 1 or saved != [bits(a) for a in operands]:
                raise ValueError("sphere/box count or input immutability differs")
            if output.dist != contact["dist"] or list(output.pos) != contact["pos"]:
                raise ValueError(f"raw kernel does not reproduce original contact at {label}/{index}: "
                                 f"dist={output.dist!r}/{contact['dist']!r}, "
                                 f"pos={list(output.pos)!r}/{contact['pos']!r}")
            raw = [output.dist, *output.pos, *output.normal, *output.tangent]
            modeled = outside_model(operands)
            if bits(raw) != bits(modeled):
                raise ValueError(f"outside model differs at {label}/{index}: "
                                 f"{[(i,a,b) for i,(a,b) in enumerate(zip(raw,modeled)) if bits([a])!=bits([b])]}")
            for case in range(100):
                stress = [(ctypes.c_double * len(a))(*a) for a in operands]
                # Far-outside finite centers avoid the unqualified inside branch.
                for i in range(3):
                    stress[0][i] = stress[3][i] + rng.uniform(2.,4.)
                original = PreContact()
                before = [bits(a) for a in stress]
                if routine(ctypes.byref(original), 1e6, stress[0], stress[2],
                           stress[3], stress[4], stress[5]) != 1:
                    raise ValueError("synthetic outside contact count differs")
                actual = [original.dist,*original.pos,*original.normal,*original.tangent]
                if before != [bits(a) for a in stress] or bits(actual) != bits(outside_model(stress)):
                    raise ValueError("synthetic outside complete result differs")
                synthetic_calls += 1
            rows.append(dict(label=label, contact=index, rawOriginalBits=bits(
                [output.dist, *output.pos, *output.normal, *output.tangent]),
                originalNormal=list(output.normal), capturedNormal=contact["frame"][:3],
                browserNormal=packet["wasm"][index]["frame"][:3]))
    if not rows:
        raise ValueError("no sphere/box calls captured")
    print(json.dumps(dict(logSha256=hashlib.sha256(args.log.read_bytes()).hexdigest(),
                          calls=len(rows), syntheticCalls=synthetic_calls,
                          qualifiedBranch="outside only", results=rows, promoted=False), indent=2))


if __name__ == "__main__":
    main()
