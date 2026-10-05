"""Dependency-light integration boundary ownership and IEEE operand guards."""
import math
import re
import struct

DIMENSIONS = ("nq", "nv", "na", "nu", "nbody", "njnt", "ntree", "nD", "nC", "nactuator", "nsensor", "nhistory", "nplugin", "nflex", "ntendon")
INTEGER_MODEL = ("body_parentid", "body_dofadr", "body_dofnum", "body_jntadr", "body_jntnum", "jnt_type", "jnt_bodyid", "jnt_dofadr", "jnt_qposadr", "dof_treeid", "tree_dofnum", "dof_jntid", "M_rownnz", "M_rowadr", "M_colind", "D_rownnz", "D_rowadr", "D_colind", "D_diag", "mapD2M")


def validated_packet(packet, phase):
    """Validate the complete standalone-free-body Marble integration branch.

    Native-owned topology must additionally match before copying any operands.
    This validator alone is not native output or whole-game qualification.
    """
    if not isinstance(packet, dict) or packet.get("schema") != "neural-workshop.marble-integrator-readset.v1" or packet.get("phase") != phase or phase not in ("checkAcc", "implicit"):
        raise ValueError("assigned integration read-set required")
    for key in ("dimensions", "model", "modelBits", "options", "optionBits", "arrays", "arrayBits"):
        if not isinstance(packet.get(key), dict): raise ValueError("integration object required: " + key)
    d, m, options = packet["dimensions"], packet["model"], packet["options"]
    if set(d) != set(DIMENSIONS) or any(type(v) is not int or not 0 <= v <= 100000 for v in d.values()):
        raise ValueError("bounded explicit integration dimensions required")
    nj, nv, nq, nb = (d[k] for k in ("njnt", "nv", "nq", "nbody"))
    if not 1 <= nj <= 85 or (nv, nq, nb, d["ntree"]) != (6*nj, 7*nj, nj+1, nj):
        raise ValueError("standalone free-body integration dimensions required")
    if any(d[k] for k in ("na", "nu", "nactuator", "nsensor", "nhistory", "nplugin", "nflex", "ntendon")) or d["nD"] != 36*nj or not nv <= d["nC"] <= 21*nj:
        raise ValueError("unsupported integration branch or sparse dimensions")
    sizes = {k: nb for k in INTEGER_MODEL if k.startswith("body_")}
    sizes.update({k: nj for k in INTEGER_MODEL if k.startswith("jnt_")})
    sizes.update({k: nv for k in ("dof_treeid", "dof_jntid", "M_rownnz", "M_rowadr", "D_rownnz", "D_rowadr", "D_diag")})
    sizes.update(tree_dofnum=nj, M_colind=d["nC"], D_colind=d["nD"], mapD2M=d["nC"])
    for key, size in sizes.items():
        values = m.get(key)
        if not isinstance(values, list) or len(values) != size or any(type(v) is not int for v in values):
            raise ValueError("complete integral integration layout required: " + key)
    expected = dict(body_parentid=[0]*nb, body_dofnum=[0]+[6]*nj, body_jntnum=[0]+[1]*nj,
                    jnt_type=[0]*nj, jnt_bodyid=list(range(1,nb)), jnt_dofadr=list(range(0,nv,6)),
                    jnt_qposadr=list(range(0,nq,7)), tree_dofnum=[6]*nj,
                    dof_treeid=[j for j in range(nj) for _ in range(6)], dof_jntid=[j for j in range(nj) for _ in range(6)])
    if any(m[key] != values for key, values in expected.items()):
        raise ValueError("standalone free-body integration topology required")
    if m["body_dofadr"][1:] != list(range(0,nv,6)) or m["body_jntadr"][1:] != list(range(nj)) or m["body_dofadr"][0] not in (-1,0) or m["body_jntadr"][0] not in (-1,0):
        raise ValueError("integration body ownership addresses differ")
    for key, count, cols in (("M", d["nC"], nv), ("D", d["nD"], nv)):
        cursor = 0
        for row, (start, width) in enumerate(zip(m[key+"_rowadr"], m[key+"_rownnz"])):
            if start != cursor or not 1 <= width <= 6 or cursor+width > count:
                raise ValueError("complete sparse integration rows required")
            indices = m[key+"_colind"][cursor:cursor+width]
            if indices != sorted(set(indices)) or any(not 0 <= c < cols for c in indices) or row not in indices:
                raise ValueError("bounded ordered integration columns required")
            if any(c//6 != row//6 for c in indices) or (key == "M" and any(c > row for c in indices)):
                raise ValueError("standalone integration sparse block differs")
            if key == "D" and m["D_diag"][row] != indices.index(row):
                raise ValueError("integration diagonal address differs")
            cursor += width
        if cursor != count: raise ValueError("sparse integration layout coverage differs")
    if any(not 0 <= i < d["nD"] for i in m["mapD2M"]): raise ValueError("integration mass map out of bounds")
    for row in range(nv):
        start,width=m["M_rowadr"][row],m["M_rownnz"][row]
        for position in range(start,start+width):
            column=m["M_colind"][position]
            expected_index=m["D_rowadr"][row]+m["D_colind"][m["D_rowadr"][row]:m["D_rowadr"][row]+m["D_rownnz"][row]].index(column)
            if m["mapD2M"][position] != expected_index: raise ValueError("integration mass/derivative map differs")
    for key in ("integrator", "disableflags", "enableflags"):
        if type(options.get(key)) is not int or not 0 <= options[key] <= 2147483647:
            raise ValueError("explicit integration flags required")
    if options["integrator"] != 3 or options["enableflags"] & 16:
        raise ValueError("only sleep-disabled implicitfast qualified")
    decoded_options = {key: decoded_bits([options.get(key)], [packet["optionBits"].get(key)], 1)[0] for key in ("density", "viscosity", "timestep")}
    if decoded_options["density"] != 0 or decoded_options["viscosity"] != 0 or not 0 < decoded_options["timestep"] <= 1:
        raise ValueError("nonfluid bounded integration timestep required")
    floats = {key: decoded_bits(m.get(key), packet["modelBits"].get(key), size) for key, size in (("body_mass",nb),("body_subtreemass",nb),("body_inertia",3*nb),("dof_damping",nv),("dof_dampingpoly",2*nv))}
    arrays = {key: decoded_bits(packet["arrays"].get(key), packet["arrayBits"].get(key), size) for key, size in (("qpos",nq),("qvel",nv),("qacc",nv),("qfrc_smooth",nv),("qfrc_constraint",nv),("M",d["nC"]),("xpos",3*nb),("xipos",3*nb),("xmat",9*nb),("ximat",9*nb),("tree_awake",nj))}
    if arrays["tree_awake"] != [1]*nj: raise ValueError("awake integration trees required")
    time = decoded_bits([packet.get("time")], [packet.get("timeBits")], 1)[0]
    if time < 0: raise ValueError("nonnegative integration time required")
    outputs = None
    if phase == "implicit":
        if not isinstance(packet.get("outputs"), dict) or not isinstance(packet.get("outputBits"), dict): raise ValueError("complete integration outputs required")
        outputs = {key: decoded_bits(packet["outputs"].get(key),packet["outputBits"].get(key),size) for key,size in (("qpos",nq),("qvel",nv),("qacc_warmstart",nv),("qDeriv",d["nD"]),("qH",d["nC"]),("qHDiagInv",nv))}
    elif packet.get("outputs") is not None or packet.get("outputBits") is not None:
        raise ValueError("preintegration packet cannot claim outputs")
    return dict(model=floats, arrays=arrays, options=decoded_options, time=time, outputs=outputs)


def named_phase(event, substep, name):
    if not isinstance(event, dict) or type(substep) is not int or not 0 <= substep < 4:
        raise ValueError("bounded integration substep required")
    steps = event.get("engineStep2Phases")
    if not isinstance(steps, list) or len(steps) > 4 or substep >= len(steps):
        raise ValueError("complete integration substep phases required")
    phases = steps[substep]
    if not isinstance(phases, list) or any(not isinstance(p, dict) for p in phases):
        raise ValueError("integration phase objects required")
    owners = [p for p in phases if p.get("phase") == name]
    if len(owners) != 1 or not isinstance(owners[0].get("engine"), dict):
        raise ValueError("unique named integration phase owner required: " + name)
    return owners[0]


def decoded_bits(values, bits, size):
    """Validate both representations, retaining IEEE negative-zero signs."""
    if not isinstance(values, list) or not isinstance(bits, list) or len(values) != size or len(bits) != size:
        raise ValueError("complete integration numeric/bit arrays required")
    decoded = []
    for value, encoded in zip(values, bits):
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError("finite integration numbers required")
        if not isinstance(encoded, str) or not re.fullmatch(r"[0-9a-f]{16}", encoded):
            raise ValueError("canonical binary64 integration bits required")
        operand = struct.unpack(">d", bytes.fromhex(encoded))[0]
        if not math.isfinite(operand) or operand != value:
            raise ValueError("integration bit/value disagreement")
        decoded.append(operand)
    return decoded
