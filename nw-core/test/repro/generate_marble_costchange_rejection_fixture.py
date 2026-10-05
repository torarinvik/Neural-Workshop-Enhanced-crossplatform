#!/usr/bin/env python3
"""Neutral assigned-cost proof and locally corrected, physically inert rejection."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity,tagged
from marble_costchange_trace import (OriginalCostPrimitives,capture_cost,compare,
    existing_diagnostic_difference)
from marble_costchange_oracle import qualified_row
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_neutral_pair,validate_runtime_pair
from marble_trace_neutrality import first_physics_difference


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();root=args.capture_root
    trace_path=root/"cost-candidate-hard-trace.json"
    neutral_path=root/"cost-observer-hard-trace.json"
    trace=json.loads(trace_path.read_text());neutral=json.loads(neutral_path.read_text())
    before_report_path=root/"cost-observer-original-comparison.json"
    before_report=json.loads(before_report_path.read_text())
    old_path=Path(before_report["control"]["path"]);old=json.loads(old_path.read_text())
    validate_neutral_pair(neutral,old)
    if existing_diagnostic_difference(old,neutral):raise ValueError("observer changes old assigned diagnostics")
    validate_runtime_pair(trace,neutral)
    if len(trace["events"])!=7601 or first_physics_difference(neutral,trace):
        raise ValueError("this candidate must document its exact physical inertness, not infer it")
    original=OriginalCostPrimitives(args.reference_library)
    before,before_witnesses=compare(neutral,original);after,witnesses=compare(trace,original)
    expected=dict(calls=134,capturedRestoredCalls=0,composedBeforeDifferent=0,
        composedFinalDifferent=0,composedRestoredDifferent=0,dotDifferent=0,
        fiveTangentCalls=114,quadraticDifferent=0,threeTangentCalls=0,twoTangentCalls=20)
    if before!=dict(expected,quadraticDifferent=22,composedBeforeDifferent=3,composedFinalDifferent=3):
        raise ValueError("actual original pre-correction cost producer counts differ")
    if after!=expected or witnesses:raise ValueError("corrected public producer output differs")
    if (before_report["counts"]!=before or before_report["witnesses"]!=before_witnesses or
            before_report["trace"]!=identity(neutral_path) or before_report["control"]!=identity(old_path) or
            before_report["runtime"]!=neutral["runtimeProvenance"] or
            before_report["referenceSha256"]!=REFERENCE_SHA256 or
            before_report["neutrality"]!=dict(exact=True,events=7601,existingAssignedDiagnosticsExact=True)):
        raise ValueError("neutral receipt identity/actual-original scope differs")
    scope=dict(claimed=False,arithmeticCandidate=True,exact=True,events=7601,firstPhysicsDifference=None)
    after_path=root/"cost-candidate-cost-comparison.json";report=json.loads(after_path.read_text())
    if (report["counts"]!=after or report["witnesses"] or report["neutrality"]!=scope or
            report["trace"]!=identity(trace_path) or report["control"]!=identity(neutral_path) or
            report["runtime"]!=trace["runtimeProvenance"] or report["referenceSha256"]!=REFERENCE_SHA256):
        raise ValueError("candidate cost receipt identity/scope differs")
    proof_path=root/"compiled-cost-primitives-candidate-probe.log";proof=tagged(proof_path,"")
    golden_path=root/"original-cost-primitives-golden.jsonl"
    rows=[json.loads(line) for line in golden_path.read_text().splitlines()]
    if (proof["schema"]!="neural-workshop.marble-compiled-cost-primitives.v1" or
            proof["counts"]!=dict(captured=134,synthetic=1000,rejected=18) or
            proof["dimensions"]!={"2":354,"3":333,"5":447} or proof["differences"] or proof["first"] or
            proof["inputSha256"]!=identity(golden_path)["sha256"] or len(rows)!=1134 or
            sum(row["kind"]=="captured" for row in rows)!=134 or
            any(proof["runtime"][k]!=trace["runtimeProvenance"]["mujoco"][k]
                for k in ("jsSha256","wasmSha256"))):
        raise ValueError("actual compiled cost proof/golden identity differs")
    captured=[(e,s,c) for e,event in enumerate(neutral["events"])
        for s,t in enumerate(event.get("newtonTraces",[])) for c in capture_cost(t)]
    for row,(e,s,c) in zip(rows,captured):
        expected_row=qualified_row(original,c["delta"],c["matrix"],c["delta"],c["residual"],
            "captured",f"event{e}-step{s}-ordinal{c['ordinal']}")
        if row!=expected_row:raise ValueError("original captured golden differs")
    regressions={}
    for name,filename,counts in (("gauss","cost-candidate-gauss-comparison.json",
            dict(calls=125,constraintCostDifferent=0,gaussDifferent=0,originalGaussModelDifferent=0,
                 partialModelDifferentCalls=0,totalCostDifferent=0)),
            ("genericQCQP","cost-candidate-generic-comparison.json",
            dict(browserActiveDifferent=0,browserRawDifferent=0,groups=114,initializedStageDifferent=0,
                 modelActiveDifferent=0,modelRawDifferent=0,steps=1286)),
            ("qcqp2","cost-candidate-qcqp2-comparison.json",dict(activeDifferent=0,calls=18,
                 rawDifferent=0,threeTangentCalls=0,twoTangentCalls=18,twoTangentModelDifferent=0))):
        path=root/filename;r=json.loads(path.read_text())
        physical=(r.get("neutrality")==scope if name!="qcqp2" else
            r.get("physicsComparison")==dict(claimedRecorderNeutrality=False,events=7601,
                exactlyUnchanged=True,firstDifference=None))
        if (r["counts"]!=counts or r["trace"]!=identity(trace_path) or
                r["control"]!=identity(neutral_path) or r["runtime"]!=trace["runtimeProvenance"] or
                r["referenceSha256"]!=REFERENCE_SHA256 or not physical):
            raise ValueError("current-input local producer regression differs: "+name)
        regressions[name]=dict(report=identity(path),counts=counts)
    full=root/"cost-candidate-original-full.log";strict=root/"cost-candidate-original-strict.log"
    failure=[l for l in full.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if (len(failure)!=1 or "replayed 7601" not in failure[0] or "outcome=timeout" not in failure[0] or
            "home=0, lost=0, elapsed=120.016667s" not in failure[0] or
            "AssertionError: event[443].contacts:" not in strict.read_text()):
        raise ValueError("independent ordinary hard replay failure differs")
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    first=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: ");contacts=tagged(full,"CONTACT-SET MISMATCHES: ")
    if (sum(v["count"] for v in numeric.values())!=114869 or contacts["count"]!=162 or
            contacts["first"]["event"]!=443 or contacts["last"]["event"]!=2536 or
            first["context"]!="event[195].marble[0].value[10]" or first["delta"]!=8.252424372745537e-7):
        raise ValueError("hard-game rejection metrics differ")
    result=dict(schema="neural-workshop.marble-quadratic-native-order-rejected.v1",
        referenceSha256=REFERENCE_SHA256,trace=identity(trace_path),control=identity(neutral_path),
        priorArithmeticControl=identity(old_path),runtime=trace["runtimeProvenance"],
        observerPatch=identity(Path(__file__).with_name("marble_initialized_costchange_trace.patch")),
        deltaPatch=identity(Path(__file__).with_name("marble_quadratic_native_order_candidate.patch")),
        patchBase="all twelve prior recovery layers plus neutral cost observer; quadratic/probe delta additive only",
        before=dict(counts=before,firstWitness=before_witnesses[0],report=identity(before_report_path)),
        after=dict(counts=after,report=identity(after_path),physicsComparison=scope),
        compiledProof=proof,compiledProofLog=identity(proof_path),compiledGolden=identity(golden_path),
        otherLocalProducerRegressions=regressions,
        originalPrivateCostChangeCaptured=False,capturedBrowserZeroSigns=False,
        capturedThreeTangentCalls=0,syntheticThreeTangentCalls=333,
        rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,
            failFastLog=identity(strict),fullCountLog=identity(full),firstNumeric=first,
            numericExceedances=114869,contactSets=contacts,terminalSummary=failure[0]),
        scope="actual original public quadratic/dot corrected locally; all recorded physics exactly unchanged; composed cost/restoration remain reconstructions and three-tangent coverage is synthetic only; strict hard replay independently rejected; no production promotion")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
