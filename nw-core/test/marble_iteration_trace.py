"""Bounded decoding of initialized primal constraint-iteration diagnostics.

Schema 1 is retained for reading historical traces, but its pre-solve Jv/search
validity and Jv length are not trustworthy. Schema 2 declares validity and
records Jv with nefc entries. This module never weakens trajectory acceptance.
"""
from marble_cone_update_oracle import Reader


def iteration_trace_metadata(library):
    schema = (int(library.mj_solver_constraint_iteration_trace_schema())
              if hasattr(library, "mj_solver_constraint_iteration_trace_schema") else 1)
    if schema not in (1, 2):
        raise AssertionError(f"unsupported constraint-iteration schema {schema}")
    overflow = (bool(library.mj_solver_constraint_iteration_trace_overflow())
                if hasattr(library, "mj_solver_constraint_iteration_trace_overflow") else None)
    if overflow or (schema == 2 and overflow is not False):
        raise AssertionError("constraint-iteration recorder overflowed or lacks overflow status")
    return {"constraintIterationTraceSchema": schema,
            "constraintIterationTraceOverflow": overflow}


def decode_iteration_updates(values, schema=1):
    """Return validated records/error; schema 2 never reads invalid scratch."""
    records = []
    try:
        if type(schema) is not int or schema not in (1, 2):
            raise ValueError("unsupported constraint-iteration schema")
        r = Reader(values)
        while r.offset < len(values):
            if schema == 2:
                r.integer("record schema", 2, 2)
            phase = r.integer("phase", 0, 1)
            ne = r.integer("equalities", 0, 65536)
            nf = r.integer("friction rows", 0, 65536)
            nefc = r.integer("constraint rows", 0, 65536)
            ncontact = r.integer("contact count", 0, 65536)
            nv = r.integer("velocity count", 1, 512)
            hessian = r.integer("Hessian flag", 0, 1)
            cost = r.take(1, "cost")[0]
            validity = r.integer("validity bits", 0, 7) if schema == 2 else None
            if ne+nf > nefc:
                raise ValueError("equality/friction rows exceed constraint count")
            if schema == 2 and ((validity & 2 and not validity & 4) or
                                (phase == 1 and not validity & 1)):
                raise ValueError("invalid initialized-field lifecycle")
            lengths = (nefc, nefc, nf, nefc, nefc, nefc, nefc, nefc,
                       nefc if schema == 2 else nv, nv, 7*ncontact)
            names = ("efc_D", "efc_R", "frictionloss", "Jaref", "efc_type",
                     "efc_id", "efc_state", "efc_force", "Jv", "search",
                     "contact_dim_mu_friction")
            fields = {name: r.take(n, name) for name, n in zip(names, lengths)}
            valid = {"cost": bool(validity & 1) if schema == 2 else None,
                     "Jv": bool(validity & 2) if schema == 2 else None,
                     "search": bool(validity & 4) if schema == 2 else None}
            if schema == 2:
                if not valid["cost"] and cost != 0:
                    raise ValueError("invalid cost must use a zero placeholder")
                for name in ("Jv", "search"):
                    if not valid[name] and any(v != 0 for v in fields[name]):
                        raise ValueError(f"invalid {name} must use zero placeholders")
            records.append({"schema": schema, "phase": phase, "ne": ne, "nf": nf,
                            "nv": nv, "nefc": nefc, "ncontact": ncontact,
                            "hessian": hessian, "cost": cost,
                            "validity": valid, "fields": fields})
        r.finish()
    except (ValueError, OverflowError) as error:
        return records, {"field": str(error)}
    return records, None


def compare_iteration_traces(native, wasm):
    """Never equate different schemas or infer legacy scratch validity."""
    schemas = [t.get("constraintIterationTraceSchema", 1) for t in (native, wasm)]
    arrays = [t.get("constraintIterationTrace", []) for t in (native, wasm)]
    decoded = [decode_iteration_updates(a, s) for a, s in zip(arrays, schemas)]
    errors = [d[1] for d in decoded]
    for i, (trace, schema) in enumerate(zip((native, wasm), schemas)):
        if schema == 2 and trace.get("constraintIterationTraceOverflow") is not False:
            errors[i] = {"field": "recorder overflowed or lacks overflow status"}
    result = {"schemas": schemas, "records": [d[0] for d in decoded],
              "errors": errors, "comparable": False, "firstDifference": None}
    if any(errors):
        result["firstDifference"] = {"field": "decode error", "errors": errors}
        return result
    if schemas != [2, 2]:
        result["firstDifference"] = {
            "field": "schema/validity", "native": schemas[0], "wasm": schemas[1],
            "caveat": "legacy Jv/search validity is unknown; raw values are not initialized parity evidence"}
        return result
    left, right = result["records"]
    result["comparable"] = len(left) == len(right)
    if len(left) != len(right):
        result["firstDifference"] = {"field": "record count", "native": len(left),
                                      "wasm": len(right)}
        return result
    for i, (a, b) in enumerate(zip(left, right)):
        for field in ("phase", "ne", "nf", "nefc", "nv", "ncontact", "hessian", "validity"):
            if a[field] != b[field]:
                result["firstDifference"] = {"record": i, "field": field,
                                              "native": a[field], "wasm": b[field]}
                return result
        if a["validity"]["cost"] and a["cost"] != b["cost"]:
            result["firstDifference"] = {"record": i, "field": "cost",
                                          "native": a["cost"], "wasm": b["cost"]}
            return result
        for field in a["fields"]:
            if field in a["validity"] and not a["validity"][field]:
                continue
            av, bv = a["fields"][field], b["fields"][field]
            differences = [(k, x, y) for k, (x, y) in enumerate(zip(av, bv)) if x != y]
            if differences:
                result["firstDifference"] = {
                    "record": i, "phase": a["phase"], "field": field,
                    "differentCount": len(differences), "firstDifferences": differences[:8]}
                return result
    return result
