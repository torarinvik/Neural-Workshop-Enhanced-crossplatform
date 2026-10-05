"""Bounded branch-valid generic QCQP iterations and direct producer diagnosis."""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path

from marble_cone_update_oracle import Reader
from marble_constraint_update_oracle import captured_difference
from marble_dense_solve_oracle import native_dot, solve
from marble_primal_eval_oracle import REFERENCE_SHA256
from marble_qcqp_original import OriginalQCQP5, validated
from marble_qcqp_trace import capture_qcqp, validate_neutral_pair, validate_runtime_pair
from marble_trace_neutrality import first_physics_difference

REASONS = ("rank", "value", "delta", "update", "limit")


def decode_kernel(values, calls, contacts):
    if type(calls) is not int or not 0 <= calls <= 1000000:
        raise ValueError("QCQP kernel count must be a bounded integer")
    r = Reader(values)
    if len(values) > 300000:
        raise ValueError("QCQP kernel exceeds recorder capacity")
    if not isinstance(contacts, list) or len(contacts) > 1000000:
        raise ValueError("QCQP outer contacts must be a bounded decoded list")
    owners = {}
    for c in contacts:
        if not isinstance(c, dict) or type(c.get("route")) is not int or c["route"] not in (0, 2, 3, 5):
            raise ValueError("invalid decoded outer contact route")
        if c.get("route") == 5:
            if c.get("dim") != 6 or c.get("valid") != 7:
                raise ValueError("generic outer contact needs initialized five-tangent data")
            validated(c["matrix"], c["rhs"], c["mu"], c["normal"])
            Reader(c["rawForce"])
            if (type(c["ordinal"]) is not int or not 0 <= c["ordinal"] < 1000000
                    or c["ordinal"] in owners or len(c["rawForce"]) != 5
                    or type(c["active"]) is not bool):
                raise ValueError("invalid generic outer ownership/return data")
            owners[c["ordinal"]] = c
    groups = []
    steps = 0
    while r.offset < len(values):
        r.integer("kernel schema", 1, 1)
        ordinal = r.integer("kernel ordinal", 0, 999999)
        if ordinal != steps:
            raise ValueError("kernel ordinals must be contiguous")
        parent = r.integer("outer-call ordinal", 0, 999999)
        if parent not in owners:
            raise ValueError("kernel has no actual generic outer-call owner")
        iteration = r.integer("kernel iteration", 0, 19)
        n = r.integer("kernel tangent dimension", 5, 5)
        rank = r.integer("factor rank", 0, n)
        valid = r.integer("kernel validity", 0, 31)
        reason = r.integer("kernel termination branch", 0, 4)
        before, after, norm, value, product, derivative, delta = r.take(7, "kernel scalars")
        if valid != (3 if reason == 0 else 7 if reason == 1 else 15 if reason == 2 else 31):
            raise ValueError("kernel validity does not match assigned branch fields")
        if (before < 0 or after < 0 or
                (reason == 0 and (rank == n or any((norm, value, product, derivative, delta)))) or
                (reason != 0 and rank != n) or
                (reason == 1 and (value >= 1e-10 or any((product, derivative, delta)))) or
                (reason >= 2 and value < 1e-10) or
                (reason == 2 and delta >= 1e-10) or
                (reason >= 3 and delta < 1e-10) or
                (reason == 3 and iteration >= 19) or
                (reason == 4 and iteration != 19)):
            raise ValueError("kernel rank/termination/initialized scalars are inconsistent")
        if reason >= 2:
            if derivative != -2.*product or derivative == 0 or delta != -value/derivative:
                raise ValueError("kernel derivative/delta relationship is inconsistent")
        if after != (before + delta if valid & 16 else before):
            raise ValueError("kernel lambda update does not match actual branch")
        A = r.take(n*n, "scaled matrix")
        b = r.take(n, "scaled RHS")
        prefactor = r.take(n*n, "initialized matrix before factorization")
        factor = r.take(n*n, "initialized factor")
        row = dict(ordinal=ordinal, parent=parent, iteration=iteration,
            rank=rank, valid=valid, reason=REASONS[reason], lambdaBefore=before,
            lambdaAfter=after, scaledMatrix=A, scaledRhs=b,
            prefactor=prefactor, factor=factor)
        if valid & 4:
            row.update(solved=r.take(n, "negated solve"), norm=norm, value=value)
        if valid & 8:
            row.update(inverseSolved=r.take(n, "second solve"), product=product,
                       derivative=derivative, delta=delta)
        if not groups or groups[-1]["parent"] != parent:
            if (iteration != 0 or (groups and (parent <= groups[-1]["parent"]
                    or groups[-1]["steps"][-1]["reason"] == "update"))):
                raise ValueError("kernel parent/order/previous termination differs")
            groups.append(dict(parent=parent, contact=owners[parent], steps=[]))
        group = groups[-1]
        if iteration != len(group["steps"]):
            raise ValueError("kernel iterations must be contiguous per outer call")
        if group["steps"]:
            last = group["steps"][-1]
            if (last["reason"] != "update" or before != last["lambdaAfter"]
                    or A != last["scaledMatrix"] or b != last["scaledRhs"]):
                raise ValueError("kernel continued after termination or mutated initialized inputs")
        group["steps"].append(row)
        steps += 1
    r.finish()
    if steps != calls or {g["parent"] for g in groups} != set(owners):
        raise ValueError("kernel count/complete generic parent coverage differs")
    for g in groups:
        last = g["steps"][-1]
        if last["reason"] == "update":
            raise ValueError("kernel capture omits its terminal iteration")
        raw = ([0.]*5 if last["reason"] == "rank" else
               [x*d for x, d in zip(last["solved"], g["contact"]["mu"])])
        active = False if last["reason"] == "rank" else last["lambdaAfter"] != 0
        if raw != g["contact"]["rawForce"] or active != g["contact"]["active"]:
            raise ValueError("kernel terminal state differs from actual raw outer return")
    return groups


def capture_kernel(trace):
    if not isinstance(trace, dict):
        raise ValueError("kernel trace must be an object")
    if type(trace.get("qcqpKernelSchema")) is not int or trace["qcqpKernelSchema"] != 1:
        raise ValueError("kernel schema must be explicitly 1")
    if trace.get("qcqpKernelOverflow") is not False or trace.get("qcqpKernelInvalid") is not False:
        raise ValueError("kernel recorder overflow/invalid metadata must be explicitly false")
    return decode_kernel(trace.get("qcqpKernelTrace"), trace.get("qcqpKernelCalls"),
                         capture_qcqp(trace))


def model_difference(actual, expected, library):
    """Compare in producer order; do not label reconstructed state as captured original."""
    fields = ("scaledRhs", "scaledMatrix", "lambdaBefore", "prefactor", "rank",
              "factor", "solved", "norm", "value", "inverseSolved", "product",
              "derivative", "delta", "lambdaAfter", "reason")
    for i, (a, base) in enumerate(zip(actual, expected)):
        e = base.copy()
        e["prefactor"] = e["scaledMatrix"].copy()
        for j in range(5):
            e["prefactor"][j*6] += e["lambdaBefore"]
        e.setdefault("lambdaAfter", e["lambdaBefore"])
        if "inverseSolved" in e:
            e["product"] = native_dot(library, e["solved"], e["inverseSolved"])
        for field in fields:
            if a.get(field) != e.get(field):
                return dict(iteration=i, field=field,
                    referenceDriver=e.get(field), browser=a.get(field),
                    capturedStep=a, reconstructedStep=e)
    if len(actual) != len(expected):
        return dict(field="iterationCount", browser=len(actual), referenceDriver=len(expected))
    return None


def producer_probe(original, contact, difference):
    """Use the actual original public primitive on the exact browser operands."""
    if not difference or "capturedStep" not in difference:
        return None
    s = difference["capturedStep"]; field = difference["field"]
    library = original.anchor.library
    result = None
    inputs = {}
    scope = "actual original public primitive on identical browser operands"
    if field in ("factor", "rank"):
        values = s["prefactor"]
        Reader(values)
        routine = library.mju_cholFactor
        ptr = ctypes.POINTER(ctypes.c_double)
        routine.argtypes, routine.restype = [ptr, ctypes.c_int, ctypes.c_double], ctypes.c_int
        buffer = (ctypes.c_double*25)(*values)
        rank = routine(buffer, 5, 1e-10)
        result = list(buffer) if field == "factor" else rank
        inputs = dict(prefactor=values, n=5, threshold=1e-10, returnedRank=rank)
    elif field == "solved":
        result = [-v for v in solve(library, 5, s["factor"], s["scaledRhs"])]
        inputs = dict(factor=s["factor"], rhs=s["scaledRhs"])
    elif field == "inverseSolved":
        result = solve(library, 5, s["factor"], s["solved"])
        inputs = dict(factor=s["factor"], rhs=s["solved"])
    elif field in ("norm", "product"):
        b = s["solved"] if field == "norm" else s["inverseSolved"]
        result = native_dot(library, s["solved"], b)
        inputs = dict(a=s["solved"], b=b)
    elif field == "value":
        result = math.fma(-contact["normal"], contact["normal"], s["norm"])
        inputs = dict(normal=contact["normal"], norm=s["norm"])
        scope = "exact-wheel disassembly-backed fused scalar operation, not a private intermediate capture"
    if result is None:
        return None
    Reader(result if isinstance(result, list) else [result])
    a = result if isinstance(result, list) else [result]
    b = s[field] if isinstance(s[field], list) else [s[field]]
    return dict(field=field, scope=scope, inputs=inputs, originalResult=result,
                capturedResult=s[field], difference=captured_difference(a, b))


def comparison_scope(candidate, control, arithmetic_candidate=False):
    if not arithmetic_candidate:
        validate_neutral_pair(candidate, control)
        return dict(exact=True, events=len(candidate["events"]))
    validate_runtime_pair(candidate, control)
    return dict(claimed=False, arithmeticCandidate=True,
        exact=first_physics_difference(control, candidate) is None,
        firstPhysicsDifference=first_physics_difference(control, candidate),
        events=len(candidate["events"]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("--control", type=Path, required=True)
    p.add_argument("--reference-library", type=Path, required=True)
    p.add_argument("--arithmetic-candidate", action="store_true",
        help="explicitly diagnose changed physics; never claim recorder neutrality or trajectory acceptance")
    args = p.parse_args()
    candidate = json.loads(args.trace.read_text())
    control = json.loads(args.control.read_text())
    neutrality = comparison_scope(candidate, control, args.arithmetic_candidate)
    # Decode every complete packet before performing any original native call.
    captures = [(event, substep, group)
        for event, document in enumerate(candidate["events"])
        for substep, trace in enumerate(document.get("newtonTraces", []))
        for group in capture_kernel(trace)]
    if not captures:
        raise ValueError("no complete generic kernel captured")
    original = OriginalQCQP5(args.reference_library)
    counts = dict(groups=0, steps=0, modelRawDifferent=0, modelActiveDifferent=0,
                  browserRawDifferent=0, initializedStageDifferent=0)
    if args.arithmetic_candidate:
        counts["browserActiveDifferent"] = 0
    fields = {}
    first_retained = None
    witnesses = []
    for event, substep, group in captures:
        c = group["contact"]
        direct = original.solve(c["matrix"], c["rhs"], c["mu"], c["normal"])
        model = original.decomposed(c["matrix"], c["rhs"], c["mu"], c["normal"])
        d = model_difference(group["steps"], model["steps"], original.anchor.library)
        counts["groups"] += 1; counts["steps"] += len(group["steps"])
        counts["modelRawDifferent"] += direct["rawForce"] != model["rawForce"]
        counts["modelActiveDifferent"] += direct["active"] != model["active"]
        counts["browserRawDifferent"] += direct["rawForce"] != c["rawForce"]
        if args.arithmetic_candidate:
            counts["browserActiveDifferent"] += direct["active"] != c["active"]
        counts["initializedStageDifferent"] += d is not None
        if d:
            fields[d["field"]] = fields.get(d["field"], 0) + 1
        witness = dict(event=event, substep=substep, parent=group["parent"],
            contact=c, actualOriginalQCQP=direct, modelDifference=d,
            producerProbe=producer_probe(original, c, d))
        if d and len(witnesses) < 6:
            witnesses.append(witness)
        if event == 17 and substep == 0 and group["parent"] == 0:
            first_retained = witness
    if counts["modelRawDifferent"] or counts["modelActiveDifferent"]:
        raise ValueError("decomposed driver no longer qualifies against actual original")
    identity = lambda path: dict(path=str(path.resolve()),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-qcqp-kernel.v1",
        referenceSha256=REFERENCE_SHA256, trace=identity(args.trace),
        control=identity(args.control), runtime=candidate["runtimeProvenance"],
        neutrality=neutrality,
        counts=counts, firstFields=fields, firstRetainedContact=first_retained,
        witnesses=witnesses, capturedBrowserZeroSigns=False,
        scope="initialized browser kernel versus independently final-qualified original-primitive driver; producer probes use identical actual operands; uninterrupted original physics is not qualified"),
        indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
