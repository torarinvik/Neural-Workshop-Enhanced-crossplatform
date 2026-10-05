#!/usr/bin/env python3
"""Retain exact local Gauss correction without claiming gameplay improvement."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity, tagged
from marble_constraint_update_oracle import captured_difference
from marble_gauss_oracle import OriginalGauss, wheel_order
from marble_gauss_trace import capture_gauss
from marble_iteration_constraint_oracle import active_original
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_neutral_pair, validate_runtime_pair
from marble_trace_neutrality import first_physics_difference


def original_counts(selected, original, kernels):
    counts=dict(calls=0,originalGaussModelDifferent=0,gaussDifferent=0,
        constraintCostDifferent=0,totalCostDifferent=0,partialModelDifferentCalls=0)
    for g,c in selected:
        operands=[g[k] for k in ("Ma","qfrc_smooth","qacc","qacc_smooth")]
        value=original.solve(*operands);model=wheel_order(*operands)
        before=kernels.update(c["capture"])["cost"][0]
        counts["calls"]+=1
        counts["originalGaussModelDifferent"]+=value!=model["gauss"]
        counts["gaussDifferent"]+=value!=g["gauss"]
        counts["constraintCostDifferent"]+=before!=g["costBefore"]
        counts["totalCostDifferent"]+=before+value!=g["costAfter"]
        counts["partialModelDifferentCalls"]+=bool(captured_difference(
            model["partial"],g["partial"])["nonzeroDifferenceCount"])
    return counts


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();root=args.capture_root
    neutral_path=root/"gauss-hard-trace.json"
    candidate_path=root/"gauss-candidate-hard-trace.json"
    neutral=json.loads(neutral_path.read_text());candidate=json.loads(candidate_path.read_text())
    pre=json.loads((root/"gauss-original-comparison.json").read_text())
    post=json.loads((root/"gauss-candidate-original-comparison.json").read_text())
    control=json.loads(Path(pre["control"]["path"]).read_text())
    validate_neutral_pair(neutral,control)
    validate_runtime_pair(candidate,neutral)
    unchanged=first_physics_difference(neutral,candidate) is None
    if not unchanged or len(candidate["events"])!=7601:
        raise ValueError("this receipt requires the observed exactly unchanged 7601-event physics")
    expected_pre=dict(calls=125,originalGaussModelDifferent=0,gaussDifferent=43,
        constraintCostDifferent=0,totalCostDifferent=43,partialModelDifferentCalls=48)
    expected_post={k:(125 if k=="calls" else 0) for k in expected_pre}
    # Validate all packets in BOTH documents before loading/invoking private code.
    selections=[]
    for path,trace,report,expected in ((neutral_path,neutral,pre,expected_pre),
            (candidate_path,candidate,post,expected_post)):
        if (report["schema"]!="neural-workshop.marble-gauss-boundary.v1" or
                report["trace"]!=identity(path) or report["runtime"]!=trace["runtimeProvenance"] or
                report["counts"]!=expected or report["referenceSha256"]!=REFERENCE_SHA256):
            raise ValueError("captured original comparison identity/counts differ")
        selections.append([(g,c) for e in trace["events"] for t in e.get("newtonTraces",[])
            for g,c in zip(*capture_gauss(t))])
    if (post["control"]!=identity(neutral_path) or post["witnesses"] or
            pre["neutrality"]!=dict(exact=True,events=7601) or
            post["neutrality"]!=dict(claimed=False,arithmeticCandidate=True,exact=True,
                events=7601,firstPhysicsDifference=None)):
        raise ValueError("arithmetic experiment must be explicit even with unchanged physical output")
    original=OriginalGauss(args.reference_library);kernels=active_original(args.reference_library)
    for selected,expected in zip(selections,(expected_pre,expected_post)):
        if original_counts(selected,original,kernels)!=expected:
            raise ValueError("fresh direct-original replay does not reproduce retained counts")
    proof_path=root/"compiled-gauss-candidate-probe.log"
    proof=tagged(proof_path,"");runtime=candidate["runtimeProvenance"]
    golden=root/"original-gauss-golden.jsonl"
    if (proof["schema"]!="neural-workshop.marble-compiled-gauss.v1" or
            proof["counts"]!=dict(captured=125,synthetic=1000,rejected=16) or
            proof["differences"]!=0 or proof["first"] or
            proof["inputSha256"]!=identity(golden)["sha256"] or
            any(proof["runtime"][k]!=runtime["mujoco"][k] for k in ("jsSha256","wasmSha256"))):
        raise ValueError("actual compiled Gauss probe proof does not qualify")
    rows=[json.loads(l) for l in golden.read_text().splitlines()]
    if (len(rows)!=1125 or sum(r["kind"]=="captured" for r in rows)!=125 or
            any(r["referenceSha256"]!=REFERENCE_SHA256 for r in rows)):
        raise ValueError("actual original golden selection/identity differs")
    full=root/"gauss-candidate-original-full.log"
    failure=[l for l in full.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if len(failure)!=1 or "replayed 7601" not in failure[0] or "outcome=timeout" not in failure[0]:
        raise ValueError("expected ordinary uninterrupted original rejection")
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    result=dict(schema="neural-workshop.marble-gauss-native-order-rejected.v1",
        referenceSha256=REFERENCE_SHA256,runtime=runtime,trace=identity(candidate_path),
        recorderPatch=identity(Path(__file__).with_name("marble_initialized_gauss_trace.patch")),
        deltaPatch=identity(Path(__file__).with_name("marble_gauss_native_order_rejected.patch")),
        patchBase="nine QCQP recovery layers including fused radius, then neutral initialized Gauss recorder; arithmetic/probe delta additive only",
        neutral=dict(report=identity(root/"gauss-original-comparison.json"),trace=identity(neutral_path),
            control=pre["control"],counts=pre["counts"],neutrality=pre["neutrality"]),
        corrected=dict(report=identity(root/"gauss-candidate-original-comparison.json"),
            counts=post["counts"],comparison=post["neutrality"]),
        physics=dict(exactlyUnchanged=True,events=7601,firstDifference=None,
            scope="candidate arithmetic differs, but all recorded input/physics/contact fields are exactly unchanged relative to the rejected neutral Gauss control; not original gameplay parity"),
        compiledProof=proof,compiledProofLog=identity(proof_path),compiledGolden=identity(golden),
        originalPrivatePartialSumsCaptured=False,capturedBrowserZeroSigns=False,
        rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,
            failFastLog=identity(root/"gauss-candidate-original-strict.log"),fullCountLog=identity(full),
            firstNumeric=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: "),
            numericExceedances=sum(v["count"] for v in numeric.values()),
            contactSets=tagged(full,"CONTACT-SET MISMATCHES: "),terminalSummary=failure[0]),
        scope="local actual-original Gauss producer corrected; partial sums reconstructed/final-qualified; constraint cost from original exported impl; zero-constraint isolation is not full-context replay; physical failure unchanged; no production promotion")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
