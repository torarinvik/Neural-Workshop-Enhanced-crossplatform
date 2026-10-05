#!/usr/bin/env python3
"""Emit initialized evaluation evidence checked by the exact original routine.

This emits JSON only; it never changes libraries, sources or production assets.
Use the original application's Python on Darwin arm64. The private bridge's
hash/layout/loaded-image/entry guards are mandatory, not optional provenance.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marble_cone_update_oracle import difference, bits
from marble_constraint_update_oracle import captured_difference
from marble_eval_trace import capture_evaluations, qualified_evaluations
from marble_primal_eval_oracle import (OriginalEval, ORIGINAL_DOT_OFFSET,
                                      ORIGINAL_EVAL_OFFSET, EVAL_ENTRY, evaluate)
from marble_trace_neutrality import first_physics_difference, runtime_provenance_error


FIELDS = ("prepareTrace", "prepareTraceSchema", "prepareTraceCalls",
          "prepareTraceOverflow", "prepareTraceInvalid", "evalTrace", "evalTraceSchema",
          "evalTraceCalls", "evalTraceOverflow", "evalTraceInvalid")


def identity(path):
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def comparisons(captures, original):
    result = []
    for c in captures:
        exact = original.evaluate(**c["inputs"])
        modeled = evaluate(**c["inputs"])
        if not difference(exact, modeled["result"])["exact"]:
            raise AssertionError("evaluation model differs from exact original routine")
        item = {"ordinal": c["ordinal"], "preparationOrdinal": c["preparationOrdinal"],
                "originalResult": exact, "originalResultBits": [bits(v).hex() for v in exact],
                "modelMatchesOriginalBits": True,
                "capturedComparison": captured_difference(exact, c["result"]),
                "rawSecondComparison": captured_difference([modeled["rawSecond"]], [c["rawSecond"]]),
                "convexityClamped": modeled["convexityClamped"]}
        if item["capturedComparison"]["nonzeroDifferenceCount"]:
            item["modelStages"] = modeled["stages"]
        result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--neutral-trace", required=True, type=Path)
    parser.add_argument("--candidate-trace", required=True, type=Path)
    parser.add_argument("--maintained-control-trace", required=True, type=Path)
    parser.add_argument("--reference-library", required=True, type=Path)
    parser.add_argument("--diagnostic-library", required=True, type=Path)
    parser.add_argument("--captured-on", required=True, type=date.fromisoformat)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    reference, diagnostic = identity(args.reference_library), identity(args.diagnostic_library)
    original = OriginalEval(reference["path"])
    paths = {"neutral": args.neutral_trace, "rejectedThreePrimitive": args.candidate_trace}
    traces = {name: json.loads(path.read_text()) for name, path in paths.items()}
    control = json.loads(args.maintained_control_trace.read_text())
    # Schema-1 preparation payloads in the older rejected candidate cannot be
    # relabeled schema-2 eval evidence. Only its qualified native calls are used.
    for t in (control, traces["neutral"]):
        error = runtime_provenance_error(t)
        if error:
            raise ValueError(error)
        provenance = t["runtimeProvenance"]
        core, mj = provenance["coreWasm"], provenance["mujoco"]
        for path, sha in ((core["path"], core["sha256"]),
                          (mj["jsPath"], mj["jsSha256"]), (mj["wasmPath"], mj["wasmSha256"])):
            if identity(Path(path))["sha256"] != sha:
                raise ValueError("retained runtime artifact changed since trace capture")
    if control["runtimeProvenance"]["mujoco"]["maintainedFilesMatchManifest"] is not True:
        raise ValueError("neutrality control is not the maintained browser runtime")
    neutral_difference = first_physics_difference(control, traces["neutral"])
    if neutral_difference is not None:
        raise AssertionError("evaluation recorder is not exactly replay-neutral: "+str(neutral_difference))
    inputs = {name: identity(path) for name, path in paths.items()}
    result = {"schema": "neural-workshop.marble-evaluation-full-oracle.v1",
        "provenance": {"capturedOn": args.captured_on.isoformat(), "nativeArchitecture": "arm64",
            "engineCommit": "13827e9ee56f097f57acf69ae52b078f9839682d",
            "referenceSha256": reference["sha256"], "diagnosticLibrarySha256": diagnostic["sha256"],
            "referenceLibrary": reference, "diagnosticLibrary": diagnostic,
            "inputTraces": inputs, "maintainedControlTrace": identity(args.maintained_control_trace),
            "neutralRuntime": traces["neutral"]["runtimeProvenance"],
            "originalBridge": {"publicDotOffset": ORIGINAL_DOT_OFFSET,
                "privateEvalOffset": ORIGINAL_EVAL_OFFSET, "entryBytes": EVAL_ENTRY.hex(),
                "contextBytes": 632, "pointBytes": 32, "layoutGuarded": True,
                "actualLoadedWheelGuarded": True},
            "neutralEvents": len(traces["neutral"]["events"]), "exactPhysicsNeutrality": True,
            "capturedBrowserZeroSigns": False,
            "scope": "direct hash-pinned original PrimalEval on bounded actual prepared operands; whole-solver-qualified native rebuild can still differ internally; not full original trajectory acceptance"},
        "summary": {"qualifiedBoundaries": 0, "nativeCalls": 0, "browserCalls": 0,
            "modelOriginalBitMatches": 0, "nativeDifferentCalls": 0, "browserDifferentCalls": 0,
            "nativeNonzeroDifferences": 0, "browserNonzeroDifferences": 0,
            "nativeZeroSignOnlyDifferences": 0, "browserZeroSignOnlyDifferences": 0},
        "captureFiles": [], "entries": []}
    for matrix, events, prefix in (("neutral", (17, 18, 216), "neutral-final"),
                                   ("rejectedThreePrimitive", (18, 216), "native-wheel-order-prefix")):
        for event in events:
            capture_path = args.capture_root/f"{prefix}-prepare{event}.jsonl"
            result["captureFiles"].append(identity(capture_path))
            documents = [json.loads(line) for line in capture_path.read_text().splitlines()]
            if len(documents) != 4 or [d.get("substep") for d in documents] != list(range(4)):
                raise ValueError("qualification must contain four ordered substeps")
            for document in documents:
                if document["event"] != event:
                    raise ValueError("qualification event differs from selection")
                captures = qualified_evaluations(document, reference_sha256=reference["sha256"],
                    diagnostic_sha256=diagnostic["sha256"], input_trace_sha256=inputs[matrix]["sha256"])
                native = comparisons(captures, original)
                boundary = {"matrix": matrix, "qualification": document, "nativeComparisons": native}
                summary = result["summary"]
                summary["qualifiedBoundaries"] += 1
                groups = [("native", native)]
                if matrix == "neutral":
                    browser_trace = traces[matrix]["events"][event]["newtonTraces"][document["substep"]]
                    browser = comparisons(capture_evaluations(browser_trace), original)
                    boundary["browserTrace"] = {k: browser_trace[k] for k in FIELDS}
                    boundary["browserComparisons"] = browser
                    groups.append(("browser", browser))
                for name, group in groups:
                    summary[name+"Calls"] += len(group)
                    summary["modelOriginalBitMatches"] += len(group)
                    for item in group:
                        diff = item["capturedComparison"]
                        summary[name+"DifferentCalls"] += bool(diff["nonzeroDifferenceCount"])
                        summary[name+"NonzeroDifferences"] += diff["nonzeroDifferenceCount"]
                        summary[name+"ZeroSignOnlyDifferences"] += diff["zeroSignOnlyCount"]
                document["trace"] = {k: document["trace"][k] for k in FIELDS}
                document["inputTrace"] = {k: document["inputTrace"][k] for k in ("path", "sha256")}
                document["nativeWheel"] = {k: document["nativeWheel"][k] for k in
                    ("distributionVersion", "mujocoVersion", "activeEngineLibrary")}
                result["entries"].append(boundary)
    print(json.dumps(result, indent=None if args.compact else 2, sort_keys=True,
                     separators=(",", ":") if args.compact else None, allow_nan=False))


if __name__ == "__main__":
    main()
