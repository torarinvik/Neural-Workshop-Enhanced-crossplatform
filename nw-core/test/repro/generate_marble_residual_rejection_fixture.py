#!/usr/bin/env python3
"""Save the second rejected candidate and its next initialized no-slip split."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity, tagged, DIAGNOSTIC_SHA, JS_SHA
from marble_constraint_update_oracle import captured_difference
from marble_eval_trace import capture_evaluations, qualified_evaluations
from marble_iteration_trace import compare_iteration_traces
from marble_prepare_trace import capture_preparations, qualified_preparations
from marble_primal_eval_oracle import OriginalEval, REFERENCE_SHA256
from marble_primal_prepare_oracle import prepare
from marble_native_dot_oracle import wheel_dot
from marble_trace_neutrality import runtime_provenance_error
from marble_qcqp_original import OriginalQCQP5, QCQP_OFFSET, QCQP_ENTRY

TRACE_SHA="e9dd0001c861c7c577605cd36b317907f61203a9f5cbcb83c0e95df77940291a"
WASM_SHA="1021f8da126d1c91075e4d1f10eebc9dd2d4389f10815b5e274a6c8f5ffd9387"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root",required=True,type=Path)
    parser.add_argument("--reference-library",required=True,type=Path)
    parser.add_argument("--diagnostic-library",required=True,type=Path)
    parser.add_argument("--captured-on",required=True,type=date.fromisoformat)
    args=parser.parse_args()
    root=args.capture_root;path=root/"coherent-residual-v2-hard-trace.json"
    trace=json.loads(path.read_text());original=OriginalEval(args.reference_library)
    original_qcqp=OriginalQCQP5(args.reference_library)
    if identity(path)["sha256"]!=TRACE_SHA or runtime_provenance_error(trace):
        raise ValueError("second candidate trace identity/schema differs")
    if identity(args.diagnostic_library)["sha256"]!=DIAGNOSTIC_SHA:
        raise ValueError("native qualification library identity differs")
    runtime=trace["runtimeProvenance"]
    for name,sha,key in (("mujoco.js",JS_SHA,"jsSha256"),("mujoco.wasm",WASM_SHA,"wasmSha256")):
        if identity(root/"retained-residual-v2-dist"/name)["sha256"]!=sha or runtime["mujoco"][key]!=sha:
            raise ValueError("second candidate retained pair identity differs")
    if identity(Path(runtime["coreWasm"]["path"]))["sha256"]!=runtime["coreWasm"]["sha256"]:
        raise ValueError("core artifact changed")
    proofs={}
    for name,filename,inputfile,counts in (
        ("eval","compiled-eval-residual-v2.log","original-eval-golden.jsonl",dict(fma=1002,eval=5465,rejected=7)),
        ("noSlip","compiled-noslip-residual-v2.log","original-noslip-golden.jsonl",dict(dot=9200,residual=9205,rejected=8))):
        proof=json.loads((root/filename).read_text())
        if (proof["counts"]!=counts or proof["differences"] or proof["first"] or
            proof["runtime"]["wasmSha256"]!=WASM_SHA or proof["runtime"]["jsSha256"]!=JS_SHA or
            proof["inputSha256"]!=identity(root/inputfile)["sha256"]):
            raise ValueError("compiled proof identity/count differs")
        proofs[name]=dict(result=proof,log=identity(root/filename))
    full=root/"coherent-residual-v2-full-count.log"
    failure=[l for l in full.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if len(failure)!=1 or "replayed 7601" not in failure[0]:
        raise ValueError("missing ordinary uninterrupted full rejection")
    first=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: ")
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    summary=dict(qualifiedBoundaries=0,wholeSolverDifferentBoundaries=0,preparationCalls=0,
        preparationValues=0,preparationNonzeroDifferences=0,evaluationCalls=0,
        evaluationNonzeroDifferences=0,iterationExactBoundaries=0)
    result=dict(schema="neural-workshop.marble-residual-order-rejected.v1",
        provenance=dict(capturedOn=args.captured_on.isoformat(),referenceSha256=REFERENCE_SHA256,
            diagnosticLibrary=identity(args.diagnostic_library),trace=identity(path),runtime=runtime,
            retainedRuntime={n:identity(root/"retained-residual-v2-dist"/n) for n in ("mujoco.js","mujoco.wasm")},
            capturedBrowserZeroSigns=False,
            scope="private arithmetic candidate rejected; compound residual model uses actual original public dot, not a private original residual call; qualified rebuild intermediates are not universally original"),
        compiledProofs=proofs,rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,
            failFastLog=identity(root/"coherent-residual-v2-strict.log"),fullCountLog=identity(full),
            firstNumeric=first,numericExceedances=sum(v["count"] for v in numeric.values()),
            contactSets=tagged(full,"CONTACT-SET MISMATCHES: "),terminalSummary=failure[0]),
        summary=summary,boundaries=[])
    for event in (17,18,216):
        capture_path=root/f"residual-v2-native-prepare{event}.jsonl"
        output_path=root/f"residual-v2-original-output{event}.jsonl"
        documents=[json.loads(l) for l in capture_path.read_text().splitlines()]
        outputs=[json.loads(l) for l in output_path.read_text().splitlines()]
        if len(documents)!=4 or len(outputs)!=4:raise ValueError("four qualification substeps required")
        for substep,(document,output) in enumerate(zip(documents,outputs)):
            if (document["event"],document["substep"],output["event"],output["substep"])!=(event,substep,event,substep):
                raise ValueError("qualification selection differs")
            for qualify in (qualified_preparations,qualified_evaluations):
                qualify(document,reference_sha256=REFERENCE_SHA256,diagnostic_sha256=DIAGNOSTIC_SHA,input_trace_sha256=TRACE_SHA)
            browser=trace["events"][event]["newtonTraces"][substep]
            preparations=capture_preparations(browser);prep_diff=values=0
            for c in preparations:
                p=prepare(**c["inputs"],dot=wheel_dot)
                a=p["quadGauss"]+[v for row in p["rows"] for v in row["quad"]]
                b=c["quadGauss"]+[v for row in c["rows"] for v in row["quad"]]
                values+=len(a);prep_diff+=captured_difference(a,b)["nonzeroDifferenceCount"]
            evaluations=capture_evaluations(browser)
            eval_diff=sum(captured_difference(original.evaluate(**c["inputs"]),c["result"])["nonzeroDifferenceCount"] for c in evaluations)
            phase=next(p for p in trace["events"][event]["engineStep2Phases"][substep] if p["phase"]=="fwdConstraint")
            whole={}
            for field,a in output["arrays"].items():
                b=phase["engine"]["arrays"][field]
                if len(a)!=len(b):raise ValueError("whole output width differs")
                diffs=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
                if diffs:whole[field]=dict(count=len(diffs),first=diffs[:3])
            iteration=compare_iteration_traces(document["trace"],browser)
            if not iteration["comparable"]:raise ValueError("invalid iteration comparison")
            report_path=root/f"residual-v2-matched-solver{event}.log"
            report=tagged(report_path,f"COMPILED NEWTON TRACE event[{event}].substep[{substep}]: ")
            summary["qualifiedBoundaries"]+=1;summary["wholeSolverDifferentBoundaries"]+=bool(whole)
            summary["preparationCalls"]+=len(preparations);summary["preparationValues"]+=values
            summary["preparationNonzeroDifferences"]+=prep_diff
            summary["evaluationCalls"]+=len(evaluations);summary["evaluationNonzeroDifferences"]+=eval_diff
            summary["iterationExactBoundaries"]+=iteration["firstDifference"] is None
            result["boundaries"].append(dict(event=event,substep=substep,
                nativeCapture=identity(capture_path),originalOutputCapture=identity(output_path),
                exactNativeCopyAndWholeOutputQualification=True,originalWholeSolverDifferences=whole,
                preparation=dict(calls=len(preparations),values=values,nonzeroDifferences=prep_diff),
                evaluation=dict(calls=len(evaluations),nonzeroDifferences=eval_diff),
                iterationFirstDifference=iteration["firstDifference"],
                noSlipContactFirstDifference=report["noSlipContactTraceFirstRecordDifference"]))
            if event==17 and substep==0:
                a,b=report["nativeNoSlipContactTrace"][0],report["wasmNoSlipContactTrace"][0]
                fields=("normal","mu","matrix","rhs","residual","oldForce","bias","regularizer")
                if any(a[k]!=b[k] for k in fields):raise ValueError("first force-solve inputs differ")
                result["nextNoSlipForceBoundary"]=dict(event=17,substep=0,island=0,iteration=0,contact=0,
                    inputsExactlyEqual=True,inputFields=list(fields),qualifiedNative=a,browser=b,
                    report=identity(report_path),firstDifferentTangent=4,
                    actualOriginalQCQP=original_qcqp.solve(a["matrix"],a["rhs"],a["mu"],a["normal"]),
                    originalQCQPBridge=dict(offset=hex(QCQP_OFFSET),entryBytes=QCQP_ENTRY.hex(),
                        loadedWheelAndABIAnchorGuarded=True,tangentDimension=5),
                    scope="initialized QCQP/projectEllipsoid wrapper output differs at identical inputs; direct guarded original generic QCQP is constrained, so raw WASM QCQP and projection outputs must be captured separately; costChange can restore force; not full trajectory acceptance")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":
    main()
