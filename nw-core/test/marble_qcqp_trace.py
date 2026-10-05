"""Decode initialized no-slip solve/projection/restoration boundaries.

Direct original calls are deliberately limited to the guarded five-tangent
kernel. Recorder neutrality is a separate prerequisite, never an original
trajectory acceptance claim.
"""
import argparse
import hashlib
import json
from pathlib import Path

from marble_cone_update_oracle import Reader
from marble_constraint_update_oracle import captured_difference
from marble_qcqp_original import OriginalQCQP5, validated
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_trace_neutrality import first_physics_difference, runtime_provenance_error


def decode_qcqp(values, calls):
    if type(calls) is not int or not 0 <= calls <= 1000000:
        raise ValueError("QCQP call count must be a bounded integer")
    r = Reader(values)
    if len(values) > 300000:
        raise ValueError("QCQP capture exceeds recorder capacity")
    result = []
    while r.offset < len(values):
        r.integer("QCQP schema", 1, 1)
        ordinal = r.integer("QCQP ordinal", 0, 999999)
        if ordinal != len(result):
            raise ValueError("QCQP ordinals must be contiguous")
        island = r.integer("island", -1, 65536)
        iteration = r.integer("iteration", 0, 1000000)
        row = r.integer("global constraint row", 0, 65536)
        contact = r.integer("contact id", 0, 65536)
        dim = r.integer("contact dimension", 3, 6)
        if dim not in (3, 4, 6):
            raise ValueError("unsupported QCQP contact dimension")
        n = dim - 1
        route = r.integer("QCQP routine tangent dimension", 0, 5)
        valid = r.integer("initialized validity", 0, 7)
        active = r.integer("active constraint flag", -1, 1)
        projected = r.integer("projection branch", 0, 1)
        restored = r.integer("cost-change restoration branch", 0, 1)
        cost, normal = r.take(2, "cost change and normal force")
        if ((valid == 7 and (route != n or active not in (0, 1) or projected != active or normal < 1e-15))
                or (valid == 4 and (route != 0 or active != -1 or projected != 0 or normal >= 1e-15))
                or valid not in (4, 7)):
            raise ValueError("QCQP route/validity/branch metadata is inconsistent")
        mu = r.take(n, "friction scaling")
        if any(v <= 0 for v in mu):
            raise ValueError("QCQP friction scaling must be positive")
        matrix = r.take(n*n, "QCQP matrix")
        rhs = r.take(n, "QCQP RHS")
        old = r.take(n, "old tangent force")
        residual = r.take(n, "no-slip residual")
        raw = r.take(n, "raw QCQP output") if valid & 1 else None
        post = r.take(n, "post-projection force") if valid & 2 else None
        retained = r.take(n, "retained force after cost change")
        if restored:
            if cost != 0 or retained != old:
                raise ValueError("restored force/cost disagrees with the actual restoration branch")
        elif valid == 7:
            if retained != post:
                raise ValueError("unrestored force differs from post-projection force")
        elif any(retained):
            raise ValueError("unrestored normal-guard force must be zero")
        if valid == 7 and not projected and raw != post:
            raise ValueError("inactive QCQP must not project the raw output")
        if n == 5:
            # Entire native-call operands are bounded and validated first.
            validated(matrix, rhs, mu, max(0., normal))
        result.append(dict(ordinal=ordinal, island=island, iteration=iteration,
            row=row, contact=contact, dim=dim, route=route, valid=valid,
            active=bool(active) if valid == 7 else None, projected=bool(projected),
            restored=bool(restored), costChange=cost, normal=normal, mu=mu,
            matrix=matrix, rhs=rhs, oldForce=old, residual=residual,
            rawForce=raw, projectedForce=post, retainedForce=retained))
    r.finish()
    if len(result) != calls:
        raise ValueError("QCQP call count differs from capture")
    return result


def capture_qcqp(trace):
    if not isinstance(trace, dict):
        raise ValueError("QCQP trace must be an object")
    if type(trace.get("qcqpTraceSchema")) is not int or trace["qcqpTraceSchema"] != 1:
        raise ValueError("QCQP schema metadata must be 1")
    if trace.get("qcqpTraceOverflow") is not False or trace.get("qcqpTraceInvalid") is not False:
        raise ValueError("QCQP overflow/invalid metadata must be explicitly false")
    return decode_qcqp(trace.get("qcqpTrace"), trace.get("qcqpTraceCalls"))


def validate_runtime_pair(candidate, control):
    """Check retained byte identities, without asserting unchanged physics."""
    for trace in (candidate, control):
        error = runtime_provenance_error(trace)
        if error:
            raise ValueError(error)
        provenance = trace["runtimeProvenance"]
        for path, digest in ((provenance["coreWasm"]["path"], provenance["coreWasm"]["sha256"]),
                (provenance["mujoco"]["jsPath"], provenance["mujoco"]["jsSha256"]),
                (provenance["mujoco"]["wasmPath"], provenance["mujoco"]["wasmSha256"])):
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                raise ValueError("retained runtime file no longer matches its trace identity")
    if candidate["runtimeProvenance"]["coreWasm"]["sha256"] != control["runtimeProvenance"]["coreWasm"]["sha256"]:
        raise ValueError("QCQP paired diagnosis needs identical core artifacts")


def validate_neutral_pair(candidate, control):
    validate_runtime_pair(candidate, control)
    if first_physics_difference(control, candidate) is not None:
        raise ValueError("QCQP recorder is not neutral against its retained control")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--reference-library", required=True, type=Path)
    args = parser.parse_args()
    candidate = json.loads(args.trace.read_text())
    control = json.loads(args.control.read_text())
    validate_neutral_pair(candidate, control)
    original = OriginalQCQP5(args.reference_library)
    counts = dict(records=0, genericCalls=0, active=0, inactive=0, normalGuard=0,
                  rawDifferentCalls=0, activeDifferentCalls=0, restored=0,
                  qcqp2Calls=0, qcqp3Calls=0,
                  decomposedCalls=0, decomposedNonzeroDifferentCalls=0,
                  decomposedActiveDifferentCalls=0)
    witnesses = []
    first_retained_contact = None
    for event, document in enumerate(candidate["events"]):
        for substep, trace in enumerate(document.get("newtonTraces", [])):
            for c in capture_qcqp(trace):
                counts["records"] += 1
                counts["restored"] += c["restored"]
                if c["route"] == 0:
                    counts["normalGuard"] += 1
                    continue
                if c["route"] != 5:
                    counts["qcqp2Calls" if c["route"] == 2 else "qcqp3Calls"] += 1
                    continue  # Not authorized to reinterpret a 2/3-tangent ABI.
                counts["genericCalls"] += 1
                counts["active" if c["active"] else "inactive"] += 1
                a = original.solve(c["matrix"], c["rhs"], c["mu"], c["normal"])
                model = original.decomposed(c["matrix"], c["rhs"], c["mu"], c["normal"])
                counts["decomposedCalls"] += 1
                counts["decomposedNonzeroDifferentCalls"] += captured_difference(a["rawForce"], model["rawForce"])["nonzeroDifferenceCount"] > 0
                counts["decomposedActiveDifferentCalls"] += a["active"] != model["active"]
                diff = captured_difference(a["rawForce"], c["rawForce"])
                differs = diff["nonzeroDifferenceCount"] > 0
                counts["rawDifferentCalls"] += differs
                counts["activeDifferentCalls"] += a["active"] != c["active"]
                witness = dict(event=event, substep=substep, captured=c,
                    actualOriginalQCQP=a, rawDifference=diff)
                if event == 17 and substep == 0 and c["ordinal"] == 0:
                    witness["decomposedOriginalDriver"] = model
                    first_retained_contact = witness
                if (differs or a["active"] != c["active"] or (event == 17 and substep == 0 and c["ordinal"] == 0)) and len(witnesses) < 8:
                    witnesses.append(witness)
    if not counts["genericCalls"]:
        raise ValueError("no initialized generic QCQP calls captured")
    identity = lambda p: dict(path=str(p.resolve()),
        sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-qcqp-boundary.v1",
        referenceSha256=REFERENCE_SHA256, trace=identity(args.trace),
        control=identity(args.control), runtime=candidate["runtimeProvenance"],
        neutrality=dict(exact=True, events=len(candidate["events"])),
        counts=counts, witnesses=witnesses, firstRetainedContact=first_retained_contact,
        recorderPatch=identity(Path(__file__).with_name("repro").joinpath(
            "marble_initialized_qcqp_boundary.patch")),
        capturedBrowserZeroSigns=False,
        scope="direct original generic raw-QCQP comparison; decomposed driver final outputs are checked independently but its intermediates are reconstructed using original public primitives; projection and uninterrupted original physics remain separate gates"),
        indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
