"""Decode initialized PrimalEval outputs against their actual preparation call."""
import ctypes

from marble_cone_update_oracle import Reader
from marble_prepare_trace import capture_preparations, qualified_preparations
from marble_primal_eval_oracle import validated_inputs


def decode_evaluations(values, calls, preparations):
    if type(calls) is not int or not 0 <= calls <= 1000000:
        raise ValueError("evaluation call count must be a bounded integer")
    r = Reader(values)
    if len(values) > 300000:
        raise ValueError("capture exceeds evaluation recorder capacity")
    if not isinstance(preparations, list) or len(preparations) > 1000000:
        raise ValueError("evaluation preparations must be bounded")
    captures = []
    while r.offset < len(values):
        r.integer("evaluation schema", 1, 1)
        ordinal = r.integer("evaluation ordinal", 0, 999999)
        if ordinal != len(captures):
            raise ValueError("evaluation ordinals must be contiguous")
        preparation = r.integer("preparation ordinal", 0, len(preparations)-1)
        c = preparations[preparation]
        island = r.integer("evaluation island", -1, 65536)
        nv = r.integer("velocity dimension", 1, 512)
        n = r.integer("constraint dimension", 0, 65536)
        ne = r.integer("equality count", 0, n)
        nf = r.integer("friction count", 0, n-ne)
        if ((island, nv, n, ne, nf) !=
                (c["island"], c["nv"], c["nefc"], c["ne"], c["nf"])):
            raise ValueError("evaluation and preparation dimensions differ")
        alpha = r.take(1, "alpha")[0]
        output = r.take(3, "cost and derivatives")
        raw = r.take(1, "raw second derivative")[0]
        if output[2] != (raw if raw > 0 else 1e-15):
            raise ValueError("evaluation convexity clamp is inconsistent")
        inputs = {name: c["inputs"][name] for name in
                  ("jaref", "jv", "D", "types", "ids", "contacts")}
        inputs.update(alpha=alpha, ne=ne, nf=nf, gauss=c["quadGauss"],
                      rows=c["rows"], R=r.take(n, "constraint R"),
                      frictionloss=r.take(nf, "friction loss"))
        validated_inputs(**inputs)
        captures.append({"ordinal": ordinal, "preparationOrdinal": preparation,
                         "island": island, "nv": nv, "nefc": n,
                         "inputs": inputs, "result": output, "rawSecond": raw})
    r.finish()
    if len(captures) != calls:
        raise ValueError("evaluation call count differs from capture")
    return captures


def capture_evaluations(trace):
    if not isinstance(trace, dict):
        raise ValueError("evaluation trace must be an object")
    if trace.get("evalTraceSchema") != 1 or type(trace.get("evalTraceSchema")) is not int:
        raise ValueError("evaluation schema metadata must be 1")
    if trace.get("evalTraceOverflow") is not False or trace.get("evalTraceInvalid") is not False:
        raise ValueError("evaluation overflow/invalid metadata must be explicitly false")
    return decode_evaluations(trace.get("evalTrace"), trace.get("evalTraceCalls"),
                              capture_preparations(trace))


def qualified_evaluations(document, **selection):
    # Whole-solver qualification and all three identities must pass BEFORE
    # decoding any eval arrays or calling a model/private original routine.
    qualified_preparations(document, **selection)
    return capture_evaluations(document["trace"])


def capture_native_evaluations(library, preparations):
    """Read optional exports, checking capacity and metadata before copying."""
    if not hasattr(library, "mj_solver_eval_trace_schema"):
        return {}
    result = {}
    for field, suffix in (("evalTraceSchema", "schema"), ("evalTraceCalls", "calls"),
                          ("evalTraceOverflow", "overflow"), ("evalTraceInvalid", "invalid")):
        routine = getattr(library, "mj_solver_eval_trace_"+suffix)
        routine.argtypes, routine.restype = [], ctypes.c_int
        result[field] = bool(routine()) if suffix in ("overflow", "invalid") else int(routine())
    size = library.mj_solver_eval_trace_size
    size.argtypes, size.restype = [], ctypes.c_int
    length = int(size())
    if not 0 <= length <= 300000:
        raise ValueError("native evaluation copy size outside recorder capacity")
    if result["evalTraceOverflow"] or result["evalTraceInvalid"]:
        raise ValueError("native evaluation recorder overflowed or has invalid fields")
    values = (ctypes.c_double*length)()
    copy = library.mj_solver_eval_trace_copy
    copy.argtypes, copy.restype = [ctypes.POINTER(ctypes.c_double)], None
    copy(values)
    result["evalTrace"] = list(values)
    capture_evaluations({**preparations, **result})
    return result
