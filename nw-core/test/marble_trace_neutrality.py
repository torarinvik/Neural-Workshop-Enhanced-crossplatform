#!/usr/bin/env python3
"""Compare two generated-play traces for exact physics-state neutrality.

Use this to decide whether a diagnostic MuJoCo build preserves the retained
runtime's recorded behavior. Solver/RNE trace payloads are excluded because
their purpose is to differ in schema/content; all event inputs, public state,
engine snapshots, contacts, and phase snapshots are compared exactly. The four
unused sparse-Jacobian indexing buffers are excluded only when both snapshots
explicitly identify their Jacobian representation as dense.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


TRACE_ONLY_KEYS = frozenset({
    "newtonTraces", "rneTraces", "rneAwakeStates", "rneProjectionTrace",
})
OPTIONAL_DIAGNOSTIC_KEYS = frozenset({
    "integratorReadSet",
    "engineSubsteps", "substepStates", "engineStep1Substeps",
    "engineStep1Inputs", "engineStep1Phases", "engineStep2Phases",
})
IDENTITY_KEYS = (
    "version", "rung", "runSeed", "boardSeed", "timeLimitMs",
    "contactDiagnostics", "engineDiagnosticEvents", "outcome", "result",
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DENSE_UNUSED_JACOBIAN_FIELDS = frozenset({
    "efc_J_rownnz", "efc_J_rowadr", "efc_J_colind", "efc_J_rowsuper",
})


def _both_dense_snapshots(reference: dict, candidate: dict) -> bool:
    """Require explicit representation metadata, not a default or truthiness."""
    return all(
        isinstance(snapshot.get("arrays"), dict)
        and isinstance(snapshot.get("model"), dict)
        and snapshot["model"].get("sparse_jacobian") is False
        for snapshot in (reference, candidate)
    )


def runtime_provenance_error(trace: dict[str, Any]) -> str | None:
    """Validate that a trace identifies the exact core and MuJoCo files used."""
    provenance = trace.get("runtimeProvenance")
    if not isinstance(provenance, dict):
        return "runtimeProvenance is missing or is not an object"
    if provenance.get("schema") != "neural-workshop.marble-runtime-provenance.v1":
        return "runtimeProvenance has an unsupported schema"
    core = provenance.get("coreWasm")
    mujoco = provenance.get("mujoco")
    if not isinstance(core, dict) or not isinstance(mujoco, dict):
        return "runtimeProvenance must identify coreWasm and mujoco objects"
    fields = (
        (core, "path", "core WASM"),
        (core, "sha256", "core WASM"),
        (mujoco, "jsPath", "MuJoCo JavaScript"),
        (mujoco, "jsSha256", "MuJoCo JavaScript"),
        (mujoco, "wasmPath", "MuJoCo WASM"),
        (mujoco, "wasmSha256", "MuJoCo WASM"),
    )
    for artifact, key, label in fields:
        value = artifact.get(key)
        if not isinstance(value, str) or not value:
            return f"{label} {key} is missing"
        if key.endswith("Sha256") or key == "sha256":
            if not SHA256_PATTERN.fullmatch(value):
                return f"{label} {key} is not a lowercase SHA-256 digest"
    if not isinstance(mujoco.get("maintainedFilesMatchManifest"), bool):
        return "MuJoCo maintainedFilesMatchManifest must be a boolean"
    if not isinstance(mujoco.get("wasmResolution"), str):
        return "MuJoCo wasmResolution is missing"
    return None


def _difference(reference: Any, candidate: Any, path: str) -> tuple[str, Any, Any] | None:
    if type(reference) is not type(candidate):
        return path, reference, candidate

    if isinstance(reference, dict):
        both_dense = _both_dense_snapshots(reference, candidate)
        reference_keys = reference.keys() - TRACE_ONLY_KEYS
        candidate_keys = candidate.keys() - TRACE_ONLY_KEYS
        for key in sorted(reference_keys | candidate_keys):
            if key in OPTIONAL_DIAGNOSTIC_KEYS and (
                    key not in reference or key not in candidate):
                continue
            child_path = f"{path}.{key}" if path else key
            if key not in reference:
                return child_path, "<missing>", candidate[key]
            if key not in candidate:
                return child_path, reference[key], "<missing>"
            left, right = reference[key], candidate[key]
            if key == "arrays" and both_dense:
                # MuJoCo's dense mj_addConstraint branch writes efc_J directly;
                # it neither initializes nor consumes these sparse indices.
                # Do not mask efc_J itself or fields in any other dictionary.
                left = {name: value for name, value in left.items()
                        if name not in DENSE_UNUSED_JACOBIAN_FIELDS}
                right = {name: value for name, value in right.items()
                         if name not in DENSE_UNUSED_JACOBIAN_FIELDS}
            found = _difference(left, right, child_path)
            if found is not None:
                return found
        return None

    if isinstance(reference, list):
        if len(reference) != len(candidate):
            return f"{path}.length", len(reference), len(candidate)
        for index, (left, right) in enumerate(zip(reference, candidate)):
            found = _difference(left, right, f"{path}[{index}]")
            if found is not None:
                return found
        return None

    if isinstance(reference, float):
        if math.isnan(reference) and math.isnan(candidate):
            return None
    if reference != candidate:
        return path, reference, candidate
    return None


def first_physics_difference(
    reference: dict[str, Any], candidate: dict[str, Any]
) -> tuple[str, Any, Any] | None:
    """Return the first exact non-trace difference, or None if equivalent."""
    for key in IDENTITY_KEYS:
        if key not in reference or key not in candidate:
            return f"metadata.{key}", reference.get(key, "<missing>"), candidate.get(key, "<missing>")
        found = _difference(reference[key], candidate[key], f"metadata.{key}")
        if found is not None:
            return found

    reference_events = reference.get("events")
    candidate_events = candidate.get("events")
    if not isinstance(reference_events, list) or not isinstance(candidate_events, list):
        return "events", type(reference_events).__name__, type(candidate_events).__name__
    if len(reference_events) != len(candidate_events):
        return "events.length", len(reference_events), len(candidate_events)

    for index, (left, right) in enumerate(zip(reference_events, candidate_events)):
        found = _difference(left, right, f"events[{index}]")
        if found is not None:
            return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="retained-runtime trace")
    parser.add_argument("candidate", type=Path, help="diagnostic/candidate trace")
    parser.add_argument("--require-provenance", action="store_true",
                        help="require SHA-256 identities for both traces' core and MuJoCo files")
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text())
    candidate = json.loads(args.candidate.read_text())
    if args.require_provenance:
        for label, trace in (("reference", reference), ("candidate", candidate)):
            error = runtime_provenance_error(trace)
            if error is not None:
                print(f"FAIL: {label} trace provenance: {error}")
                return 2
            provenance = trace["runtimeProvenance"]
            print(f"PROVENANCE {label}: core={provenance['coreWasm']['sha256']} "
                  f"mujoco.js={provenance['mujoco']['jsSha256']} "
                  f"mujoco.wasm={provenance['mujoco']['wasmSha256']} "
                  f"maintained={provenance['mujoco']['maintainedFilesMatchManifest']}")
    difference = first_physics_difference(reference, candidate)
    if difference is None:
        print("PASS: all recorded event and physics snapshots are exactly equal")
        return 0
    path, left, right = difference
    print(f"FAIL: first physics-trace difference at {path}")
    print(f"  reference: {left!r}")
    print(f"  candidate: {right!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
