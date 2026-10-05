"""Bounded PrimalEval model and exact-library-only original arm64 oracle.

The private function bridge is intentionally NOT a general MuJoCo API: it
requires the exact original wheel hash, Darwin arm64, verified loaded image,
public-dot anchor, entry bytes and field offsets. The partial context contains
only fields the verified function reads/writes; padding is initialized and is
not solver scratch evidence. Never use this bridge with another library.
"""
import ctypes
import hashlib
import math
from pathlib import Path
import platform
import sys

from marble_cone_update_oracle import Reader
from marble_constraint_update_oracle import MjContact312

REFERENCE_SHA256 = "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c"
ORIGINAL_DOT_OFFSET = 0x10c504
ORIGINAL_EVAL_OFFSET = 0x105808
EVAL_ENTRY = bytes.fromhex("ff8301d1ed33016deb2b026de923036d")


def validated_inputs(*, alpha, ne, nf, gauss, jaref, jv, D, R,
                     frictionloss, types, ids, contacts, rows):
    Reader([alpha])
    Reader(jaref)
    n = len(jaref)
    if n > 65536 or type(ne) is not int or type(nf) is not int or not 0 <= ne <= ne+nf <= n:
        raise ValueError("invalid bounded evaluation constraint dimensions")
    for values, size in ((gauss, 3), (jv, n), (D, n), (R, n),
                         (frictionloss, nf), (types, n), (ids, n)):
        Reader(values)
        if len(values) != size:
            raise ValueError("evaluation array dimensions differ")
    if any(x < 0 for x in D+R+frictionloss):
        raise ValueError("negative evaluation impedance or friction loss")
    if any(v != int(v) or not 0 <= v <= 7 for v in types):
        raise ValueError("invalid evaluation constraint type")
    if any(v != int(v) or not -1 <= v <= 2147483647 for v in ids):
        raise ValueError("invalid evaluation constraint id")
    if not isinstance(contacts, list) or len(contacts) > 65536:
        raise ValueError("evaluation contacts must be bounded")
    for contact in contacts:
        if (not isinstance(contact, dict) or type(contact.get("dim")) is not int or
                contact["dim"] not in (1, 3, 4, 6)):
            raise ValueError("invalid evaluation contact dimension")
        Reader([contact.get("mu")])
        if contact["mu"] < 0:
            raise ValueError("negative evaluation friction parameter")
    if not isinstance(rows, list) or len(rows) > n:
        raise ValueError("evaluation rows must be bounded")
    offset = 0
    for row in rows:
        if (not isinstance(row, dict) or offset >= n or
                type(row.get("row")) is not int or row["row"] != offset):
            raise ValueError("evaluation row coverage differs")
        elliptic = types[offset] == 7
        dim = 1
        if elliptic:
            conid = int(ids[offset])
            if not 0 <= conid < len(contacts):
                raise ValueError("evaluation contact id outside capture")
            contact = contacts[conid]
            dim = contact["dim"]
            if (offset < ne+nf or dim not in (3, 4, 6) or contact["mu"] <= 0 or
                    offset+dim > n or any(types[k] != 7 or ids[k] != conid
                                         for k in range(offset, offset+dim))):
                raise ValueError("inconsistent evaluation elliptic group")
        if type(row.get("dim")) is not int or row["dim"] != dim:
            raise ValueError("evaluation active dimension differs")
        Reader(row.get("quad"))
        if len(row["quad"]) != (9 if elliptic else 3):
            raise ValueError("evaluation active coefficient width differs")
        offset += dim
    if offset != n:
        raise ValueError("evaluation rows do not cover constraints")
    return n


def evaluate(*, alpha, ne, nf, gauss, jaref, jv, D, R, frictionloss,
             types, ids, contacts, rows, fma=None):
    validated_inputs(alpha=alpha, ne=ne, nf=nf, gauss=gauss, jaref=jaref, jv=jv,
                     D=D, R=R, frictionloss=frictionloss, types=types, ids=ids,
                     contacts=contacts, rows=rows)
    fma = fma or getattr(math, "fma", None)
    if not callable(fma):
        raise ValueError("evaluation requires correctly rounded fma")
    cost = d0 = d1 = q0 = 0.0
    q1, q2 = gauss[1:]
    alpha2 = alpha*alpha
    twice_alpha = alpha+alpha
    stages = []
    for row in rows:
        i, quad = row["row"], row["quad"]
        stage = {"row": i}
        if i < ne:
            q1 += quad[1]
            q2 += quad[2]
            stage["kind"] = "equality"
        elif i < ne+nf:
            start, direction = jaref[i], jv[i]
            x = fma(alpha, direction, start)
            f, bound = frictionloss[i-ne], R[i]*frictionloss[i-ne]
            def zone(value):
                return 0 if -bound < value < bound else (-1 if value <= -bound else 1)
            start_zone, end_zone = zone(start), zone(x)
            if start_zone == end_zone == 0:
                delta = ((x-start)*(0.5*D[i]))*(start+x)
            elif start_zone == end_zone == -1:
                delta = (start-x)*f
            elif start_zone == end_zone == 1:
                delta = (x-start)*f
            else:
                def absolute(value, z):
                    if z == 0:
                        return ((0.5*D[i])*value)*value
                    return f*fma(-0.5, bound, value if z == 1 else -value)
                delta = absolute(x, end_zone)-absolute(start, start_zone)
            cost += delta
            if end_zone == 0:
                d0 = fma(x*D[i], direction, d0)
                d1 = fma(direction*D[i], direction, d1)
            else:
                d0 = fma(f if end_zone == 1 else -f, direction, d0)
            stage.update(kind="friction", zones=[start_zone, end_zone], x=x, delta=delta)
        elif types[i] != 7:
            start = jaref[i]
            x = fma(alpha, jv[i], start)
            cost0 = quad[0] if start < 0 else 0.0
            if x < 0:
                q0 += quad[0]-cost0
                q1 += quad[1]
                q2 += quad[2]
            else:
                cost -= cost0
            stage.update(kind="inequality", x=x, active=x < 0)
        else:
            mu = contacts[int(ids[i])]["mu"]
            U0, V0, UU, UV, VV, Dm = quad[3:]
            T0 = math.sqrt(UU) if UU > 0 else 0.0
            zone0 = (2 if U0 < 0 else 1) if UU <= 0 else (
                1 if U0 >= mu*T0 else (2 if fma(mu, U0, T0) <= 0 else 3))
            N = fma(alpha, V0, U0)
            inner = fma(2.0, UV, alpha*VV)
            tsqr = fma(alpha, inner, UU)
            T = math.sqrt(tsqr) if tsqr > 0 else 0.0
            zone1 = (2 if N < 0 else 1) if tsqr <= 0 else (
                1 if N >= mu*T else (2 if fma(mu, N, T) <= 0 else 3))
            zones = (zone0, zone1)
            if zones == (1, 1):
                delta = 0.0
            elif zones == (2, 2):
                delta = fma(alpha2, quad[2], alpha*quad[1])
            elif zones == (3, 3):
                # The wheel negates the separately rounded tangential delta
                # before division, then fuses alpha*V0 with its scaled value.
                td = -(inner*alpha)/(T0+T)
                rd = fma(alpha, V0, mu*td)
                r0 = fma(-mu, T0, U0)
                delta = ((0.5*Dm)*rd)*fma(2.0, r0, rd)
            elif zones == (3, 2):
                dq = alpha*fma(alpha, quad[2], quad[1])
                boundary = fma(mu, U0, T0)
                delta = ((0.5*Dm)*boundary)*boundary+dq
            elif zones == (2, 3):
                dq = alpha*fma(alpha, quad[2], quad[1])
                boundary = fma(mu, N, T)
                delta = dq+((-0.5*Dm)*boundary)*boundary
            elif zones == (1, 2):
                delta = quad[0]+fma(alpha2, quad[2], alpha*quad[1])
            elif zones == (1, 3):
                r = fma(-mu, T, N)
                delta = ((0.5*Dm)*r)*r
            elif zones == (3, 1):
                r = fma(-mu, T0, U0)
                delta = ((-0.5*Dm)*r)*r
            else:  # bottom -> top
                delta = -quad[0]
            if zone1 == 2:
                d0 += fma(twice_alpha, quad[2], quad[1])
                d1 = fma(2.0, quad[2], d1)
            elif zone1 == 3:
                tangent = fma(alpha, VV, UV)
                T1 = tangent/T
                T2 = VV/T-(tangent*T1)/(T*T)
                r = fma(-mu, T, N)
                slope = fma(-mu, T1, V0)
                d0 = fma(Dm*r, slope, d0)
                second = fma(slope, slope, r*((-mu)*T2))
                d1 = fma(Dm, second, d1)
            cost += delta
            stage.update(kind="elliptic", zones=list(zones), N=N, Tsqr=tsqr, delta=delta)
        stage.update(cost=cost, deriv=[d0, d1], totalQuad=[q0, q1, q2])
        stages.append(stage)
    raw_second = fma(2.0, q2, d1)
    derivative0 = fma(twice_alpha, q2, q1)+d0
    final_cost = (q0+fma(alpha2, q2, alpha*q1))+cost
    output = [final_cost, derivative0, raw_second if raw_second > 0 else 1e-15]
    Reader(output+[raw_second])
    return {"result": output, "rawSecond": raw_second, "convexityClamped": raw_second <= 0,
            "stages": stages}


class EvalContext(ctypes.Structure):
    """Exact consumed/written offsets of the hash-pinned original PrimalEval."""
    _fields_ = [("header", ctypes.c_int*8), ("contact", ctypes.c_void_p),
        ("unused28", ctypes.c_byte*0x50), ("efc_D", ctypes.c_void_p),
        ("efc_R", ctypes.c_void_p), ("frictionloss", ctypes.c_void_p),
        ("unused90", ctypes.c_void_p), ("ids", ctypes.c_void_p),
        ("types", ctypes.c_void_p), ("unusedA8", ctypes.c_byte*0x60),
        ("jaref", ctypes.c_void_p), ("jv", ctypes.c_void_p),
        ("unused118", ctypes.c_byte*0x28), ("quad", ctypes.c_void_p),
        ("unused148", ctypes.c_byte*0xf0), ("gauss", ctypes.c_double*3),
        ("unused250", ctypes.c_byte*0x14), ("LSiter", ctypes.c_int),
        ("unused268", ctypes.c_byte*0x10)]


class EvalPoint(ctypes.Structure):
    _fields_ = [("alpha", ctypes.c_double), ("cost", ctypes.c_double),
                ("deriv", ctypes.c_double*2)]


class DlInfo(ctypes.Structure):
    _fields_ = [("filename", ctypes.c_char_p), ("base", ctypes.c_void_p),
                ("symbol", ctypes.c_char_p), ("symbol_address", ctypes.c_void_p)]


def check_layout():
    expected = {"contact": 0x20, "efc_D": 0x78, "efc_R": 0x80,
        "frictionloss": 0x88, "ids": 0x98, "types": 0xa0,
        "jaref": 0x108, "jv": 0x110, "quad": 0x140, "gauss": 0x238,
        "LSiter": 0x264}
    if (ctypes.sizeof(ctypes.c_double) != 8 or ctypes.sizeof(ctypes.c_int) != 4 or
            ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(EvalContext) != 0x278 or
            ctypes.sizeof(EvalPoint) != 32 or ctypes.sizeof(MjContact312) != 0x248 or
            MjContact312.mu.offset != 0xe8 or MjContact312.dim.offset != 0x210 or
            any(getattr(EvalContext, name).offset != offset for name, offset in expected.items())):
        raise ValueError("original wheel evaluation layout mismatch")


class OriginalEval:
    """Call ONLY the verified exact original function on validated owned arrays."""
    def __init__(self, path):
        if sys.platform != "darwin" or platform.machine() != "arm64":
            raise ValueError("original private evaluation bridge requires Darwin arm64")
        check_layout()
        self.path = Path(path).resolve()
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != REFERENCE_SHA256:
            raise ValueError("original evaluation bridge requires the exact authoritative wheel")
        self.library = ctypes.CDLL(str(self.path))
        dot_address = ctypes.cast(self.library.mju_dot, ctypes.c_void_p).value
        dladdr = ctypes.CDLL(None).dladdr
        dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
        dladdr.restype = ctypes.c_int
        info = DlInfo()
        if (not dladdr(dot_address, ctypes.byref(info)) or not info.filename or
                Path(info.filename.decode()).resolve() != self.path or
                info.base != dot_address-ORIGINAL_DOT_OFFSET):
            raise ValueError("public-dot anchor does not identify the verified loaded wheel")
        address = info.base+ORIGINAL_EVAL_OFFSET
        if ctypes.string_at(address, len(EVAL_ENTRY)) != EVAL_ENTRY:
            raise ValueError("original evaluation entry bytes differ")
        self.routine = ctypes.CFUNCTYPE(None, ctypes.POINTER(EvalContext),
                                       ctypes.POINTER(EvalPoint))(address)

    def evaluate(self, **inputs):
        n = validated_inputs(**inputs)
        ctx = EvalContext()
        ne, nf = inputs["ne"], inputs["nf"]
        ctx.header[:] = [0, int(7 in inputs["types"]), -1, 1, ne, nf, n, 0]
        keep = []
        for field, values, scalar in (("efc_D", inputs["D"], ctypes.c_double),
            ("efc_R", inputs["R"], ctypes.c_double),
            ("frictionloss", [0.]*ne+inputs["frictionloss"], ctypes.c_double),
            ("ids", [int(i) for i in inputs["ids"]], ctypes.c_int),
            ("types", [int(i) for i in inputs["types"]], ctypes.c_int),
            ("jaref", inputs["jaref"], ctypes.c_double),
            ("jv", inputs["jv"], ctypes.c_double)):
            array = (scalar*max(1, len(values)))(*values)
            keep.append(array)
            setattr(ctx, field, ctypes.cast(array, ctypes.c_void_p).value)
        contacts = (MjContact312*max(1, len(inputs["contacts"])))()
        for i, contact in enumerate(inputs["contacts"]):
            contacts[i].dim, contacts[i].mu = contact["dim"], contact["mu"]
        quad = (ctypes.c_double*max(1, 3*n))()
        for row in inputs["rows"]:
            for j, value in enumerate(row["quad"]):
                quad[3*row["row"]+j] = value
        ctx.contact = ctypes.cast(contacts, ctypes.c_void_p).value
        ctx.quad = ctypes.cast(quad, ctypes.c_void_p).value
        ctx.gauss[:] = inputs["gauss"]
        point = EvalPoint()
        point.alpha = inputs["alpha"]
        self.routine(ctypes.byref(ctx), ctypes.byref(point))
        if ctx.LSiter != 1 or point.alpha != inputs["alpha"]:
            raise ValueError("original evaluation bridge postcondition mismatch")
        output = [point.cost, *point.deriv]
        Reader(output)
        return output
