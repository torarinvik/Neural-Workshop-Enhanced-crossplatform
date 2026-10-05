#!/usr/bin/env python3
"""Emit actual-original Eval golden packets for isolated compiled-WASM tests.

JSONL stdout is generated test data, not a production fixture/API. The exact
original private-routine guards remain mandatory. Includes the complete prior
branch matrix and all saved initialized selections, not only observed winners.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marble_eval_trace import capture_evaluations, qualified_evaluations
from marble_primal_eval_oracle import OriginalEval, REFERENCE_SHA256, validated_inputs
from marble_primal_eval_oracle_test import empty, scalar, cone, random_inputs


def packet(inputs):
    n = validated_inputs(**inputs)
    quad = [0.]* (3*n)
    for row in inputs["rows"]:
        begin = 3*row["row"]
        quad[begin:begin+len(row["quad"])] = row["quad"]
    contacts = [v for c in inputs["contacts"] for v in (c["dim"], c["mu"])]
    return ([1, inputs["alpha"], inputs["ne"], inputs["nf"], n, len(inputs["contacts"])]+
            inputs["gauss"]+inputs["jaref"]+inputs["jv"]+inputs["D"]+inputs["R"]+
            inputs["frictionloss"]+inputs["types"]+inputs["ids"]+contacts+quad)


def branch_matrix():
    for start in (-2., 0., 2.):
        for end in (-2., 0., 2.):
            yield scalar(start, end, nf=1, kind=1)
    for dim in (3, 4, 6):
        for mu in (0.5, 1., 2.):
            for start in (-4., 0., 4.):
                for end in (-4., 0., 4.):
                    yield cone(start, end, dim=dim, mu=mu)
    yield empty()
    for start in (-1., 0., 1.):
        for end in (-1., 0., 1.):
            yield scalar(start, end, kind=0, ne=1)
            yield scalar(start, end, kind=1, nf=1)
            yield scalar(start, end)
    for dim in (3, 4, 6):
        for start in (-4., 0., 4.):
            for end in (-4., 0., 4.):
                yield cone(start, end, dim=dim, zero_tangent=True)


def hex_bits(values):
    return [struct.pack("!d", v).hex() for v in values]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-library", required=True, type=Path)
    args = parser.parse_args()
    original = OriginalEval(args.reference_library)
    def emit(kind, label, values, expected):
        print(json.dumps(dict(kind=kind, label=label, values=values, expectedBits=hex_bits(expected),
                              referenceSha256=REFERENCE_SHA256), separators=(",", ":"), allow_nan=False))
    rng = random.Random(42002106)
    fmas = [(1.+2.**-27, 1.-2.**-27, -1.), (-(1.+2.**-27), 1.-2.**-27, 1.)]
    for _ in range(1000):
        fmas.append(tuple(rng.uniform(-1, 1)*2.**rng.randrange(-30, 30) for _ in range(3)))
    for i, values in enumerate(fmas):
        emit("fma", f"fma:{i}", list(values), [math.fma(*values)])
    for name, cases in (("branch", branch_matrix()), ("mixed", random_inputs())):
        for i, inputs in enumerate(cases):
            emit("eval", f"{name}:{i}", packet(inputs), original.evaluate(**inputs))
    path = Path(__file__).resolve().parents[1]/"fixtures/marble_primal_eval_full_oracle.json"
    fixture = json.loads(path.read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != (
            "4091bf83521cac28c6a415ee37b63420f1bc839dc757f4be4bf24edec1b2ed22"):
        raise ValueError("saved evaluation fixture identity changed")
    p = fixture["provenance"]
    for entry in fixture["entries"]:
        native = qualified_evaluations(entry["qualification"], reference_sha256=p["referenceSha256"],
            diagnostic_sha256=p["diagnosticLibrarySha256"],
            input_trace_sha256=p["inputTraces"][entry["matrix"]]["sha256"])
        groups = [("native", native)]
        if "browserTrace" in entry:
            groups.append(("browser", capture_evaluations(entry["browserTrace"])))
        for name, captures in groups:
            for c in captures:
                label = f"{name}:{entry['matrix']}:{entry['qualification']['event']}:{entry['qualification']['substep']}:{c['ordinal']}"
                emit("eval", label, packet(c["inputs"]), original.evaluate(**c["inputs"]))


if __name__ == "__main__":
    main()
