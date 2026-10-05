#!/usr/bin/env python3
"""Emit reproducible rejected-candidate and matched-solver localization data.

All artifact/capture qualification guards are required. This saves concise
evidence, not another acceptance oracle or a production arithmetic policy.
"""
import argparse
import ctypes
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marble_constraint_update_oracle import captured_difference
from marble_dense_solve_oracle import native_dot
from marble_eval_trace import capture_evaluations, qualified_evaluations
from marble_iteration_trace import compare_iteration_traces
from marble_noslip_residual_oracle import residual, rejected_dot
from marble_prepare_trace import capture_preparations, qualified_preparations
from marble_primal_eval_oracle import OriginalEval, REFERENCE_SHA256
from marble_primal_prepare_oracle import prepare
from marble_native_dot_oracle import wheel_dot
from marble_trace_neutrality import runtime_provenance_error

TRACE_SHA = "40b4b78c09595466db90acae2bbd0b4791f9c6959104b42aaa8e701b522e2de3"
DIAGNOSTIC_SHA = "446aea43c3a11f1a2d6b03439af645fc35401bf48c75c41545cf03c62ec05840"
JS_SHA = "08831c72c0bdc72b4f3113963540527909eb98cd2be3cc2522c7225db4779ce8"
WASM_SHA = "f05012702617d207541b00a4fc938a9ce114d3b0946bc9747a5a1714f6f55775"


def identity(path):
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def tagged(path, prefix):
    values = [json.loads(l[len(prefix):]) for l in path.read_text().splitlines() if l.startswith(prefix)]
    if len(values) != 1:
        raise ValueError("expected exactly one report: "+prefix)
    return values[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--reference-library", required=True, type=Path)
    parser.add_argument("--diagnostic-library", required=True, type=Path)
    parser.add_argument("--captured-on", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    root = args.capture_root
    trace_path = root/"coherent-hard-trace.json"
    trace = json.loads(trace_path.read_text())
    original = OriginalEval(args.reference_library)
    library = ctypes.CDLL(str(original.path))
    if identity(trace_path)["sha256"] != TRACE_SHA or runtime_provenance_error(trace):
        raise ValueError("rejected input-trace identity/schema changed")
    if identity(args.diagnostic_library)["sha256"] != DIAGNOSTIC_SHA:
        raise ValueError("qualified native library changed")
    runtime = trace["runtimeProvenance"]
    for name, expected in (("mujoco.js", JS_SHA), ("mujoco.wasm", WASM_SHA)):
        if identity(root/"retained-coherent-v1-dist"/name)["sha256"] != expected:
            raise ValueError("retained v1 pair changed")
    if runtime["mujoco"]["jsSha256"] != JS_SHA or runtime["mujoco"]["wasmSha256"] != WASM_SHA:
        raise ValueError("capture runtime is not the retained pair")
    if identity(Path(runtime["coreWasm"]["path"]))["sha256"] != runtime["coreWasm"]["sha256"]:
        raise ValueError("capture core artifact changed")
    compiled_path = root/"compiled-eval-probe-complete.log"
    compiled = json.loads(compiled_path.read_text())
    if (compiled["counts"] != dict(fma=1002, eval=5465, rejected=7) or
            compiled["differences"] != 0 or compiled["first"] or
            compiled["runtime"]["jsSha256"] != JS_SHA or
            compiled["runtime"]["wasmSha256"] != WASM_SHA or
            identity(root/"original-eval-golden.jsonl")["sha256"] != compiled["inputSha256"]):
        raise ValueError("compiled complete evaluator proof is missing/mismatched")
    full_path = root/"coherent-full-count-diagnostic.log"
    first = tagged(full_path, "FIRST NUMERIC PARITY EXCEEDANCE: ")
    numeric = tagged(full_path, "NUMERIC PARITY EXCEEDANCES: ")
    contacts = tagged(full_path, "CONTACT-SET MISMATCHES: ")
    failures = [l for l in full_path.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if len(failures) != 1 or "replayed 7601" not in failures[0]:
        raise ValueError("expected full unsynchronized failed replay")
    summary = dict(qualifiedBoundaries=0, wholeSolverDifferentBoundaries=0, preparationCalls=0,
                   preparationValues=0, preparationNonzeroDifferences=0,
                   evaluationCalls=0, evaluationNonzeroDifferences=0, iterationExactBoundaries=0)
    result = dict(schema="neural-workshop.marble-coherent-solver-rejected.v1",
        provenance=dict(capturedOn=args.captured_on.isoformat(), referenceSha256=REFERENCE_SHA256,
            diagnosticLibrary=identity(args.diagnostic_library), trace=identity(trace_path),
            runtime=runtime, retainedRuntime={n:identity(root/"retained-coherent-v1-dist"/n)
                                            for n in ("mujoco.js","mujoco.wasm")},
            runtimeRelocation="trace paths describe capture time; v1 pair retained before further private rebuild",
            scope="isolated candidate rejected; captured JSON zero signs are unverified; matched solver and primitive passes are not full trajectory acceptance"),
        compiledEval=compiled, compiledEvalLog=identity(compiled_path),
        rejection=dict(promoted=False, failFastLog=identity(root/"coherent-strict-unsynchronized.log"),
            fullCountLog=identity(full_path), replayEvents=7601, ordinaryUnsynchronized=True,
            firstNumeric=first, numericExceedances=sum(v["count"] for v in numeric.values()),
            contactSets=contacts, terminalSummary=failures[0]), summary=summary, boundaries=[])
    for event in (17,18,216):
        capture_path = root/f"coherent-native-prepare{event}.jsonl"
        output_path = root/f"coherent-original-output{event}.jsonl"
        documents = [json.loads(l) for l in capture_path.read_text().splitlines()]
        outputs = [json.loads(l) for l in output_path.read_text().splitlines()]
        if len(documents) != 4 or len(outputs) != 4:
            raise ValueError("qualified event must have exactly four outputs/captures")
        for substep,(document,output) in enumerate(zip(documents,outputs)):
            if (document["event"],document["substep"],output["event"],output["substep"]) != (event,substep,event,substep):
                raise ValueError("native/original output selections differ")
            qualified_preparations(document, reference_sha256=REFERENCE_SHA256,
                diagnostic_sha256=DIAGNOSTIC_SHA, input_trace_sha256=TRACE_SHA)
            qualified_evaluations(document, reference_sha256=REFERENCE_SHA256,
                diagnostic_sha256=DIAGNOSTIC_SHA, input_trace_sha256=TRACE_SHA)
            browser = trace["events"][event]["newtonTraces"][substep]
            prep_diff=values=calls=0
            for c in capture_preparations(browser):
                modeled=prepare(**c["inputs"],dot=wheel_dot)
                a=modeled["quadGauss"]+[v for r in modeled["rows"] for v in r["quad"]]
                b=c["quadGauss"]+[v for r in c["rows"] for v in r["quad"]]
                prep_diff+=captured_difference(a,b)["nonzeroDifferenceCount"]
                values+=len(a);calls+=1
            eval_diff=0
            evaluations=capture_evaluations(browser)
            for c in evaluations:
                eval_diff+=captured_difference(original.evaluate(**c["inputs"]),c["result"])["nonzeroDifferenceCount"]
            phases=trace["events"][event]["engineStep2Phases"][substep]
            phase=next(p for p in phases if p["phase"]=="fwdConstraint")
            if set(output["arrays"])-set(phase["engine"]["arrays"]):
                raise ValueError("browser whole-solver output fields missing")
            whole={}
            for field,a in output["arrays"].items():
                b=phase["engine"]["arrays"][field]
                if len(a)!=len(b):raise ValueError("whole-solver field width differs")
                differences=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
                if differences:whole[field]=dict(count=len(differences),first=differences[:3])
            iteration=compare_iteration_traces(document["trace"],browser)
            if not iteration["comparable"]:raise ValueError("iteration capture not comparable")
            summary["qualifiedBoundaries"]+=1;summary["wholeSolverDifferentBoundaries"]+=bool(whole)
            summary["preparationCalls"]+=calls;summary["preparationValues"]+=values
            summary["preparationNonzeroDifferences"]+=prep_diff
            summary["evaluationCalls"]+=len(evaluations);summary["evaluationNonzeroDifferences"]+=eval_diff
            summary["iterationExactBoundaries"]+=iteration["firstDifference"] is None
            log_path=root/f"coherent-matched-solver{event}.log"
            report=tagged(log_path,f"COMPILED NEWTON TRACE event[{event}].substep[{substep}]: ")
            result["boundaries"].append(dict(event=event,substep=substep,
                nativeCapture=identity(capture_path),originalOutputCapture=identity(output_path),
                exactNativeCopyAndWholeOutputQualification=True,
                preparation=dict(calls=calls,values=values,nonzeroDifferences=prep_diff),
                evaluation=dict(calls=len(evaluations),nonzeroDifferences=eval_diff),
                originalWholeSolverDifferences=whole,
                iterationFirstDifference=iteration["firstDifference"],
                noSlipContactFirstDifference=report["noSlipContactTraceFirstRecordDifference"],
                noSlipStepFirstDifference=report["noSlipStepTraceFirstRecordDifference"]))
    # Earliest initialized residual: AR, b, R, normal and old tangent force
    # agree; verify both recorded residuals using the public original dot and
    # the historical browser-specific rounded-product kernel respectively.
    report_path=root/"coherent-matched-noslip17.log"
    report=tagged(report_path,"COMPILED NEWTON TRACE event[17].substep[0]: ")
    native,browser=report["nativeNoSlipContactTrace"][0],report["wasmNoSlipContactTrace"][0]
    state=trace["events"][17]["newtonTraces"][0]["residualInputStates"][0]
    if (report["residualInputStateComparable"] is not True or report["residualInputStateFirstDifferences"] or
            native["island"]!=0 or native["iteration"]!=0 or native["row"]!=0):
        raise ValueError("first no-slip entry input is not exactly qualified/comparable")
    for field in ("bias","regularizer","matrix","oldForce","mu","normal"):
        if native[field]!=browser[field]:raise ValueError("first contact input differs: "+field)
    rows=[]
    for row in range(1,6):
        n=state["nefc"];a=state["AR"][row*n:(row+1)*n];b=state["force"]
        scalars=[state[k][row] for k in ("b","R","force")]
        dot=native_dot(library,a,b)
        expected=math.fma(-scalars[1],scalars[2],scalars[0]+dot)
        old=math.fma(-scalars[1],scalars[2],scalars[0]+rejected_dot(a,b))
        if expected!=native["residual"][row-1] or old!=browser["residual"][row-1]:
            raise AssertionError("matched-input residual mechanism did not reproduce capture")
        rows.append(dict(row=row,ARrow=a,allforce=b,bias=scalars[0],regularizer=scalars[1],force=scalars[2],
            originalPublicDot=dot,rejectedBrowserDot=rejected_dot(a,b),
            originalPublicDotMatchesModel=dot==wheel_dot(a,b),
            modeledOriginalResidual=expected,recordedQualifiedNativeResidual=native["residual"][row-1],
            recordedRejectedBrowserResidual=browser["residual"][row-1],rejectedModelResidual=old))
    result["firstNoSlipResidual"]=dict(event=17,substep=0,island=0,iteration=0,contact=0,
        recordSource=identity(report_path),entryInputsExactlyEqual=True,rows=rows,
        firstDifferentRow=next(r["row"] for r in rows if r["modeledOriginalResidual"]!=r["rejectedModelResidual"]),
        scope="public-original dot and specified addition/FMA reproduce qualified native residual; not direct invocation of private original residual or proof of QCQP identity")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":
    main()
