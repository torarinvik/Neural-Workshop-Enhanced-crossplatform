#!/usr/bin/env python3
"""Replay dense cone-factor captures through the active, unmodified MuJoCo wheel.

This is an exact-input diagnostic, not a trajectory acceptance test. Trace
neutrality must be established separately before treating a capture as evidence
of the maintained browser runtime. The reference calls use the unmodified
wheel; the optional rank-update model is checked against those calls, not used
as a replacement reference or a production solver.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct


def bits(value: float) -> bytes:
    return struct.pack("!d", value)


def difference(reference: list, captured: list) -> dict:
    if len(reference) != len(captured):
        raise ValueError("array dimensions differ")
    indices = [i for i, (a, b) in enumerate(zip(reference, captured))
               if bits(a) != bits(b)]
    result = {"exact": not indices, "count": len(indices)}
    if indices:
        i = indices[0]
        result["first"] = {"index": i, "reference": reference[i],
                           "captured": captured[i],
                           "referenceBits": bits(reference[i]).hex(),
                           "capturedBits": bits(captured[i]).hex()}
    return result


class Reader:
    def __init__(self, values: list):
        if not isinstance(values, list) or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or
                not math.isfinite(v) for v in values):
            raise ValueError("capture must be a finite numeric array")
        self.values = values
        self.offset = 0

    def take(self, count: int, name: str) -> list:
        end = self.offset + count
        if end > len(self.values):
            raise ValueError(f"truncated {name} at offset {self.offset}")
        result = self.values[self.offset:end]
        self.offset = end
        return result

    def integer(self, name: str, low: int, high: int) -> int:
        value = self.take(1, name)[0]
        if value != int(value) or not low <= value <= high:
            raise ValueError(f"invalid {name}: {value}")
        return int(value)

    def finish(self):
        if self.offset != len(self.values):
            raise ValueError(f"trailing capture values at offset {self.offset}")


@dataclass
class Update:
    before: list
    after: list
    x_after: list
    steps: list


@dataclass
class Contact:
    row: int
    dim: int
    hessian: list
    factor: list
    jacobian: list
    ltj: list
    updates: list[Update]


@dataclass
class ConeCapture:
    nv: int
    ncone: int
    initial: list
    contacts: list[Contact]


def rank_update_inputs(matrix: list, x: list, n: int, plus: bool) -> None:
    """Bound and validate operands before native pointer access or modelling."""
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 512:
        raise ValueError("rank update dimension must be an integer in 1..512")
    if not isinstance(plus, bool):
        raise ValueError("rank update plus flag must be boolean")
    Reader(matrix)
    Reader(x)
    if len(matrix) != n*n or len(x) != n:
        raise ValueError("rank update operand dimensions differ")
    if any(matrix[k*(n+1)] <= 0 for k in range(n)):
        raise ValueError("rank update factor diagonal must be positive")


def wheel_order_rank_update(matrix: list, x: list, n: int, *,
                           plus: bool = True, fma=None) -> tuple:
    """Diagnostic operation-order model of the recorded arm64 wheel primitive.

    The native mju_cholUpdate multiplies x[k]^2 separately, fuses Lkk^2
    into that rounded value, and divides to obtain c and 1/c. Matrix updates
    fuse s*x[i] into L[i,k], then multiply by 1/c. Vector updates instead
    round (-s)*new_L[i,k] first and fuse c*old_x[i] into that value. Fusing
    the *other* product is not equivalent. The negative update computes
    (-x[k])/Lkk before the matrix and vector loops. mjMINVAL is 1e-15.

    All array entries, including upper-triangle sentinels and skipped zero
    entries, are preserved. Steps describe complete post-k arrays. This
    models one primitive; it does not establish full Newton/trajectory parity.
    """
    rank_update_inputs(matrix, x, n, plus)
    if fma is None:
        fma = getattr(math, "fma", None)
    if fma is None:
        raise ValueError("wheel-order model requires correctly rounded math.fma")
    factor, vector = matrix.copy(), x.copy()
    rank, steps = n, []
    for k in range(n):
        if vector[k] == 0:
            continue
        diagonal = factor[k*(n+1)]
        square = vector[k]*vector[k]
        tmp = fma(diagonal, diagonal, square if plus else -square)
        if tmp < 1e-15:
            tmp = 1e-15
            rank -= 1
        root = math.sqrt(tmp)
        factor[k*(n+1)] = root
        # The wheel does not evaluate these constants on the last row.
        if k+1 < n:
            c = root/diagonal
            cinv = 1/c
            signed_s = vector[k]/diagonal if plus else (-vector[k])/diagonal
            negative_s = -signed_s if plus else signed_s
            for i in range(k+1, n):
                factor[i*n+k] = fma(signed_s, vector[i], factor[i*n+k])*cinv
            for i in range(k+1, n):
                vector[i] = fma(c, vector[i], negative_s*factor[i*n+k])
        steps.append((k, vector.copy(), factor.copy()))
    return rank, factor, vector, steps


def captured_cone(values: list) -> ConeCapture:
    """Decode the dense HessianCone recorder, including skipped x[k]==0 steps.

    ncone counts constraint rows, not contacts. Each rank update records its
    input L, then [k,nv], post-x, post-L for each nonzero x[k], then final L/x.
    Validate and consume everything before passing pointers to a native routine.
    """
    r = Reader(values)
    nv = r.integer("dense dimension", 1, 512)
    ncone = r.integer("cone row count", 0, 65536)
    initial = r.take(nv*nv, "initial factor")
    previous = initial
    contacts = []
    rows = 0
    last_end = 0
    while rows < ncone:
        row = r.integer("contact row", last_end, 65535)
        dim = r.integer("contact dimension", 1, 6)
        if rows + dim > ncone or row + dim > 65536:
            raise ValueError("contact exceeds cone row count or row bound")
        hessian = r.take(dim*dim, "contact Hessian")
        factor = r.take(dim*dim, "contact factor")
        jacobian = r.take(dim*nv, "contact Jacobian")
        ltj = r.take(dim*nv, "transformed Jacobian")
        updates = []
        for update_row in range(dim):
            before = r.take(nv*nv, "rank update input")
            if not difference(previous, before)["exact"]:
                raise ValueError("rank update factor chain is discontinuous")
            x = ltj[update_row*nv:(update_row+1)*nv]
            last_factor = before
            steps = []
            for k in range(nv):
                if x[k] == 0:
                    continue
                step = r.integer("rank update step", k, k)
                r.integer("rank update step dimension", nv, nv)
                x = r.take(nv, "rank update step vector")
                last_factor = r.take(nv*nv, "rank update step factor")
                steps.append((step, x, last_factor))
            after = r.take(nv*nv, "rank update output")
            x_after = r.take(nv, "rank update output vector")
            if (not difference(last_factor, after)["exact"] or
                    not difference(x, x_after)["exact"]):
                raise ValueError("rank update final output differs from last step")
            updates.append(Update(before, after, x_after, steps))
            previous = after
        contacts.append(Contact(row, dim, hessian, factor, jacobian, ltj, updates))
        rows += dim
        last_end = row + dim
    r.finish()
    return ConeCapture(nv, ncone, initial, contacts)


class Kernels:
    def __init__(self, path: Path):
        self.library = ctypes.CDLL(str(path.resolve()))
        scalar = ctypes.c_double
        pointer = ctypes.POINTER(scalar)
        self.factor_routine = self.library.mju_cholFactor
        self.factor_routine.argtypes = [pointer, ctypes.c_int, scalar]
        self.factor_routine.restype = ctypes.c_int
        self.add_routine = self.library.mju_addToScl
        self.add_routine.argtypes = [pointer, pointer, scalar, ctypes.c_int]
        self.add_routine.restype = None
        self.update_routine = self.library.mju_cholUpdate
        self.update_routine.argtypes = [pointer, pointer, ctypes.c_int, ctypes.c_int]
        self.update_routine.restype = ctypes.c_int

    def factor(self, matrix: list, n: int) -> tuple[int, list]:
        array = (ctypes.c_double*(n*n))(*matrix)
        rank = self.factor_routine(array, n, 1e-15)  # MuJoCo 3.12 mjMINVAL
        return rank, list(array)

    def transformed(self, factor: list, jacobian: list, dim: int, nv: int) -> list:
        rows = [(ctypes.c_double*nv)() for _ in range(dim)]
        for r in range(dim):
            source = (ctypes.c_double*nv)(*jacobian[r*nv:(r+1)*nv])
            for c in range(r+1):
                self.add_routine(rows[c], source, factor[r*dim+c], nv)
        return [value for row in rows for value in row]

    def update(self, matrix: list, x: list, nv: int, *,
               plus: bool = True) -> tuple[int, list, list]:
        rank_update_inputs(matrix, x, nv, plus)
        factor = (ctypes.c_double*(nv*nv))(*matrix)
        vector = (ctypes.c_double*nv)(*x)
        rank = self.update_routine(factor, vector, nv, int(plus))
        return rank, list(factor), list(vector)


def replay(capture: ConeCapture, kernels: Kernels, *,
           check_wheel_order_model: bool = False) -> list[dict]:
    """Report exact captured-input calls separately from propagated cone replay."""
    output = []
    sequential = capture.initial
    for contact in capture.contacts:
        rank, local = kernels.factor(contact.hessian, contact.dim)
        direct_ltj = kernels.transformed(contact.factor, contact.jacobian,
                                         contact.dim, capture.nv)
        sequential_ltj = kernels.transformed(local, contact.jacobian,
                                             contact.dim, capture.nv)
        output.append({"stage": "contactFactor", "contactRow": contact.row,
                       "rank": rank, **difference(local, contact.factor)})
        output.append({"stage": "transformedJacobian", "contactRow": contact.row,
                       **difference(direct_ltj, contact.ltj)})
        for row, update in enumerate(contact.updates):
            start, end = row*capture.nv, (row+1)*capture.nv
            rank, factor, x = kernels.update(update.before,
                                             contact.ltj[start:end], capture.nv)
            output.append({"stage": "rankUpdate", "contactRow": contact.row,
                           "row": row, "rank": rank,
                           "factor": difference(factor, update.after),
                           "vector": difference(x, update.x_after)})
            if check_wheel_order_model:
                model_rank, model_factor, model_x, model_steps = wheel_order_rank_update(
                    update.before, contact.ltj[start:end], capture.nv)
                output.append({"stage": "wheelOrderRankUpdateModel",
                               "contactRow": contact.row, "row": row,
                               "rank": model_rank, "exact": model_rank == rank,
                               "factor": difference(factor, model_factor),
                               "vector": difference(x, model_x),
                               "modelSteps": len(model_steps),
                               "capturedSteps": len(update.steps)})
                # This is model-vs-captured, not an instrumented native stage.
                if [s[0] for s in model_steps] == [s[0] for s in update.steps]:
                    for model, recorded in zip(model_steps, update.steps):
                        output.append({"stage": "modeledRankUpdateStepVsCaptured",
                                       "contactRow": contact.row, "row": row,
                                       "k": model[0],
                                       "factor": difference(model[2], recorded[2]),
                                       "vector": difference(model[1], recorded[1])})
                else:
                    output.append({"stage": "modeledRankUpdateStepSequenceVsCaptured",
                                   "contactRow": contact.row, "row": row,
                                   "exact": False,
                                   "model": [s[0] for s in model_steps],
                                   "captured": [s[0] for s in update.steps]})
            rank, sequential, x = kernels.update(sequential,
                                                 sequential_ltj[start:end], capture.nv)
            output.append({"stage": "sequentialRankUpdate", "contactRow": contact.row,
                           "row": row, "rank": rank,
                           "factor": difference(sequential, update.after),
                           "vector": difference(x, update.x_after)})
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--event", type=int, required=True)
    parser.add_argument("--reference-library", type=Path, required=True,
                        help="active original MuJoCo wheel, not an instrumented rebuild")
    parser.add_argument("--check-wheel-order-model", action="store_true",
                        help="also compare the diagnostic rank-update model to the wheel")
    args = parser.parse_args()
    raw_trace = args.trace.read_bytes()
    document = json.loads(raw_trace)
    if not 0 <= args.event < len(document["events"]):
        parser.error("event index outside trace")
    records = document["events"][args.event].get("newtonTraces", [])
    # Parse all records before loading native code; do not partially run a malformed capture.
    try:
        captures = [(step, captured_cone(record["coneTrace"]))
                    for step, record in enumerate(records) if record.get("coneTrace")]
    except ValueError as error:
        parser.error(str(error))
    if not captures or not any(c.contacts for _, c in captures):
        parser.error("selected event has no dense cone rank updates")
    reference_path = args.reference_library.resolve()
    provenance = {"referenceLibrary": str(reference_path),
                  "referenceSha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                  "trace": str(args.trace.resolve()),
                  "traceSha256": hashlib.sha256(raw_trace).hexdigest(),
                  "event": args.event}
    if "sourceEvent" in document:
        provenance["sourceEvent"] = document["sourceEvent"]
    kernels = Kernels(reference_path)
    mismatched = False
    for step, capture in captures:
        for row in replay(capture, kernels,
                          check_wheel_order_model=args.check_wheel_order_model):
            print(json.dumps({**provenance, "substep": step, **row},
                             allow_nan=False, sort_keys=True))
            mismatched |= not row.get("exact", True)
            mismatched |= not row.get("factor", {}).get("exact", True)
            mismatched |= not row.get("vector", {}).get("exact", True)
    return int(mismatched)


if __name__ == "__main__":
    raise SystemExit(main())
