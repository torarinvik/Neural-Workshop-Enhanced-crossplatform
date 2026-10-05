#!/usr/bin/env python3
"""Replay captured constraint-update operands in the unmodified MuJoCo wheel.

This diagnoses exact force/state/cost arithmetic, not full trajectory parity.
It does not reconstruct solver inputs or compare qfrc_constraint: that output
requires the wrapper's Jacobian transpose multiply, not the called impl routine.
Establish capture neutrality separately before interpreting the results.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from marble_cone_update_oracle import Reader, difference


def captured_difference(reference: list, captured: list) -> dict:
    """Keep bit differences, but distinguish zero signs lost by JSON.stringify.

    A zero-only bit disagreement is unverified, not evidence of a runtime bug.
    Nonzero numbers round-trip through the browser's JSON encoding exactly.
    """
    result = difference(reference, captured)
    nonzero = [i for i, (a, b) in enumerate(zip(reference, captured))
               if a != b]
    result["nonzeroDifferenceCount"] = len(nonzero)
    result["zeroSignOnlyCount"] = result["count"] - len(nonzero)
    if nonzero:
        i = nonzero[0]
        result["firstNonzero"] = {"index": i, "reference": reference[i],
                                  "captured": captured[i]}
    return result


@dataclass
class Contact:
    dim: int
    mu: float
    friction: list


@dataclass
class Capture:
    ne: int
    nf: int
    nefc: int
    nv: int
    hessian: bool
    has_cost: bool
    jar: list
    D: list
    R: list
    frictionloss: list
    aref: list
    types: list
    ids: list
    state_before: list
    force_before: list
    contacts: list[Contact]
    force_after: list
    state_after: list
    cost_after: list
    qfrc_after: list


def _integers(reader: Reader, n: int, name: str, low: int, high: int) -> list:
    return [reader.integer(name, low, high) for _ in range(n)]


def captured_updates(values: list) -> list[Capture]:
    """Decode every record and reject unsafe dimensions before any native call."""
    reader = Reader(values)
    captures = []
    while reader.offset < len(values):
        ne = reader.integer("equality count", 0, 65536)
        nf = reader.integer("friction count", 0, 65536)
        nefc = reader.integer("constraint count", ne + nf, 65536)
        ncon = reader.integer("contact count", 0, 65536)
        hessian = bool(reader.integer("Hessian flag", 0, 1))
        has_cost = bool(reader.integer("cost flag", 0, 1))
        nv = reader.integer("velocity dimension", 0, 512)
        # The recorder stores floss[0:nf], but impl indexes floss[ne:ne+nf].
        # Do not invent the omitted operands when equality and friction coexist.
        if ne and nf:
            raise ValueError("capture omits frictionloss operands after equality rows")
        jar = reader.take(nefc, "jar")
        D = reader.take(nefc, "D")
        R = reader.take(nefc, "R")
        frictionloss = reader.take(nf, "frictionloss")
        aref = reader.take(nefc, "aref")
        types = _integers(reader, nefc, "constraint type", 0, 7)
        ids = _integers(reader, nefc, "constraint id", -1, 2147483647)
        state_before = _integers(reader, nefc, "initial state", -2147483648, 2147483647)
        force_before = reader.take(nefc, "initial force")
        contacts = []
        for _ in range(ncon):
            dim = reader.integer("contact dimension", 1, 6)
            if dim not in (1, 3, 4, 6):
                raise ValueError("unsupported contact dimension")
            mu = reader.take(1, "contact mu")[0]
            friction = reader.take(5, "contact friction")
            if mu < 0 or any(v < 0 for v in friction):
                raise ValueError("negative contact friction")
            contacts.append(Contact(dim, mu, friction))
        force_after = reader.take(nefc, "output force")
        state_after = _integers(reader, nefc, "output state", 0, 4)
        cost_after = reader.take(int(has_cost), "output cost")
        qfrc_after = reader.take(nv, "output generalized force")
        if any(v <= 0 for v in D + R) or any(v < 0 for v in frictionloss):
            raise ValueError("invalid constraint impedance or friction loss")
        row = ne + nf
        while row < nefc:
            if types[row] != 7:  # mjCNSTR_CONTACT_ELLIPTIC
                row += 1
                continue
            contact_id = ids[row]
            if not 0 <= contact_id < ncon:
                raise ValueError("elliptic row references a missing contact")
            contact = contacts[contact_id]
            end = row + contact.dim
            if end > nefc or contact.mu <= 0:
                raise ValueError("elliptic block exceeds rows or has nonpositive mu")
            if (any(t != 7 for t in types[row:end]) or
                    any(i != contact_id for i in ids[row:end])):
                raise ValueError("inconsistent elliptic block rows")
            row = end
        captures.append(Capture(ne, nf, nefc, nv, hessian, has_cost, jar, D, R,
                                frictionloss, aref, types, ids, state_before,
                                force_before, contacts, force_after, state_after,
                                cost_after, qfrc_after))
    reader.finish()
    return captures


class MjContact312(ctypes.Structure):
    """Native double-precision mjContact from the MuJoCo 3.12.0 wheel header."""
    _fields_ = [
        ("dist", ctypes.c_double), ("pos", ctypes.c_double * 3),
        ("frame", ctypes.c_double * 9), ("includemargin", ctypes.c_double),
        ("friction", ctypes.c_double * 5), ("solref", ctypes.c_double * 2),
        ("solreffriction", ctypes.c_double * 2), ("solimp", ctypes.c_double * 5),
        ("adhesion", ctypes.c_double), ("mu", ctypes.c_double),
        ("H", ctypes.c_double * 36), ("dim", ctypes.c_int),
        ("geom1", ctypes.c_int), ("geom2", ctypes.c_int),
        ("geom", ctypes.c_int * 2), ("flex", ctypes.c_int * 2),
        ("elem", ctypes.c_int * 2), ("vert", ctypes.c_int * 2),
        ("exclude", ctypes.c_int), ("efc_address", ctypes.c_int),
    ]


def _initial_hessians(capture: Capture, values: list | None) -> list:
    """Explicit synthetic H inputs; saved warmstart captures do not contain H."""
    if values is None:
        return [[0.0]*36 for _ in capture.contacts]
    if len(values) != len(capture.contacts):
        raise ValueError("initial contact Hessian count does not match contacts")
    result = []
    for row in values:
        reader = Reader(row)
        result.append(reader.take(36, "initial contact Hessian"))
        reader.finish()
    return result


class Kernels:
    def __init__(self, path: Path):
        self.library = ctypes.CDLL(str(path.resolve()))
        version = self.library.mj_version
        version.argtypes, version.restype = [], ctypes.c_int
        if version() != 3012000:
            raise ValueError("contact ABI requires MuJoCo 3.12.0")
        expected_offsets = {"pos": 8, "frame": 32, "friction": 112,
                            "mu": 232, "H": 240, "dim": 528,
                            "geom": 540, "efc_address": 576}
        if (ctypes.sizeof(MjContact312) != 584 or
                any(getattr(MjContact312, k).offset != v
                    for k, v in expected_offsets.items())):
            raise ValueError("unsupported native contact ABI")
        pointer, integer = ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_int)
        self.routine = self.library.mj_constraintUpdate_impl
        self.routine.argtypes = [ctypes.c_int] * 3 + [pointer] * 4 + [integer] * 2 + [
            ctypes.POINTER(MjContact312), integer, pointer, pointer, ctypes.c_int]
        self.routine.restype = None
        self.norm_routine = self.library.mju_norm
        self.norm_routine.argtypes = [pointer, ctypes.c_int]
        self.norm_routine.restype = ctypes.c_double

    def norm(self, values: list) -> float:
        return self.norm_routine((ctypes.c_double * len(values))(*values), len(values))

    def update(self, capture: Capture, *, include_contact_hessians: bool = False,
               initial_contact_hessians: list | None = None) -> dict:
        # capture must come from captured_updates; the CLI parses all captures
        # before loading the library so no earlier record runs on bad input.
        scalar = lambda values: (ctypes.c_double * len(values))(*values)
        integer = lambda values: (ctypes.c_int * len(values))(*values)
        hessians = _initial_hessians(capture, initial_contact_hessians)
        contacts = (MjContact312 * len(capture.contacts))()
        for target, source, hessian in zip(contacts, capture.contacts, hessians):
            target.dim, target.mu = source.dim, source.mu
            target.friction[:] = source.friction
            target.H[:] = hessian
        force, state = scalar(capture.force_before), integer(capture.state_before)
        cost = ctypes.c_double()
        self.routine(capture.ne, capture.nf, capture.nefc,
                     scalar(capture.D), scalar(capture.R), scalar(capture.frictionloss),
                     scalar(capture.jar), integer(capture.types), integer(capture.ids),
                     contacts, state, force,
                     ctypes.byref(cost) if capture.has_cost else None, int(capture.hessian))
        result = {"force": list(force), "state": list(state),
                  "cost": [cost.value] if capture.has_cost else []}
        if include_contact_hessians:
            result["contactHessians"] = [v for con in contacts for v in con.H]
        return result


def replay(capture: Capture, kernels: Kernels) -> dict:
    result = kernels.update(capture)
    return {"force": captured_difference(result["force"], capture.force_after),
            "state": difference(result["state"], capture.state_after),
            "cost": captured_difference(result["cost"], capture.cost_after)}


def wheel_order_update(c: Capture, norm, fma, *,
                       include_contact_hessians: bool = False,
                       initial_contact_hessians: list | None = None) -> dict:
    """Diagnostic model of the wheel's scalar force/state/cost instruction order.

    The pinned arm64 wheel inlines norm and contracts the bottom predicate,
    middle denominator, normal projection, and scalar cost accumulation. Its
    bottom-zone dim>=8 vector cost loop is irrelevant to valid contact dims
    (1/3/4/6). Opt-in Hessian output requires explicitly initialized synthetic
    H storage: the recorded warmstart operands omit incoming H. The model does
    not reconstruct the Jacobian transpose multiply, and must be checked
    against direct wheel calls rather than used as an acceptance oracle or
    inserted into the browser runtime.
    fma/norm are supplied explicitly so parsing/fixture tests remain portable.
    """
    force = [-d*v for d, v in zip(c.D, c.jar)]
    state = list(c.state_before)
    hessians = _initial_hessians(c, initial_contact_hessians)
    cost = 0.0
    i = 0
    while i < c.nefc:
        if i < c.ne:
            if c.has_cost:
                cost = fma((.5*c.D[i])*c.jar[i], c.jar[i], cost)
            state[i] = 1
        elif i < c.ne + c.nf:
            if c.jar[i] <= -c.R[i]*c.frictionloss[i]:
                if c.has_cost:
                    increment = fma((-.5*c.R[i])*c.frictionloss[i],
                                    c.frictionloss[i], -c.frictionloss[i]*c.jar[i])
                    cost += increment
                force[i], state[i] = c.frictionloss[i], 2
            elif c.jar[i] >= c.R[i]*c.frictionloss[i]:
                if c.has_cost:
                    increment = fma((-.5*c.R[i])*c.frictionloss[i],
                                    c.frictionloss[i], c.frictionloss[i]*c.jar[i])
                    cost += increment
                force[i], state[i] = -c.frictionloss[i], 3
            else:
                if c.has_cost:
                    cost = fma((.5*c.D[i])*c.jar[i], c.jar[i], cost)
                state[i] = 1
        elif c.types[i] != 7:
            if c.jar[i] >= 0:
                force[i], state[i] = 0.0, 0
            else:
                if c.has_cost:
                    cost = fma((.5*c.D[i])*c.jar[i], c.jar[i], cost)
                state[i] = 1
        else:
            con = c.contacts[c.ids[i]]
            mu, dim = con.mu, con.dim
            normal = c.jar[i]*mu
            tangent = [c.jar[i+j]*con.friction[j-1] for j in range(1, dim)]
            t = norm(tangent)
            if normal >= mu*t or (t <= 0 and normal >= 0):
                force[i:i+dim] = [0.0]*dim
                classification = 0
            elif fma(mu, normal, t) <= 0 or (t <= 0 and normal < 0):
                if c.has_cost:
                    for j in range(dim):
                        term = (.5*c.D[i+j])*c.jar[i+j]
                        cost = fma(term, c.jar[i+j], cost)
                classification = 1
            else:
                dm = c.D[i]/((mu*mu)*fma(mu, mu, 1.0))
                nmt = fma(-mu, t, normal)
                if c.has_cost:
                    cost = fma((.5*dm)*nmt, nmt, cost)
                force[i] = (-dm*nmt)*mu
                for j in range(1, dim):
                    force[i+j] = ((-force[i]/t)*tangent[j-1])*con.friction[j-1]
                classification = 4
                if c.hessian and include_contact_hessians:
                    h = hessians[c.ids[i]]
                    u = [normal] + tangent
                    h[0] = 1.0
                    scale = -mu/t
                    for j in range(1, dim):
                        h[j] = scale*u[j]
                    mu_n = mu*normal
                    scale = mu_n/((t*t)*t)
                    for k in range(1, dim):
                        for j in range(k, dim):
                            h[k*dim+j] = (scale*u[j])*u[k]
                    # Wheel 0x4adf0..0x4adf8: fneg(mu*N), fdiv(T),
                    # fmadd(mu, mu, quotient); diagonal addition is separate.
                    scale = fma(mu, mu, -mu_n/t)
                    for j in range(1, dim):
                        h[j*(dim+1)] += scale
                    diagonal = [mu] + con.friction[:dim-1]
                    for k in range(dim):
                        scale = dm*diagonal[k]
                        for j in range(k, dim):
                            h[k*dim+j] *= scale*diagonal[j]
                    for k in range(dim):
                        for j in range(k+1, dim):
                            h[j*dim+k] = h[k*dim+j]
            state[i:i+dim] = [classification]*dim
            i += dim - 1
        i += 1
    result = {"force": force, "state": state, "cost": [cost] if c.has_cost else []}
    if include_contact_hessians:
        result["contactHessians"] = [v for h in hessians for v in h]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--event", type=int, action="append", required=True)
    parser.add_argument("--reference-library", type=Path, required=True,
                        help="original active wheel, not an instrumented rebuild")
    parser.add_argument("--check-wheel-order-model", action="store_true",
                        help="check the diagnostic scalar arithmetic model against direct wheel outputs")
    args = parser.parse_args()
    if args.check_wheel_order_model and not hasattr(math, "fma"):
        parser.error("wheel-order model requires Python with math.fma (3.13+)")
    raw = args.trace.read_bytes()
    document = json.loads(raw)
    selected = []
    try:
        for event in args.event:
            if not 0 <= event < len(document["events"]):
                raise ValueError("event index outside trace")
            for step, record in enumerate(document["events"][event].get("newtonTraces", [])):
                for call, capture in enumerate(captured_updates(record.get("constraintUpdateTrace", []))):
                    selected.append((event, step, call, capture))
        if not selected:
            raise ValueError("selected events have no constraint update captures")
        library = args.reference_library.resolve()
        kernels = Kernels(library)
    except ValueError as error:
        parser.error(str(error))
    provenance = {"referenceLibrary": str(library),
                  "referenceSha256": hashlib.sha256(library.read_bytes()).hexdigest(),
                  "trace": str(args.trace.resolve()),
                  "traceSha256": hashlib.sha256(raw).hexdigest(),
                  "zeroSignsCaptured": False,
                  "zeroSignCaveat": "browser JSON numbers do not preserve negative zero"}
    mismatch = False
    for event, step, call, capture in selected:
        output = replay(capture, kernels)
        mismatch |= any(not value["exact"] for value in output.values())
        source_event = document["events"][event].get("sourceEvent", event)
        if args.check_wheel_order_model:
            native = kernels.update(capture)
            modeled = wheel_order_update(capture, kernels.norm, math.fma)
            model_checks = {name: difference(native[name], modeled[name]) for name in native}
            mismatch |= any(not v["exact"] for v in model_checks.values())
            output["wheelOrderModelAgainstDirectWheel"] = model_checks
        print(json.dumps({**provenance, "event": event, "substep": step, "call": call,
                          "sourceEvent": source_event, "hessian": capture.hessian,
                          **output}, allow_nan=False, sort_keys=True))
    return int(mismatch)


if __name__ == "__main__":
    raise SystemExit(main())
