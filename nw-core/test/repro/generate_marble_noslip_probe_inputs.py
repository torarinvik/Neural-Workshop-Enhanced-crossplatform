#!/usr/bin/env python3
"""Emit public-original dot and modeled residual packets for compiled probes.

The original wheel hash/loaded-image guards are retained. Residual goldens
combine an actual original public dot call with the documented bias/FMA order;
they are not described as direct calls to the original private residual.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marble_dense_solve_oracle import native_dot
from marble_native_dot_oracle_test import input_matrix
from marble_primal_eval_oracle import OriginalEval, REFERENCE_SHA256
from marble_noslip_residual_oracle import packet, residual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-library", required=True, type=Path)
    parser.add_argument("--rejected-fixture", required=True, type=Path)
    args = parser.parse_args()
    original = OriginalEval(args.reference_library)
    library = ctypes.CDLL(str(original.path))
    if hashlib.sha256(args.rejected_fixture.read_bytes()).hexdigest() != (
            "fa808c9b7696c063085dc6024cd6abed956845f425efaabfc0b176bd5170d0aa"):
        raise ValueError("qualified rejection fixture identity differs")
    fixture = json.loads(args.rejected_fixture.read_text())
    if fixture.get("schema") != "neural-workshop.marble-coherent-solver-rejected.v1":
        raise ValueError("expected qualified coherent-candidate rejection evidence")
    if fixture["provenance"]["referenceSha256"] != REFERENCE_SHA256:
        raise ValueError("rejection reference identity changed")
    rng = random.Random(42002107)
    def emit(kind, label, a, b, bias=0., regularizer=0., force=0.):
        dot = native_dot(library, a, b)
        expected = math.fma(-regularizer, force, bias+dot)
        if struct.pack("!d", residual(a, b, bias, regularizer, force)) != struct.pack("!d", expected):
            raise AssertionError("compound residual model differs from actual public dot/FMA")
        print(json.dumps(dict(kind=kind, label=label, values=packet(a, b, bias, regularizer, force),
            expectedBits=struct.pack("!d", expected).hex(), referenceSha256=REFERENCE_SHA256,
            goldenScope="actual original public dot plus rounded bias addition and exact FMA"),
            separators=(",", ":"), allow_nan=False))
    for i, (a, b) in enumerate(input_matrix()):
        emit("dot", f"dot:{i}", a, b)
        scalars = [rng.uniform(-1, 1)*2.**rng.randrange(-30, 30) for _ in range(3)]
        emit("residual", f"synthetic:{i}", a, b, *scalars)
    for row in fixture["firstNoSlipResidual"]["rows"]:
        emit("residual", f"captured:17:0:{row['row']}", row["ARrow"], row["allforce"],
             row["bias"], row["regularizer"], row["force"])


if __name__ == "__main__":
    main()
