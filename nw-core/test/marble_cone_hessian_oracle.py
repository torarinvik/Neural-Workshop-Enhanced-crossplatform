#!/usr/bin/env python3
"""Replay initialized live cone-Hessian operands through the original wheel.

The diagnostic recorder copies the active H prefix only after the middle-zone
update has written every slot. Incoming H and unused trailing storage are not
read or inferred. Exact recorder neutrality must be established separately.
This is a function-level diagnostic, not full-solver or trajectory acceptance.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from marble_cone_update_oracle import Reader, difference
from marble_constraint_update_oracle import (
    Capture, Contact, Kernels, captured_difference, wheel_order_update,
)


@dataclass
class HessianCapture:
    call: int
    row: int
    nefc: int
    dim: int
    contact_id: int
    has_cost: bool
    mu: float
    normal: float
    tangent: float
    dm: float
    nmt: float
    friction: list
    jar: list
    D: list
    R: list
    force: list
    hessian: list

    def local_call(self) -> Capture:
        # Global contact ID and island row remain provenance labels. The impl
        # uses no contact fields besides dim/mu/friction/H for this one block.
        # Every active H slot is overwritten on a middle-zone update; zero
        # synthetic incoming H is not claimed to equal the omitted live cache.
        n = self.dim
        return Capture(0, 0, n, 0, True, self.has_cost, self.jar, self.D, self.R,
                       [], [0.0]*n, [7]*n, [0]*n, [0]*n, [0.0]*n,
                       [Contact(n, self.mu, self.friction)], self.force, [4]*n,
                       [], [])


def captured_hessians(values: list, calls: int) -> list[HessianCapture]:
    """Schema 1: 12 header + 5 friction + 4*dim operands + dim*dim H."""
    if isinstance(calls, bool) or not isinstance(calls, int) or not 0 <= calls <= 1000000:
        raise ValueError("invalid impl call count")
    reader = Reader(values)
    records = []
    previous = (-1, -1)
    while reader.offset < len(values):
        reader.integer("schema", 1, 1)
        call = reader.integer("impl call ordinal", 0, calls-1)
        row = reader.integer("constraint row", 0, 65535)
        nefc = reader.integer("constraint count", 1, 65536)
        dim = reader.integer("contact dimension", 3, 6)
        if dim not in (3, 4, 6) or row+dim > nefc:
            raise ValueError("invalid initialized cone block")
        contact_id = reader.integer("global contact id", 0, 2147483647)
        has_cost = bool(reader.integer("cost presence", 0, 1))
        mu, normal, tangent, dm, nmt = reader.take(5, "cone scalars")
        friction = reader.take(5, "friction")
        jar = reader.take(dim, "jar")
        D = reader.take(dim, "D")
        R = reader.take(dim, "R")
        force = reader.take(dim, "force")
        hessian = reader.take(dim*dim, "initialized active H")
        if (mu <= 0 or tangent <= 0 or dm <= 0 or
                any(v < 0 for v in friction) or any(v <= 0 for v in D+R)):
            raise ValueError("invalid cone impedance/friction/scalars")
        if (call, row) <= previous:
            raise ValueError("cone calls/rows are duplicated or out of order")
        previous = (call, row)
        records.append(HessianCapture(call, row, nefc, dim, contact_id, has_cost,
                                      mu, normal, tangent, dm, nmt, friction,
                                      jar, D, R, force, hessian))
    reader.finish()
    return records


def selected_captures(document: dict, events: list[int]) -> list:
    """Validate all chosen records, including overflow/schema, before native calls."""
    selected = []
    for event in events:
        if not 0 <= event < len(document["events"]):
            raise ValueError("event index outside trace")
        source_event = document["events"][event].get("sourceEvent", event)
        for step, record in enumerate(document["events"][event].get("newtonTraces", [])):
            if (type(record.get("coneHessianUpdateSchema")) is not int or
                    record.get("coneHessianUpdateSchema") != 1):
                raise ValueError("missing or unsupported live cone-Hessian schema")
            if record.get("coneHessianUpdateOverflow") is not False:
                raise ValueError("cone-Hessian recorder overflowed or lacks overflow status")
            captures = captured_hessians(record.get("coneHessianUpdateTrace"),
                                         record.get("coneHessianUpdateCalls"))
            selected.extend((event, source_event, step, capture) for capture in captures)
    if not selected:
        raise ValueError("selected events contain no initialized middle-zone Hessians")
    return selected


def replay(capture: HessianCapture, kernels: Kernels) -> dict:
    local = capture.local_call()
    native = kernels.update(local, include_contact_hessians=True)
    modeled = wheel_order_update(local, kernels.norm, math.fma,
                                 include_contact_hessians=True)
    classified_cone = native["state"] == [4]*capture.dim
    model_checks = {field: difference(native[field], modeled[field]) for field in native}
    tangent = kernels.norm([capture.jar[j]*capture.friction[j-1]
                            for j in range(1, capture.dim)])
    normal = capture.jar[0]*capture.mu
    dm = capture.D[0]/((capture.mu*capture.mu)*math.fma(capture.mu, capture.mu, 1.0))
    nmt = math.fma(-capture.mu, tangent, normal)
    intermediates = {
        "normal": captured_difference([normal], [capture.normal]),
        "tangent": captured_difference([tangent], [capture.tangent]),
        "dm": captured_difference([dm], [capture.dm]),
        "nmt": captured_difference([nmt], [capture.nmt]),
    }
    return {
        "classifiedConeInWheel": classified_cone,
        "state": difference(native["state"], [4]*capture.dim),
        "force": captured_difference(native["force"], capture.force),
        "hessian": (captured_difference(native["contactHessians"][:capture.dim**2],
                                         capture.hessian) if classified_cone else None),
        "wheelOrderModelAgainstDirectWheel": model_checks,
        "wheelOrderModelIntermediatesAgainstCapture": intermediates,
        "intermediateCaveat": "tangent uses exported wheel mju_norm; intermediates are a bounded instruction-order model, not instrumented native internals",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--event", type=int, action="append", required=True)
    parser.add_argument("--reference-library", type=Path, required=True)
    args = parser.parse_args()
    if not hasattr(math, "fma"):
        parser.error("wheel-order diagnostic requires Python 3.13+ with math.fma")
    raw = args.trace.read_bytes()
    try:
        selected = selected_captures(json.loads(raw), args.event)
        library = args.reference_library.resolve()
        kernels = Kernels(library)
    except ValueError as error:
        parser.error(str(error))
    provenance = {
        "referenceLibrary": str(library),
        "referenceSha256": hashlib.sha256(library.read_bytes()).hexdigest(),
        "trace": str(args.trace.resolve()), "traceSha256": hashlib.sha256(raw).hexdigest(),
        "zeroSignsCaptured": False,
        "scope": "initialized active cone H prefix and per-contact force; no incoming H or whole-solver/trajectory acceptance",
    }
    mismatch = False
    for event, source_event, step, capture in selected:
        report = replay(capture, kernels)
        mismatch |= not report["state"]["exact"] or not report["force"]["exact"]
        mismatch |= report["hessian"] is not None and not report["hessian"]["exact"]
        mismatch |= any(not value["exact"] for value in
                        report["wheelOrderModelAgainstDirectWheel"].values())
        print(json.dumps({**provenance, "event": event, "sourceEvent": source_event,
                          "substep": step, "call": capture.call, "row": capture.row,
                          "dim": capture.dim, "contactId": capture.contact_id,
                          **report}, sort_keys=True, allow_nan=False))
    return int(mismatch)


if __name__ == "__main__":
    raise SystemExit(main())
