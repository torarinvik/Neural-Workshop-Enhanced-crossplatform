#!/usr/bin/env python3
"""Retain local generic-kernel success and independent full-game rejection."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity, tagged, DIAGNOSTIC_SHA
from marble_constraint_update_oracle import captured_difference
from marble_eval_trace import capture_evaluations, qualified_evaluations
from marble_iteration_trace import compare_iteration_traces
from marble_prepare_trace import capture_preparations, qualified_preparations
from marble_primal_eval_oracle import OriginalEval, REFERENCE_SHA256
from marble_primal_prepare_oracle import prepare
from marble_native_dot_oracle import wheel_dot
from marble_qcqp_kernel_trace import capture_kernel
from marble_qcqp_trace import validate_runtime_pair
from marble_trace_neutrality import first_physics_difference


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    p.add_argument("--diagnostic-library",type=Path,required=True)
    args=p.parse_args();root=args.capture_root
    path=root/"fused-candidate-hard-trace.json"
    trace=json.loads(path.read_text())
    control=json.loads((root/"kernel-hard-trace.json").read_text())
    validate_runtime_pair(trace,control)
    if identity(args.diagnostic_library)["sha256"]!=DIAGNOSTIC_SHA:
        raise ValueError("native diagnostic qualification identity differs")
    pair=root/"retained-fused-candidate-dist"
    runtime=trace["runtimeProvenance"]
    for name,key in (("mujoco.js","jsSha256"),("mujoco.wasm","wasmSha256")):
        if identity(pair/name)["sha256"]!=runtime["mujoco"][key]:
            raise ValueError("retained compiled pair differs")
    proof=tagged(root/"compiled-qcqp-fused-probe.log","")
    if (proof["schema"]!="neural-workshop.marble-compiled-qcqp.v1" or
            proof["counts"]!=dict(captured=114,synthetic=1000,rejected=13) or
            proof["differences"]!=0 or proof["first"] or
            proof["inputSha256"]!=identity(root/"original-qcqp-golden.jsonl")["sha256"] or
            any(proof["runtime"][k]!=runtime["mujoco"][k] for k in ("jsSha256","wasmSha256"))):
        raise ValueError("actual compiled generic proof does not qualify")
    golden=[json.loads(l) for l in (root/"original-qcqp-golden.jsonl").read_text().splitlines()]
    if (len(golden)!=1114 or sum(g["kind"]=="captured" for g in golden)!=114 or
            any(g["referenceSha256"]!=REFERENCE_SHA256 for g in golden)):
        raise ValueError("original golden selection/identity differs")
    update_log=root/"fused-actual-original-constraint-updates.jsonl"
    updates=[json.loads(l) for l in update_log.read_text().splitlines()]
    if (len(updates)!=38 or any(r["referenceSha256"]!=REFERENCE_SHA256 or
            r["traceSha256"]!=identity(path)["sha256"] or
            any(r[k].get("nonzeroDifferenceCount",r[k]["count"]) for k in ("force","state","cost")) or
            any(v["count"] for v in r["wheelOrderModelAgainstDirectWheel"].values()) for r in updates)):
        raise ValueError("actual original constraint-update operand/output proof differs")
    kernel=json.loads((root/"fused-candidate-kernel-comparison.json").read_text())
    counts=dict(groups=114,steps=1286,modelRawDifferent=0,modelActiveDifferent=0,
        browserRawDifferent=0,initializedStageDifferent=0,browserActiveDifferent=0)
    actual=[g for e in trace["events"] for t in e.get("newtonTraces",[]) for g in capture_kernel(t)]
    if (kernel["counts"]!=counts or kernel["firstFields"] or
            len(actual)!=114 or sum(len(g["steps"]) for g in actual)!=1286 or
            kernel["referenceSha256"]!=REFERENCE_SHA256 or
            kernel["trace"]!=identity(path) or kernel["runtime"]!=runtime or
            kernel["neutrality"].get("claimed") is not False or
            kernel["neutrality"].get("arithmeticCandidate") is not True or
            kernel["neutrality"]["firstPhysicsDifference"]!=list(first_physics_difference(control,trace))):
        raise ValueError("captured compiled kernel comparison is missing/mismatched")
    full=root/"fused-candidate-original-full.log"
    failure=[l for l in full.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if len(failure)!=1 or "replayed 7601" not in failure[0]:
        raise ValueError("expected independent ordinary uninterrupted rejection")
    summary=dict(qualifiedBoundaries=0,wholeSolverDifferentBoundaries=0,
        preparationCalls=0,preparationValues=0,preparationNonzeroDifferences=0,
        evaluationCalls=0,evaluationNonzeroDifferences=0,iterationExactBoundaries=0,
        noSlipContactExactBoundaries=0)
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    result=dict(schema="neural-workshop.marble-qcqp-fused-radius-rejected.v1",
        provenance=dict(referenceSha256=REFERENCE_SHA256,diagnosticLibrary=identity(args.diagnostic_library),
            trace=identity(path),runtime=runtime,
            scope="local generic QCQP is corrected; complete uninterrupted game still rejected; rebuild intermediates are not universally original private-state captures"),
        deltaPatch=identity(Path(__file__).with_name("marble_qcqp_fused_radius_rejected.patch")),
        patchBase="five neutral layers + complete residual v2 alternative + raw QCQP observer + kernel observer; additive radius/probe delta only",
        compiledProof=proof,compiledProofLog=identity(root/"compiled-qcqp-fused-probe.log"),
        compiledGolden=identity(root/"original-qcqp-golden.jsonl"),
        actualOriginalConstraintUpdate=dict(calls=38,forceNonzeroDifferences=0,
            stateDifferences=0,costNonzeroDifferences=0,referenceModelDifferences=0,
            zeroSignOnlyCalls=sum(any(r[k].get("zeroSignOnlyCount",0) for k in ("force","cost")) for r in updates),
            log=identity(update_log),scope="actual original exported constraintUpdate impl on initialized captured operands; does not include Gauss-cost accumulation or Jacobian transpose multiplication"),
        kernel=dict(counts=counts,neutrality=kernel["neutrality"],
            comparisonReport=identity(root/"fused-candidate-kernel-comparison.json"),
            control=kernel["control"],firstRetainedContact=kernel["firstRetainedContact"]),
        rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,
            failFastLog=identity(root/"fused-candidate-original-strict.log"),fullCountLog=identity(full),
            firstNumeric=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: "),
            numericExceedances=sum(v["count"] for v in numeric.values()),
            contactSets=tagged(full,"CONTACT-SET MISMATCHES: "),terminalSummary=failure[0]),
        summary=summary,boundaries=[])
    original=OriginalEval(args.reference_library)
    for event in (17,18,216):
        capture=root/f"fused-native-prepare{event}.jsonl"
        output=root/f"fused-original-output{event}.jsonl"
        documents=[json.loads(l) for l in capture.read_text().splitlines()]
        outputs=[json.loads(l) for l in output.read_text().splitlines()]
        if len(documents)!=4 or len(outputs)!=4:
            raise ValueError("exactly four qualified substeps required")
        for substep,(document,active) in enumerate(zip(documents,outputs)):
            if (document["event"],document["substep"],active["event"],active["substep"])!=(event,substep,event,substep):
                raise ValueError("native/original selection differs")
            for qualify in (qualified_preparations,qualified_evaluations):
                qualify(document,reference_sha256=REFERENCE_SHA256,diagnostic_sha256=DIAGNOSTIC_SHA,
                    input_trace_sha256=identity(path)["sha256"])
            browser=trace["events"][event]["newtonTraces"][substep]
            preparations=capture_preparations(browser);values=prep_diff=0
            for c in preparations:
                model=prepare(**c["inputs"],dot=wheel_dot)
                a=model["quadGauss"]+[v for row in model["rows"] for v in row["quad"]]
                b=c["quadGauss"]+[v for row in c["rows"] for v in row["quad"]]
                values+=len(a);prep_diff+=captured_difference(a,b)["nonzeroDifferenceCount"]
            evaluations=capture_evaluations(browser)
            eval_diff=sum(captured_difference(original.evaluate(**c["inputs"]),c["result"])["nonzeroDifferenceCount"] for c in evaluations)
            phase=next(s for s in trace["events"][event]["engineStep2Phases"][substep] if s["phase"]=="fwdConstraint")
            whole={}
            for field,a in active["arrays"].items():
                b=phase["engine"]["arrays"][field]
                if len(a)!=len(b):raise ValueError("whole solver output width differs")
                diffs=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
                if diffs:whole[field]=dict(count=len(diffs),first=diffs[:3])
            iteration=compare_iteration_traces(document["trace"],browser)
            if not iteration["comparable"]:raise ValueError("invalid initialized iteration comparison")
            report=tagged(root/f"fused-matched-solver{event}.log",
                f"COMPILED NEWTON TRACE event[{event}].substep[{substep}]: ")
            ns=report["noSlipContactTraceFirstRecordDifference"]
            summary["qualifiedBoundaries"]+=1;summary["wholeSolverDifferentBoundaries"]+=bool(whole)
            summary["preparationCalls"]+=len(preparations);summary["preparationValues"]+=values
            summary["preparationNonzeroDifferences"]+=prep_diff
            summary["evaluationCalls"]+=len(evaluations);summary["evaluationNonzeroDifferences"]+=eval_diff
            summary["iterationExactBoundaries"]+=iteration["firstDifference"] is None
            summary["noSlipContactExactBoundaries"]+=ns is None
            result["boundaries"].append(dict(event=event,substep=substep,
                nativeCapture=identity(capture),originalOutputCapture=identity(output),
                exactNativeCopyAndWholeOutputQualification=True,
                originalWholeSolverDifferences=whole,
                preparation=dict(calls=len(preparations),values=values,nonzeroDifferences=prep_diff),
                evaluation=dict(calls=len(evaluations),nonzeroDifferences=eval_diff),
                iterationFirstDifference=iteration["firstDifference"],
                noSlipContactFirstDifference=ns,
                qualifiedRebuildTraceFirstDifference=report["firstDifference"],
                numpyDiagnosticCostProbeFirstDifferences=report["noSlipCostChangeProbeFirstDifferences"][:8]))
            if event==17 and substep==0:
                a,b=report["nativeNoSlipContactTrace"][0],report["wasmNoSlipContactTrace"][0]
                if a!=b:raise ValueError("first formerly split projected wrapper still differs")
                result["firstFormerlySplitWrapper"]=dict(event=17,substep=0,
                    inputsAndProjectedRetainedOutputEqual=True,qualifiedNative=a,browser=b,
                    scope="new candidate operands, not old v2 operands; only selected exact-copy native whole output is qualified")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
