#!/usr/bin/env python3
"""Reproduce actual-original complete comVel qualification and game rejection."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity, tagged
from marble_comvel_original import (OriginalComVel, selected_inputs, validated_engine,
                                    reconstruct, compact, bit_vectors, LAYOUTS)
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_runtime_pair
from marble_trace_neutrality import first_physics_difference, IDENTITY_KEYS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--reference-library", type=Path, required=True)
    args = parser.parse_args()
    root = args.capture_root
    paths = [root / (prefix + "-hard-trace.json") for prefix in
             ("rne-family-candidate", "comvel-family-candidate")]
    traces = [json.loads(p.read_text()) for p in paths]
    before, after = traces
    validate_runtime_pair(after, before)
    if any(len(t["events"]) != 7601 for t in traces) or any(before.get(k) != after.get(k) for k in IDENTITY_KEYS):
        raise ValueError("complete unchanged hard configuration and results required")
    for event, (a, b) in enumerate(zip(before["events"], after["events"])):
        if {k: a[k] for k in ("kind", "dt", "held", "key") if k in a} != {k: b[k] for k in ("kind", "dt", "held", "key") if k in b}:
            raise ValueError("input schedule changed at event " + str(event))
    selected = [selected_inputs(t) for t in traces]
    matrix = [(e, s) for e in (0, 1, 17, 18, 216) for s in range(4)]
    if any([(r["event"], r["substep"]) for r in rows] != matrix for rows in selected):
        raise ValueError("complete current named comVel matrix required")
    original = OriginalComVel(args.reference_library)
    import mujoco
    from marble_source_play_trace import native_mujoco_provenance
    native = native_mujoco_provenance(mujoco)["activeEngineLibrary"]
    if native["sha256"] != REFERENCE_SHA256 or Path(native["path"]).resolve() != original.guard.anchor.path:
        raise ValueError("owned models must come from the exact original wheel")
    model = mujoco.MjModel.from_xml_string(LAYOUTS[1])
    data = mujoco.MjData(model)
    expected_counts = [dict(boundaries=20, differentBoundaries=8, differentValues=21,
                            cvelDifferentBoundaries=0, cdofDotDifferentBoundaries=8,
                            modelDifferentBoundaries=0, modelDifferentValues=0),
                       dict(boundaries=20, differentBoundaries=0, differentValues=0,
                            cvelDifferentBoundaries=0, cdofDotDifferentBoundaries=0,
                            modelDifferentBoundaries=0, modelDifferentValues=0)]
    reports = []
    for path, trace, rows, counts, filename in zip(paths, traces, selected, expected_counts,
            ("rne-family-comvel-original-comparison.json", "comvel-family-current-original-comparison.json")):
        report_path = root / filename
        report = json.loads(report_path.read_text())
        if (report["trace"] != identity(path) or report["control"] != identity(paths[0]) or
                report["runtime"] != trace["runtimeProvenance"] or report["counts"] != counts or
                report["referenceSha256"] != REFERENCE_SHA256 or len(report["boundaries"]) != 20 or
                report["nativeRuntime"]["activeEngineLibrary"]["sha256"] != REFERENCE_SHA256 or
                not report["matchedInputs"] or report["ordinaryTrajectoryAcceptance"] or report["promoted"]):
            raise ValueError("complete actual-original comVel report identity/scope differs")
        computed_different, computed_values = 0, 0
        for row, boundary in zip(rows, report["boundaries"]):
            actual = original.evaluate(model, data, row["engine"])
            differences = {}
            for field, values in actual.items():
                d = [dict(index=i, original=x, browser=y) for i, (x, y) in
                     enumerate(zip(values, row["captured"][field])) if x != y]
                if d:
                    differences[field] = d
            if ((boundary["event"], boundary["substep"]) != (row["event"], row["substep"]) or
                    boundary["input"] != compact(row["engine"]) or boundary["captured"] != row["captured"] or
                    boundary["actualOriginalBits"] != bit_vectors(actual) or boundary["actualOriginal"] != actual or
                    boundary["differences"] != differences or boundary["modelDifferences"] or
                    bit_vectors(reconstruct(row["engine"])) != bit_vectors(actual)):
                raise ValueError("complete original comVel return/input/model differs")
            computed_different += bool(differences)
            computed_values += sum(len(v) for v in differences.values())
        if (computed_different, computed_values) != (counts["differentBoundaries"], counts["differentValues"]):
            raise ValueError("complete comVel counts disagree with actual returns")
        # Keep every complete input and actual-original return bit, but avoid
        # duplicating two full float renderings of those same output arrays.
        # Captured nonzero values reconstruct from actualOriginalBits plus the
        # retained differences; browser JSON zero signs remain unqualified.
        receipt_boundaries = [{k: b[k] for k in
                              ("event", "substep", "input", "actualOriginalBits", "differences")}
                             for b in report["boundaries"]]
        reports.append(dict(report=identity(report_path), counts=counts, boundaries=receipt_boundaries))
    golden_path = root / "original-comvel-golden.jsonl"
    golden = [json.loads(line) for line in golden_path.read_text().splitlines()]
    if len(golden) != 1020:
        raise ValueError("complete captured/synthetic original comVel golden required")
    for row in golden:
        validated_engine(row["input"])
        if (type(row["layout"]) is not int or not 0 <= row["layout"] < len(LAYOUTS) or
                row["xml"] != LAYOUTS[row["layout"]] or row["referenceSha256"] != REFERENCE_SHA256):
            raise ValueError("actual original golden layout/reference differs")
    for golden_row, row in zip(golden[:20], selected[0]):
        if (golden_row["kind"] != "captured" or golden_row["layout"] != 1 or
                golden_row["label"] != f"event{row['event']}-step{row['substep']}" or
                golden_row["input"] != compact(row["engine"])):
            raise ValueError("golden captured operands differ from retained16")
    contexts = {}
    for index, row in enumerate(golden):
        if index >= 20 and (row["kind"] != "synthetic" or row["label"] != f"synthetic{index - 20}" or row["layout"] != (index - 20) % 5):
            raise ValueError("complete deterministic synthetic matrix required")
        if row["xml"] not in contexts:
            m = mujoco.MjModel.from_xml_string(row["xml"])
            contexts[row["xml"]] = (m, mujoco.MjData(m))
        actual = original.evaluate(*contexts[row["xml"]], row["input"])
        if (bit_vectors(actual) != row["expectedBits"] or bit_vectors(row["expected"]) != row["expectedBits"] or
                bit_vectors(reconstruct(row["input"])) != row["expectedBits"]):
            raise ValueError("actual original golden/model bits differ")
    proofs = []
    for filename, trace, expected_differing in (
            ("compiled-comvel-family-control.log", before, dict(captured=8, synthetic=675)),
            ("compiled-comvel-family-candidate-qualified.log", after, dict(captured=0, synthetic=0))):
        log = root / filename
        proof = tagged(log, "")
        if (proof["counts"] != dict(captured=20, synthetic=1000) or
                proof["layouts"] != {"0": 200, "1": 220, "2": 200, "3": 200, "4": 200} or
                proof["differingCalls"] != expected_differing or
                proof["differences"] != sum(expected_differing.values()) or
                proof["inputSha256"] != identity(golden_path)["sha256"] or
                not proof["completePublicCall"] or proof["ordinaryTrajectoryAcceptance"] or proof["promoted"] or
                any(proof["runtime"][k] != trace["runtimeProvenance"]["mujoco"][k] for k in ("jsSha256", "wasmSha256"))):
            raise ValueError("compiled actual complete comVel identity/counts differ")
        if not sum(expected_differing.values()) and (proof["first"] or proof["differentValues"]):
            raise ValueError("compiled complete comVel still differs")
        proofs.append(dict(log=identity(log), proof=proof))
    regressions = {}
    for name, size, count_key in (("inertia", 120, "calls"), ("cost", 134, "calls"),
            ("gauss", 125, "calls"), ("generic", 114, "groups"), ("qcqp2", 18, "calls"), ("rne", 20, "boundaries")):
        path = root / ("comvel-family-candidate-" + name + "-comparison.json")
        report = json.loads(path.read_text())
        excluded = {count_key, "accelerationCalls", "velocityCalls", "twoTangentCalls", "fiveTangentCalls", "steps"}
        if (report["counts"][count_key] != size or any(v for k, v in report["counts"].items() if k not in excluded) or
                report["trace"] != identity(paths[1]) or report["control"] != identity(paths[0]) or
                report["runtime"] != after["runtimeProvenance"] or report["referenceSha256"] != REFERENCE_SHA256):
            raise ValueError("current local producer regression differs: " + name)
        log = root / ("compiled-comvel-family-" + name + "-regression.log")
        compiled = tagged(log, "")
        if compiled["differences"] or compiled["first"] or any(compiled["runtime"][k] != proofs[1]["proof"]["runtime"][k] for k in ("jsSha256", "wasmSha256")):
            raise ValueError("frozen compiled producer regression differs: " + name)
        if name == "rne" and compiled["accelerationControlMatches"] != 1020:
            raise ValueError("RNE acceleration path control is missing")
        regressions[name] = dict(report=identity(path), counts=report["counts"], compiledLog=identity(log), compiledProof=compiled)
    full, strict = root / "comvel-family-candidate-original-full.log", root / "comvel-family-candidate-original-strict.log"
    first = tagged(full, "FIRST NUMERIC PARITY EXCEEDANCE: ")
    contacts = tagged(full, "CONTACT-SET MISMATCHES: ")
    numeric = tagged(full, "NUMERIC PARITY EXCEEDANCES: ")
    failures = [line for line in full.read_text().splitlines() if line.startswith("FAIL: original Python Marble")]
    if (len(failures) != 1 or "replayed 7601" not in failures[0] or "outcome=timeout" not in failures[0] or
            "home=0, lost=0, elapsed=120.016667s" not in failures[0] or
            "AssertionError: event[463].contacts:" not in strict.read_text() or
            sum(v["count"] for v in numeric.values()) != 111510 or contacts["count"] != 103 or
            (contacts["first"]["event"], contacts["last"]["event"]) != (463, 1966) or
            first["context"] != "event[195].marble[0].value[10]" or first["delta"] != 4.950429832728531e-7):
        raise ValueError("independent ordinary complete-game rejection differs")
    difference = first_physics_difference(before, after)
    if difference is None:
        raise ValueError("arithmetic candidate must not be labeled recorder neutral")
    result = dict(schema="neural-workshop.marble-comvel-family-rejected.v1",
                  referenceSha256=REFERENCE_SHA256, control=identity(paths[0]), trace=identity(paths[1]),
                  runtime=after["runtimeProvenance"],
                  deltaPatch=identity(Path(__file__).with_name("marble_comvel_family_candidate.patch")),
                  patchBase="all sixteen ordered layers; Emscripten-only complete comVel cross-motion/grouped DOF producer; native macros resolve to original calls; no shared generic primitive or RNE branch modification",
                  before=reports[0], after=reports[1], compiledControl=proofs[0], compiledCandidate=proofs[1],
                  compiledGolden=identity(golden_path), localProducerRegressions=regressions,
                  originalPrivateIntermediatesCaptured=False, capturedBrowserZeroSignsQualified=False,
                  physicsComparison=dict(claimedRecorderNeutrality=False, exactlyUnchanged=False,
                                         events=7601, firstDifference=list(difference)),
                  rejection=dict(promoted=False, ordinaryUnsynchronized=True, replayEvents=7601,
                                 firstNumeric=first, numericExceedances=111510, contactSets=contacts,
                                 failFastLog=identity(strict), fullCountLog=identity(full), terminalSummary=failures[0]),
                  scope="complete actual original comVel locally qualified; full hard replay has fewer contact differences but more numeric breaches than retained16; rejected, no production promotion or threshold change")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
