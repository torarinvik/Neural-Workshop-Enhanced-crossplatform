#!/usr/bin/env python3
"""Retain qualified complete-RNE bias correction and ordinary hard rejection."""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity,tagged
from marble_rne_original import OriginalRNE,selected_inputs,validated_engine,LAYOUTS
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_trace import validate_runtime_pair
from marble_trace_neutrality import first_physics_difference,IDENTITY_KEYS
from marble_source_play_trace import native_mujoco_provenance


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--reference-library",type=Path,required=True)
    args=p.parse_args();root=args.capture_root
    paths=[root/(prefix+"-hard-trace.json") for prefix in ("inertia-candidate","rne-family-candidate")]
    traces=[json.loads(path.read_text()) for path in paths];before,after=traces
    validate_runtime_pair(after,before)
    if any(len(t["events"])!=7601 for t in traces) or any(before.get(k)!=after.get(k) for k in IDENTITY_KEYS):
        raise ValueError("complete identical hard configuration/result required")
    for e,(a,b) in enumerate(zip(before["events"],after["events"])):
        if {k:a[k] for k in ("kind","dt","held","key") if k in a}!={k:b[k] for k in ("kind","dt","held","key") if k in b}:
            raise ValueError("input schedule changed at event "+str(e))
    selected=[selected_inputs(t) for t in traces]
    if any(len(s)!=20 for s in selected):raise ValueError("complete selected actual RNE matrix required")
    original=OriginalRNE(args.reference_library)
    import mujoco
    native=native_mujoco_provenance(mujoco)["activeEngineLibrary"]
    if native["sha256"]!=REFERENCE_SHA256 or Path(native["path"]).resolve()!=original.guard.anchor.path:
        raise ValueError("owned model/data must be allocated by the exact original wheel")
    model=mujoco.MjModel.from_xml_string(LAYOUTS[1]);data=mujoco.MjData(model)
    bits=lambda values:[struct.pack("!d",x).hex() for x in values]
    reports=[]
    expected_counts=[dict(boundaries=20,differentBoundaries=10,differentValues=21,modelDifferentBoundaries=0,modelDifferentValues=0),
        dict(boundaries=20,differentBoundaries=0,differentValues=0,modelDifferentBoundaries=0,modelDifferentValues=0)]
    for path,trace,rows,count,filename,control_path in zip(paths,traces,selected,expected_counts,
            ("inertia-candidate-rne-original-comparison.json","rne-family-candidate-rne-original-comparison.json"),
            (root/"cost-candidate-hard-trace.json",paths[0])):
        report_path=root/filename;report=json.loads(report_path.read_text())
        if (report["counts"]!=count or report["trace"]!=identity(path) or report["control"]!=identity(control_path) or
                report["runtime"]!=trace["runtimeProvenance"] or report["referenceSha256"]!=REFERENCE_SHA256 or
                report["nativeRuntime"]["activeEngineLibrary"]["sha256"]!=REFERENCE_SHA256 or
                not report["matchedInputs"] or report["ordinaryTrajectoryAcceptance"] or report["promoted"]):
            raise ValueError("actual-original complete RNE report identity/scope differs")
        for row,b in zip(rows,report["boundaries"]):
            actual=original.evaluate(model,data,row["engine"])
            if (b["event"],b["substep"])!=(row["event"],row["substep"]) or b["actualOriginalBits"]!=bits(actual) or b["captured"]!=row["captured"]:
                raise ValueError("actual original RNE return or owner differs")
            expected_differences=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(actual,row["captured"])) if x!=y]
            if b["differences"]!=expected_differences:raise ValueError("captured RNE numeric differences disagree with actual returns")
        reports.append(dict(report=identity(report_path),counts=count,boundaries=report["boundaries"]))
    proof_path=root/"compiled-rne-family-candidate-qualified.log";proof=tagged(proof_path,"")
    golden_path=root/"original-rne-golden.jsonl"
    golden=[json.loads(line) for line in golden_path.read_text().splitlines()]
    for row in golden:validated_engine(row["input"])
    for row,captured in zip(golden[:20],selected[0]):
        if (row["kind"]!="captured" or row["label"]!=f"event{captured['event']}-step{captured['substep']}" or
                row["layout"]!=1 or any(row["input"]["arrays"][field]!=captured["engine"]["arrays"][field]
                for field in ("cinert","cvel","cdof","cdof_dot","qvel","qfrc_bias"))):
            raise ValueError("compiled captured golden no longer uses the retained15 operands")
    native_contexts={}
    for row in golden:
        if row["xml"] not in LAYOUTS or row["referenceSha256"]!=REFERENCE_SHA256:raise ValueError("original golden context differs")
        if row["xml"] not in native_contexts:
            m=mujoco.MjModel.from_xml_string(row["xml"]);native_contexts[row["xml"]]=(m,mujoco.MjData(m))
        result=original.evaluate(*native_contexts[row["xml"]],row["input"])
        if bits(result)!=row["expectedBits"]:raise ValueError("golden actual-original RNE return differs")
    if (proof["counts"]!=dict(captured=20,synthetic=1000) or proof["layouts"]!={"0":334,"1":353,"2":333} or
            proof["differences"] or proof["first"] or proof["accelerationControlMatches"]!=1020 or
            proof["inputSha256"]!=identity(golden_path)["sha256"] or len(golden)!=1020 or
            any(proof["runtime"][k]!=after["runtimeProvenance"]["mujoco"][k] or
                proof["accelerationControl"][k]!=before["runtimeProvenance"]["mujoco"][k]
                for k in ("jsSha256","wasmSha256"))):
        raise ValueError("actual compiled RNE/control qualification differs")
    regressions={}
    for name,size in (("inertia",120),("cost",134),("gauss",125),("generic",114),("qcqp2",18)):
        path=root/("rne-family-candidate-"+name+"-comparison.json");r=json.loads(path.read_text())
        count_key="groups" if name=="generic" else "calls"
        excluded={count_key,"accelerationCalls","velocityCalls","twoTangentCalls","fiveTangentCalls","steps"}
        if (r["counts"][count_key]!=size or any(v for k,v in r["counts"].items() if k not in excluded) or
                r["trace"]!=identity(paths[1]) or r["control"]!=identity(paths[0]) or
                r["runtime"]!=after["runtimeProvenance"] or r["referenceSha256"]!=REFERENCE_SHA256):
            raise ValueError("current input local producer regression differs: "+name)
        log=root/("compiled-rne-family-"+name+"-regression.log");compiled=tagged(log,"")
        if compiled["differences"] or compiled["first"] or any(compiled["runtime"][k]!=proof["runtime"][k] for k in ("jsSha256","wasmSha256")):
            raise ValueError("frozen compiled producer regression differs: "+name)
        regressions[name]=dict(report=identity(path),counts=r["counts"],compiledLog=identity(log),compiledProof=compiled)
    full=root/"rne-family-candidate-original-full.log";strict=root/"rne-family-candidate-original-strict.log"
    first=tagged(full,"FIRST NUMERIC PARITY EXCEEDANCE: ");contacts=tagged(full,"CONTACT-SET MISMATCHES: ")
    numeric=tagged(full,"NUMERIC PARITY EXCEEDANCES: ")
    failure=[l for l in full.read_text().splitlines() if l.startswith("FAIL: original Python Marble")]
    if (len(failure)!=1 or "replayed 7601" not in failure[0] or "outcome=timeout" not in failure[0] or
            "home=0, lost=0, elapsed=120.016667s" not in failure[0] or
            "AssertionError: event[463].contacts:" not in strict.read_text() or
            sum(v["count"] for v in numeric.values())!=110690 or contacts["count"]!=105 or
            (contacts["first"]["event"],contacts["last"]["event"])!=(463,1966) or
            first["context"]!="event[195].marble[0].value[10]" or first["delta"]!=4.996572333659799e-7):
        raise ValueError("independent ordinary complete-game rejection differs")
    difference=first_physics_difference(before,after)
    if difference is None:raise ValueError("arithmetic candidate must not be mislabeled recorder neutral")
    result=dict(schema="neural-workshop.marble-rne-bias-family-rejected.v1",
        referenceSha256=REFERENCE_SHA256,control=identity(paths[0]),trace=identity(paths[1]),runtime=after["runtimeProvenance"],
        deltaPatch=identity(Path(__file__).with_name("marble_rne_bias_family_candidate.patch")),
        patchBase="all fifteen prior ordered layers; bias-only private DOF accumulation/cross-force/projection helpers and matching assigned mirror",
        before=reports[0],after=reports[1],compiledProof=proof,compiledProofLog=identity(proof_path),compiledGolden=identity(golden_path),
        localProducerRegressions=regressions,originalPrivateIntermediatesCaptured=False,capturedBrowserZeroSignsQualified=False,
        physicsComparison=dict(claimedRecorderNeutrality=False,exactlyUnchanged=False,events=7601,firstDifference=list(difference)),
        rejection=dict(promoted=False,ordinaryUnsynchronized=True,replayEvents=7601,firstNumeric=first,
            numericExceedances=110690,contactSets=contacts,failFastLog=identity(strict),fullCountLog=identity(full),terminalSummary=failure[0]),
        scope="complete actual original RNE bias locally qualified; acceleration mode remains identical to retained15,not original-acceleration acceptance; live physics changes but hard breach/contact counts persist; whole-game rejected,no production promotion")
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
