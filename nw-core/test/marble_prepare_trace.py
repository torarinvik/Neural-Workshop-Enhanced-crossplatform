"""Decode bounded initialized preparation captures before native model calls."""
import ctypes

from marble_cone_update_oracle import Reader


def decode_preparations(values, calls):
    if type(calls) is not int or not 0 <= calls <= 1000000:
        raise ValueError("preparation call count must be a bounded integer")
    r = Reader(values)
    if len(values) > 300000:
        raise ValueError("capture exceeds preparation recorder capacity")
    captures = []
    while r.offset < len(values):
        r.integer("preparation schema", 1, 1)
        ordinal = r.integer("preparation ordinal", 0, 999999)
        if ordinal != len(captures):
            raise ValueError("preparation ordinals must be contiguous")
        island = r.integer("island", -1, 65536)
        nv = r.integer("velocity dimension", 1, 512)
        n = r.integer("constraint dimension", 0, 65536)
        ne = r.integer("equality count", 0, n)
        nf = r.integer("friction count", 0, n-ne)
        sparse = r.integer("sparse flag", 0, 1)
        blocks = r.integer("block count", 0, n)
        r.integer("initialized validity bits", 79, 79)
        inputs = {name: r.take(nv, name) for name in ("search", "Ma", "Mv", "qfrc_smooth")}
        inputs.update({name: r.take(n, name) for name in ("jaref", "jv", "D")})
        inputs["types"] = [r.integer("constraint type", 0, 7) for _ in range(n)]
        ids = [r.integer("constraint id", -1, 2147483647) for _ in range(n)]
        inputs["ids"] = ids.copy()
        gauss = r.take(3, "prepared Gauss coefficients")
        inputs["gauss0"] = gauss[0]
        if any(v < 0 for v in inputs["D"]):
            raise ValueError("negative constraint impedance")
        contacts, contact_ids, outputs = [], {}, []
        row = 0
        for _ in range(blocks):
            if row >= n:
                raise ValueError("too many preparation blocks")
            r.integer("block row", row, row)
            dim = r.integer("block dimension", 1, 6)
            conid = r.integer("block global id", -1, 2147483647)
            kind = r.integer("block kind", 0, 7)
            width = r.integer("initialized coefficient width", 3, 9)
            elliptic = kind == 7
            if kind != inputs["types"][row] or conid != ids[row]:
                raise ValueError("block metadata differs from constraint arrays")
            if (dim not in ((3, 4, 6) if elliptic else (1,)) or
                    width != (9 if elliptic else 3) or row+dim > n):
                raise ValueError("invalid active coefficient layout")
            if elliptic:
                if conid < 0 or any(inputs["types"][k] != 7 or ids[k] != conid
                                    for k in range(row, row+dim)):
                    raise ValueError("inconsistent elliptic constraint block")
                mu = r.take(1, "mu")[0]
                friction = r.take(5, "friction")
                if mu <= 0 or any(f < 0 for f in friction):
                    raise ValueError("invalid elliptic friction parameters")
                contact = {"dim": dim, "mu": mu, "friction": friction}
                if conid not in contact_ids:
                    contact_ids[conid] = len(contacts)
                    contacts.append(contact)
                elif contacts[contact_ids[conid]] != contact:
                    raise ValueError("repeated contact parameters differ")
                for k in range(row, row+dim):
                    inputs["ids"][k] = contact_ids[conid]
            outputs.append({"row": row, "dim": dim, "globalContactId": conid,
                            "type": kind, "quad": r.take(width, "initialized coefficients")})
            row += dim
        if row != n:
            raise ValueError("preparation blocks do not cover all constraint rows")
        inputs["contacts"] = contacts
        captures.append({"ordinal": ordinal, "island": island, "nv": nv, "nefc": n,
                         "ne": ne, "nf": nf, "sparse": sparse, "inputs": inputs,
                         "quadGauss": gauss, "rows": outputs})
    r.finish()
    if len(captures) != calls:
        raise ValueError("preparation call count differs from capture")
    return captures


def capture_preparations(trace):
    if not isinstance(trace, dict):
        raise ValueError("preparation trace must be an object")
    if trace.get("prepareTraceSchema") != 1 or type(trace.get("prepareTraceSchema")) is not int:
        raise ValueError("preparation schema metadata must be 1")
    if (trace.get("prepareTraceOverflow") is not False or
            trace.get("prepareTraceInvalid") is not False):
        raise ValueError("preparation overflow/invalid metadata must be explicitly false")
    return decode_preparations(trace.get("prepareTrace"), trace.get("prepareTraceCalls"))


def qualified_preparations(document, *, reference_sha256, diagnostic_sha256,
                           input_trace_sha256):
    """Accept only explicitly qualified exact-input native boundaries.

    This is bounded whole-output qualification of a diagnostic rebuild, not
    instrumentation of the original wheel or full trajectory acceptance.
    Validate qualification/provenance before decoding or calling a model.
    """
    if not isinstance(document, dict) or document.get("schema") != (
            "neural-workshop.marble-preparation-qualified.v1"):
        raise ValueError("unsupported preparation qualification document")
    if (document.get("exactInputCopy") is not True or
            document.get("solverOutputsExactlyEqual") is not True or
            document.get("outputDifferences") != {}):
        raise ValueError("native preparation boundary lacks exact whole-solver qualification")
    for field, maximum in (("event", 1000000), ("substep", 3)):
        value = document.get(field)
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError("invalid preparation qualification "+field)
    wheel = document.get("nativeWheel")
    diagnostic = document.get("diagnosticLibrary")
    if not isinstance(wheel, dict) or not isinstance(diagnostic, dict):
        raise ValueError("missing native preparation provenance")
    active = wheel.get("activeEngineLibrary")
    if (wheel.get("distributionVersion") != "3.12.0" or
            wheel.get("mujocoVersion") != "3.12.0" or
            not isinstance(active, dict) or
            active.get("loadedInProcess") is not True or
            active.get("wheelRecordMatches") is not True):
        raise ValueError("reference wheel was not verified active in the qualification process")
    source = document.get("inputTrace")
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        raise ValueError("missing preparation input-trace provenance")
    for expected, actual in ((reference_sha256, active.get("sha256")),
                             (diagnostic_sha256, diagnostic.get("sha256")),
                             (input_trace_sha256, source.get("sha256"))):
        if (not isinstance(expected, str) or len(expected) != 64 or
                any(c not in "0123456789abcdef" for c in expected) or actual != expected):
            raise ValueError("preparation qualification library hash mismatch")
    return capture_preparations(document.get("trace"))


def capture_native_preparations(library):
    """Read an optional native capture, bounding its size before pointer copying."""
    if not hasattr(library, "mj_solver_prepare_trace_schema"):
        return {}
    fields = {"prepareTraceSchema": "schema", "prepareTraceCalls": "calls",
              "prepareTraceOverflow": "overflow", "prepareTraceInvalid": "invalid"}
    result = {}
    for field, suffix in fields.items():
        routine = getattr(library, "mj_solver_prepare_trace_"+suffix)
        routine.argtypes, routine.restype = [], ctypes.c_int
        result[field] = bool(routine()) if suffix in ("overflow", "invalid") else int(routine())
    size = library.mj_solver_prepare_trace_size
    size.argtypes, size.restype = [], ctypes.c_int
    length = int(size())
    if not 0 <= length <= 300000:
        raise ValueError("native preparation copy size outside recorder capacity")
    if result["prepareTraceOverflow"] or result["prepareTraceInvalid"]:
        raise ValueError("native preparation recorder overflowed or has invalid fields")
    values = (ctypes.c_double*length)()
    copy = library.mj_solver_prepare_trace_copy
    copy.argtypes, copy.restype = [ctypes.POINTER(ctypes.c_double)], None
    copy(values)
    result["prepareTrace"] = list(values)
    capture_preparations(result)
    return result
