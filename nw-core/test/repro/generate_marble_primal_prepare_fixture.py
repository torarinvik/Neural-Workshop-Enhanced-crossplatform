#!/usr/bin/env python3
"""Emit the bounded preparation fixture after exact whole-solver qualification.

Run from the original application's Python environment. Output is JSON on
stdout, never a library/artifact/source mutation. See the adjacent reproduction
note for capture commands and the distinction from full replay acceptance.
"""
import argparse
import ctypes
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marble_constraint_update_oracle import captured_difference
from marble_dense_solve_oracle import native_dot
from marble_iteration_trace import compare_iteration_traces, decode_iteration_updates
from marble_native_dot_oracle import wheel_dot
from marble_prepare_trace import capture_preparations, qualified_preparations
from marble_primal_prepare_oracle import prepare


REFERENCE_SHA256 = "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c"
PREPARATION_FIELDS = ("prepareTrace", "prepareTraceSchema", "prepareTraceCalls",
                      "prepareTraceOverflow", "prepareTraceInvalid")


def identity(path):
    return {"path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def comparisons(captures, dot):
    comparisons = []
    for c in captures:
        modeled = prepare(**c["inputs"], dot=dot)
        rows = [{"row": a["row"], "dim": a["dim"],
                 "difference": captured_difference(a["quad"], b["quad"])}
                for a, b in zip(modeled["rows"], c["rows"])]
        comparisons.append({"ordinal": c["ordinal"],
            "initializedOutputs": 3+sum(len(row["quad"]) for row in c["rows"]),
            "gauss": captured_difference(modeled["quadGauss"], c["quadGauss"]),
            "rows": rows})
    return comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--neutral-trace", required=True, type=Path)
    parser.add_argument("--candidate-trace", required=True, type=Path)
    parser.add_argument("--reference-library", required=True, type=Path)
    parser.add_argument("--diagnostic-library", required=True, type=Path)
    parser.add_argument("--captured-on", required=True, type=date.fromisoformat,
                        help="actual qualification date as YYYY-MM-DD")
    parser.add_argument("--compact", action="store_true", help="compact JSON output")
    args = parser.parse_args()
    reference, diagnostic = identity(args.reference_library), identity(args.diagnostic_library)
    if reference["sha256"] != REFERENCE_SHA256:
        parser.error("reference is not the authoritative original arm64 wheel")
    wheel = ctypes.CDLL(reference["path"])
    traces = {name: json.loads(path.read_text()) for name, path in (
        ("neutral", args.neutral_trace), ("rejectedThreePrimitive", args.candidate_trace))}
    paths = {"neutral": args.neutral_trace, "rejectedThreePrimitive": args.candidate_trace}
    inputs = {name: identity(path) for name, path in paths.items()}
    result = {"schema": "neural-workshop.marble-preparation-full-oracle.v1",
        "provenance": {"capturedOn": args.captured_on.isoformat(), "nativeArchitecture": "arm64",
            "engineCommit": "13827e9ee56f097f57acf69ae52b078f9839682d",
            "referenceSha256": reference["sha256"],
            "diagnosticLibrarySha256": diagnostic["sha256"],
            "diagnosticLibrary": diagnostic, "inputTraces": inputs,
            "neutralRuntime": traces["neutral"]["runtimeProvenance"],
            "capturedZeroSigns": False,
            "scope": "initialized preparation of a native rebuild qualified at exact-input whole-solver boundaries; not direct internal wheel instrumentation, not full trajectory acceptance"},
        "entries": [], "summary": {"qualifiedBoundaries": 0, "preparations": 0,
            "initializedOutputs": 0, "nonzeroDifferences": 0,
            "zeroSignOnlyDifferences": 0, "schema2NeutralComparisons": 0,
            "schema2NeutralDifferentBoundaries": 0}, "captureFiles": []}
    for matrix, events, prefix in (("neutral", (17, 18, 216), "neutral-native"),
                                   ("rejectedThreePrimitive", (18, 216), "native-wheel-order")):
        for event in events:
            capture_path = args.capture_root/f"{prefix}-prepare{event}.jsonl"
            result["captureFiles"].append(identity(capture_path))
            documents = [json.loads(line) for line in capture_path.read_text().splitlines()]
            if len(documents) != 4 or [d.get("substep") for d in documents] != list(range(4)):
                raise ValueError("qualification capture must contain exactly four ordered substeps")
            for document in documents:
                if document["event"] != event:
                    raise ValueError("qualification event differs from file selection")
                captures = qualified_preparations(document,
                    reference_sha256=reference["sha256"], diagnostic_sha256=diagnostic["sha256"],
                    input_trace_sha256=inputs[matrix]["sha256"])
                if "referenceRuntime" not in result["provenance"]:
                    result["provenance"]["referenceRuntime"] = document["nativeWheel"]
                checked = comparisons(captures, lambda a, b: native_dot(wheel, a, b))
                # The portable fixture callback must agree with the direct wheel
                # on all Gauss operands, before native comparison summaries are saved.
                if comparisons(captures, wheel_dot) != checked:
                    raise AssertionError("portable dot model differs from direct wheel on captured inputs")
                summary = result["summary"]
                summary["qualifiedBoundaries"] += 1
                summary["preparations"] += len(captures)
                for c in checked:
                    summary["initializedOutputs"] += c["initializedOutputs"]
                    for diff in [c["gauss"]]+[r["difference"] for r in c["rows"]]:
                        summary["nonzeroDifferences"] += diff["nonzeroDifferenceCount"]
                        summary["zeroSignOnlyDifferences"] += diff["zeroSignOnlyCount"]
                if summary["nonzeroDifferences"]:
                    raise AssertionError("complete native preparation model differs")
                boundary = {"matrix": matrix, "qualification": document,
                            "modelComparisons": checked}
                native_iteration, error = decode_iteration_updates(
                    document["trace"]["constraintIterationTrace"], 2)
                if error:
                    raise ValueError(error)
                boundary["nativeIterationRecords"] = len(native_iteration)
                if matrix == "neutral":
                    browser = traces[matrix]["events"][event]["newtonTraces"][document["substep"]]
                    comparison = compare_iteration_traces(document["trace"], browser)
                    if not comparison["comparable"] or any(comparison["errors"]):
                        raise AssertionError("schema-2 comparison is not validity-aware/comparable")
                    boundary["iterationComparison"] = {k: comparison[k] for k in
                        ("schemas", "comparable", "firstDifference")}
                    boundary["browserModelComparisons"] = comparisons(
                        capture_preparations(browser), lambda a, b: native_dot(wheel, a, b))
                    summary["schema2NeutralComparisons"] += 1
                    summary["schema2NeutralDifferentBoundaries"] += comparison["firstDifference"] is not None
                # Preserve active preparation, not the large unrelated global
                # contact/iteration arrays. Their raw capture hashes are above.
                document["trace"] = {k: document["trace"][k] for k in PREPARATION_FIELDS}
                document["inputTrace"] = {k: document["inputTrace"][k] for k in ("path", "sha256")}
                document["nativeWheel"] = {k: document["nativeWheel"][k] for k in (
                    "distributionVersion", "mujocoVersion", "activeEngineLibrary")}
                result["entries"].append(boundary)
    print(json.dumps(result, indent=None if args.compact else 2,
                     separators=(",", ":") if args.compact else None,
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
