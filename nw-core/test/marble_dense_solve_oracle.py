#!/usr/bin/env python3
"""Replay captured dense Newton solves directly in the original MuJoCo library.

Run with the original application's Python environment. This diagnoses exact
rounding differences; it does not replace the full trajectory acceptance gate.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import math
from pathlib import Path

from marble_cone_update_oracle import Reader, difference
from marble_constraint_update_oracle import captured_difference


def captured_dense_stages(trace: dict) -> tuple[int, list, list, list, list]:
    """Decode initialized first-solve inputs and each post-diagonal vector."""
    reader = Reader(trace.get("denseSolveStages"))
    n = reader.integer("dense solve dimension", 1, 512)
    matrix = reader.take(n*n, "factor")
    rhs = reader.take(n, "right hand side")
    forward = [reader.take(n, "forward stage") for _ in range(n)]
    backward = [reader.take(n, "backward stage") for _ in range(n)]
    reader.finish()
    if any(matrix[i*(n+1)] <= 0 for i in range(n)):
        raise ValueError("dense factor has nonpositive diagonal")
    return n, matrix, rhs, forward, backward


def wheel_order_solve(n: int, matrix: list, rhs: list, dot, fma) -> dict:
    """Bounded arithmetic model; not a replacement for the active-wheel oracle."""
    result = list(rhs)
    forward, backward = [], []
    for i in range(n):
        if i:
            result[i] -= dot(matrix[i*n:i*n+i], result[:i])
        result[i] /= matrix[i*(n+1)]
        forward.append(list(result))
    for i in range(n-1, -1, -1):
        for j in range(i+1, n):
            result[i] = fma(-matrix[j*n+i], result[j], result[i])
        result[i] /= matrix[i*(n+1)]
        backward.append(list(result))
    return {"result": result, "forward": forward, "backward": backward}


def native_dot(library: ctypes.CDLL, a: list, b: list) -> float:
    if len(a) != len(b):
        raise ValueError("dot operands differ in length")
    scalar = ctypes.c_double
    routine = library.mju_dot
    routine.argtypes = [ctypes.POINTER(scalar)]*2 + [ctypes.c_int]
    routine.restype = scalar
    n = len(a)
    return routine((scalar*n)(*a), (scalar*n)(*b), n)


def captured_solve(trace: dict) -> tuple[int, list, list, list]:
    operands = trace["cholSolveInput"]
    if not isinstance(operands, list) or len(operands) < 2:
        raise ValueError("missing Cholesky operand header")
    reader = Reader(operands)
    n = reader.integer("dense Cholesky dimension", 1, 512)
    reader.integer("dense Cholesky format", -1, -1)
    matrix = reader.take(n*n, "Cholesky factor")
    rhs = reader.take(n, "Cholesky RHS")
    reader.finish()
    if any(matrix[i*(n+1)] <= 0 for i in range(n)):
        raise ValueError("Cholesky factor has nonpositive diagonal")
    values = trace["values"]
    if not isinstance(values, list):
        raise ValueError("missing Newton record payload")
    offset = 0
    while offset < len(values):
        if len(values) - offset < 9:
            raise ValueError("truncated Newton record header")
        dimensions = Reader(values[offset+4:offset+6])
        nv = dimensions.integer("Newton velocity dimension", 1, 512)
        nefc = dimensions.integer("Newton constraint dimension", 0, 65536)
        width = 9 + 5*nv + 2*nefc
        if offset + width > len(values):
            raise ValueError("truncated Newton record payload")
        if values[offset] == 1:
            if nv != n:
                raise ValueError("first Newton solve dimension differs from operands")
            start = offset + 9 + nefc + 3*nv
            result = Reader(values[start:start+n]).take(n, "initialized Mgrad")
            return n, matrix, rhs, result
        offset += width
    raise ValueError("missing first solved Mgrad record (label 1)")


def solve(library: ctypes.CDLL, n: int, matrix: list, rhs: list) -> list:
    scalar = ctypes.c_double
    routine = library.mju_cholSolve
    routine.argtypes = [ctypes.POINTER(scalar)] * 3 + [ctypes.c_int]
    routine.restype = None
    result = (scalar*n)()
    routine(result, (scalar*(n*n))(*matrix), (scalar*n)(*rhs), n)
    return list(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--event", type=int, required=True)
    parser.add_argument("--reference-library", type=Path, required=True,
                        help="original MuJoCo library, not an instrumented rebuild")
    parser.add_argument("--diagnostic-library", type=Path)
    parser.add_argument("--check-wheel-order-model", action="store_true",
                        help="compare a dot/backward-FMA model and captured stage vectors")
    args = parser.parse_args()
    if args.check_wheel_order_model and not hasattr(math, "fma"):
        parser.error("dense arithmetic model requires Python 3.13+ with math.fma")
    trace = json.loads(args.trace.read_text())
    if not 0 <= args.event < len(trace["events"]):
        parser.error("event index outside trace")
    records = trace["events"][args.event].get("newtonTraces", [])
    if not records:
        parser.error("selected event has no Newton traces")
    reference = ctypes.CDLL(str(args.reference_library.resolve()))
    diagnostic = (ctypes.CDLL(str(args.diagnostic_library.resolve()))
                  if args.diagnostic_library else None)
    mismatches = 0
    compared = 0
    for substep, record in enumerate(records):
        # A captured event can include warm-up/empty solver calls before the
        # first dense Newton solve. Those records are valid trace entries,
        # but they do not contain Cholesky operands and must not make the
        # oracle abort before reaching the first comparable solve.
        if not record.get("cholSolveInput"):
            continue
        n, matrix, rhs, wasm = captured_solve(record)
        original = solve(reference, n, matrix, rhs)
        row = {"event": args.event, "substep": substep,
               "referenceLibrary": str(args.reference_library.resolve()),
               "original": original, "wasm": wasm,
               "originalWasmExact": original == wasm}
        mismatches += original != wasm
        compared += 1
        if args.check_wheel_order_model:
            stage_n, stage_matrix, stage_rhs, forward, backward = captured_dense_stages(record)
            if (stage_n != n or matrix != stage_matrix or rhs != stage_rhs):
                raise ValueError("stage recorder operands differ from the first Newton solve")
            modeled = wheel_order_solve(n, matrix, rhs,
                                       lambda a, b: native_dot(reference, a, b), math.fma)
            row["wheelOrderModelAgainstDirectWheel"] = difference(original, modeled["result"])
            row["forwardStageDifferences"] = [
                captured_difference(a, b) for a, b in zip(modeled["forward"], forward)]
            row["backwardStageDifferences"] = [
                captured_difference(a, b) for a, b in zip(modeled["backward"], backward)]
            row["zeroSignsCaptured"] = False
            row["modelScope"] = "direct wheel mju_dot plus scalar backward fma; intermediate vectors are modeled, not instrumented original-wheel internals"
            mismatches += not row["wheelOrderModelAgainstDirectWheel"]["exact"]
        if diagnostic is not None:
            rebuilt = solve(diagnostic, n, matrix, rhs)
            row.update(diagnostic=rebuilt, nativeExact=original == rebuilt)
            mismatches += original != rebuilt
        print(json.dumps(row, allow_nan=False, sort_keys=True))
    if not compared:
        parser.error("selected event has no dense Newton solves")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
