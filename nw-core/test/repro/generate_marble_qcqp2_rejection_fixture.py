#!/usr/bin/env python3
"""Actual two-tangent local correction plus independent hard-game rejection."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity,tagged
from marble_qcqp_small_original import OriginalQCQPSmall
from marble_qcqp2_trace import compare
from marble_qcqp_trace import validate_runtime_pair,capture_qcqp
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_trace_neutrality import first_physics_difference


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();root=args.capture_root
    trace_path=root/"qcqp2-candidate-hard-trace.json"
    control_path=root/"gauss-candidate-hard-trace.json"
    trace=json.loads(trace_path.read_text());control=json.loads(control_path.read_text())
    validate_runtime_pair(trace,control)
    for document in (control,trace):
        for e in document["events"]:
            for t in e.get("newtonTraces",[]):capture_qcqp(t)
    original=OriginalQCQPSmall(args.reference_library)
    before,before_witnesses=compare(control,original);after,witnesses=compare(trace,original)
    expected=dict(calls=18,twoTangentCalls=18,threeTangentCalls=0,
        rawDifferent=0,activeDifferent=0,twoTangentModelDifferent=0)
    if before!=dict(expected,rawDifferent=11) or after!=expected or witnesses:
        raise ValueError("direct original two-tangent operand/output qualification differs")
    report_path=root/"qcqp2-candidate-original-comparison.json"
    report=json.loads(report_path.read_text())
    difference=first_physics_difference(control,trace)
    if (len(trace["events"])!=7601 or report["counts"]!=after or
            report["trace"]!=identity(trace_path) or report["control"]!=identity(control_path) or
            report["runtime"]!=trace["runtimeProvenance"] or
            report["referenceSha256"]!=REFERENCE_SHA256 or report["witnesses"] or
            report["physicsComparison"]!=dict(claimedRecorderNeutrality=False,events=7601,
                exactlyUnchanged=difference is None,firstDifference=list(difference) if difference else None)):
        raise ValueError("retained arithmetic comparison identity/physics scope differs")
    proof_path=root/"compiled-qcqp2-candidate-probe.log";proof=tagged(proof_path,"")
    golden=root/"original-qcqp2-golden.jsonl";runtime=trace["runtimeProvenance"]
    if (proof["schema"]!="neural-workshop.marble-compiled-qcqp2.v1" or
            proof["counts"]!=dict(captured=18,synthetic=1000,rejected=13) or
            proof["differences"] or proof["first"] or
            proof["inputSha256"]!=identity(golden)["sha256"] or
            any(proof["runtime"][k]!=runtime["mujoco"][k] for k in ("jsSha256","wasmSha256"))):
        raise ValueError("actual compiled small-QCQP qualification does not match")
    rows=[json.loads(l) for l in golden.read_text().splitlines()]
    if (len(rows)!=1018 or sum(r["kind"]=="captured" for r in rows)!=18 or
            any(r["referenceSha256"]!=REFERENCE_SHA256 for r in rows)):
        raise ValueError("actual original small-QCQP golden selection differs")
    full=root/"qcqp2-candidate-original-full.log"
    failure=[l for l in full.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if len(failure)!=1 or "replayed 7601" not in failure[0] or "outcome=timeout" not in failure[0]:
        raise ValueError("expected independently rejected ordinary original hard replay")
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    regressions={}
    for name,filename,expected_counts in (("gauss","qcqp2-candidate-gauss-comparison.json",
            dict(calls=125,originalGaussModelDifferent=0,gaussDifferent=0,
                constraintCostDifferent=0,totalCostDifferent=0,partialModelDifferentCalls=0)),
            ("genericQCQP","qcqp2-candidate-generic-comparison.json",
            dict(groups=114,steps=1286,modelRawDifferent=0,modelActiveDifferent=0,
                browserRawDifferent=0,initializedStageDifferent=0,browserActiveDifferent=0))):
        path=root/filename;r=json.loads(path.read_text())
        if (r["counts"]!=expected_counts or r["trace"]!=identity(trace_path) or
                r["control"]!=identity(control_path) or r["runtime"]!=runtime or
                r["referenceSha256"]!=REFERENCE_SHA256 or
                r["neutrality"]!=dict(claimed=False,arithmeticCandidate=True,exact=False,
                    events=7601,firstPhysicsDifference=list(difference))):
            raise ValueError("current-input regression no longer qualifies: "+name)
        regressions[name]=dict(report=identity(path),counts=expected_counts,
            scope="current initialized operands, not substitution into the prior trace's receipt")
    result=dict(schema="neural-workshop.marble-qcqp2-native-order-rejected.v1",
        referenceSha256=REFERENCE_SHA256,trace=identity(trace_path),control=identity(control_path),
        runtime=runtime,deltaPatch=identity(Path(__file__).with_name("marble_qcqp2_native_order_candidate.patch")),
        patchBase="all nine QCQP recovery layers, neutral Gauss observer and rejected Gauss arithmetic/probe delta; two-tangent arithmetic/probe delta additive only",
        before=dict(counts=before,firstWitness=before_witnesses[0]),after=dict(counts=after,
            report=identity(report_path),physicsComparison=report["physicsComparison"]),
        compiledProof=proof,compiledProofLog=identity(proof_path),compiledGolden=identity(golden),
        otherLocalProducerRegressions=regressions,
        originalPrivateIntermediatesCaptured=False,capturedBrowserZeroSigns=False,
        threeTangentCapturedCalls=0,threeTangentArithmeticChanged=False,
        rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,
            failFastLog=identity(root/"qcqp2-candidate-original-strict.log"),fullCountLog=identity(full),
            firstNumeric=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: "),
            numericExceedances=sum(v["count"] for v in numeric.values()),
            contactSets=tagged(full,"CONTACT-SET MISMATCHES: "),terminalSummary=failure[0]),
        scope="actual original public two-tangent raw kernel corrected locally; synthetic and current captured raw/flag proofs are not projection/costChange/restoration or full-game acceptance; intermediate model reconstructed/final-qualified; no production promotion")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
