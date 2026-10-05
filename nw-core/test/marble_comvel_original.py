"""Complete actual-original mj_comVel on owned, identical finite operands.

This diagnostic calls the original public routine. The scalar reconstruction
is independently checked against complete original outputs; it is not an
original private intermediate capture or uninterrupted trajectory acceptance.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

from marble_cone_update_oracle import Reader
from marble_inertia_original import OriginalInertia
from marble_primal_eval_oracle import ORIGINAL_EVAL_OFFSET, REFERENCE_SHA256, DlInfo
from marble_qcqp_trace import validate_runtime_pair

OFFSET = 0x60110
INPUTS = ("qvel", "cdof")
OUTPUTS = ("cvel", "cdof_dot")
TOPOLOGY = ("body_parentid", "body_dofadr", "body_dofnum", "dof_jntid",
            "jnt_type", "jnt_dofadr")
JOINT_WIDTH = (6, 3, 1, 1)
LAYOUTS = (
    '<mujoco><worldbody><body><freejoint/><geom size=".1"/></body></worldbody></mujoco>',
    '<mujoco><worldbody><body><freejoint/><geom size=".1"/></body><body><freejoint/><geom size=".1"/></body><body><freejoint/><geom size=".1"/></body></worldbody></mujoco>',
    '<mujoco><worldbody><body><freejoint/><geom size=".1"/><body pos="0 0 1"><joint type="hinge"/><geom size=".1"/></body></body></worldbody></mujoco>',
    '<mujoco><worldbody><body><joint type="ball"/><geom size=".1"/><body pos="0 0 1"><joint type="slide"/><geom size=".1"/><body pos="1 0 0"><geom size=".1"/></body></body></body></worldbody></mujoco>',
    '<mujoco><worldbody><body><joint type="hinge" axis="1 0 0"/><joint type="hinge" axis="0 1 0"/><geom size=".1"/><body pos="0 0 1"><joint type="slide" axis="1 0 0"/><geom size=".1"/></body></body></worldbody></mujoco>',
)


def validated_engine(engine):
    if not isinstance(engine, dict) or not isinstance(engine.get("model"), dict) or not isinstance(engine.get("arrays"), dict):
        raise ValueError("complete comVel engine/model/arrays objects required")
    model, arrays = engine["model"], engine["arrays"]
    for name in TOPOLOGY:
        Reader(model.get(name))
        if any(x != int(x) for x in model[name]):
            raise ValueError("integral comVel topology required: " + name)
    Reader(arrays.get("qvel"))
    nb, nv, nj = len(model["body_parentid"]), len(arrays["qvel"]), len(model["jnt_type"])
    if not 1 <= nb <= 1000 or not 1 <= nv <= 512 or not 1 <= nj <= 512:
        raise ValueError("bounded nonempty comVel dimensions required")
    parents = model["body_parentid"]
    if parents[0] != 0 or any(not 0 <= p < b for b, p in enumerate(parents[1:], 1)):
        raise ValueError("topologically ordered comVel parents required")
    if len(model["body_dofadr"]) != nb or len(model["body_dofnum"]) != nb or model["body_dofnum"][0] != 0:
        raise ValueError("complete body DOF ownership required")
    owned = []
    dof_body = [-1] * nv
    for body, (start, count) in enumerate(zip(model["body_dofadr"], model["body_dofnum"])):
        if not 0 <= count <= 6:
            raise ValueError("bounded Marble body DOF count required")
        if count:
            if start < 0 or start + count > nv:
                raise ValueError("body DOF range out of bounds")
            for dof in range(int(start), int(start + count)):
                owned.append(dof)
                dof_body[dof] = body
        elif start not in (-1, 0):
            raise ValueError("explicit empty body DOF address required")
    if sorted(owned) != list(range(nv)):
        raise ValueError("complete nonoverlapping body DOF ownership required")
    if len(model["dof_jntid"]) != nv or len(model["jnt_dofadr"]) != nj:
        raise ValueError("complete joint/DOF topology required")
    joint_owned = []
    for joint, (kind, start) in enumerate(zip(model["jnt_type"], model["jnt_dofadr"])):
        if not 0 <= kind <= 3:
            raise ValueError("unsupported joint kind")
        width = JOINT_WIDTH[int(kind)]
        if start < 0 or start + width > nv:
            raise ValueError("joint DOF range out of bounds")
        indices = list(range(int(start), int(start + width)))
        if any(model["dof_jntid"][dof] != joint for dof in indices) or len({dof_body[dof] for dof in indices}) != 1:
            raise ValueError("complete contiguous single-body joint ownership required")
        if kind == 0 and start != model["body_dofadr"][dof_body[int(start)]]:
            raise ValueError("free joint must begin its body DOFs")
        joint_owned.extend(indices)
    if sorted(joint_owned) != list(range(nv)):
        raise ValueError("complete nonoverlapping joint DOF ownership required")
    options = model.get("options")
    if not isinstance(options, dict):
        raise ValueError("explicit comVel options required")
    for flag in ("enableflags", "disableflags"):
        value = options.get(flag)
        if type(value) is not int or not 0 <= value <= 2147483647:
            raise ValueError("explicit bounded comVel flags required")
    if options["enableflags"] & 16:
        raise ValueError("sleep-enabled comVel is not qualified")
    if type(model.get("disableflags")) is not int or model["disableflags"] != options["disableflags"]:
        raise ValueError("inconsistent duplicate comVel disable flags")
    for name, width in (("qvel", nv), ("cdof", 6 * nv), ("cvel", 6 * nb), ("cdof_dot", 6 * nv)):
        Reader(arrays.get(name))
        if len(arrays[name]) != width:
            raise ValueError("complete comVel array required: " + name)
    return nb, nv, nj


def selected_inputs(trace):
    if not isinstance(trace, dict) or not isinstance(trace.get("events"), list):
        raise ValueError("comVel trace needs events array")
    rows = []
    for event_index, event in enumerate(trace["events"]):
        if not isinstance(event, dict):
            raise ValueError("comVel event must be an object")
        phases = event.get("engineStep1Phases", [])
        if not isinstance(phases, list) or len(phases) > 4:
            raise ValueError("bounded comVel substep array required")
        for substep, checkpoints in enumerate(phases):
            if not isinstance(checkpoints, list) or any(not isinstance(p, dict) for p in checkpoints):
                raise ValueError("comVel checkpoints must be objects in an array")
            owners = {name: [p.get("engine") for p in checkpoints if p.get("phase") == name]
                      for name in ("probe_input", "probe_comVel")}
            if not any(owners.values()):
                continue
            if any(len(v) != 1 for v in owners.values()):
                raise ValueError("unique named before/after comVel owners required")
            before, after = owners["probe_input"][0], owners["probe_comVel"][0]
            validated_engine(before)
            validated_engine(after)
            if before["model"] != after["model"] or any(before["arrays"][f] != after["arrays"][f] for f in INPUTS):
                raise ValueError("comVel input operands mutated across captured call")
            rows.append(dict(event=event_index, substep=substep, engine=before,
                             captured={f: after["arrays"][f] for f in OUTPUTS}))
    if not rows:
        raise ValueError("no complete named comVel boundaries")
    return rows


class OriginalComVel:
    def __init__(self, path):
        self.guard = OriginalInertia(path)
        anchor = self.guard.anchor
        base = ctypes.cast(anchor.routine, ctypes.c_void_p).value - ORIGINAL_EVAL_OFFSET
        self.routine = anchor.library.mj_comVel
        address = ctypes.cast(self.routine, ctypes.c_void_p).value
        dladdr = ctypes.CDLL(None).dladdr
        dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
        dladdr.restype = ctypes.c_int
        info = DlInfo()
        if address != base + OFFSET or not dladdr(address, ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve() != anchor.path:
            raise ValueError("original comVel symbol/image/address differs")
        self.routine.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.routine.restype = None

    def evaluate(self, model, data, engine):
        nb, nv, nj = validated_engine(engine)
        m, a = engine["model"], engine["arrays"]
        if (model.nbody, model.nv, model.njnt) != (nb, nv, nj):
            raise ValueError("owned original comVel model dimensions differ")
        for name in TOPOLOGY:
            if getattr(model, name).tolist() != m[name]:
                raise ValueError("owned original comVel topology differs: " + name)
        expected_body = [b for b in range(nb) for _ in range(int(m["body_dofnum"][b]))]
        if model.dof_bodyid.tolist() != expected_body:
            raise ValueError("owned original comVel DOF bodies differ")
        model.opt.enableflags = m["options"]["enableflags"]
        model.opt.disableflags = m["options"]["disableflags"]
        for field in INPUTS + OUTPUTS:
            target = getattr(data, field).ravel()
            if target.size != len(a[field]):
                raise ValueError("owned comVel data shape differs")
            target[:] = a[field]
        if any(getattr(data, f).ravel().tolist() != a[f] for f in INPUTS + OUTPUTS):
            raise ValueError("owned original comVel input copy differs")
        self.routine(ctypes.c_void_p(int(model._address)), ctypes.c_void_p(int(data._address)))
        result = {f: getattr(data, f).ravel().tolist() for f in OUTPUTS}
        for values in result.values():
            Reader(values)
        if any(getattr(data, f).ravel().tolist() != a[f] for f in INPUTS):
            raise ValueError("original comVel mutated input arrays")
        return result


def reconstruct(engine):
    nb, nv, _ = validated_engine(engine)
    if not callable(getattr(math, "fma", None)):
        raise ValueError("requires correctly rounded fma")
    fma = math.fma
    m, a = engine["model"], engine["arrays"]
    cvel = [0.] * (6 * nb)
    derivatives = [0.] * (6 * nv)

    def cross(v, axis):
        return [fma(-v[2], axis[1], v[1] * axis[2]),
                fma(v[2], axis[0], (-v[0]) * axis[2]),
                fma(-v[1], axis[0], v[0] * axis[1]),
                fma(-v[2], axis[4], v[1] * axis[5]) + fma(-v[5], axis[1], v[4] * axis[2]),
                fma(v[2], axis[3], (-v[0]) * axis[5]) + fma(v[5], axis[0], (-v[3]) * axis[2]),
                fma(-v[1], axis[3], v[0] * axis[4]) + fma(-v[4], axis[0], v[3] * axis[1])]

    def increment(velocity, start, count):
        product = [0.] * 6
        for dof in range(start, start + count):
            speed = a["qvel"][dof]
            if speed != 0.:
                for component in range(6):
                    product[component] = fma(a["cdof"][6 * dof + component], speed, product[component])
        return [velocity[c] + product[c] for c in range(6)]

    for body in range(1, nb):
        parent = int(m["body_parentid"][body])
        velocity = cvel[6 * parent:6 * parent + 6]
        start, count = int(m["body_dofadr"][body]), int(m["body_dofnum"][body])
        local = 0
        while local < count:
            dof = start + local
            kind = int(m["jnt_type"][int(m["dof_jntid"][dof])])
            if kind == 0:
                velocity = increment(velocity, dof, 3)
                local += 3
                dof += 3
                kind = 1
            width = 3 if kind == 1 else 1
            for axis in range(width):
                index = dof + axis
                derivatives[6 * index:6 * index + 6] = cross(velocity, a["cdof"][6 * index:6 * index + 6])
            if width == 3:
                velocity = increment(velocity, dof, 3)
            else:
                # Original single-axis path uses a rounded product followed by
                # a separate add, unlike the grouped three-DOF FMA accumulator.
                velocity = [velocity[c] + a["cdof"][6 * dof + c] * a["qvel"][dof] for c in range(6)]
            local += width
        cvel[6 * body:6 * body + 6] = velocity
    result = dict(cvel=cvel, cdof_dot=derivatives)
    for values in result.values():
        Reader(values)
    return result


def compact(engine):
    return dict(model={f: engine["model"][f] for f in TOPOLOGY + ("options", "disableflags")},
                arrays={f: engine["arrays"][f] for f in INPUTS + OUTPUTS})


def bit_vectors(output):
    return {field: [struct.pack("!d", value).hex() for value in values] for field, values in output.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--reference-library", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--golden", action="store_true")
    args = parser.parse_args()
    trace, control = json.loads(args.trace.read_text()), json.loads(args.control.read_text())
    validate_runtime_pair(trace, control)
    rows = selected_inputs(trace)  # Validate every packet before any native call.
    original = OriginalComVel(args.reference_library)
    import mujoco
    from marble_source_play_trace import native_mujoco_provenance
    native = native_mujoco_provenance(mujoco)
    if native["activeEngineLibrary"]["sha256"] != REFERENCE_SHA256 or Path(native["activeEngineLibrary"]["path"]).resolve() != original.guard.anchor.path:
        raise ValueError("owned models must come from the exact original wheel")
    sys.path.insert(0, str(args.source_root.resolve()))
    from neural_workshop import marblemaze as source
    from marble_source_capture import float32_abi_tray
    sim = source.Simulation(float32_abi_tray(source.deal(trace["rung"], seed=trace["boardSeed"])))
    sim._ensure_engine()
    counts = dict(boundaries=len(rows), differentBoundaries=0, differentValues=0,
                  cvelDifferentBoundaries=0, cdofDotDifferentBoundaries=0,
                  modelDifferentBoundaries=0, modelDifferentValues=0)
    boundaries = []
    for row in rows:
        actual = original.evaluate(sim._model, sim._data, row["engine"])
        modeled = reconstruct(row["engine"])
        differences, model_differences = {}, {}
        for field in OUTPUTS:
            d = [dict(index=i, original=x, browser=y) for i, (x, y) in enumerate(zip(actual[field], row["captured"][field])) if x != y]
            md = [dict(index=i, original=x, model=y) for i, (x, y) in enumerate(zip(actual[field], modeled[field])) if struct.pack("!d", x) != struct.pack("!d", y)]
            if d:
                differences[field] = d
            if md:
                model_differences[field] = md
        counts["differentBoundaries"] += bool(differences)
        counts["differentValues"] += sum(len(v) for v in differences.values())
        counts["cvelDifferentBoundaries"] += "cvel" in differences
        counts["cdofDotDifferentBoundaries"] += "cdof_dot" in differences
        counts["modelDifferentBoundaries"] += bool(model_differences)
        counts["modelDifferentValues"] += sum(len(v) for v in model_differences.values())
        boundaries.append(dict(event=row["event"], substep=row["substep"], input=compact(row["engine"]),
                               actualOriginal=actual, actualOriginalBits=bit_vectors(actual),
                               captured=row["captured"], differences=differences, modelDifferences=model_differences))
    if args.golden:
        models = [mujoco.MjModel.from_xml_string(xml) for xml in LAYOUTS]
        data = [mujoco.MjData(m) for m in models]

        def emit(engine, kind, label, layout):
            actual = original.evaluate(models[layout], data[layout], engine)
            modeled = reconstruct(engine)
            if bit_vectors(actual) != bit_vectors(modeled):
                raise ValueError("complete comVel model does not match actual original bits: " + label)
            print(json.dumps(dict(kind=kind, label=label, layout=layout, xml=LAYOUTS[layout],
                                  input=compact(engine), referenceSha256=REFERENCE_SHA256,
                                  expected=actual, expectedBits=bit_vectors(actual)), allow_nan=False))

        for row in rows:
            emit(row["engine"], "captured", f"event{row['event']}-step{row['substep']}", 1)
        rng = random.Random(OFFSET)
        for case in range(1000):
            layout = case % len(LAYOUTS)
            model, d = models[layout], data[layout]
            draw = lambda: math.ldexp(rng.uniform(-2., 2.), rng.randrange(-12, 13))
            arrays = {f: [draw() for _ in range(getattr(d, f).size)] for f in INPUTS + OUTPUTS}
            if case % 7 == 0:
                arrays["qvel"] = [-0. if j % 2 else 0. for j in range(model.nv)]
            if case % 11 == 0:
                arrays["cdof"] = [-0. if j % 2 else 0. for j in range(6 * model.nv)]
            flags = 128 if case % 5 == 0 else 0
            m = {f: getattr(model, f).tolist() for f in TOPOLOGY}
            m.update(disableflags=flags, options=dict(enableflags=0, disableflags=flags))
            emit(dict(model=m, arrays=arrays), "synthetic", f"synthetic{case}", layout)
        return
    identity = lambda p: dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    print(json.dumps(dict(schema="neural-workshop.marble-original-comvel.v1", trace=identity(args.trace),
                          control=identity(args.control), runtime=trace["runtimeProvenance"], nativeRuntime=native,
                          referenceSha256=REFERENCE_SHA256, originalSource=identity(Path(source.__file__)),
                          counts=counts, boundaries=boundaries, matchedInputs=True,
                          capturedBrowserZeroSignsQualified=False, originalPrivateIntermediatesCaptured=False,
                          ordinaryTrajectoryAcceptance=False, promoted=False,
                          scope="actual original complete public comVel outputs on owned identical finite sleep-disabled operands; reconstruction separately checked; not original private intermediates or uninterrupted-game acceptance"),
                     indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
