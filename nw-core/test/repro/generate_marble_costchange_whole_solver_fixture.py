#!/usr/bin/env python3
"""Latest matched-input original whole-solver output; not trajectory acceptance."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_marble_coherent_rejection_fixture import identity
from marble_cone_update_oracle import Reader
from marble_prepare_trace import qualified_preparations
from marble_primal_eval_oracle import REFERENCE_SHA256

DIAGNOSTIC_SHA="446aea43c3a11f1a2d6b03439af645fc35401bf48c75c41545cf03c62ec05840"
FIELDS=frozenset(("efc_b","efc_force","efc_state","iacc","iacc_smooth",
    "ifrc_constraint","ifrc_smooth","iefc_D","iefc_R","iefc_frictionloss",
    "iefc_type","iefc_id","iefc_state","iefc_force","iefc_aref","solver_niter",
    "solver_nnz","solver_fwdinv","solver_stats","qacc","qfrc_constraint"))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-root",type=Path,required=True)
    p.add_argument("--candidate-prefix",choices=("cost-candidate","inertia-candidate","rne-family-candidate","comvel-family-candidate","quaternion-integration-candidate","bias-local-candidate"),default="cost-candidate")
    args=p.parse_args();root=args.capture_root
    prefix=args.candidate_prefix
    path=root/(prefix+"-hard-trace.json");trace=json.loads(path.read_text())
    outputs_path=root/(prefix+"-qualified-outputs.jsonl")
    captures_path=root/(prefix+"-qualified-captures.jsonl")
    read=lambda p:[json.loads(line) for line in p.read_text().splitlines()]
    outputs=read(outputs_path);captures=read(captures_path)
    selected=[(e,s) for e in (0,1,17,18,216) for s in range(4)]
    if len(outputs)!=20 or len(captures)!=20:raise ValueError("complete selected matrix required")
    boundaries=[]
    for (e,s),output,capture in zip(selected,outputs,captures):
        if (output["event"],output["substep"],capture["event"],capture["substep"])!=(e,s,e,s):
            raise ValueError("original/candidate selection differs")
        qualified_preparations(capture,reference_sha256=REFERENCE_SHA256,
            diagnostic_sha256=DIAGNOSTIC_SHA,input_trace_sha256=identity(path)["sha256"])
        if set(output["arrays"])!=FIELDS:raise ValueError("all original output fields required")
        phases=trace["events"][e]["engineStep2Phases"][s]
        actual=[p["engine"]["arrays"] for p in phases if p["phase"]=="fwdConstraint"]
        if len(actual)!=1:raise ValueError("one actual final constraint phase required")
        differences={}
        for field,a in output["arrays"].items():
            b=actual[0][field]
            Reader(a);Reader(b)
            if len(a)>300000 or len(a)!=len(b):raise ValueError("finite complete bounded output required")
            d=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
            if d:differences[field]=dict(count=len(d),first=d[:3])
        boundaries.append(dict(event=e,substep=s,allOutputNonzeroDifferences=differences))
    different=sum(bool(b["allOutputNonzeroDifferences"]) for b in boundaries)
    nonstat=sum(any(k!="solver_stats" for k in b["allOutputNonzeroDifferences"]) for b in boundaries)
    values=sum(v["count"] for b in boundaries for v in b["allOutputNonzeroDifferences"].values())
    if prefix=="cost-candidate" and (different,nonstat,values)!=(2,0,2):
        raise ValueError("retained cost whole-solver localization differs")
    schema=("neural-workshop.marble-costchange-whole-solver.v1" if prefix=="cost-candidate"
        else "neural-workshop.marble-inertia-whole-solver.v1" if prefix=="inertia-candidate"
        else "neural-workshop.marble-rne-family-whole-solver.v1" if prefix=="rne-family-candidate"
        else "neural-workshop.marble-comvel-family-whole-solver.v1" if prefix=="comvel-family-candidate"
        else "neural-workshop.marble-quaternion-integration-whole-solver.v1" if prefix=="quaternion-integration-candidate"
        else "neural-workshop.marble-bias-local-whole-solver.v1")
    result=dict(schema=schema,
        inputTrace=identity(path),runtime=trace["runtimeProvenance"],
        originalOutputCapture=identity(outputs_path),qualifiedNativeCapture=identity(captures_path),
        qualificationLog=identity(root/(prefix+"-whole-qualified.log")),
        referenceSha256=REFERENCE_SHA256,diagnosticLibrarySha256=DIAGNOSTIC_SHA,
        counts=dict(exactInputOriginalQualifiedBoundaries=20,allOutputNonzeroExactBoundaries=20-different,
            statisticDifferentBoundaries=sum("solver_stats" in b["allOutputNonzeroDifferences"] for b in boundaries),
            statisticDifferentValues=sum(b["allOutputNonzeroDifferences"].get("solver_stats",{}).get("count",0) for b in boundaries),
            otherOutputDifferentBoundaries=nonstat),fieldsCompared=sorted(FIELDS),boundaries=boundaries,
        capturedBrowserZeroSigns=False,originalPrivateIntermediatesCaptured=False,
        synchronizationUsed=True,ordinaryTrajectoryAcceptance=False,promoted=False,
        scope="current exact-input original fwdConstraint final arrays; rebuilt native final outputs qualified on all20 copies, not private intermediate identity; JSON zero signs unqualified; two statistic ulps retained, no other nonzero final-output difference; not uninterrupted trajectory acceptance")
    if prefix!="cost-candidate":
        result["scope"]=f"current {prefix} exact-input original fwdConstraint final arrays; rebuilt native final outputs qualified on all20 copies, not private intermediate identity; all field differences retained, JSON zero signs unqualified; not uninterrupted trajectory acceptance"
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
