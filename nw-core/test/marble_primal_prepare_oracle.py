"""Bounded diagnostic model of the original arm64 wheel's PrimalPrepare.

This models one initialized solver boundary, not a replacement reference
simulation. The operation order comes from the active wheel's inlined
mj_solPrimal instructions at 0x1017a4..0x1019fc. Gauss dot products are supplied
by a separately verified callback (the original wheel's public mju_dot in
native checks). Never use synchronized/model results as trajectory acceptance.
"""
import math

from marble_cone_update_oracle import Reader


def finite_vector(values, length, name):
    Reader(values)
    if len(values) != length:
        raise ValueError(f"{name} dimensions differ")


def prepare_rows(jaref, jv, D, types, ids, contacts, *, fma=None):
    """Return only initialized quad entries and full per-tangent stages.

    Scalar rows initialize 3 entries. An elliptic group initializes 9 entries
    at its first row and consumes dim constraint rows. Remaining unused slots
    for dim=4/6 are not read, compared, or invented. All input validation occurs
    before computation; this function never invokes a native pointer API.
    """
    Reader(jaref)
    n = len(jaref)
    if n > 65536:
        raise ValueError("constraint rows exceed bounded capture limit")
    for values, name in ((jv, "Jv"), (D, "D"), (types, "types"), (ids, "ids")):
        finite_vector(values, n, name)
    if any(v < 0 for v in D):
        raise ValueError("constraint impedance must be nonnegative")
    if not isinstance(contacts, list) or len(contacts) > 65536:
        raise ValueError("contacts must be a bounded list")
    for con in contacts:
        if (not isinstance(con, dict) or type(con.get("dim")) is not int or
                con["dim"] not in (1, 3, 4, 6)):
            raise ValueError("contact dimension must be an integer in 1, 3, 4, 6")
        Reader([con.get("mu")])
        finite_vector(con.get("friction"), 5, "friction")
        if con["mu"] < 0 or any(v < 0 for v in con["friction"]):
            raise ValueError("mu and friction must be nonnegative")
    groups = []
    row = 0
    while row < n:
        if types[row] != int(types[row]) or not 0 <= types[row] <= 7:
            raise ValueError("invalid constraint type")
        if ids[row] != int(ids[row]):
            raise ValueError("contact id must be integral")
        dim = 1
        if types[row] == 7:
            if not 0 <= ids[row] < len(contacts):
                raise ValueError("elliptic contact id outside capture")
            dim = contacts[int(ids[row])]["dim"]
            if dim not in (3, 4, 6) or contacts[int(ids[row])]["mu"] <= 0:
                raise ValueError("elliptic contacts require dim=3/4/6 and positive mu")
            if row+dim > n or any(types[k] != 7 or ids[k] != ids[row]
                                   for k in range(row, row+dim)):
                raise ValueError("incomplete or inconsistent elliptic group")
        groups.append((row, dim))
        row += dim
    fma = fma or getattr(math, "fma", None)
    if not callable(fma):
        raise ValueError("PrimalPrepare model requires correctly rounded fma")
    result = []
    for row, dim in groups:
        dj = D[row]*jaref[row]
        q = [jaref[row]*dj, jv[row]*dj, (jv[row]*D[row])*jv[row]]
        item = {"row": row, "dim": dim, "initial": q.copy(), "bottomStages": []}
        if types[row] == 7:
            con = contacts[int(ids[row])]
            mu, friction = con["mu"], con["friction"]
            for j in range(1, dim):
                k = row+j
                dj = D[k]*jaref[k]
                before = q.copy()
                q = [fma(jaref[k], dj, q[0]), fma(jv[k], dj, q[1]),
                     fma(jv[k]*D[k], jv[k], q[2])]
                item["bottomStages"].append({"tangent": j, "DJ": dj,
                    "before": before, "after": q.copy(),
                    "roundedIncrements": [jaref[k]*dj, jv[k]*dj, (jv[k]*D[k])*jv[k]]})
            U = [jaref[row]*mu] + [jaref[row+j]*friction[j-1] for j in range(1, dim)]
            V = [jv[row]*mu] + [jv[row+j]*friction[j-1] for j in range(1, dim)]
            uu = uv = vv = 0.0
            stages = []
            for j in range(1, dim):
                uu = fma(U[j], U[j], uu)
                uv = fma(U[j], V[j], uv)
                vv = fma(V[j], V[j], vv)
                stages.append({"tangent": j, "U": U[j], "V": V[j],
                               "roundedProducts": [U[j]*U[j], U[j]*V[j], V[j]*V[j]],
                               "UU": uu, "UV": uv, "VV": vv})
            # Separate rounded mu^2, but fused (mu*mu+1) in the second factor.
            dm = D[row]/((mu*mu)*fma(mu, mu, 1.0))
            q += [U[0], V[0], uu, uv, vv, dm]
            item.update(U=U, V=V, tangentStages=stages)
        q[0] *= 0.5
        q[2] *= 0.5
        Reader(q)
        item["quad"] = q
        result.append(item)
    return result


def prepare(*, search, Ma, Mv, qfrc_smooth, gauss0, jaref, jv, D,
            types, ids, contacts, dot, fma=None):
    """Model complete initialized Gauss and constraint preparation outputs."""
    Reader(search)
    nv = len(search)
    if not 1 <= nv <= 512:
        raise ValueError("velocity count must be in 1..512")
    for values, name in ((Ma, "Ma"), (Mv, "Mv"), (qfrc_smooth, "qfrc_smooth")):
        finite_vector(values, nv, name)
    Reader([gauss0])
    if not callable(dot):
        raise ValueError("Gauss preparation requires a verified dot callback")
    # Validate the whole constraint selection before invoking even the dot callback.
    rows = prepare_rows(jaref, jv, D, types, ids, contacts, fma=fma)
    terms = [dot(search, Ma), dot(qfrc_smooth, search), dot(search, Mv)]
    Reader(terms)
    gauss = [gauss0, terms[0]-terms[1], 0.5*terms[2]]
    Reader(gauss)
    return {"quadGauss": gauss, "rows": rows}
