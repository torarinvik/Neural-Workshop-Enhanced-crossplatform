#!/usr/bin/env python3
"""Qualify the layer-15 local inertia correction and independent game rejection."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity,tagged
from marble_inertia_original import OriginalInertia,captures,compare,qualified_row,synthetic_inputs
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_runtime_pair
from marble_trace_neutrality import first_physics_difference,IDENTITY_KEYS


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();root=args.capture_root
    before_path=root/"cost-candidate-hard-trace.json"
    after_path=root/"inertia-candidate-hard-trace.json"
    before=json.loads(before_path.read_text());after=json.loads(after_path.read_text())
    validate_runtime_pair(after,before)
    if len(before["events"])!=7601 or len(after["events"])!=7601:
        raise ValueError("complete hard trace required")
    if any(before.get(key)!=after.get(key) for key in IDENTITY_KEYS):
        raise ValueError("hard replay configuration/outcome identity differs")
    for e,(a,b) in enumerate(zip(before["events"],after["events"])):
        if {k:a[k] for k in ("kind","dt","held","key") if k in a}!={k:b[k] for k in ("kind","dt","held","key") if k in b}:
            raise ValueError("hard input schedule differs at event "+str(e))
    original=OriginalInertia(args.reference_library)
    old_counts,old_witnesses=compare(before,original)
    counts,witnesses=compare(after,original)
    expected=dict(calls=120,accelerationCalls=60,velocityCalls=60,differentCalls=0,
        nonzeroDifferentValues=0,zeroSignOnlyCalls=0,modelDifferentCalls=0)
    if old_counts!=dict(expected,differentCalls=42,nonzeroDifferentValues=66):
        raise ValueError("pre-correction actual-original inertia evidence differs")
    if counts!=expected or witnesses:raise ValueError("current inertia producer still differs")
    first=first_physics_difference(before,after)
    if first is not None:first=list(first)
    if first!=["events[0].engineStep1Inputs[1].arrays.qacc[4]",0,-4.9679927381240586e-27]:
        raise ValueError("first recorded physical change differs")
    physical=dict(claimedRecorderNeutrality=False,events=7601,exactlyUnchanged=False,firstDifference=first)
    report_paths=(root/"inertia-before-original.json",root/"inertia-candidate-original-comparison.json")
    for path,trace_path,trace,control_path,expected_counts,expected_witnesses,scope in (
            (report_paths[0],before_path,before,before_path,old_counts,old_witnesses,
             dict(claimedRecorderNeutrality=False,events=7601,exactlyUnchanged=True,firstDifference=None)),
            (report_paths[1],after_path,after,before_path,counts,witnesses,physical)):
        report=json.loads(path.read_text())
        if (report["counts"]!=expected_counts or report["witnesses"]!=expected_witnesses or
                report["trace"]!=identity(trace_path) or report["control"]!=identity(control_path) or
                report["runtime"]!=trace["runtimeProvenance"] or
                report["referenceSha256"]!=REFERENCE_SHA256 or report["physicsComparison"]!=scope or
                report["capturedBrowserZeroSigns"] or report["originalPrivateRneIntermediatesCaptured"]):
            raise ValueError("inertia comparison receipt identity/scope differs")
    golden_path=root/"original-inertia-golden.jsonl"
    rows=[json.loads(line) for line in golden_path.read_text().splitlines()]
    selected=captures(before)
    expected_rows=[qualified_row(original,c["inertia"],c["vector"],"captured",
        f"event{c['event']}-step{c['substep']}-body{c['body']}-{c['stage']}") for c in selected]
    expected_rows.extend(qualified_row(original,*operands,"synthetic",f"synthetic{i}")
        for i,operands in enumerate(synthetic_inputs()))
    if rows!=expected_rows:raise ValueError("actual original compiled golden differs")
    proof_path=root/"compiled-inertia-candidate-probe.log";proof=tagged(proof_path,"")
    if (proof["schema"]!="neural-workshop.marble-compiled-inertia.v1" or
            proof["counts"]!=dict(captured=120,synthetic=1000,rejected=12) or
            proof["differences"] or proof["first"] or
            proof["inputSha256"]!=identity(golden_path)["sha256"] or
            any(proof["runtime"][k]!=after["runtimeProvenance"]["mujoco"][k]
                for k in ("jsSha256","wasmSha256"))):
        raise ValueError("actual compiled inertia proof differs")
    expected_producers=dict(
        cost=dict(calls=134,capturedRestoredCalls=0,composedBeforeDifferent=0,
            composedFinalDifferent=0,composedRestoredDifferent=0,dotDifferent=0,
            fiveTangentCalls=114,quadraticDifferent=0,threeTangentCalls=0,twoTangentCalls=20),
        gauss=dict(calls=125,constraintCostDifferent=0,gaussDifferent=0,originalGaussModelDifferent=0,
            partialModelDifferentCalls=0,totalCostDifferent=0),
        generic=dict(browserActiveDifferent=0,browserRawDifferent=0,groups=114,
            initializedStageDifferent=0,modelActiveDifferent=0,modelRawDifferent=0,steps=1286),
        qcqp2=dict(activeDifferent=0,calls=18,rawDifferent=0,threeTangentCalls=0,
            twoTangentCalls=18,twoTangentModelDifferent=0))
    regressions={}
    for name,expected_counts in expected_producers.items():
        path=root/("inertia-candidate-"+name+"-comparison.json");report=json.loads(path.read_text())
        expected_physical=(physical if name=="qcqp2" else dict(claimed=False,arithmeticCandidate=True,
            exact=False,events=7601,firstPhysicsDifference=first))
        if (report["counts"]!=expected_counts or report["trace"]!=identity(after_path) or
                report["control"]!=identity(before_path) or report["runtime"]!=after["runtimeProvenance"] or
                report["referenceSha256"]!=REFERENCE_SHA256 or
                report.get("physicsComparison" if name=="qcqp2" else "neutrality")!=expected_physical):
            raise ValueError("current-input producer regression differs: "+name)
        regressions[name]=dict(report=identity(path),counts=expected_counts)
    compiled_regressions={}
    for name in ("cost-primitives","gauss","generic","qcqp2"):
        path=root/("compiled-inertia-"+name+"-regression.log");report=tagged(path,"")
        if report["differences"] or report["first"] or any(report["runtime"][k]!=proof["runtime"][k]
                for k in ("jsSha256","wasmSha256")):
            raise ValueError("frozen actual compiled producer regression differs: "+name)
        compiled_regressions[name]=dict(log=identity(path),proof=report)
    strict=root/"inertia-candidate-original-strict.log";full=root/"inertia-candidate-original-full.log"
    failure=[line for line in full.read_text().splitlines() if line.startswith("FAIL: original Python Marble")]
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    first_numeric=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: ")
    contacts=tagged(full,"CONTACT-SET MISMATCHES: ")
    if (len(failure)!=1 or "replayed 7601" not in failure[0] or "outcome=timeout" not in failure[0] or
            "home=0, lost=0, elapsed=120.016667s" not in failure[0] or
            "AssertionError: event[463].contacts:" not in strict.read_text() or
            sum(v["count"] for v in numeric.values())!=110690 or contacts["count"]!=105 or
            (contacts["first"]["event"],contacts["last"]["event"])!=(463,1966) or
            first_numeric["context"]!="event[195].marble[0].value[10]" or
            first_numeric["delta"]!=4.996572333659799e-7):
        raise ValueError("independent ordinary full-game rejection differs")
    result=dict(schema="neural-workshop.marble-inertia-native-order-rejected.v1",
        referenceSha256=REFERENCE_SHA256,control=identity(before_path),trace=identity(after_path),
        runtime=after["runtimeProvenance"],
        deltaPatch=identity(Path(__file__).with_name("marble_inertia_native_order_candidate.patch")),
        patchBase="all fourteen prior ordered recovery layers; additive platform-guarded shared inertia/probe delta only",
        before=dict(report=identity(report_paths[0]),counts=old_counts,firstWitness=old_witnesses[0]),
        after=dict(report=identity(report_paths[1]),counts=counts,physicsComparison=physical),
        compiledProof=proof,compiledProofLog=identity(proof_path),compiledGolden=identity(golden_path),
        otherCurrentLocalProducerRegressions=regressions,compiledProducerRegressions=compiled_regressions,
        capturedBrowserZeroSigns=False,originalPrivateRneIntermediatesCaptured=False,
        sharedHelperOtherCallers=["mass-matrix initialization","composite rigid-body inertia","derivatives"],
        rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,
            failFastLog=identity(strict),fullCountLog=identity(full),firstNumeric=first_numeric,
            numericExceedances=110690,contactSets=contacts,terminalSummary=failure[0]),
        scope="actual original shared public inertia return locally corrected on current combined candidate; recorded physics changes but strict original hard replay still fails; not proof of complete RNE/Jacobian identity, not a compiler defect, no production promotion")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
