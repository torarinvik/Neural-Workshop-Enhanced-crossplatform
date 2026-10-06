#!/usr/bin/env python3
"""Replay one held-input WASM play trace through the original MuJoCo Simulation.

This deliberately imports the original physics model without importing its
pyglet UI. It therefore works in a headless reference environment while still
using the original board generator and physics wrapper.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import importlib.metadata
import itertools
import json
import math
import os
import sys
from pathlib import Path
import numpy as np

from marble_iteration_trace import compare_iteration_traces, iteration_trace_metadata
from marble_prepare_trace import capture_native_preparations
from marble_eval_trace import capture_native_evaluations
from marble_gauss_trace import capture_native_gauss
from marble_costchange_trace import capture_native_cost
from marble_integrator_readset import named_phase


POSITION_TOLERANCE = 1e-8
VELOCITY_TOLERANCE = 1e-7
QUATERNION_TOLERANCE = 1e-8
ANGULAR_VELOCITY_TOLERANCE = 1e-7
TIME_TOLERANCE = 1e-10
first_exceedance: dict[str, object] | None = None
MUJOCO_API = None
RNE_TRACE_LIBRARY = None
NOSLIP_TRACE_LIBRARY = None
FREE_SOLVE_LIBRARY = None


def loaded_process_images() -> list[Path]:
    """Return canonical native-library paths mapped into this Python process."""
    raw_paths: list[str] = []
    if sys.platform == "darwin":
        dyld = ctypes.CDLL(None)
        dyld._dyld_image_count.restype = ctypes.c_uint32
        dyld._dyld_get_image_name.argtypes = [ctypes.c_uint32]
        dyld._dyld_get_image_name.restype = ctypes.c_char_p
        for index in range(int(dyld._dyld_image_count())):
            value = dyld._dyld_get_image_name(index)
            if value:
                raw_paths.append(os.fsdecode(value))
    elif sys.platform.startswith("linux"):
        maps = Path("/proc/self/maps")
        if maps.is_file():
            for line in maps.read_text().splitlines():
                fields = line.split()
                if fields and fields[-1].startswith("/"):
                    raw_paths.append(fields[-1].removesuffix(" (deleted)"))
    elif sys.platform == "win32":
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        modules = (ctypes.c_void_p * 4096)()
        needed = ctypes.c_ulong()
        process = kernel32.GetCurrentProcess()
        if psapi.EnumProcessModules(process, modules, ctypes.sizeof(modules),
                                    ctypes.byref(needed)):
            count = min(len(modules), needed.value // ctypes.sizeof(ctypes.c_void_p))
            for module in modules[:count]:
                buffer = ctypes.create_unicode_buffer(32768)
                length = psapi.GetModuleFileNameExW(
                    process, module, buffer, len(buffer))
                if length:
                    raw_paths.append(buffer.value)
    return sorted({Path(path).resolve() for path in raw_paths})


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_promoted_artifact(manifest: dict[str, object]) -> dict[str, object]:
    """Resolve current promotion by the live alias, not a date-specific key."""
    current = manifest.get("currentArtifact", {}).get("artifact", {})
    current_hash = current.get("wasmSha256")
    matches = [record["promotedArtifact"]
               for name, record in manifest.items()
               if name.startswith("holeWallVisualClearanceCurrent")
               and isinstance(record, dict)
               and isinstance(record.get("promotedArtifact"), dict)
               and record["promotedArtifact"].get("sha256") == current_hash]
    if len(matches) != 1:
        raise ValueError(
            "physics manifest currentArtifact alias must match exactly one "
            "current Marble clearance record")
    promoted = matches[0]
    if current.get("wasmBytes") != promoted.get("bytes"):
        raise ValueError(
            "physics manifest currentArtifact byte count disagrees with its "
            "promoted Marble artifact")
    return promoted


def wheel_record_matches(distribution, path: Path) -> bool:
    """Check an installed wheel file against its distribution RECORD digest."""
    distribution_root = Path(distribution.locate_file("")).resolve()
    try:
        relative = path.resolve().relative_to(distribution_root).as_posix()
    except ValueError:
        return False
    entry = next((item for item in distribution.files
                  if item.as_posix() == relative), None)
    expected = getattr(entry, "hash", None)
    if expected is None or expected.mode != "sha256":
        return False
    digest = hashlib.sha256(path.read_bytes()).digest()
    actual = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return actual == expected.value


def native_mujoco_provenance(mujoco) -> dict[str, object]:
    """Identify the active MuJoCo wheel, binding, and loaded engine library."""
    import importlib

    distribution = importlib.metadata.distribution("mujoco")
    package_root = Path(mujoco.__file__).resolve().parent
    binding_module = importlib.import_module("mujoco._functions")
    binding_path = Path(binding_module.__file__).resolve()
    images = loaded_process_images()
    engine_matches = [path for path in images
                      if path.name.startswith("libmujoco") and
                      path.suffix.lower() in {".dylib", ".so", ".dll"}]
    engine_matches = [path for path in engine_matches
                      if path.parent == package_root]
    if len(engine_matches) != 1:
        raise RuntimeError(
            "could not prove one active MuJoCo engine library inside the "
            f"imported wheel package; matches={engine_matches}")
    engine_path = engine_matches[0]
    if not hasattr(distribution, "files") or distribution.files is None:
        raise RuntimeError("MuJoCo distribution has no installed wheel file manifest")
    record_file = next((Path(distribution.locate_file(item)).resolve()
                        for item in distribution.files
                        if item.as_posix().endswith(".dist-info/RECORD")), None)
    wheel_file = next((Path(distribution.locate_file(item)).resolve()
                       for item in distribution.files
                       if item.as_posix().endswith(".dist-info/WHEEL")), None)
    if record_file is None or wheel_file is None:
        raise RuntimeError("MuJoCo wheel RECORD/WHEEL metadata is missing")
    engine_record_matches = wheel_record_matches(distribution, engine_path)
    binding_record_matches = wheel_record_matches(distribution, binding_path)
    if not engine_record_matches or not binding_record_matches:
        raise RuntimeError(
            "active MuJoCo library/binding does not match the installed "
            "wheel RECORD digest")
    return {
        "pythonExecutable": str(Path(sys.executable).resolve()),
        "pythonVersion": sys.version,
        "platform": sys.platform,
        "distribution": "mujoco",
        "distributionVersion": distribution.version,
        "mujocoVersion": mujoco.__version__,
        "packageRoot": str(package_root),
        "binding": {
            "path": str(binding_path),
            "sha256": sha256_path(binding_path),
            "wheelRecordMatches": binding_record_matches,
        },
        "activeEngineLibrary": {
            "path": str(engine_path),
            "sha256": sha256_path(engine_path),
            "wheelRecordMatches": engine_record_matches,
            "loadedInProcess": engine_path in images,
        },
        "wheelMetadata": {
            "recordPath": str(record_file),
            "recordSha256": sha256_path(record_file),
            "wheelPath": str(wheel_file),
            "wheelSha256": sha256_path(wheel_file),
        },
    }


def capture_free_joint_solve_probe(sim) -> list[float]:
    """Run the native free-joint implicit solve on an isolated data copy."""
    lib = FREE_SOLVE_LIBRARY
    model_pointer = ctypes.c_void_p(int(sim._model._address))
    source_pointer = ctypes.c_void_p(int(sim._data._address))
    clone = lib.mj_copyData(None, model_pointer, source_pointer)
    if not clone:
        raise RuntimeError("mj_copyData failed for free-joint solve probe")
    result: list[float] = []
    try:
        lib.mjd_smooth_vel(model_pointer, clone, 0)
        for joint, joint_type in enumerate(sim._model.jnt_type):
            if int(joint_type) != 0:  # mjJNT_FREE
                continue
            matrix = (ctypes.c_double * 36)()
            if not lib.mjd_freeMhat(model_pointer, clone, joint,
                                    float(sim._model.opt.timestep), matrix):
                continue
            lu = (ctypes.c_double * 36)(*matrix)
            pivots = (ctypes.c_int * 6)()
            singular = lib.mju_factorLU6(lu, pivots)
            adr = int(sim._model.jnt_dofadr[joint])
            rhs = (ctypes.c_double * 6)(*(
                float(sim._data.qfrc_smooth[adr + i]) +
                float(sim._data.qfrc_constraint[adr + i]) for i in range(6)))
            solution = (ctypes.c_double * 6)()
            if singular:
                lib.mju_solveLU6(solution, lu, rhs, pivots)
            result.extend(matrix)
            result.extend(lu)
            result.extend(pivots)
            result.extend(solution)
    finally:
        lib.mj_deleteData(clone)
    return result


def capture_free_joint_derivative_probe(sim) -> list[float]:
    """Capture native qDeriv and free-bias blocks without mutating live data."""
    lib = FREE_SOLVE_LIBRARY
    if not hasattr(lib, "mjd_freeJoint_qDeriv_probe"):
        return []
    model_pointer = ctypes.c_void_p(int(sim._model._address))
    data_pointer = ctypes.c_void_p(int(sim._data._address))
    result: list[float] = []
    for joint, joint_type in enumerate(sim._model.jnt_type):
        if int(joint_type) != 0:
            continue
        qderiv = (ctypes.c_double * 36)()
        lib.mjd_freeJoint_qDeriv_probe(
            model_pointer, data_pointer, joint, qderiv)
        result.extend(qderiv)
        bias = (ctypes.c_double * 36)()
        lib.mjd_freeBias_vel(model_pointer, data_pointer, joint, bias)
        result.extend(bias)
    return result


def capture_free_bias_intermediate_probe(sim) -> list[float]:
    lib = FREE_SOLVE_LIBRARY
    if not hasattr(lib, "mjd_freeBias_vel_trace"):
        return []
    model_pointer = ctypes.c_void_p(int(sim._model._address))
    data_pointer = ctypes.c_void_p(int(sim._data._address))
    result: list[float] = []
    for joint, joint_type in enumerate(sim._model.jnt_type):
        if int(joint_type) != 0:
            continue
        trace = (ctypes.c_double * 100)()
        lib.mjd_freeBias_vel_trace(model_pointer, data_pointer, joint, trace)
        body = int(sim._model.jnt_bodyid[joint])
        if list(trace[:9]) != np.asarray(sim._data.xmat[body]).ravel().tolist():
            raise AssertionError(
                f"free-bias trace R does not match native xmat body {body}: "
                f"trace={list(trace[:9])}, "
                f"xmat={np.asarray(sim._data.xmat[body]).ravel().tolist()}")
        result.extend(trace)
    return result


def capture_instrumented_rne_trace(sim) -> list[float] | None:
    if RNE_TRACE_LIBRARY is None:
        return None
    model_pointer = ctypes.c_void_p(int(sim._model._address))
    data_pointer = ctypes.c_void_p(int(sim._data._address))
    saved_qfrc_bias = [float(value) for value in sim._data.qfrc_bias]
    trace_size = int(RNE_TRACE_LIBRARY.mj_rne_trace_size(model_pointer))
    trace = (ctypes.c_double * trace_size)()
    RNE_TRACE_LIBRARY.mj_rne_trace(model_pointer, data_pointer, trace)
    sim._data.qfrc_bias[:] = saved_qfrc_bias
    return list(trace)


def compare_compiled_rne_traces(native_trace: list[float], wasm_trace: list[float],
                                body_count: int, nv: int, label: str,
                                native_engine: dict[str, object] | None = None,
                                wasm_engine: dict[str, object] | None = None) -> None:
    trace_length = 36*body_count + 13*nv
    if len(native_trace) != len(wasm_trace) or len(native_trace) != trace_length:
        raise AssertionError(
            f"{label} RNE trace lengths differ: native={len(native_trace)}, "
            f"WASM={len(wasm_trace)}, expected={trace_length}")
    stages = (
        ("cacc", 0), ("inertial_acceleration", 6),
        ("inertial_velocity", 12), ("cross_force", 18),
        ("body_force_before_reverse", 24),
        ("body_force_after_reverse", 30),
    )
    summaries = {}
    for name, offset in stages:
        start, end = offset, 36*body_count
        indices = [body*36 + offset + component
                   for body in range(body_count) for component in range(6)]
        deltas = [(index, native_trace[index], wasm_trace[index],
                   abs(native_trace[index] - wasm_trace[index]))
                  for index in indices]
        differing = [item for item in deltas if item[3] != 0]
        summaries[name] = {
            "differentCount": len(differing),
            "maxAbs": max((item[3] for item in differing), default=0.0),
            "first": [[item[0], item[1], item[2]] for item in differing[:4]],
        }
    qfrc_start = 36 * body_count
    projection_start = qfrc_start + nv
    qfrc_differences = [
        (index, native_trace[qfrc_start + index], wasm_trace[qfrc_start + index])
        for index in range(nv)
        if native_trace[qfrc_start + index] != wasm_trace[qfrc_start + index]
    ]
    summaries["qfrc_bias"] = {
        "differentCount": len(qfrc_differences),
        "maxAbs": max((abs(item[1] - item[2]) for item in qfrc_differences),
                      default=0.0),
        "first": [list(item) for item in qfrc_differences[:4]],
    }
    print(f"COMPILED RNE TRACE PARITY {label}: " +
          json.dumps(summaries, sort_keys=True))
    if native_engine is not None and wasm_engine is not None:
        differing = [body * 36 + 12 + component
                     for body in range(body_count)
                     for component in range(6)
                     if native_trace[body * 36 + 12 + component] !=
                     wasm_trace[body * 36 + 12 + component]]
        if differing:
            trace_index = differing[0]
            body, component = divmod(trace_index, 36)
            component = (trace_index - body * 36 - 12)
            details = {}
            for backend, engine in (("native", native_engine),
                                    ("wasm", wasm_engine)):
                arrays = engine["arrays"]
                inertial = arrays["cinert"][body * 10:body * 10 + 10]
                velocity = arrays["cvel"][body * 6:body * 6 + 6]
                formula_terms = {
                    0: ((inertial[0], velocity[0]), (inertial[3], velocity[1]),
                        (inertial[4], velocity[2]), (-inertial[8], velocity[4]),
                        (inertial[7], velocity[5])),
                    1: ((inertial[3], velocity[0]), (inertial[1], velocity[1]),
                        (inertial[5], velocity[2]), (inertial[8], velocity[3]),
                        (-inertial[6], velocity[5])),
                    2: ((inertial[4], velocity[0]), (inertial[5], velocity[1]),
                        (inertial[2], velocity[2]), (-inertial[7], velocity[3]),
                        (inertial[6], velocity[4])),
                    3: ((inertial[8], velocity[1]), (-inertial[7], velocity[2]),
                        (inertial[9], velocity[3])),
                    4: ((inertial[6], velocity[2]), (-inertial[8], velocity[0]),
                        (inertial[9], velocity[4])),
                    5: ((inertial[7], velocity[0]), (-inertial[6], velocity[1]),
                        (inertial[9], velocity[5])),
                }[component]
                details[backend] = {
                    "inertia": inertial,
                    "velocity": velocity,
                    "terms": [list(term) for term in formula_terms],
                }
            details["body"] = body
            details["component"] = component
            details["nativeLocal"] = native_trace[trace_index]
            details["wasmLocal"] = wasm_trace[trace_index]
            details["operandsMatch"] = all(
                details["native"][key] == details["wasm"][key]
                for key in ("inertia", "velocity"))
            print(f"FIRST RNE VELOCITY-PRODUCT OPERANDS {label}: " +
                  json.dumps(details, sort_keys=True))
        acceleration_differences = [
            body * 36 + 6 + component
            for body in range(body_count)
            for component in range(6)
            if native_trace[body * 36 + 6 + component] !=
            wasm_trace[body * 36 + 6 + component]
        ]
        if acceleration_differences:
            trace_index = acceleration_differences[0]
            body, slot = divmod(trace_index, 36)
            component = slot - 6
            details = {}
            for backend, engine, trace_values in (
                    ("native", native_engine, native_trace),
                    ("wasm", wasm_engine, wasm_trace)):
                inertia = engine["arrays"]["cinert"][body * 10:body * 10 + 10]
                acceleration = trace_values[body * 36:body * 36 + 6]
                formula_terms = {
                    0: ((inertia[0], acceleration[0]), (inertia[3], acceleration[1]),
                        (inertia[4], acceleration[2]), (-inertia[8], acceleration[4]),
                        (inertia[7], acceleration[5])),
                    1: ((inertia[3], acceleration[0]), (inertia[1], acceleration[1]),
                        (inertia[5], acceleration[2]), (inertia[8], acceleration[3]),
                        (-inertia[6], acceleration[5])),
                    2: ((inertia[4], acceleration[0]), (inertia[5], acceleration[1]),
                        (inertia[2], acceleration[2]), (-inertia[7], acceleration[3]),
                        (inertia[6], acceleration[4])),
                    3: ((inertia[8], acceleration[1]), (-inertia[7], acceleration[2]),
                        (inertia[9], acceleration[3])),
                    4: ((inertia[6], acceleration[2]), (-inertia[8], acceleration[0]),
                        (inertia[9], acceleration[4])),
                    5: ((inertia[7], acceleration[0]), (-inertia[6], acceleration[1]),
                        (inertia[9], acceleration[5])),
                }[component]
                products = [left * right for left, right in formula_terms]
                details[backend] = {
                    "inertia": inertia,
                    "acceleration": acceleration,
                    "terms": [list(term) for term in formula_terms],
                    "roundedProducts": products,
                    "leftToRightResult": sum(products),
                    "localResult": trace_values[trace_index],
                }
            details["body"] = body
            details["component"] = component
            details["operandsMatch"] = (
                details["native"]["inertia"] == details["wasm"]["inertia"] and
                details["native"]["acceleration"] == details["wasm"]["acceleration"]
            )
            print(f"FIRST RNE ACCELERATION-PRODUCT OPERANDS {label}: " +
                  json.dumps(details, sort_keys=True))


def _dense_efc_ar(data, model) -> list[float] | None:
    nefc = int(data.nefc)
    if not MUJOCO_API.mj_isSparse(model):
        values = data.efc_AR
        if len(values) < nefc * nefc:
            return None
        return [float(value) for value in values[:nefc * nefc]]
    result = [0.0] * (nefc * nefc)
    rowadr = data.efc_AR_rowadr
    rownnz = data.efc_AR_rownnz
    colind = data.efc_AR_colind
    values = data.efc_AR
    for row in range(nefc):
        adr = int(rowadr[row])
        nnz = int(rownnz[row])
        if adr < 0 or nnz < 0 or adr + nnz > len(values) or adr + nnz > len(colind):
            return None
        for index in range(nnz):
            column = int(colind[adr + index])
            if 0 <= column < nefc:
                result[row * nefc + column] = float(values[adr + index])
    return result


def capture_native_noslip_input_states() -> list[dict[str, object]]:
    """Copy every island's global operands and row map at no-slip entry."""
    if RNE_TRACE_LIBRARY is None or not hasattr(
            RNE_TRACE_LIBRARY, "mj_noslip_input_trace_size"):
        return []
    size = int(RNE_TRACE_LIBRARY.mj_noslip_input_trace_size())
    if size < 4:
        return []
    values = (ctypes.c_double * size)()
    RNE_TRACE_LIBRARY.mj_noslip_input_trace_copy(values)
    flat = list(values)
    states = []
    offset = 0
    while offset + 4 <= size:
        island, island_nefc, nefc = map(int, flat[offset:offset + 3])
        ar_available = bool(flat[offset + 3])
        offset += 4
        required = island_nefc + 3 * nefc + (nefc * nefc if ar_available else 0)
        if min(island_nefc, nefc) < 0 or offset + required > size:
            break
        efclist = [int(value) for value in flat[offset:offset + island_nefc]]
        offset += island_nefc
        b = flat[offset:offset + nefc]
        offset += nefc
        regularizer = flat[offset:offset + nefc]
        offset += nefc
        force = flat[offset:offset + nefc]
        offset += nefc
        matrix = flat[offset:offset + nefc * nefc] if ar_available else []
        offset += nefc * nefc if ar_available else 0
        states.append({"island": island, "islandNefc": island_nefc,
                       "efclist": efclist, "nefc": nefc, "b": b,
                       "R": regularizer, "force": force, "AR": matrix,
                       "arAvailable": ar_available})
    return states


def capture_native_newton_trace(model, data) -> dict[str, object]:
    if RNE_TRACE_LIBRARY is None:
        raise RuntimeError("native Newton diagnostic library is not loaded")
    model_pointer = ctypes.c_void_p(int(model._address))
    data_pointer = ctypes.c_void_p(int(data._address))
    RNE_TRACE_LIBRARY.mj_solver_trace_run(model_pointer, data_pointer)
    residual_input_states = capture_native_noslip_input_states()
    residual_input_state = residual_input_states[0] if residual_input_states else None
    size = int(RNE_TRACE_LIBRARY.mj_solver_trace_size())
    trace = (ctypes.c_double * size)()
    RNE_TRACE_LIBRARY.mj_solver_trace_copy(trace)
    sparse_size = int(RNE_TRACE_LIBRARY.mj_solver_sparse_input_size())
    sparse_input = (ctypes.c_double * sparse_size)()
    RNE_TRACE_LIBRARY.mj_solver_sparse_input_copy(sparse_input)
    constraint_size = int(
        RNE_TRACE_LIBRARY.mj_solver_constraint_input_size())
    constraint_input = (ctypes.c_double * constraint_size)()
    RNE_TRACE_LIBRARY.mj_solver_constraint_input_copy(constraint_input)
    # Older diagnostic MuJoCo builds predate the optional iteration-level
    # recorder.  Keep those libraries usable: the other solver traces still
    # provide the no-slip update/cost evidence, and an absent optional export
    # should decode as an empty capture rather than aborting library setup.
    if hasattr(RNE_TRACE_LIBRARY,
               "mj_solver_constraint_iteration_trace_size"):
        iteration_size = int(
            RNE_TRACE_LIBRARY.mj_solver_constraint_iteration_trace_size())
        iteration_trace = (ctypes.c_double * iteration_size)()
        RNE_TRACE_LIBRARY.mj_solver_constraint_iteration_trace_copy(
            iteration_trace)
    else:
        iteration_trace = ()
    chol_size = int(RNE_TRACE_LIBRARY.mj_solver_chol_solve_size())
    chol_solve_input = (ctypes.c_double * chol_size)()
    RNE_TRACE_LIBRARY.mj_solver_chol_solve_copy(chol_solve_input)
    hessian_size = int(RNE_TRACE_LIBRARY.mj_solver_hessian_size())
    hessian_trace = (ctypes.c_double * hessian_size)()
    RNE_TRACE_LIBRARY.mj_solver_hessian_copy(hessian_trace)
    cone_size = int(RNE_TRACE_LIBRARY.mj_solver_cone_trace_size())
    cone_trace = (ctypes.c_double * cone_size)()
    RNE_TRACE_LIBRARY.mj_solver_cone_trace_copy(cone_trace)
    solve_stage_size = int(
        RNE_TRACE_LIBRARY.mj_solver_dense_solve_trace_size())
    solve_stages = (ctypes.c_double * solve_stage_size)()
    RNE_TRACE_LIBRARY.mj_solver_dense_solve_trace_copy(solve_stages)
    constraint_update_size = int(
        RNE_TRACE_LIBRARY.mj_constraint_update_trace_size())
    constraint_updates = (ctypes.c_double * constraint_update_size)()
    RNE_TRACE_LIBRARY.mj_constraint_update_trace_copy(constraint_updates)
    state_size = int(RNE_TRACE_LIBRARY.mj_constraint_state_trace_size())
    state_trace = (ctypes.c_double * state_size)()
    RNE_TRACE_LIBRARY.mj_constraint_state_trace_copy(state_trace)
    preparation_capture = capture_native_preparations(RNE_TRACE_LIBRARY)
    return {**iteration_trace_metadata(RNE_TRACE_LIBRARY),
            **preparation_capture,
            **capture_native_evaluations(RNE_TRACE_LIBRARY, preparation_capture),
            **capture_native_gauss(RNE_TRACE_LIBRARY),
            **capture_native_cost(RNE_TRACE_LIBRARY),
            "records": int(RNE_TRACE_LIBRARY.mj_solver_trace_records()),
            "modelDisableFlags": int(model.opt.disableflags),
            "modelSolver": int(model.opt.solver),
            "dataConstraintCount": int(data.nefc),
            "values": list(trace), "sparseInput": list(sparse_input),
            "constraintInput": list(constraint_input),
            "constraintIterationTrace": list(iteration_trace),
            "residualInputState": residual_input_state,
            "residualInputStates": residual_input_states,
            "cholSolveInput": list(chol_solve_input),
            "hessianTrace": list(hessian_trace),
            "coneTrace": list(cone_trace),
            "denseSolveStages": list(solve_stages),
            "constraintUpdateTrace": list(constraint_updates),
            "constraintStateTrace": list(state_trace)}


def newton_record_payload(label: int, values: list[float]) -> dict[str, object]:
    """Decode the three generic trace slots using the record's label."""
    slots = values[6:9]
    if 3000 <= label < 4000:
        names = ("objective_cost", "first_derivative", "second_derivative")
        kind = "line_search_result"
    elif 4000 <= label < 6000:
        names = ("objective_cost", "first_derivative", "second_derivative")
        kind = "constraint_accumulator"
    elif 600000 <= label < 700000:
        names = ("normal_component", "tangential_squared", "contact_id")
        kind = "elliptic_N_Tsqr"
    elif 700000 <= label < 800000:
        names = ("operand_value", "constraint_row", "contact_id")
        kind = "elliptic_operand"
    elif 25000 <= label < 30000 and label % 10 in (0, 1, 2, 3):
        names = {
            0: ("U_tangent", "V_tangent", "rounded_U_squared"),
            1: ("rounded_UV_product", "rounded_V_squared", "UU_partial_sum"),
            2: ("UV_partial_sum", "VV_partial_sum", "reserved"),
            3: ("Jaref_tangent", "Jv_tangent", "friction"),
        }[label % 10]
        kind = "primal_prepare_tangent_accumulation"
    elif 910000 <= label < 970000:
        probe = (label-910000) % 1000
        names = {
            0: ("quad_linear_initial", "quad_quadratic_initial", "DJ_normal"),
            1: ("quad_linear_before", "quad_quadratic_before", "DJ_tangent"),
            2: ("DJ_tangent", "rounded_linear_increment", "rounded_quadratic_increment"),
            3: ("quad_linear_after", "quad_quadratic_after", "DJ_tangent"),
            4: ("Jv_tangent", "D_tangent", "Jaref_tangent"),
        }.get(0 if probe == 0 else probe % 10, ("value0", "value1", "value2"))
        kind = "primal_prepare_bottom_polynomial"
    elif 800000 <= label < 9000000:
        probe = label % 10
        names_by_probe = {
            1: ("tangent_norm", "top_zone_margin", "reserved"),
            2: ("bottom_zone_margin", "quad_linear", "quad_quadratic"),
            3: ("first_derivative_before", "first_derivative_increment",
                "second_derivative_after_increment"),
            4: ("first_derivative_after", "second_derivative_after", "reserved"),
            5: ("top_zone_margin", "top_zone_margin_derivative",
                "first_derivative_increment"),
            6: ("second_derivative_increment",
                "first_derivative_before", "second_derivative_before"),
            7: ("tangent_norm_derivative", "tangent_norm_second_derivative",
                "reserved"),
            8: ("first_derivative_after", "second_derivative_after", "reserved"),
        }
        names = names_by_probe.get(probe, ("value0", "value1", "value2"))
        kind = "elliptic_zone_probe"
    elif 9000000 <= label < 9100000:
        names_by_probe = {
            1: ("normal_component", "tangential_squared", "initial_tangent_norm"),
            2: ("tangent_norm", "top_zone_margin", "bottom_zone_margin"),
            9: ("elliptic_cost_delta", "initial_zone", "alpha_zone"),
        }
        names = names_by_probe.get(label % 10,
                                   ("value0", "value1", "value2"))
        kind = "elliptic_cost_intermediate"
    elif 9100000 <= label < 9200000:
        names_by_probe = {
            1: ("objective_cost_before", "constraint_row", "constraint_kind"),
            2: ("objective_cost_after", "constraint_row", "constraint_kind"),
            3: ("row_cost_delta", "constraint_row", "reserved"),
            4: ("objective_cost_after_delta", "constraint_row", "reserved"),
        }
        names = names_by_probe.get(label % 10,
                                   ("value0", "value1", "value2"))
        kind = "primal_eval_cost_row"
    else:
        names = ("cost_slot", "derivative0_slot", "derivative1_slot")
        kind = "generic_newton_record"
    return {"kind": kind, "payload": dict(zip(names, slots))}


def elliptic_cost_operand_pair(label: int, native_records: list[dict[str, object]],
                               wasm_records: list[dict[str, object]]) \
        -> dict[str, object] | None:
    """Join U0/alpha/V0 and related operands for an elliptic-cost probe label."""
    if not 9000000 <= label < 9100000 or label % 10000 != 1:
        return None
    evaluation = (label - 9000000) // 10000
    constraint_row = ((label - 9000000) % 10000) // 10
    operand_names = {
        1: "U0",
        2: "V0",
        3: "UU",
        4: "UV",
        5: "VV",
        6: "Dm",
        7: "mu",
    }

    def collect(records):
        matched = {record["field"]: record for record in records
                   if record.get("eval") == evaluation and
                   record.get("row") == constraint_row and
                   record.get("field") in operand_names}
        return {
            "alpha": next((record["alpha"] for record in matched.values()), None),
            "contactId": next((record["contactId"]
                               for record in matched.values()), None),
            "values": {operand_names[field]: record["cost"]
                       for field, record in sorted(matched.items())},
        }

    native = collect(native_records)
    wasm = collect(wasm_records)
    return {
        "evaluation": evaluation,
        "constraintRow": constraint_row,
        "native": native,
        "wasm": wasm,
        "equalInputs": native == wasm,
    }


def decode_noslip_summary(values: list[float]) -> tuple[list[dict[str, object]], str | None]:
    """Decode the variable-width no-slip iteration/state trace."""
    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(values):
        if len(values) - offset < 6:
            return records, f"truncated header at offset {offset}"
        island, iteration, nefc = map(int, values[offset:offset + 3])
        width = 6 + 3 * nefc
        if nefc < 0 or offset + width > len(values):
            return records, (f"invalid record at offset {offset}: nefc={nefc}, "
                             f"remaining={len(values) - offset}")
        rows = []
        cursor = offset + 6
        for _ in range(nefc):
            rows.append({"row": int(values[cursor]), "force": values[cursor + 1],
                         "state": int(values[cursor + 2])})
            cursor += 3
        records.append({"island": island, "iteration": iteration,
                        "nefc": nefc, "improvement": values[offset + 3],
                        "nactive": int(values[offset + 4]),
                        "nchange": int(values[offset + 5]), "rows": rows})
        offset += width
    return records, None


def decode_jaref_trace(values: list[float]) -> tuple[list[dict[str, object]], str | None]:
    """Decode dense Jaref construction operands and its post-subtraction result.

    Each record is [island, nefc, nv, sparse, qacc, efc_aref, J, Jaref].
    This is deliberately a post-operation diagnostic record: it observes the
    operands and result without replacing the solver's arithmetic.
    """
    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(values):
        if len(values) - offset < 4:
            return records, f"truncated header at offset {offset}"
        island, nefc, nv, sparse = map(int, values[offset:offset + 4])
        width = 4 + nv + nefc + nefc * nv + nefc
        if (nefc < 0 or nv < 0 or sparse != 0 or
                offset + width > len(values)):
            return records, (
                f"invalid record at offset {offset}: nefc={nefc}, nv={nv}, "
                f"sparse={sparse}, remaining={len(values) - offset}")
        cursor = offset + 4
        qacc = values[cursor:cursor + nv]
        cursor += nv
        aref = values[cursor:cursor + nefc]
        cursor += nefc
        jacobian = values[cursor:cursor + nefc * nv]
        cursor += nefc * nv
        jaref = values[cursor:cursor + nefc]
        records.append({"island": island, "nefc": nefc, "nv": nv,
                        "sparse": sparse, "qacc": qacc,
                        "aref": aref, "J": jacobian, "Jaref": jaref})
        offset += width
    return records, None


def decode_jaref_update_trace(values: list[float]) -> tuple[list[dict[str, object]], str | None]:
    """Decode the later line-search update ``Jaref += alpha * Jv`` records."""
    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(values):
        if len(values) - offset < 3:
            return records, f"truncated header at offset {offset}"
        island, nefc = map(int, values[offset:offset + 2])
        width = 3 + 3 * nefc
        if nefc < 0 or offset + width > len(values):
            return records, (f"invalid record at offset {offset}: nefc={nefc}, "
                             f"remaining={len(values) - offset}")
        cursor = offset + 3
        before = values[cursor:cursor + nefc]
        cursor += nefc
        direction = values[cursor:cursor + nefc]
        cursor += nefc
        after = values[cursor:cursor + nefc]
        records.append({"island": island, "nefc": nefc,
                        "alpha": values[offset + 2],
                        "before": before, "direction": direction,
                        "after": after})
        offset += width
    return records, None


def decode_jv_trace(values: list[float]) -> tuple[list[dict[str, object]], str | None]:
    """Decode dense ``J * search`` operands and result records."""
    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(values):
        if len(values) - offset < 4:
            return records, f"truncated header at offset {offset}"
        island, nefc, nv, sparse = map(int, values[offset:offset + 4])
        width = 4 + nv + nefc * nv + nefc
        if (nefc < 0 or nv < 0 or sparse != 0 or
                offset + width > len(values)):
            return records, (
                f"invalid record at offset {offset}: nefc={nefc}, nv={nv}, "
                f"sparse={sparse}, remaining={len(values) - offset}")
        cursor = offset + 4
        search = values[cursor:cursor + nv]
        cursor += nv
        jacobian = values[cursor:cursor + nefc * nv]
        cursor += nefc * nv
        jv = values[cursor:cursor + nefc]
        records.append({"island": island, "nefc": nefc, "nv": nv,
                        "sparse": sparse, "search": search,
                        "J": jacobian, "Jv": jv})
        offset += width
    return records, None


def decode_noslip_contacts(values: list[float]) -> tuple[list[dict[str, object]], str | None]:
    """Decode variable-width elliptic-contact updates emitted by no-slip."""
    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(values):
        if len(values) - offset < 6:
            return records, f"truncated header at offset {offset}"
        island, iteration, row, dim, contact_id = map(int, values[offset:offset + 5])
        tangent = dim - 1
        width = 12 + 7 * tangent + tangent * tangent
        if tangent < 0 or offset + width > len(values):
            return records, (f"invalid record at offset {offset}: dim={dim}, "
                             f"remaining={len(values) - offset}")
        cursor = offset + 6
        mu = values[cursor:cursor + 5]
        cursor += 5
        residual = values[cursor:cursor + tangent]
        cursor += tangent
        old_force = values[cursor:cursor + tangent]
        cursor += tangent
        matrix = values[cursor:cursor + tangent * tangent]
        cursor += tangent * tangent
        rhs = values[cursor:cursor + tangent]
        cursor += tangent
        updated_force = values[cursor:cursor + tangent]
        cursor += tangent
        cost_change = values[cursor]
        cursor += 1
        bias = values[cursor:cursor + tangent]
        cursor += tangent
        regularizer = values[cursor:cursor + tangent]
        cursor += tangent
        tangent_force = values[cursor:cursor + tangent]
        cursor += tangent
        records.append({"island": island, "iteration": iteration, "row": row,
                        "dim": dim, "contactId": contact_id,
                        "normal": values[offset + 5], "mu": mu,
                        "residual": residual, "oldForce": old_force,
                        "matrix": matrix, "rhs": rhs,
                        "updatedForce": updated_force, "costChange": cost_change,
                        "bias": bias,
                        "regularizer": regularizer,
                        "tangentForce": tangent_force})
        offset += width
    return records, None


def decode_noslip_steps(values: list[float]) -> tuple[list[dict[str, object]], str | None]:
    """Decode the no-slip reduction/state decision trace."""
    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(values):
        if len(values) - offset < 8:
            return records, f"truncated header at offset {offset}"
        island, iteration, nefc = map(int, values[offset:offset + 3])
        width = 8 + 4 * nefc
        if nefc < 0 or offset + width > len(values):
            return records, (f"invalid record at offset {offset}: nefc={nefc}, "
                             f"remaining={len(values) - offset}")
        rows = []
        cursor = offset + 8
        for _ in range(nefc):
            rows.append({"row": int(values[cursor]),
                         "force": values[cursor + 1],
                         "oldState": int(values[cursor + 2]),
                         "state": int(values[cursor + 3])})
            cursor += 4
        records.append({"island": island, "iteration": iteration,
                        "nefc": nefc,
                        "rawImprovement": values[offset + 3],
                        "scale": values[offset + 4],
                        "improvement": values[offset + 5],
                        "nactive": int(values[offset + 6]),
                        "nchange": int(values[offset + 7]),
                        "rows": rows})
        offset += width
    return records, None


def no_slip_cost_change_probes(values: list[float]) -> list[dict[str, object]]:
    records, error = decode_noslip_contacts(values)
    if error:
        return []
    probes = []
    for record in records:
        dimension = int(record["dim"]) - 1
        old_force = np.asarray(record["oldForce"], dtype=np.float64)
        new_force = np.asarray(record["updatedForce"], dtype=np.float64)
        delta = np.ascontiguousarray(new_force - old_force)
        matrix = np.ascontiguousarray(record["matrix"], dtype=np.float64)
        residual = np.ascontiguousarray(record["residual"], dtype=np.float64)
        quadratic = float(delta @ matrix.reshape((dimension, dimension)) @ delta)
        linear = float(delta @ residual)
        probes.append({"island": record["island"],
                       "iteration": record["iteration"], "row": record["row"],
                       "quadratic": quadratic, "linear": linear,
                       "change": 0.5 * quadratic + linear,
                       "actualChange": record["costChange"]})
    return probes


def first_record_difference(native: list[dict[str, object]],
                            wasm: list[dict[str, object]]) -> dict[str, object] | None:
    """Return the first semantic field mismatch between decoded records."""
    for record_index, (left, right) in enumerate(zip(native, wasm)):
        for field in left:
            if left[field] != right.get(field):
                if (isinstance(left[field], list) and
                        isinstance(right.get(field), list)):
                    left_items = left[field]
                    right_items = right[field]
                    for item_index, (left_item, right_item) in enumerate(
                            zip(left_items, right_items)):
                        if left_item != right_item:
                            if isinstance(left_item, dict) and isinstance(right_item, dict):
                                for item_field, item_value in left_item.items():
                                    if item_value != right_item.get(item_field):
                                        return {"record": record_index,
                                                "field": field,
                                                "item": item_index,
                                                "itemField": item_field,
                                                "native": item_value,
                                                "wasm": right_item.get(item_field)}
                            return {"record": record_index, "field": field,
                                    "item": item_index,
                                    "native": left_item, "wasm": right_item}
                return {"record": record_index, "field": field,
                        "native": left[field], "wasm": right.get(field)}
    if len(native) != len(wasm):
        return {"field": "recordCount", "native": len(native), "wasm": len(wasm)}
    return None


def decoded_record_field_differences(
        native: list[dict[str, object]],
        wasm: list[dict[str, object]]) -> dict[str, object]:
    """Summarize per-field mismatches without hiding later fields in a record."""
    fields = sorted(set().union(*(record.keys() for record in native + wasm)))
    result: dict[str, object] = {}
    for field in fields:
        differences = []
        for record_index, (left, right) in enumerate(zip(native, wasm)):
            a, b = left.get(field), right.get(field)
            if a == b:
                continue
            if isinstance(a, list) and isinstance(b, list):
                items = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
                if items:
                    differences.append({"record": record_index,
                                        "row": left.get("row"),
                                        "contactId": left.get("contactId"),
                                        "items": items[:8],
                                        "differentCount": len(items)})
                elif len(a) != len(b):
                    differences.append({"record": record_index,
                                        "row": left.get("row"),
                                        "contactId": left.get("contactId"),
                                        "lengths": [len(a), len(b)]})
            else:
                differences.append({"record": record_index,
                                    "row": left.get("row"),
                                    "contactId": left.get("contactId"),
                                    "native": a, "wasm": b})
        if differences:
            result[field] = {"differentRecords": len(differences),
                             "first": differences[0],
                             "samples": differences[:4]}
    if len(native) != len(wasm):
        result["recordCount"] = {"native": len(native), "wasm": len(wasm)}
    return result


def first_noslip_active_set_difference(
        native: list[dict[str, object]],
        wasm: list[dict[str, object]]) -> dict[str, object] | None:
    """Report the first discrete no-slip active-count/state mismatch."""
    for record_index, (left, right) in enumerate(zip(native, wasm)):
        for field in ("nactive", "nchange"):
            if left[field] != right[field]:
                return {"record": record_index, "iteration": left["iteration"],
                        "field": field, "native": left[field],
                        "wasm": right[field]}
        for row_index, (left_row, right_row) in enumerate(
                zip(left["rows"], right["rows"])):
            if left_row["state"] != right_row["state"]:
                return {"record": record_index, "iteration": left["iteration"],
                        "row": row_index, "field": "state",
                        "native": left_row["state"],
                        "wasm": right_row["state"]}
    return None


def reconstruct_noslip_iteration1_inputs(
        trace: dict[str, object], island_id: int = 0) -> dict[str, object]:
    """Join neutral entry matrices with the existing post-iteration force trace.

    This deliberately runs after the solver has completed. It does not add
    probes or execute floating-point operations inside the physics kernel.
    """
    states = trace.get("residualInputStates", [])
    state = next((item for item in states
                  if item.get("island") == island_id), None)
    iterations, iteration_error = decode_noslip_summary(
        trace.get("noSlipTrace", []))
    contacts, contact_error = decode_noslip_contacts(
        trace.get("noSlipContactTrace", []))
    after_iter0 = next((item for item in iterations
                        if item.get("island") == island_id and
                        item.get("iteration") == 0), None)
    first_iter1_contact = next((item for item in contacts
                                if item.get("island") == island_id and
                                item.get("iteration") == 1), None)
    if state is None or after_iter0 is None or first_iter1_contact is None:
        return {"available": False, "island": island_id,
                "iterationDecodeError": iteration_error,
                "contactDecodeError": contact_error}
    # Unmapped rows belong to other islands and are unchanged by this island's
    # iter-0 pass, so retain their exact solver-entry forces.
    force = list(state["force"])
    for item in after_iter0["rows"]:
        force[item["row"]] = item["force"]
    complete_force = len(force) == int(state["nefc"])
    row = int(first_iter1_contact["row"])
    tangent_rows = list(range(row + 1, row + int(first_iter1_contact["dim"])))
    return {
        "available": complete_force and bool(state.get("arAvailable")),
        "island": island_id,
        "nefc": int(state["nefc"]),
        "entryB": state["b"],
        "entryR": state["R"],
        "entryAR": state["AR"],
        "forceAfterIteration0": force,
        "completeForce": complete_force,
        "contactRow": row,
        "tangentRows": tangent_rows,
        "recordedIteration1Residual": first_iter1_contact["residual"],
        "recordedIteration1OldForce": first_iter1_contact["oldForce"],
    }


def compare_compiled_newton_traces(native_trace: dict[str, object],
                                   wasm_trace: dict[str, object],
                                   label: str) -> None:
    native_values = native_trace["values"]
    wasm_values = wasm_trace["values"]
    native_count = int(native_trace["records"])
    wasm_count = int(wasm_trace["records"])
    native_sparse = native_trace.get("sparseInput", [])
    wasm_sparse = wasm_trace.get("sparseInput", [])
    sparse_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_sparse, wasm_sparse)) if a != b]
    native_constraint = native_trace.get("constraintInput", [])
    wasm_constraint = wasm_trace.get("constraintInput", [])
    constraint_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_constraint, wasm_constraint)) if a != b]
    constraint_field_differences: dict[str, list[tuple[int, float, float]]] = {}
    if (len(native_constraint) == len(wasm_constraint) and
            len(native_constraint) >= 6 and
            all(native_constraint[i] == wasm_constraint[i]
                for i in range(5))):
        ne, nf, nefc, ncontact = map(int, native_constraint[:4])
        offset = 6  # five integer metadata fields and the scalar cost
        field_ranges = (
            ("efc_D", nefc),
            ("efc_R", nefc),
            ("efc_frictionloss", nf),
            ("Jaref", nefc),
            ("efc_type", nefc),
            ("efc_id", nefc),
            ("efc_state", nefc),
            ("efc_force", nefc),
            ("contact_dim_mu_friction", 7*ncontact),
            ("efc_force_after_constraint_update", nefc),
            ("efc_state_after_constraint_update", nefc),
            ("cost_after_constraint_update", 1),
        )
        for field_name, field_length in field_ranges:
            field_differences = [
                (index - offset, native_constraint[index],
                 wasm_constraint[index])
                for index in range(offset, offset + field_length)
                if native_constraint[index] != wasm_constraint[index]
            ]
            if field_differences:
                constraint_field_differences[field_name] = field_differences
            offset += field_length
        if offset != len(native_constraint):
            constraint_field_differences["layout_length_mismatch"] = [
                (offset, float(offset), float(len(native_constraint)))
            ]
    native_chol = native_trace.get("cholSolveInput", [])
    wasm_chol = wasm_trace.get("cholSolveInput", [])
    chol_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_chol, wasm_chol)) if a != b]
    native_hessian = native_trace.get("hessianTrace", [])
    wasm_hessian = wasm_trace.get("hessianTrace", [])
    hessian_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_hessian, wasm_hessian)) if a != b]
    native_cone = native_trace.get("coneTrace", [])
    wasm_cone = wasm_trace.get("coneTrace", [])
    cone_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_cone, wasm_cone)) if a != b]
    native_solve_stages = native_trace.get("denseSolveStages", [])
    wasm_solve_stages = wasm_trace.get("denseSolveStages", [])
    solve_stage_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_solve_stages, wasm_solve_stages)) if a != b]
    native_updates = native_trace.get("constraintUpdateTrace", [])
    wasm_updates = wasm_trace.get("constraintUpdateTrace", [])
    native_iteration_updates = native_trace.get("constraintIterationTrace", [])
    wasm_iteration_updates = wasm_trace.get("constraintIterationTrace", [])
    iteration_comparison = compare_iteration_traces(native_trace, wasm_trace)
    native_update_records, wasm_update_records = iteration_comparison["records"]
    native_iteration_error, wasm_iteration_error = iteration_comparison["errors"]
    iteration_update_first = iteration_comparison["firstDifference"]
    native_states = native_trace.get("constraintStateTrace", [])
    wasm_states = wasm_trace.get("constraintStateTrace", [])
    native_noslip = native_trace.get("noSlipTrace", [])
    wasm_noslip = wasm_trace.get("noSlipTrace", [])
    noslip_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_noslip, wasm_noslip)) if a != b]
    native_noslip_contacts = native_trace.get("noSlipContactTrace", [])
    wasm_noslip_contacts = wasm_trace.get("noSlipContactTrace", [])
    native_noslip_steps = native_trace.get("noSlipStepTrace", [])
    wasm_noslip_steps = wasm_trace.get("noSlipStepTrace", [])
    native_jaref = native_trace.get("jarefTrace", [])
    wasm_jaref = wasm_trace.get("jarefTrace", [])
    native_jv = native_trace.get("jvTrace", [])
    wasm_jv = wasm_trace.get("jvTrace", [])
    native_jaref_updates = native_trace.get("jarefUpdateTrace", [])
    wasm_jaref_updates = wasm_trace.get("jarefUpdateTrace", [])
    native_cost_probes = native_trace.get("noSlipCostChangeProbe", [])
    wasm_cost_probes = wasm_trace.get("noSlipCostChangeProbe", [])
    cost_probe_differences = []
    for index, (left, right) in enumerate(zip(native_cost_probes,
                                               wasm_cost_probes)):
        for field in ("quadratic", "linear", "change"):
            if left.get(field) != right.get(field):
                cost_probe_differences.append(
                    (index, field, left.get(field), right.get(field)))
    if len(native_cost_probes) != len(wasm_cost_probes):
        cost_probe_differences.append(
            ("count", "records", len(native_cost_probes),
             len(wasm_cost_probes)))
    native_residual_state = native_trace.get("residualInputState", {})
    wasm_residual_state = wasm_trace.get("residualInputState", {})
    native_residual_states = native_trace.get("residualInputStates", [])
    wasm_residual_states = wasm_trace.get("residualInputStates", [])
    residual_state_differences = []
    for field in ("nefc", "b", "R", "force", "AR", "arAvailable"):
        left = native_residual_state.get(field, [])
        right = wasm_residual_state.get(field, [])
        if isinstance(left, list) and isinstance(right, list):
            residual_state_differences.extend(
                (field, index, a, right[index])
                for index, a in enumerate(left[:len(right)])
                if a != right[index])
        elif left != right:
            residual_state_differences.append((field, 0, left, right))
    noslip_contact_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_noslip_contacts, wasm_noslip_contacts)) if a != b]
    update_fields = ("jar", "D", "R", "frictionloss", "efc_aref",
                     "efc_type", "efc_id", "efc_state_before",
                     "efc_force_before", "contact_dim_mu_friction",
                     "efc_force_after", "efc_state_after", "cost_after",
                     "qfrc_constraint_after")

    def decode_update_calls(values):
        calls = []
        offset = 0
        while offset < len(values):
            if len(values) - offset < 7:
                return calls, {"field": "truncated header", "offset": offset}
            ne, nf, nefc, ncon = map(int, values[offset:offset+4])
            has_cost, nv = int(values[offset+5]), int(values[offset+6])
            sizes = (nefc, nefc, nefc, nf, nefc, nefc, nefc, nefc,
                     nefc, 7*ncon, nefc, nefc, has_cost, nv)
            width = 7 + sum(sizes)
            if min(ne, nf, nefc, ncon, has_cost, nv) < 0 or offset + width > len(values):
                return calls, {"field": "invalid record width", "offset": offset,
                               "header": values[offset:offset+7], "width": width,
                               "remaining": len(values)-offset}
            cursor = offset + 7
            fields = {}
            for field_name, size in zip(update_fields, sizes):
                fields[field_name] = values[cursor:cursor+size]
                cursor += size
            calls.append({"header": values[offset:offset+7], "fields": fields})
            offset += width
        return calls, None

    native_calls, native_update_error = decode_update_calls(native_updates)
    wasm_calls, wasm_update_error = decode_update_calls(wasm_updates)
    update_first = None
    for call_index, (native_call, wasm_call) in enumerate(zip(native_calls, wasm_calls)):
        if native_call["header"] != wasm_call["header"]:
            update_first = {"call": call_index, "field": "header",
                            "native": native_call["header"],
                            "wasm": wasm_call["header"]}
            break
        for field_name in update_fields:
            left = native_call["fields"][field_name]
            right = wasm_call["fields"][field_name]
            differing = [(i, a, b) for i, (a, b) in enumerate(zip(left, right))
                         if a != b]
            if differing or len(left) != len(right):
                update_first = {"call": call_index, "field": field_name,
                                "firstDifferences": differing[:8],
                                "sizes": [len(left), len(right)]}
                break
        if update_first:
            break
    if update_first is None and len(native_calls) != len(wasm_calls):
        update_first = {"field": "call count", "native": len(native_calls),
                        "wasm": len(wasm_calls)}
    native_noslip_records, native_noslip_error = decode_noslip_summary(native_noslip)
    wasm_noslip_records, wasm_noslip_error = decode_noslip_summary(wasm_noslip)
    native_noslip_contact_records, native_noslip_contact_error = (
        decode_noslip_contacts(native_noslip_contacts))
    wasm_noslip_contact_records, wasm_noslip_contact_error = (
        decode_noslip_contacts(wasm_noslip_contacts))
    native_noslip_step_records, native_noslip_step_error = (
        decode_noslip_steps(native_noslip_steps))
    wasm_noslip_step_records, wasm_noslip_step_error = (
        decode_noslip_steps(wasm_noslip_steps))
    native_jaref_records, native_jaref_error = decode_jaref_trace(native_jaref)
    wasm_jaref_records, wasm_jaref_error = decode_jaref_trace(wasm_jaref)
    native_jv_records, native_jv_error = decode_jv_trace(native_jv)
    wasm_jv_records, wasm_jv_error = decode_jv_trace(wasm_jv)
    native_jaref_update_records, native_jaref_update_error = (
        decode_jaref_update_trace(native_jaref_updates))
    wasm_jaref_update_records, wasm_jaref_update_error = (
        decode_jaref_update_trace(wasm_jaref_updates))
    jaref_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_jaref, wasm_jaref)) if a != b]
    jaref_operand_differences = []
    jaref_result_differences = []
    for record_index, (left, right) in enumerate(
            zip(native_jaref_records, wasm_jaref_records)):
        for field in ("qacc", "aref", "J"):
            if left[field] != right[field]:
                differences = [(i, a, b) for i, (a, b) in enumerate(
                    zip(left[field], right[field])) if a != b]
                jaref_operand_differences.append({
                    "record": record_index, "field": field,
                    "differentCount": len(differences),
                    "firstDifferences": differences[:8],
                    "lengths": [len(left[field]), len(right[field])]})
        if left["Jaref"] != right["Jaref"]:
            differences = [(i, a, b) for i, (a, b) in enumerate(
                zip(left["Jaref"], right["Jaref"])) if a != b]
            jaref_result_differences.append({
                "record": record_index, "field": "Jaref",
                "differentCount": len(differences),
                "firstDifferences": differences[:8],
                "lengths": [len(left["Jaref"]), len(right["Jaref"]) ]})
    jaref_update_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_jaref_updates, wasm_jaref_updates))
        if a != b]
    jaref_update_field_differences = []
    for record_index, (left, right) in enumerate(zip(
            native_jaref_update_records, wasm_jaref_update_records)):
        for field in ("alpha", "before", "direction", "after"):
            if left[field] != right[field]:
                differences = [(i, a, b) for i, (a, b) in enumerate(
                    zip(left[field], right[field]))] if isinstance(
                        left[field], list) else [(0, left[field], right[field])]
                differences = [item for item in differences if item[1] != item[2]]
                jaref_update_field_differences.append({
                    "record": record_index, "field": field,
                    "differentCount": len(differences),
                    "firstDifferences": differences[:8]})
    jv_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_jv, wasm_jv)) if a != b]
    jv_field_differences = []
    for record_index, (left, right) in enumerate(zip(
            native_jv_records, wasm_jv_records)):
        for field in ("search", "J", "Jv"):
            if left[field] != right[field]:
                differences = [(i, a, b) for i, (a, b) in enumerate(
                    zip(left[field], right[field])) if a != b]
                jv_field_differences.append({
                    "record": record_index, "field": field,
                    "differentCount": len(differences),
                    "firstDifferences": differences[:8]})
    noslip_step_differences = [(i, a, b) for i, (a, b) in enumerate(
        zip(native_noslip_steps, wasm_noslip_steps)) if a != b]
    native_iter1_inputs = reconstruct_noslip_iteration1_inputs(native_trace)
    wasm_iter1_inputs = reconstruct_noslip_iteration1_inputs(wasm_trace)
    iter1_input_fields = ("entryB", "entryR", "entryAR",
                          "forceAfterIteration0", "tangentRows",
                          "recordedIteration1OldForce")
    iter1_input_differences = {}
    for field in iter1_input_fields:
        left = native_iter1_inputs.get(field)
        right = wasm_iter1_inputs.get(field)
        if left != right:
            if isinstance(left, list) and isinstance(right, list):
                iter1_input_differences[field] = {
                    "differentCount": sum(a != b for a, b in zip(left, right)),
                    "lengths": [len(left), len(right)],
                    "first": next(((i, a, b) for i, (a, b) in
                                   enumerate(zip(left, right)) if a != b), None)}
            else:
                iter1_input_differences[field] = [left, right]
    iter1_operands_exact = (
        native_iter1_inputs.get("available") is True and
        wasm_iter1_inputs.get("available") is True and
        not iter1_input_differences)
    native_residual_states = native_trace.get("residualInputStates", [])
    wasm_residual_states = wasm_trace.get("residualInputStates", [])
    residual_island_ids = sorted({int(item["island"])
                                  for item in native_residual_states} |
                                 {int(item["island"])
                                  for item in wasm_residual_states})
    iter1_reconstructions_by_island = {}
    wasm_dot_probes = {
        int(item["island"]): item
        for item in wasm_trace.get("noSlipIteration1DotProbe", [])}
    for island_id in residual_island_ids:
        native_island_inputs = reconstruct_noslip_iteration1_inputs(
            native_trace, island_id)
        wasm_island_inputs = reconstruct_noslip_iteration1_inputs(
            wasm_trace, island_id)
        field_differences = {}
        for field in iter1_input_fields:
            left = native_island_inputs.get(field)
            right = wasm_island_inputs.get(field)
            if left != right:
                if isinstance(left, list) and isinstance(right, list):
                    field_differences[field] = {
                        "differentCount": sum(a != b for a, b in
                                              zip(left, right)),
                        "lengths": [len(left), len(right)],
                        "first": next(((i, a, b) for i, (a, b) in
                                       enumerate(zip(left, right))
                                       if a != b), None)}
                else:
                    field_differences[field] = [left, right]
        available = (native_island_inputs.get("available") is True and
                     wasm_island_inputs.get("available") is True)
        residual_rows = []
        if available:
            nefc = int(native_island_inputs["nefc"])
            native_ar = native_island_inputs["entryAR"]
            wasm_ar = wasm_island_inputs["entryAR"]
            native_force = native_island_inputs["forceAfterIteration0"]
            wasm_force = wasm_island_inputs["forceAfterIteration0"]
            native_residual = native_island_inputs.get(
                "recordedIteration1Residual", [])
            wasm_residual = wasm_island_inputs.get(
                "recordedIteration1Residual", [])
            wasm_dot_rows = {
                int(item["row"]): item
                for item in wasm_dot_probes.get(island_id, {}).get("rows", [])}
            for tangent_offset, row in enumerate(
                    native_island_inputs.get("tangentRows", [])):
                start = int(row) * nefc
                native_row = native_ar[start:start + nefc]
                wasm_row = wasm_ar[start:start + nefc]
                columns = [column for column, (left, right) in enumerate(
                    zip(native_row, wasm_row)) if left != 0.0 or right != 0.0]
                product_differences = [
                    (column, native_row[column] * native_force[column],
                     wasm_row[column] * wasm_force[column])
                    for column in columns
                    if native_row[column] * native_force[column] !=
                    wasm_row[column] * wasm_force[column]]
                native_reg = (native_island_inputs["entryR"][int(row)] *
                              native_force[int(row)])
                wasm_reg = (wasm_island_inputs["entryR"][int(row)] *
                            wasm_force[int(row)])
                native_dot = None
                if RNE_TRACE_LIBRARY is not None and hasattr(
                        RNE_TRACE_LIBRARY, "mju_dot"):
                    dot_function = RNE_TRACE_LIBRARY.mju_dot
                    dot_function.argtypes = [
                        ctypes.POINTER(ctypes.c_double),
                        ctypes.POINTER(ctypes.c_double), ctypes.c_int]
                    dot_function.restype = ctypes.c_double
                    native_row_buffer = (ctypes.c_double * nefc)(*native_row)
                    native_force_buffer = (ctypes.c_double * nefc)(
                        *native_force)
                    native_dot = float(dot_function(
                        native_row_buffer, native_force_buffer, nefc))
                wasm_dot_row = wasm_dot_rows.get(int(row), {})
                wasm_dot = wasm_dot_row.get("dot")
                native_separate = (native_island_inputs["entryB"][int(row)] +
                                   native_dot - native_reg
                                   if native_dot is not None else None)
                native_fused = None
                if native_dot is not None:
                    fma_function = ctypes.CDLL(None).fma
                    fma_function.argtypes = [ctypes.c_double, ctypes.c_double,
                                             ctypes.c_double]
                    fma_function.restype = ctypes.c_double
                    native_fused = float(fma_function(
                        -native_island_inputs["entryR"][int(row)],
                        native_force[int(row)],
                        native_island_inputs["entryB"][int(row)] + native_dot))
                wasm_separate = wasm_dot_row.get(
                    "separatelyRoundedResidual")
                residual_rows.append({
                    "row": int(row),
                    "b": [native_island_inputs["entryB"][int(row)],
                          wasm_island_inputs["entryB"][int(row)]],
                    "nonzeroColumns": columns,
                    "matrixRowDifferentCount": sum(
                        left != right for left, right in
                        zip(native_row, wasm_row)),
                    "forceDifferentCountAtNonzeroColumns": sum(
                        native_force[column] != wasm_force[column]
                        for column in columns),
                    "productDifferentCount": len(product_differences),
                    "productFirstDifferences": product_differences[:8],
                    "regularizerProduct": [native_reg, wasm_reg],
                    "dot": [native_dot, wasm_dot],
                    "separatelyRoundedResidual": [
                        native_separate, wasm_separate],
                    "nativeFusedResidual": native_fused,
                    "capturedResidual": [
                        native_residual[tangent_offset]
                        if tangent_offset < len(native_residual) else None,
                        wasm_residual[tangent_offset]
                        if tangent_offset < len(wasm_residual) else None],
                })
        iter1_reconstructions_by_island[str(island_id)] = {
            "nativeAvailable": native_island_inputs.get("available"),
            "wasmAvailable": wasm_island_inputs.get("available"),
            "operandsExactlyEqual": available and not field_differences,
            "operandDifferences": field_differences,
            "tangentResidualRows": residual_rows,
            "nativeResidual": native_island_inputs.get(
                "recordedIteration1Residual"),
            "wasmResidual": wasm_island_inputs.get(
                "recordedIteration1Residual"),
            "contactRow": native_island_inputs.get("contactRow"),
            "tangentRows": native_island_inputs.get("tangentRows"),
        }
    # A zip over differently sized diagnostic captures silently compares only
    # the common prefix. Report such captures as incomparable rather than
    # presenting a zero prefix-difference count as evidence of parity.
    auxiliary_comparisons = {
        "sparseInput": (native_sparse, wasm_sparse, sparse_differences),
        "constraintInput": (native_constraint, wasm_constraint,
                            constraint_differences),
        "cholSolveInput": (native_chol, wasm_chol, chol_differences),
        "hessianTrace": (native_hessian, wasm_hessian, hessian_differences),
        "coneTrace": (native_cone, wasm_cone, cone_differences),
        "denseSolveStages": (native_solve_stages, wasm_solve_stages,
                             solve_stage_differences),
        "constraintUpdateTrace": (native_updates, wasm_updates,
                                  [(i, a, b) for i, (a, b) in enumerate(
                                      zip(native_updates, wasm_updates)) if a != b]),
        "constraintIterationTrace": (
            native_iteration_updates, wasm_iteration_updates,
            [(i, a, b) for i, (a, b) in enumerate(zip(
                native_iteration_updates, wasm_iteration_updates)) if a != b]),
        "constraintStateTrace": (native_states, wasm_states,
                                 [(i, a, b) for i, (a, b) in enumerate(
                                     zip(native_states, wasm_states)) if a != b]),
        "noSlipTrace": (native_noslip, wasm_noslip, noslip_differences),
        "noSlipContactTrace": (native_noslip_contacts,
                               wasm_noslip_contacts,
                               noslip_contact_differences),
        "noSlipStepTrace": (native_noslip_steps, wasm_noslip_steps,
                             noslip_step_differences),
        "jarefTrace": (native_jaref, wasm_jaref, jaref_differences),
        "jvTrace": (native_jv, wasm_jv, jv_differences),
        "jarefUpdateTrace": (native_jaref_updates, wasm_jaref_updates,
                              jaref_update_differences),
        "noSlipCostChangeProbe": (
            [value for item in native_cost_probes
             for value in (item.get("quadratic"), item.get("linear"),
                           item.get("change"))],
            [value for item in wasm_cost_probes
             for value in (item.get("quadratic"), item.get("linear"),
                           item.get("change"))],
            cost_probe_differences),
        "residualInputState": (
            [native_residual_state.get("nefc"),
             *native_residual_state.get("b", []),
             *native_residual_state.get("R", []),
             *native_residual_state.get("AR", []),
             native_residual_state.get("arAvailable")],
            [wasm_residual_state.get("nefc"),
             *wasm_residual_state.get("b", []),
             *wasm_residual_state.get("R", []),
             *wasm_residual_state.get("AR", []),
             wasm_residual_state.get("arAvailable")],
            residual_state_differences),
        "residualInputStates": (
            native_residual_states, wasm_residual_states,
            [(i, left, right) for i, (left, right) in enumerate(
                zip(native_residual_states, wasm_residual_states))
             if left != right]),
    }
    auxiliary_comparable = {
        name: len(native) == len(wasm)
        for name, (native, wasm, _) in auxiliary_comparisons.items()
    }
    first = None
    divergences = []
    record_headers = []
    native_offset = wasm_offset = 0
    native_tail_label = wasm_tail_label = None
    common_records = min(native_count, wasm_count)
    native_operand_probes = []
    wasm_operand_probes = []
    line_search_records = []
    primal_prepare_probe_groups: dict[int, list[dict[str, object]]] = {}
    for record in range(common_records):
        no, wo = native_offset, wasm_offset
        native_nv, native_nefc = int(native_values[no+4]), int(native_values[no+5])
        wasm_nv, wasm_nefc = int(wasm_values[wo+4]), int(wasm_values[wo+5])
        native_width = 9 + 5*native_nv + 2*native_nefc
        wasm_width = 9 + 5*wasm_nv + 2*wasm_nefc
        if (native_nv, native_nefc) != (wasm_nv, wasm_nefc):
            first = {"record": record, "field": "island dimensions",
                     "native": [native_nv, native_nefc],
                     "wasm": [wasm_nv, wasm_nefc]}
            break
        if native_values[no] != wasm_values[wo]:
            # Diagnostic builds can carry different probe sets. Once labels
            # diverge, positional payload/state comparison would pair
            # unrelated records and manufacture apparent numeric failures.
            first = {"record": record, "field": "trace label alignment",
                     "nativeLabel": native_values[no],
                     "wasmLabel": wasm_values[wo]}
            break
        record_semantics = newton_record_payload(int(native_values[no]),
                                                 native_values[no:no+9])
        record_headers.append({
            "record": record,
            "label": native_values[no],
            "native": native_values[no:no+9],
            "wasm": wasm_values[wo:wo+9],
            "semantics": record_semantics,
            "wasmSemantics": newton_record_payload(
                int(wasm_values[wo]), wasm_values[wo:wo+9]),
            "validStateFields": [],
        })
        header_diffs = [(i, native_values[no+i], wasm_values[wo+i])
                        for i in (*range(4), *range(6, 9))
                        if native_values[no+i] != wasm_values[wo+i]]
        native_payload = record_semantics["payload"]
        wasm_payload = record_headers[-1]["wasmSemantics"]["payload"]
        payload_differences = {
            name: {"native": native_payload.get(name),
                   "wasm": wasm_payload.get(name)}
            for name in native_payload.keys() | wasm_payload.keys()
            if native_payload.get(name) != wasm_payload.get(name)
        }
        schema_differences = {
            "nativeOnly": sorted(native_payload.keys() - wasm_payload.keys()),
            "wasmOnly": sorted(wasm_payload.keys() - native_payload.keys()),
        }
        current = ({"record": record, "label": native_values[no],
                    "semantics": record_semantics["kind"],
                    "payloadDifferences": payload_differences,
                    "payloadSchemaDifferences": schema_differences,
                    "headerDifferences": header_diffs}
                   if header_diffs or payload_differences or any(
                       schema_differences.values()) else None)
        native_tail_label, wasm_tail_label = native_values[no], wasm_values[wo]
        label_value = int(native_values[no])
        if label_value >= 3000:
            line_search_records.append({
                "record": record,
                "label": label_value,
                "native": native_values[no:no+9],
                "wasm": wasm_values[wo:wo+9],
                "semantics": record_semantics,
                "wasmSemantics": record_headers[-1]["wasmSemantics"],
            })
        if 25000 <= label_value < 30000:
            # Marble's opt-in solver instrumentation records each elliptic
            # tangent's source terms and running UU/UV/VV partial sums in
            # header slots 6..8. Keep the entire affected contact family so
            # an accumulator mismatch can be distinguished from a different
            # Jaref/Jv/friction input or an earlier partial-sum mismatch.
            contact_index = (label_value - 25000) // 100
            probe_kind = label_value % 10
            probe_fields = {
                0: ("U", "V", "U_squared"),
                1: ("U_times_V", "V_squared", "UU_after_tangent"),
                2: ("UV_partial_sum", "VV_partial_sum", "reserved"),
                3: ("Jaref", "Jv", "friction"),
            }.get(probe_kind, ("value0", "value1", "value2"))
            primal_prepare_probe_groups.setdefault(contact_index, []).append({
                "record": record,
                "label": label_value,
                "fields": probe_fields,
                "native": native_values[no+6:no+9],
                "wasm": wasm_values[wo+6:wo+9],
            })
        if ((10000 <= label_value < 20000 and
             label_value % 100 in {*range(0, 8), 10, 11, 20, 30}) or
                600000 <= label_value < 1000000):
            # The elliptic-contact trace emits the N/Tsqr result at label
            # *00, source operands (U0,V0,UU,UV,VV,Dm,mu) at *01..*07,
            # zone/derivative diagnostics at *10,*11,*20,*30, and alpha in
            # every record header. Preserve these scalars directly so operand
            # mismatches are distinguishable from expression-rounding or
            # branch/derivative differences.
            for probes, values, offset in (
                    (native_operand_probes, native_values, no),
                    (wasm_operand_probes, wasm_values, wo)):
                probe = {
                    "record": record,
                    "label": int(values[offset]),
                    "alpha": values[offset + 1],
                    "cost": values[offset + 6],
                    "deriv0": values[offset + 7],
                    "deriv1": values[offset + 8],
                }
                if 600000 <= label_value < 700000:
                    probe["eval"] = (label_value - 600000) // 1000
                    probe["row"] = (label_value - 600000) % 1000
                    probe["contactId"] = int(values[offset + 8])
                    probe["probe"] = "N_Tsqr"
                elif 700000 <= label_value < 800000:
                    encoded = label_value - 700000
                    probe["eval"] = encoded // 10000
                    probe["row"] = (encoded % 10000) // 10
                    probe["field"] = encoded % 10
                    probe["contactId"] = int(values[offset + 8])
                elif 800000 <= label_value < 1000000:
                    encoded = label_value - 800000
                    probe["eval"] = encoded // 100000
                    probe["row"] = (encoded % 100000) // 10
                    probe["zoneProbe"] = encoded % 10
                probes.append(probe)
        nv, nefc = native_nv, native_nefc
        fields = (("efc_force", 9, nefc), ("qacc", 9+nefc, nv),
                  ("Ma", 9+nefc+nv, nv),
                  ("grad", 9+nefc+2*nv, nv),
                  ("Mgrad", 9+nefc+3*nv, nv),
                  ("search", 9+nefc+4*nv, nv),
                  ("Jaref", 9+nefc+5*nv, nefc))
        # The solver emits checkpoints before every scratch vector has been
        # initialized. Comparing those slots treated allocator leftovers as
        # numerical divergence and could mask the first real solver split.
        invalid_fields = set()
        if label_value == 10:
            invalid_fields.update(("Ma", "grad", "Mgrad", "search", "Jaref"))
        elif label_value == 11:
            invalid_fields.update(("grad", "Mgrad", "search", "Jaref"))
        elif label_value == 12:
            invalid_fields.update(("grad", "Mgrad", "search"))
        elif label_value == 13:
            invalid_fields.update(("grad", "Mgrad", "search"))
        elif label_value in (14, 15):
            invalid_fields.update(("Mgrad", "search"))
        elif label_value == 16:
            invalid_fields.add("search")
        elif label_value in (0, 1):
            invalid_fields.add("search")
        record_headers[-1]["validStateFields"] = [
            name for name, _, _ in fields if name not in invalid_fields]
        state_differences = []
        for name, offset, count in fields:
            if name in invalid_fields:
                continue
            differences = [(i, native_values[no+offset+i],
                            wasm_values[wo+offset+i])
                           for i in range(count)
                           if native_values[no+offset+i] != wasm_values[wo+offset+i]]
            if differences:
                state_diff = {"field": name,
                              "differentCount": len(differences),
                              "firstDifferences": differences[:5]}
                state_differences.append(state_diff)
                if current is None:
                    current = {"record": record, "label": native_values[no]}
        if state_differences:
            current["firstStateDifference"] = state_differences[0]
            current["allStateDifferences"] = state_differences
        if current:
            divergences.append(current)
            if first is None:
                first = current
        native_offset += native_width
        wasm_offset += wasm_width
    if first is None and native_count != wasm_count:
        first = {"field": "record count", "native": native_count,
                 "wasm": wasm_count}
    if first is None and native_count == wasm_count and (
            native_offset != len(native_values) or wasm_offset != len(wasm_values)):
        first = {"field": "trace length", "nativeValues": len(native_values),
                 "wasmValues": len(wasm_values)}
    dense_solve_context = []
    if auxiliary_comparable["denseSolveStages"] and native_solve_stages:
        n = int(native_solve_stages[0])
        if n > 0 and len(native_solve_stages) == 1 + n*n + n + 2*n*n:
            forward_start = 1 + n*n + n
            backward_start = forward_start + n*n
            for index, native_value, wasm_value in solve_stage_differences[:1]:
                if index < forward_start:
                    continue
                phase_start = forward_start if index < backward_start else backward_start
                phase = "forward" if index < backward_start else "backward"
                snapshot_index, component = divmod(index - phase_start, n)
                current_start = phase_start + snapshot_index*n
                previous_start = current_start - n
                dense_solve_context.append({
                    "firstDifferingStage": {
                        "phase": phase,
                        "iteration": (snapshot_index if phase == "forward"
                                      else n - 1 - snapshot_index),
                        "component": component,
                        "native": native_value,
                        "wasm": wasm_value,
                        "previousNative": native_solve_stages[
                            previous_start:previous_start+n]
                            if previous_start >= phase_start else None,
                        "previousWasm": wasm_solve_stages[
                            previous_start:previous_start+n]
                            if previous_start >= phase_start else None,
                        "currentNative": native_solve_stages[
                            current_start:current_start+n],
                        "currentWasm": wasm_solve_stages[
                            current_start:current_start+n],
                    }
                })
            for index, native_value, wasm_value in solve_stage_differences[:4]:
                dense_solve_context.append({
                    "index": index,
                    "native": native_value,
                    "wasm": wasm_value,
                    "matrix": native_solve_stages[1:1+n*n],
                    "rhs": native_solve_stages[1+n*n:forward_start],
                    "forwardResult": native_solve_stages[
                        forward_start+(n-1)*n:forward_start+n*n],
                    "backwardBeforeFinalRow": native_solve_stages[
                        backward_start+(n-2)*n:backward_start+(n-1)*n]
                        if n > 1 else [],
                    "nativeBackwardFinal": native_solve_stages[
                        backward_start+(n-1)*n:backward_start+n*n],
                    "wasmBackwardFinal": wasm_solve_stages[
                        backward_start+(n-1)*n:backward_start+n*n],
                })
    first_record_index = (int(first["record"])
                          if first and "record" in first else None)
    first_difference_context = []
    if first_record_index is not None:
        first_difference_context = [
            item for item in record_headers
            if max(0, first_record_index - 8) <= item["record"] <=
            first_record_index + 8]
    report = {
        "nativeRecords": native_count, "wasmRecords": wasm_count,
        "sparseInputSizes": [len(native_sparse), len(wasm_sparse)],
        "sparseInputFirstDifferences": sparse_differences[:12],
        "sparseInputComparable": auxiliary_comparable["sparseInput"],
        "sparseInputDifferentCount": (len(sparse_differences)
                                       if auxiliary_comparable["sparseInput"]
                                       else None),
        "constraintInputSizes": [len(native_constraint), len(wasm_constraint)],
        "constraintInputFirstDifferences": constraint_differences[:12],
        "constraintInputDiffByField": constraint_field_differences,
        "constraintInputComparable": auxiliary_comparable["constraintInput"],
        "constraintInputDifferentCount": (len(constraint_differences)
                                           if auxiliary_comparable["constraintInput"]
                                           else None),
        "cholSolveInputSizes": [len(native_chol), len(wasm_chol)],
        "cholSolveInputFirstDifferences": chol_differences[:12],
        "cholSolveInputComparable": auxiliary_comparable["cholSolveInput"],
        "cholSolveInputDifferentCount": (len(chol_differences)
                                         if auxiliary_comparable["cholSolveInput"]
                                         else None),
        "hessianTraceSizes": [len(native_hessian), len(wasm_hessian)],
        "hessianTraceFirstDifferences": hessian_differences[:12],
        "hessianTraceComparable": auxiliary_comparable["hessianTrace"],
        "hessianTraceDifferentCount": (len(hessian_differences)
                                        if auxiliary_comparable["hessianTrace"]
                                        else None),
        "coneTraceSizes": [len(native_cone), len(wasm_cone)],
        "coneTraceFirstDifferences": cone_differences[:12],
        "coneTraceComparable": auxiliary_comparable["coneTrace"],
        "coneTraceDifferentCount": (len(cone_differences)
                                    if auxiliary_comparable["coneTrace"]
                                    else None),
        "denseSolveStagesSizes": [len(native_solve_stages),
                                  len(wasm_solve_stages)],
        "denseSolveStagesFirstDifferences": solve_stage_differences[:12],
        "denseSolveStagesComparable": auxiliary_comparable["denseSolveStages"],
        "denseSolveStagesDifferentCount": (len(solve_stage_differences)
                                            if auxiliary_comparable["denseSolveStages"]
                                            else None),
        "noSlipTraceSizes": [len(native_noslip), len(wasm_noslip)],
        "noSlipTraceFirstDifferences": noslip_differences[:24],
        "noSlipTraceComparable": auxiliary_comparable["noSlipTrace"],
        "noSlipTraceDifferentCount": (len(noslip_differences)
                                        if auxiliary_comparable["noSlipTrace"]
                                        else None),
        "noSlipTraceDecodeErrors": [native_noslip_error, wasm_noslip_error],
        "noSlipTraceRecordCounts": [len(native_noslip_records),
                                    len(wasm_noslip_records)],
        "noSlipTraceFirstRecordDifference": first_record_difference(
            native_noslip_records, wasm_noslip_records),
        "noSlipTraceFirstActiveSetDifference":
            first_noslip_active_set_difference(native_noslip_records,
                                               wasm_noslip_records),
        "noSlipContactTraceSizes": [len(native_noslip_contacts),
                                    len(wasm_noslip_contacts)],
        "noSlipContactTraceFirstDifferences":
            noslip_contact_differences[:24],
        "noSlipContactTraceComparable":
            auxiliary_comparable["noSlipContactTrace"],
        "noSlipContactTraceDifferentCount":
            (len(noslip_contact_differences)
             if auxiliary_comparable["noSlipContactTrace"] else None),
        "noSlipContactTraceDecodeErrors": [native_noslip_contact_error,
                                           wasm_noslip_contact_error],
        "noSlipContactTraceRecordCounts": [len(native_noslip_contact_records),
                                           len(wasm_noslip_contact_records)],
        "noSlipContactTraceFirstRecordDifference": first_record_difference(
            native_noslip_contact_records, wasm_noslip_contact_records),
        "noSlipContactTraceFieldDifferences": decoded_record_field_differences(
            native_noslip_contact_records, wasm_noslip_contact_records),
        "noSlipStepTraceSizes": [len(native_noslip_steps),
                                  len(wasm_noslip_steps)],
        "noSlipStepTraceFirstDifferences": noslip_step_differences[:24],
        "noSlipStepTraceComparable": auxiliary_comparable["noSlipStepTrace"],
        "noSlipStepTraceDifferentCount": (
            len(noslip_step_differences)
            if auxiliary_comparable["noSlipStepTrace"] else None),
        "noSlipStepTraceDecodeErrors": [native_noslip_step_error,
                                         wasm_noslip_step_error],
        "noSlipStepTraceRecordCounts": [len(native_noslip_step_records),
                                         len(wasm_noslip_step_records)],
        "noSlipStepTraceFirstRecordDifference": first_record_difference(
            native_noslip_step_records, wasm_noslip_step_records),
        "jarefTraceSizes": [len(native_jaref), len(wasm_jaref)],
        "jarefTraceFirstDifferences": jaref_differences[:24],
        "jarefTraceComparable": auxiliary_comparable["jarefTrace"],
        "jarefTraceDifferentCount": (
            len(jaref_differences)
            if auxiliary_comparable["jarefTrace"] else None),
        "jarefTraceDecodeErrors": [native_jaref_error, wasm_jaref_error],
        "jarefTraceRecordCounts": [len(native_jaref_records),
                                    len(wasm_jaref_records)],
        "jarefTraceOperandsExactlyEqual": (
            auxiliary_comparable["jarefTrace"] and
            not jaref_operand_differences),
        "jarefTraceOperandDifferences": jaref_operand_differences[:24],
        "jarefTraceResultFirstDifferences": jaref_result_differences[:24],
        "jvTraceSizes": [len(native_jv), len(wasm_jv)],
        "jvTraceFirstDifferences": jv_differences[:24],
        "jvTraceComparable": auxiliary_comparable["jvTrace"],
        "jvTraceDifferentCount": (
            len(jv_differences)
            if auxiliary_comparable["jvTrace"] else None),
        "jvTraceDecodeErrors": [native_jv_error, wasm_jv_error],
        "jvTraceRecordCounts": [len(native_jv_records), len(wasm_jv_records)],
        "jvTraceFieldDifferences": jv_field_differences[:24],
        "jarefUpdateTraceSizes": [len(native_jaref_updates),
                                  len(wasm_jaref_updates)],
        "jarefUpdateTraceFirstDifferences": jaref_update_differences[:24],
        "jarefUpdateTraceComparable":
            auxiliary_comparable["jarefUpdateTrace"],
        "jarefUpdateTraceDifferentCount": (
            len(jaref_update_differences)
            if auxiliary_comparable["jarefUpdateTrace"] else None),
        "jarefUpdateTraceDecodeErrors": [native_jaref_update_error,
                                          wasm_jaref_update_error],
        "jarefUpdateTraceRecordCounts": [len(native_jaref_update_records),
                                          len(wasm_jaref_update_records)],
        "jarefUpdateTraceFieldDifferences":
            jaref_update_field_differences[:24],
        "noSlipIteration1Reconstruction": {
            "nativeAvailable": native_iter1_inputs.get("available"),
            "wasmAvailable": wasm_iter1_inputs.get("available"),
            "operandsExactlyEqual": iter1_operands_exact,
            "operandDifferences": iter1_input_differences,
            "nativeResidual": native_iter1_inputs.get(
                "recordedIteration1Residual"),
            "wasmResidual": wasm_iter1_inputs.get(
                "recordedIteration1Residual"),
            "contactRow": native_iter1_inputs.get("contactRow"),
            "tangentRows": native_iter1_inputs.get("tangentRows"),
        },
        "noSlipIteration1ReconstructionsByIsland":
            iter1_reconstructions_by_island,
        "noSlipCostChangeProbeComparable":
            auxiliary_comparable["noSlipCostChangeProbe"],
        "noSlipCostChangeProbeFirstDifferences":
            cost_probe_differences[:24],
        "residualInputStateSizes": [
            len(auxiliary_comparisons["residualInputState"][0]),
            len(auxiliary_comparisons["residualInputState"][1])],
        "residualInputStateComparable":
            auxiliary_comparable["residualInputState"],
        "residualInputStateFirstDifferences": residual_state_differences[:24],
        "residualInputStatesComparable":
            auxiliary_comparable["residualInputStates"],
        "residualInputStatesDifferentCount": len(
            auxiliary_comparisons["residualInputStates"][2]),
        "residualInputStatesFirstDifferences":
            auxiliary_comparisons["residualInputStates"][2][:8],
        "denseSolveStagesContext": dense_solve_context,
        "constraintUpdateTraceSizes": [len(native_updates), len(wasm_updates)],
        "constraintStateTraceSizes": [len(native_states), len(wasm_states)],
        "constraintStateTraceFirstDifferences": [
            {"index": i, "native": a, "wasm": b}
            for i, a, b in auxiliary_comparisons["constraintStateTrace"][2][:24]],
        "constraintStateTraceComparable": auxiliary_comparable["constraintStateTrace"],
        "warmstartMetadata": {
            "native": {key: native_trace.get(key) for key in
                       ("modelDisableFlags", "modelSolver", "dataConstraintCount")},
            "wasm": {key: wasm_trace.get(key) for key in
                     ("modelDisableFlags", "modelSolver", "dataConstraintCount",
                      "constraintUpdateCaptureSize", "traceKeys")},
        },
        "constraintUpdateTraceCalls": [len(native_calls), len(wasm_calls)],
        "constraintUpdateTraceFirstDifference": update_first,
        "constraintIterationTraceSizes": [len(native_iteration_updates),
                                          len(wasm_iteration_updates)],
        "constraintIterationTraceComparable": iteration_comparison["comparable"],
        "constraintIterationTraceSchemas": iteration_comparison["schemas"],
        "constraintIterationTraceRawComparable": iteration_comparison["comparable"],
        "constraintIterationTraceRawCaveat": (
            None if iteration_comparison["comparable"] else
            "Raw offsets across different/invalid schemas are not initialized-field parity evidence"),
        "constraintIterationTraceDifferentCount": len(
            auxiliary_comparisons["constraintIterationTrace"][2]),
        "constraintIterationTraceFirstDifferences": [
            (i, a, b) for i, a, b in auxiliary_comparisons[
                "constraintIterationTrace"][2][:32]],
        "constraintIterationTraceFirstRecordDifference": iteration_update_first,
        "constraintIterationTraceSamples": [
            {"record": index,
             "native": {"phase": left["phase"], "validity": left["validity"],
                        "Jaref": left["fields"]["Jaref"],
                        "Jv": left["fields"]["Jv"], "search": left["fields"]["search"]},
             "wasm": {"phase": right["phase"], "validity": right["validity"],
                      "Jaref": right["fields"]["Jaref"],
                      "Jv": right["fields"]["Jv"], "search": right["fields"]["search"]}}
            for index, (left, right) in enumerate(zip(native_update_records[:4],
                                                       wasm_update_records[:4]))],
        "constraintIterationTraceDecodeErrors": [native_iteration_error,
                                                  wasm_iteration_error],
        "constraintIterationTraceRecordCounts": [len(native_update_records),
                                                  len(wasm_update_records)],
        "constraintUpdateTraceDecodeErrors": [native_update_error,
                                              wasm_update_error],
        "firstDifference": first,
        "firstDifferenceContext": first_difference_context,
        "earlyDifferences": divergences[:12],
        "nativeTailLabel": native_tail_label,
        "wasmTailLabel": wasm_tail_label,
        "nativeOperandProbeRecords": native_operand_probes,
        "wasmOperandProbeRecords": wasm_operand_probes,
        "lineSearchRecords": line_search_records,
    }
    if (first is not None and "label" in first and
            25000 <= int(first["label"]) < 30000):
        first_prepare_contact = (int(first["label"]) - 25000) // 100
        report["firstPrepareContactTangentProbes"] = (
            primal_prepare_probe_groups.get(first_prepare_contact, []))
    elif (first is not None and "label" in first and
          600000 <= int(first["label"]) < 900000):
        label_value = int(first["label"])
        if label_value < 700000:
            first_evaluation_row = (label_value - 600000) % 1000
        elif label_value < 800000:
            first_evaluation_row = ((label_value - 700000) % 10000) // 10
        else:
            first_evaluation_row = ((label_value - 800000) % 100000) // 10
        report["firstEvaluationContactTangentProbes"] = (
            primal_prepare_probe_groups.get(first_evaluation_row, []))
    if first is not None and first.get("semantics") == "elliptic_cost_intermediate":
        operands = elliptic_cost_operand_pair(
            int(first.get("label", 0)), native_operand_probes,
            wasm_operand_probes)
        if operands is not None:
            report["firstEllipticCostOperands"] = operands
    if first is not None and "record" in first:
        record = int(first["record"])
        report["firstDifferenceHeaderWindow"] = record_headers[
            max(0, record-8):record+9]
    if os.environ.get("NW_MARBLE_DUMP_CONE_TRACE") == "1":
        report["nativeConeTrace"] = native_cone
        report["wasmConeTrace"] = wasm_cone
    if os.environ.get("NW_MARBLE_DUMP_NOSLIP_TRACE") == "1":
        report["nativeNoSlipContactTrace"] = native_noslip_contact_records
        report["wasmNoSlipContactTrace"] = wasm_noslip_contact_records
    print(f"COMPILED NEWTON TRACE {label}: " + json.dumps(
        report, sort_keys=True))


ENGINE_DIAGNOSTIC_FIELDS = (
    "cvel", "cdof", "cdof_dot", "cacc", "cfrc_ext", "cfrc_int",
    "cinert", "crb", "subtree_com",
    "xpos", "xquat", "xipos", "ximat",
    # Primal Newton's initial Ma/Jaref depend on the packed mass matrix and
    # sparse Jacobian layout, not only the public acceleration/Jacobian values.
    # Keep these in the exact-input snapshot/synchronization set as well.
    "M", "qLD", "qLDiagInv",
    # Trace island-local solver vectors and the reverse maps through the
    # gather/scatter boundary when synchronizing an isolated fwdConstraint.
    "iacc", "iacc_smooth", "ifrc_constraint", "ifrc_smooth",
    "island_nv", "island_nefc", "map_efc2iefc",
    "qpos", "qvel", "qacc", "qacc_smooth", "qacc_warmstart",
    "qfrc_constraint", "qfrc_smooth", "qfrc_bias", "qfrc_passive",
    "qfrc_applied", "qH", "qHDiagInv", "qLDiagInv", "qDeriv",
    "efc_force", "efc_pos", "efc_vel", "efc_aref", "efc_b", "efc_state",
    "efc_D", "efc_R", "efc_KBIP", "efc_margin", "efc_diagA",
    "efc_type", "efc_id", "efc_island", "efc_frictionloss",
    "efc_J", "efc_AR",
    "efc_KBIP", "efc_D", "efc_R",
    "efc_J_rownnz", "efc_J_rowadr", "efc_J_rowsuper", "efc_J_colind",
    "map_idof2dof", "map_dof2idof", "map_iefc2efc",
    "iefc_D", "iefc_R", "iefc_frictionloss", "iefc_type", "iefc_id",
    "iefc_state", "iefc_force", "iefc_aref",
    "island_idofadr", "island_iefcadr",
    "solver_niter", "solver_nnz", "solver_fwdinv", "geom_xpos", "geom_xmat",
)

ENGINE_ISLAND_FIELDS = frozenset((
    "iacc", "iacc_smooth", "ifrc_constraint", "ifrc_smooth",
    "island_nv", "island_nefc", "map_efc2iefc", "map_idof2dof",
    "map_dof2idof", "map_iefc2efc", "iefc_D", "iefc_R",
    "iefc_frictionloss", "iefc_type", "iefc_id", "iefc_state",
    "iefc_force", "iefc_aref", "island_idofadr", "island_iefcadr",
    "efc_island", "solver_niter", "solver_nnz", "solver_fwdinv",
    "solver_stats",
))

ENGINE_SPARSE_JACOBIAN_FIELDS = frozenset((
    "efc_J_colind", "efc_J_rowadr", "efc_J_rownnz", "efc_J_rowsuper",
))

ENGINE_REFERENCE_FIELDS = frozenset(("efc_aref", "efc_vel"))
ENGINE_ACCELERATION_FIELDS = frozenset(("qacc_smooth", "qfrc_smooth"))
ENGINE_RNE_FIELDS = frozenset(("qfrc_bias",))

ENGINE_SOLVER_OUTPUT_FIELDS = frozenset((
    "efc_b", "efc_force", "efc_state", "iacc", "iacc_smooth",
    "ifrc_constraint", "ifrc_smooth", "iefc_D", "iefc_R",
    "iefc_frictionloss", "iefc_type", "iefc_id", "iefc_state",
    "iefc_force", "iefc_aref", "solver_niter", "solver_nnz",
    "solver_fwdinv", "solver_stats", "qacc", "qfrc_constraint",
))


def exact_solver_value_equal(left, right) -> bool:
    """Finite numeric equality including the sign of zero; never tolerance-based.

    Ordinary Python equality treats +0.0 and -0.0 as equal. They can affect
    later branch/sign-sensitive arithmetic, so an exact solver-neutrality claim
    must not hide that difference. Nonfinite outputs are never a passing match.
    """
    return (math.isfinite(left) and math.isfinite(right) and left == right and
            (left != 0 or math.copysign(1.0, left) == math.copysign(1.0, right)))


def engine_array_valid_at_phase(field: str, label: str,
                                nisland: int | None = None,
                                sparse_jacobian: bool | None = None) -> bool:
    """Whether an engine array has been initialized at this phase checkpoint."""
    if (field in ENGINE_SPARSE_JACOBIAN_FIELDS and
            sparse_jacobian is False):
        return False

    # '.phase2.' does not contain '.phase.'. Test both explicitly: otherwise
    # phase-2 snapshots take the full-step fast path below and compare scratch
    # before fwdAcceleration/fwdConstraint have written it.
    phase1 = label.partition(".phase.")[2]
    phase2 = label.partition(".phase2.")[2]
    has_phase = bool(phase1 or phase2)
    # The island buffers remain allocator residue when mj_island returns early.
    # This must precede the solver-output fast path, which also contains local
    # island fields (iacc, iefc_force, solver_stats, ...).
    if field in ENGINE_ISLAND_FIELDS and (nisland is None or nisland <= 0):
        return False

    if field in ENGINE_REFERENCE_FIELDS and has_phase:
        if not (phase2 or phase1 in {
                "probe_referenceConstraint", "probe_rneBias",
                "probe_rnePostConstraint_zeroacc", "fwdVelocity",
                "sensorVel"}):
            return False

    if field in ENGINE_RNE_FIELDS and has_phase:
        if not phase2 and phase1 not in {
                "probe_rneBias", "probe_rnePostConstraint_zeroacc",
                "fwdVelocity", "sensorVel"}:
            return False

    if field in ENGINE_ACCELERATION_FIELDS and has_phase:
        if phase2 not in {"fwdAcceleration", "fwdConstraint", "sensorAcc",
                          "checkAcc", "implicit"}:
            return False

    if field in ENGINE_SOLVER_OUTPUT_FIELDS:
        if not has_phase:
            return True
        return phase2 in {"fwdConstraint", "sensorAcc", "checkAcc", "implicit"}

    if field not in ENGINE_ISLAND_FIELDS:
        return True
    if not has_phase or phase2:
        # Maps/dimensions were populated in fwdPosition, before every phase2
        # checkpoint. Solver-local outputs have their later rule above.
        return True
    # mj_island creates these structures during fwdPosition; the preceding
    # isolated kernels still contain allocator residue or Wasm zero-fill.
    return phase1 not in {"checkPos", "checkVel", "kinematics", "comPos"}


def source_snapshot(sim, nudge_due: float,
                    include_contacts: bool = False,
                    include_engine: bool = False) -> dict[str, object]:
    marbles = []
    for marble in sim.marbles:
        over = None
        if marble.over is not None:
            over = next((index for index, hole in enumerate(sim.tray.holes)
                         if hole == marble.over), None)
        marbles.append({
            "values": [marble.x, marble.y, marble.z, marble.vx, marble.vy,
                       marble.vz, marble.qw, marble.qx, marble.qy, marble.qz,
                       marble.wx, marble.wy, marble.wz],
            "state": marble.state,
            "over": over,
        })
    snapshot = {
        "marbles": marbles,
        "roll": sim.roll,
        "pitch": sim.pitch,
        "elapsed": sim.elapsed,
        "struck": sim.struck_this_step,
        "cupped": sim.cupped_this_step,
        "lostThisStep": sim.lost_this_step,
        "home": sim.home,
        "lost": sim.lost,
        "nudgeDue": nudge_due,
    }
    if include_contacts:
        snapshot["contacts"] = [
            {
                "geom1": int(sim._data.contact[index].geom1),
                "geom2": int(sim._data.contact[index].geom2),
                "dist": float(sim._data.contact[index].dist),
                "pos": [float(value) for value in sim._data.contact[index].pos],
            }
            for index in range(sim._data.ncon)
        ]
    if include_engine and sim._data is not None:
        snapshot["engine"] = source_engine_snapshot(sim)
    return snapshot


def source_engine_snapshot(sim) -> dict[str, object]:
    data = sim._data
    awake_state = {
        "nbody_awake": int(data.nbody_awake),
        "nparent_awake": int(data.nparent_awake),
        "nv_awake": int(data.nv_awake),
        "body_awake": data.body_awake.tolist(),
        "body_awake_ind": data.body_awake_ind.tolist(),
        "parent_awake_ind": data.parent_awake_ind.tolist(),
        "dof_awake_ind": data.dof_awake_ind.tolist(),
    }
    contact_jacobians: dict[str, list[float]] = {}
    for contact_index in range(data.ncon):
        contact = data.contact[contact_index]
        for side in range(2):
            geom = int(contact.geom[side])
            if geom < 0:
                continue
            body = int(sim._model.geom_bodyid[geom])
            jacp = __import__("numpy").zeros((3, sim._model.nv))
            jacr = __import__("numpy").zeros((3, sim._model.nv))
            MUJOCO_API.mj_jac(sim._model, data, jacp, jacr, contact.pos, body)
            contact_jacobians[f"contact{contact_index}_side{side}_jacp"] = jacp.ravel().tolist()
            contact_jacobians[f"contact{contact_index}_side{side}_jacr"] = jacr.ravel().tolist()
    arrays = {
        field: getattr(data, field).ravel().tolist()
        for field in ENGINE_DIAGNOSTIC_FIELDS
    }
    # Preserve the live operands of mj_jac's cross product and final
    # translational addition. A one-ULP Jacobian result alone cannot tell
    # whether the cause was upstream state drift or backend contraction.
    point_jacobian_terms = []
    for contact_index in range(data.ncon):
        contact = data.contact[contact_index]
        point = contact.pos.tolist()
        for side in range(2):
            geom = int(contact.geom[side])
            if geom < 0:
                continue
            body = int(sim._model.geom_bodyid[geom])
            root = int(sim._model.body_rootid[body])
            subtree_com = data.subtree_com.ravel()
            com = subtree_com[3*root:3*root+3].tolist()
            offset = [float(point[axis]) - float(com[axis])
                      for axis in range(3)]
            dof = (int(sim._model.body_dofadr[body]) +
                   int(sim._model.body_dofnum[body]) - 1)
            while dof >= 0:
                spatial = data.cdof.ravel()[6*dof:6*dof+6].tolist()
                product_pairs = (
                    (spatial[1]*offset[2], spatial[2]*offset[1]),
                    (spatial[2]*offset[0], spatial[0]*offset[2]),
                    (spatial[0]*offset[1], spatial[1]*offset[0]),
                )
                point_jacobian_terms.extend((
                    contact_index, side, body, dof, *point, *com, *offset,
                    *spatial,
                ))
                for component, (left, right) in enumerate(product_pairs):
                    cross = left - right
                    point_jacobian_terms.extend((
                        left, right, spatial[component+3], cross,
                        spatial[component+3] + cross,
                    ))
                dof = int(sim._model.dof_parentid[dof])
    arrays["contact_jacobian_terms"] = point_jacobian_terms
    solver_islands = len(data.solver_niter)
    solver_capacity = len(data.solver) // max(1, solver_islands)
    solver_stats = []
    for island, iteration_count in enumerate(data.solver_niter):
        for iteration in range(min(solver_capacity, int(iteration_count))):
            stat = data.solver[island * solver_capacity + iteration]
            solver_stats.extend((
                island, iteration, float(stat.improvement), float(stat.gradient),
                float(stat.lineslope), float(stat.nactive), float(stat.nchange),
                float(stat.neval), float(stat.nupdate),
            ))
    arrays["solver_stats"] = solver_stats
    arrays.update(contact_jacobians)
    free_joint_cross_motion = []
    model = sim._model
    cdof = data.cdof.ravel()
    cdof_dot = data.cdof_dot.ravel()
    qvel = data.qvel.ravel()
    for body in range(1, model.nbody):
        if int(model.body_parentid[body]) != 0 or int(model.body_dofnum[body]) != 6:
            continue
        bda = int(model.body_dofadr[body])
        joint = int(model.dof_jntid[bda])
        if int(model.jnt_type[joint]) != 0:
            continue
        vel = [0.0] * 6
        for dof in range(3):
            qvel_value = float(qvel[bda + dof])
            for component in range(6):
                vel[component] += float(cdof[(bda + dof) * 6 + component]) * qvel_value
        for dof in range(3, 6):
            index = bda + dof
            free_joint_cross_motion.extend((body, index, *vel))
            free_joint_cross_motion.extend(
                float(cdof[index * 6 + component]) for component in range(6))
            free_joint_cross_motion.extend(
                float(cdof_dot[index * 6 + component]) for component in range(6))
    arrays["free_joint_cross_motion"] = free_joint_cross_motion
    return {
        "time": float(data.time),
        "ncon": int(data.ncon),
        "nefc": int(data.nefc),
        "nisland": int(data.nisland),
        "nidof": int(data.nidof),
        "flags": {
            "flg_energypos": int(data.flg_energypos),
            "flg_energyvel": int(data.flg_energyvel),
            "flg_subtreevel": int(data.flg_subtreevel),
            "flg_rnepost": int(data.flg_rnepost),
        },
        "awake": awake_state,
        "contacts": [
            {
                "geom1": int(data.contact[index].geom1),
                "geom2": int(data.contact[index].geom2),
                "dist": float(data.contact[index].dist),
                "pos": data.contact[index].pos.tolist(),
                "frame": data.contact[index].frame.tolist(),
                "dim": int(data.contact[index].dim),
                "mu": float(data.contact[index].mu),
                "friction": data.contact[index].friction.tolist(),
            }
            for index in range(data.ncon)
        ],
        "arrays": arrays,
        "model": {
            "gravity": sim._model.opt.gravity.tolist(),
            "timestep": float(sim._model.opt.timestep),
            "disableflags": int(sim._model.opt.disableflags),
            "solver": int(sim._model.opt.solver),
            "options": {
                "integrator": int(sim._model.opt.integrator),
                "cone": int(sim._model.opt.cone),
                "jacobian": int(sim._model.opt.jacobian),
                "solver": int(sim._model.opt.solver),
                "iterations": int(sim._model.opt.iterations),
                "ls_iterations": int(sim._model.opt.ls_iterations),
                "noslip_iterations": int(sim._model.opt.noslip_iterations),
                "tolerance": float(sim._model.opt.tolerance),
                "ls_tolerance": float(sim._model.opt.ls_tolerance),
                "noslip_tolerance": float(sim._model.opt.noslip_tolerance),
                "impratio": float(sim._model.opt.impratio),
                "disableflags": int(sim._model.opt.disableflags),
                "enableflags": int(sim._model.opt.enableflags),
                "density": float(sim._model.opt.density),
                "viscosity": float(sim._model.opt.viscosity),
            },
            "sparse_jacobian": bool(MUJOCO_API.mj_isSparse(sim._model)),
            "M_rownnz": sim._model.M_rownnz.tolist(),
            "M_rowadr": sim._model.M_rowadr.tolist(),
            "M_colind": sim._model.M_colind.tolist(),
            "geom_bodyid": sim._model.geom_bodyid.tolist(),
            "body_rootid": sim._model.body_rootid.tolist(),
            "body_parentid": sim._model.body_parentid.tolist(),
            "body_dofadr": sim._model.body_dofadr.tolist(),
            "body_dofnum": sim._model.body_dofnum.tolist(),
            "dof_parentid": sim._model.dof_parentid.tolist(),
            "body_pos": sim._model.body_pos.ravel().tolist(),
            "body_quat": sim._model.body_quat.ravel().tolist(),
            "body_ipos": sim._model.body_ipos.ravel().tolist(),
            "body_iquat": sim._model.body_iquat.ravel().tolist(),
            "body_inertia": sim._model.body_inertia.ravel().tolist(),
            "body_mass": sim._model.body_mass.ravel().tolist(),
            "geom_pos": sim._model.geom_pos.ravel().tolist(),
            "geom_quat": sim._model.geom_quat.ravel().tolist(),
            "geom_size": sim._model.geom_size.ravel().tolist(),
            "geom_friction": sim._model.geom_friction.ravel().tolist(),
            "geom_condim": sim._model.geom_condim.ravel().tolist(),
            "geom_contype": sim._model.geom_contype.ravel().tolist(),
            "geom_conaffinity": sim._model.geom_conaffinity.ravel().tolist(),
            "jnt_axis": sim._model.jnt_axis.ravel().tolist(),
            "jnt_pos": sim._model.jnt_pos.ravel().tolist(),
            "jnt_qposadr": sim._model.jnt_qposadr.ravel().tolist(),
            "jnt_dofadr": sim._model.jnt_dofadr.ravel().tolist(),
            "jnt_type": sim._model.jnt_type.ravel().tolist(),
            "dof_jntid": sim._model.dof_jntid.ravel().tolist(),
        },
    }


def source_engine_snapshot_for_data(sim, data) -> dict[str, object]:
    """Take the usual diagnostic snapshot of a shadow MjData object."""
    live_data = sim._data
    sim._data = data
    try:
        return source_engine_snapshot(sim)
    finally:
        sim._data = live_data


def assert_exact_solver_input_snapshot(
        sim, expected: dict[str, object], label: str) -> None:
    """Fail closed unless every active fwdConstraint input matches bitwise."""
    actual = source_engine_snapshot(sim)
    scalar_fields = ("time", "ncon", "nefc", "nisland", "nidof")
    scalar_mismatches = {
        field: {"native": actual[field], "wasm": expected[field]}
        for field in scalar_fields if actual[field] != expected[field]
    }
    if actual["flags"] != expected.get("flags"):
        scalar_mismatches["flags"] = {
            "native": actual["flags"], "wasm": expected.get("flags")}
    if "awake" in expected and actual["awake"] != expected["awake"]:
        scalar_mismatches["awake"] = {
            "native": actual["awake"], "wasm": expected["awake"]}
    if actual["contacts"] != expected.get("contacts"):
        scalar_mismatches["contacts"] = {
            "native": actual["contacts"],
            "wasm": expected.get("contacts"),
        }

    expected_model = expected.get("model", {})
    actual_model = actual.get("model", {})
    model_mismatches = {
        field: {"native": actual_model.get(field), "wasm": value}
        for field, value in expected_model.items()
        if actual_model.get(field) != value
    }
    if set(actual_model) != set(expected_model):
        model_mismatches["<model-field-set>"] = {
            "native": sorted(actual_model), "wasm": sorted(expected_model)}

    expected_arrays = expected.get("arrays", {})
    actual_arrays = actual.get("arrays", {})
    sparse = bool(expected_model.get("sparse_jacobian", False))
    array_mismatches = {}
    for field in ENGINE_DIAGNOSTIC_FIELDS:
        if field in ENGINE_SPARSE_JACOBIAN_FIELDS and not sparse:
            continue
        if field not in expected_arrays or field not in actual_arrays:
            array_mismatches[field] = {
                "nativePresent": field in actual_arrays,
                "wasmPresent": field in expected_arrays,
            }
        elif actual_arrays[field] != expected_arrays[field]:
            left = actual_arrays[field]
            right = expected_arrays[field]
            differing = [index for index, (a, b) in enumerate(zip(left, right))
                         if a != b]
            array_mismatches[field] = {
                "nativeLength": len(left),
                "wasmLength": len(right),
                "differentCount": len(differing) + abs(len(left) - len(right)),
                "first": [{"index": index, "native": left[index],
                           "wasm": right[index]} for index in differing[:4]],
            }
    if scalar_mismatches or model_mismatches or array_mismatches:
        raise AssertionError(
            f"native MuJoCo solver input is not exactly equal to maintained "
            f"WASM at {label}: counts/flags/contacts="
            f"{json.dumps(scalar_mismatches, sort_keys=True)}, model="
            f"{json.dumps(model_mismatches, sort_keys=True)}, arrays="
            f"{json.dumps(array_mismatches, sort_keys=True)}")


def reconstruct_rne_bias(engine: dict[str, object], *, fma=None,
                         fused_kernels: frozenset[str] = frozenset(),
                         cross_fma_order: int = 0, dot_fma_order: int = 0,
                         dot_sum_order: int = 0
                         ) -> dict[str, list[float]]:
    """Reconstruct mj_rne(flg_acc=0) stages from public mjData/model arrays.

    This deliberately uses ordinary Python float operations: compare the
    reconstructed source/WASM dependencies first, then compare each
    reconstruction with MuJoCo's compiled qfrc_bias to expose contraction or
    accumulation differences inside the native kernels.
    """
    arrays = engine["arrays"]
    model = engine["model"]
    body_dofadr = model["body_dofadr"]
    body_dofnum = model["body_dofnum"]
    body_parentid = model["body_parentid"]
    body_count = len(body_parentid)
    cvel = arrays["cvel"]
    cdof = arrays["cdof"]
    cdof_dot = arrays["cdof_dot"]
    cinert = arrays["cinert"]
    qvel = arrays["qvel"]

    def mul_dof_vec(matrix: list[float], base: int, values: list[float],
                    value_base: int, count: int) -> list[float]:
        result = [0.0] * 6
        for dof in range(count):
            scale = float(values[value_base + dof])
            if scale != 0.0:
                for component in range(6):
                    product = float(matrix[base + dof * 6 + component])
                    if "dof" in fused_kernels and fma is not None:
                        result[component] = fma(product, scale, result[component])
                    else:
                        result[component] += product * scale
        return result

    def mul_inert_vec(inertia: list[float], vec: list[float]) -> list[float]:
        i = inertia
        v = vec
        if "inert" in fused_kernels and fma is not None:
            # Operation order from the original 3.12.0 arm64 library, not
            # merely left-to-right contraction of the C expression. In
            # particular component 2 starts with i[5]*v[1], and components
            # 3..5 round the negative product before the first fused add.
            return [
                fma(i[7], v[5], fma(-i[8], v[4], fma(i[4], v[2], fma(i[0], v[0], i[3]*v[1])))),
                fma(-i[6], v[5], fma(i[8], v[3], fma(i[5], v[2], fma(i[3], v[0], i[1]*v[1])))),
                fma(i[6], v[4], fma(-i[7], v[3], fma(i[2], v[2], fma(i[4], v[0], i[5]*v[1])))),
                fma(i[9], v[3], fma(i[8], v[1], -i[7]*v[2])),
                fma(i[9], v[4], fma(i[6], v[2], -i[8]*v[0])),
                fma(i[9], v[5], fma(i[7], v[0], -i[6]*v[1])),
            ]
        return [
            i[0]*v[0] + i[3]*v[1] + i[4]*v[2] - i[8]*v[4] + i[7]*v[5],
            i[3]*v[0] + i[1]*v[1] + i[5]*v[2] + i[8]*v[3] - i[6]*v[5],
            i[4]*v[0] + i[5]*v[1] + i[2]*v[2] - i[7]*v[3] + i[6]*v[4],
            i[8]*v[1] - i[7]*v[2] + i[9]*v[3],
            i[6]*v[2] - i[8]*v[0] + i[9]*v[4],
            i[7]*v[0] - i[6]*v[1] + i[9]*v[5],
        ]

    def cross_force(vel: list[float], force: list[float]) -> list[float]:
        if "cross" in fused_kernels and fma is not None:
            def pair(first_a: float, first_b: float,
                     second_a: float, second_b: float, bit: int) -> float:
                if cross_fma_order & (1 << bit):
                    return fma(second_a, second_b, first_a*first_b)
                return fma(first_a, first_b, second_a*second_b)

            result = [
                pair(-vel[2], force[1], vel[1], force[2], 0),
                pair(vel[2], force[0], -vel[0], force[2], 1),
                pair(-vel[1], force[0], vel[0], force[1], 2),
                pair(-vel[2], force[4], vel[1], force[5], 3),
                pair(vel[2], force[3], -vel[0], force[5], 4),
                pair(-vel[1], force[3], vel[0], force[4], 5),
            ]
            correction_pairs = (
                (-vel[5], force[4], vel[4], force[5]),
                (vel[5], force[3], -vel[3], force[5]),
                (-vel[4], force[3], vel[3], force[4]),
            )
            for index, (first_a, first_b, second_a, second_b) in enumerate(
                    correction_pairs):
                bit = 6 + index
                # Original arm64 RNE rounds the second cross product before
                # adding it to the first; it does not fuse across that sum.
                result[index] += pair(first_a, first_b, second_a, second_b, bit)
            return result
        result = [
            -vel[2]*force[1] + vel[1]*force[2],
            vel[2]*force[0] - vel[0]*force[2],
            -vel[1]*force[0] + vel[0]*force[1],
            -vel[2]*force[4] + vel[1]*force[5],
            vel[2]*force[3] - vel[0]*force[5],
            -vel[1]*force[3] + vel[0]*force[4],
        ]
        result[0] += -vel[5]*force[4] + vel[4]*force[5]
        result[1] += vel[5]*force[3] - vel[3]*force[5]
        result[2] += -vel[4]*force[3] + vel[3]*force[4]
        return result

    cacc = [[0.0] * 6 for _ in range(body_count)]
    gravity = model["gravity"]
    cacc[0][3:6] = [-float(value) for value in gravity]
    body_force = [[0.0] * 6 for _ in range(body_count)]
    dof_acceleration = [[0.0] * 6 for _ in range(body_count)]
    inertial_acceleration: list[float] = []
    inertial_velocity: list[float] = []
    cross_velocity: list[float] = []
    for body in range(1, body_count):
        dof_base = int(body_dofadr[body])
        dof_count = int(body_dofnum[body])
        parent = int(body_parentid[body])
        dof_acc = mul_dof_vec(cdof_dot, dof_base * 6, qvel, dof_base, dof_count)
        dof_acceleration[body] = dof_acc
        cacc[body] = [float(cacc[parent][i]) + dof_acc[i] for i in range(6)]
        inertia = [float(value) for value in cinert[body * 10:body * 10 + 10]]
        velocity = [float(value) for value in cvel[body * 6:body * 6 + 6]]
        acc_force = mul_inert_vec(inertia, cacc[body])
        vel_force = mul_inert_vec(inertia, velocity)
        correction = cross_force(velocity, vel_force)
        body_force[body] = [acc_force[i] + correction[i] for i in range(6)]
        inertial_acceleration.extend(acc_force)
        inertial_velocity.extend(vel_force)
        cross_velocity.extend(correction)

    # Match mj_rne's reverse body-tree accumulation; the world force is zero.
    body_force[0] = [0.0] * 6
    for body in range(body_count - 1, 0, -1):
        parent = int(body_parentid[body])
        if parent:
            body_force[parent] = [body_force[parent][i] + body_force[body][i]
                                  for i in range(6)]

    qfrc_bias = [0.0] * len(qvel)

    def dot6(axis: list[float], force: list[float]) -> float:
        if "dot" in fused_kernels and fma is not None:
            pairs = []
            for pair_index, (first, second) in enumerate(((0, 2), (1, 3), (4, 5))):
                if dot_fma_order & (1 << pair_index):
                    pairs.append(fma(axis[second], force[second],
                                     axis[first]*force[first]))
                else:
                    pairs.append(fma(axis[first], force[first],
                                     axis[second]*force[second]))
            if dot_sum_order == 1:
                return (pairs[0] + pairs[2]) + pairs[1]
            if dot_sum_order == 2:
                return (pairs[1] + pairs[2]) + pairs[0]
            return (pairs[0] + pairs[1]) + pairs[2]
        return (((axis[0]*force[0] + axis[2]*force[2]) +
                 (axis[1]*force[1] + axis[3]*force[3])) +
                (axis[4]*force[4] + axis[5]*force[5]))

    for body in range(1, body_count):
        dof_base = int(body_dofadr[body])
        dof_count = int(body_dofnum[body])
        for dof in range(dof_base, dof_base + dof_count):
            axis = [float(value) for value in cdof[dof * 6:dof * 6 + 6]]
            force = body_force[body]
            qfrc_bias[dof] = dot6(axis, force)

    return {
        "cacc": [value for body in cacc for value in body],
        "dof_acceleration": [value for body in dof_acceleration for value in body],
        "inertial_acceleration": inertial_acceleration,
        "inertial_velocity": inertial_velocity,
        "cross_velocity": cross_velocity,
        "body_force": [value for body in body_force for value in body],
        "qfrc_bias": qfrc_bias,
    }


def compare_rne_bias_reconstruction(source: dict[str, object],
                                    wasm: dict[str, object], label: str) -> None:
    source_reconstruction = reconstruct_rne_bias(source)
    wasm_reconstruction = reconstruct_rne_bias(wasm)

    def difference(left: list[float], right: list[float]) -> dict[str, object]:
        differing = [index for index, (a, b) in enumerate(zip(left, right)) if a != b]
        return {
            "count": len(differing),
            "first": [[index, left[index], right[index]] for index in differing[:4]],
            "maxAbs": max((abs(left[index] - right[index]) for index in differing),
                          default=0.0),
        }

    stage_differences = {
        stage: difference(source_reconstruction[stage], wasm_reconstruction[stage])
        for stage in source_reconstruction
    }
    source_actual = source["arrays"]["qfrc_bias"]
    wasm_actual = wasm["arrays"]["qfrc_bias"]
    reconstruction_error = {
        "source": difference(source_actual, source_reconstruction["qfrc_bias"]),
        "wasm": difference(wasm_actual, wasm_reconstruction["qfrc_bias"]),
    }
    try:
        native_fma = ctypes.CDLL(None).fma
        native_fma.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
        native_fma.restype = ctypes.c_double
    except (AttributeError, OSError):
        native_fma = None
    source_dof_cross_fma = reconstruct_rne_bias(
        source, fma=native_fma,
        fused_kernels=frozenset(("dof", "cross"))) if native_fma else None
    wasm_dof_cross_fma = reconstruct_rne_bias(
        wasm, fma=native_fma,
        fused_kernels=frozenset(("dof", "cross"))) if native_fma else None

    def projection_detail(engine: dict[str, object],
                         reconstruction: dict[str, list[float]],
                         dof: int, *, include_accumulation: bool = True
                         ) -> dict[str, object]:
        model = engine["model"]
        body = next((index for index, (address, count) in enumerate(zip(
            model["body_dofadr"], model["body_dofnum"]))
            if int(address) <= dof < int(address) + int(count)), None)
        if body is None:
            return {"dof": dof, "body": None}
        axis = [float(value) for value in engine["arrays"]["cdof"][dof*6:dof*6+6]]
        force = reconstruction["body_force"][body*6:body*6+6]
        dof_base = int(model["body_dofadr"][body])
        dof_count = int(model["body_dofnum"][body])
        acceleration_terms = []
        scalar_total = 0.0
        fused_total = 0.0
        cdof_dot = engine["arrays"]["cdof_dot"]
        qvel = engine["arrays"]["qvel"]
        if include_accumulation:
            for body_dof in range(dof_base, dof_base + dof_count):
                scale = float(qvel[body_dof])
                product = float(cdof_dot[body_dof*6 + 3]) * scale
                scalar_total += product
                if native_fma is not None:
                    fused_total = native_fma(float(cdof_dot[body_dof*6 + 3]),
                                             scale, fused_total)
                acceleration_terms.append({
                    "dof": body_dof,
                    "scale": scale,
                    "cdofDotComponent3": float(cdof_dot[body_dof*6 + 3]),
                    "roundedProduct": product,
                    "scalarAccumulated": scalar_total,
                    "fmaAccumulated": fused_total if native_fma is not None else None,
                })
        products = [axis[index] * force[index] for index in range(6)]
        pairs = [products[0] + products[2], products[1] + products[3],
                 products[4] + products[5]]
        return {
            "dof": dof,
            "body": body,
            "axis": axis,
            "bodyForce": force,
            "bodyDofAccelerationComponent3":
                reconstruction["dof_acceleration"][body*6 + 3],
            "component3DofAccumulation": acceleration_terms,
            "products": products,
            "dot6Pairs": pairs,
            "groupedDot6": (pairs[0] + pairs[1]) + pairs[2],
            "compiledQfrcBias": engine["arrays"]["qfrc_bias"][dof],
        }

    dof_zero_projection = {
        "source": projection_detail(source, source_reconstruction, 0),
        "wasm": projection_detail(wasm, wasm_reconstruction, 0),
    }
    if source_dof_cross_fma is not None and wasm_dof_cross_fma is not None:
        dof_zero_projection["sourceDofCrossFmaCandidate"] = projection_detail(
            source, source_dof_cross_fma, 0)
        dof_zero_projection["wasmDofCrossFmaCandidate"] = projection_detail(
            wasm, wasm_dof_cross_fma, 0)
    backend_differing_dofs = [
        index for index, (native_value, wasm_value) in enumerate(
            zip(source_actual, wasm_actual)) if native_value != wasm_value
    ]
    backend_differing_projections = [{
        "dof": dof,
        "sourceScalar": projection_detail(
            source, source_reconstruction, dof, include_accumulation=False),
        "wasmScalar": projection_detail(
            wasm, wasm_reconstruction, dof, include_accumulation=False),
        "sourceFusedDofCross": projection_detail(
            source, source_dof_cross_fma, dof, include_accumulation=False),
        "wasmFusedDofCross": projection_detail(
            wasm, wasm_dof_cross_fma, dof, include_accumulation=False),
    } for dof in backend_differing_dofs[:16]] if (
        source_dof_cross_fma is not None and wasm_dof_cross_fma is not None) else []
    fused_kernel_candidates = {}
    if native_fma is not None:
        kernel_names = ("dof", "inert", "cross", "dot")
        kernel_sets = [
            ("+".join(kernels), frozenset(kernels))
            for size in range(1, len(kernel_names) + 1)
            for kernels in itertools.combinations(kernel_names, size)
        ]
        for name, kernels in kernel_sets:
            source_candidate = reconstruct_rne_bias(
                source, fma=native_fma, fused_kernels=kernels)["qfrc_bias"]
            wasm_candidate = reconstruct_rne_bias(
                wasm, fma=native_fma, fused_kernels=kernels)["qfrc_bias"]
            fused_kernel_candidates[name] = {
                "sourceActualVsCandidate": difference(source_actual, source_candidate),
                "wasmActualVsCandidate": difference(wasm_actual, wasm_candidate),
            }
        ranked_source_candidates = sorted(
            ((name, values["sourceActualVsCandidate"]["maxAbs"],
              values["sourceActualVsCandidate"]["count"])
             for name, values in fused_kernel_candidates.items()),
            key=lambda candidate: (candidate[1], candidate[2], candidate[0]))
    else:
        ranked_source_candidates = []
    cross_order_search = None
    if native_fma is not None and ("event[195]" in label or "event[0]" in label):
        orderings = []
        kernels = frozenset(("dof", "cross"))
        for order in range(1 << 9):
            source_candidate = reconstruct_rne_bias(
                source, fma=native_fma, fused_kernels=kernels,
                cross_fma_order=order)["qfrc_bias"]
            wasm_candidate = reconstruct_rne_bias(
                wasm, fma=native_fma, fused_kernels=kernels,
                cross_fma_order=order)["qfrc_bias"]
            source_error = difference(source_actual, source_candidate)
            wasm_error = difference(wasm_actual, wasm_candidate)
            target_dofs = (3, 4, 5)
            source_target = [abs(source_actual[index] - source_candidate[index])
                             for index in target_dofs]
            wasm_target = [abs(wasm_actual[index] - wasm_candidate[index])
                           for index in target_dofs]
            orderings.append({
                "order": order,
                "source": source_error,
                "wasm": wasm_error,
                "targetDofs_3_4_5": {
                    "sourceMaxAbs": max(source_target),
                    "sourceExactCount": sum(value == 0 for value in source_target),
                    "sourceErrors": source_target,
                    "wasmMaxAbs": max(wasm_target),
                    "wasmExactCount": sum(value == 0 for value in wasm_target),
                    "wasmErrors": wasm_target,
                },
            })
        cross_order_search = sorted(
            orderings,
            key=lambda candidate: (
                candidate["source"]["maxAbs"],
                candidate["source"]["count"],
                candidate["wasm"]["maxAbs"],
                candidate["wasm"]["count"],
                candidate["order"],
            ))[:8]
        cross_order_target_search = sorted(
            orderings,
            key=lambda candidate: (
                candidate["targetDofs_3_4_5"]["sourceMaxAbs"],
                -candidate["targetDofs_3_4_5"]["sourceExactCount"],
                candidate["targetDofs_3_4_5"]["wasmMaxAbs"],
                candidate["targetDofs_3_4_5"]["wasmExactCount"],
                candidate["order"],
            ))[:8]
        exact_search = []
        backend_differing_dofs = [
            index for index, (native_value, wasm_value) in enumerate(
                zip(source_actual, wasm_actual)) if native_value != wasm_value
        ]
        for size in range(1, len(kernel_names) + 1):
            for kernel_tuple in itertools.combinations(kernel_names, size):
                kernels = frozenset(kernel_tuple)
                name = "+".join(kernel_tuple)
                order_range = range(1 << 9) if "cross" in kernels else range(1)
                for order in order_range:
                    candidate = reconstruct_rne_bias(
                        source, fma=native_fma, fused_kernels=kernels,
                        cross_fma_order=order)["qfrc_bias"]
                    target_errors = [abs(source_actual[index] - candidate[index])
                                     for index in backend_differing_dofs]
                    exact_search.append({
                        "kernels": name,
                        "crossFmaOrder": order,
                        "sourceExactCount": sum(value == 0 for value in target_errors),
                        "sourceMaxAbs": max(target_errors, default=0.0),
                        "sourceTargetErrors": target_errors,
                    })
        full_rne_candidate_search = sorted(
            exact_search,
            key=lambda candidate: (
                candidate["sourceMaxAbs"],
                -candidate["sourceExactCount"],
                candidate["kernels"],
                candidate["crossFmaOrder"],
            ))[:8]
        dot_order_search = []
        dot_kernels = frozenset(("dof", "cross", "dot"))
        # The hard rung-16 trace has three marbles (18 DOFs), but generated
        # lower-rung boards can contain fewer. Keep the fixed diagnostic focus
        # set while excluding DOFs that do not exist in this model.
        target_dofs = tuple(dof for dof in (3, 4, 5, 9, 10, 11, 12, 15, 16, 17)
                            if dof < len(source_actual))
        for cross_order in range(1 << 9):
            for dot_order in range(1 << 3):
                for sum_order in range(3):
                    candidate = reconstruct_rne_bias(
                        source, fma=native_fma, fused_kernels=dot_kernels,
                        cross_fma_order=cross_order,
                        dot_fma_order=dot_order,
                        dot_sum_order=sum_order)["qfrc_bias"]
                    errors = [abs(source_actual[index] - candidate[index])
                              for index in target_dofs]
                    dot_order_search.append({
                        "crossFmaOrder": cross_order,
                        "dotFmaOrder": dot_order,
                        "dotSumOrder": sum_order,
                        "exactCount": sum(value == 0 for value in errors),
                        "maxAbs": max(errors, default=0.0),
                        "errors": errors,
                    })
        dot_order_search = sorted(
            dot_order_search,
            key=lambda candidate: (
                candidate["maxAbs"], -candidate["exactCount"],
                candidate["crossFmaOrder"], candidate["dotFmaOrder"],
                candidate["dotSumOrder"],
            ))[:8]
    else:
        cross_order_target_search = None
        full_rne_candidate_search = None
        dot_order_search = None
    print(f"RNE RECONSTRUCTION {label}: " + json.dumps({
        "stages": stage_differences,
        "compiledVsReconstructedBias": reconstruction_error,
        "dofZeroProjection": dof_zero_projection,
        "backendDivergingDofProjections": backend_differing_projections,
        "nativeFmaKernelCandidates": fused_kernel_candidates,
        "fmaCandidateSourceRanking": ranked_source_candidates[:8],
        "crossFmaOrderSearch_dof_cross": cross_order_search,
        "crossFmaOrderTargetSearch_dofs_3_4_5": cross_order_target_search,
        "fullRneCandidateSearch_backendDivergentDofs":
            full_rne_candidate_search,
        "dotFmaOrderSearch_backendDivergentDofs": dot_order_search,
    }, sort_keys=True))


def contact_geometry_summary(contacts: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep contact geometry available when a diagnostic phase diverges."""
    fields = ("geom1", "geom2", "dist", "pos", "frame", "dim", "mu",
              "friction")
    return [{name: contact.get(name) for name in fields}
            for contact in contacts]


def compare_engine_snapshot(source: dict[str, object], wasm: dict[str, object],
                            label: str) -> None:
    fields = {}
    for group in ("arrays", "model"):
        for name, expected_values in wasm[group].items():
            if group == "arrays" and not (
                    engine_array_valid_at_phase(
                        name, label, source.get("nisland"),
                        source["model"].get("sparse_jacobian")) and
                    engine_array_valid_at_phase(
                        name, label, wasm.get("nisland"),
                        wasm["model"].get("sparse_jacobian"))):
                continue
            actual_values = source[group][name]
            if isinstance(expected_values, list):
                if len(actual_values) != len(expected_values):
                    fields[f"{group}.{name}"] = {
                        "sourceLength": len(actual_values),
                        "wasmLength": len(expected_values),
                    }
                    continue
                differences = [abs(float(a) - float(b))
                               for a, b in zip(actual_values, expected_values)]
                differing = [i for i, delta in enumerate(differences) if delta != 0]
                fields[f"{group}.{name}"] = {
                    "maxAbs": max(differences, default=0.0),
                    "differentCount": len(differing),
                    "firstIndex": differing[0] if differing else None,
                    "firstSource": actual_values[differing[0]] if differing else None,
                    "firstWasm": expected_values[differing[0]] if differing else None,
                    "firstDifferences": [
                        [index, actual_values[index], expected_values[index]]
                        for index in differing[:12]
                    ],
                }
            elif actual_values != expected_values:
                fields[f"{group}.{name}"] = {
                    "source": actual_values,
                    "wasm": expected_values,
                }
    scalar_counts = ("time", "ncon", "nefc", "nisland", "nidof")
    fields["counts"] = {
        "source": {key: source.get(key) for key in scalar_counts},
        "wasm": {key: wasm.get(key) for key in scalar_counts},
    }
    source_contacts = source["contacts"]
    wasm_contacts = wasm["contacts"]
    if source_contacts != wasm_contacts:
        fields["contacts"] = {
            "sourcePairs": [[item["geom1"], item["geom2"]]
                            for item in source_contacts],
            "wasmPairs": [[item["geom1"], item["geom2"]]
                          for item in wasm_contacts],
            "sourceGeometry": contact_geometry_summary(source_contacts),
            "wasmGeometry": contact_geometry_summary(wasm_contacts),
        }
    def cone_metrics(engine: dict[str, object]) -> list[dict[str, object]]:
        arrays = engine["arrays"]
        metrics = []
        for contact_index, contact in enumerate(engine["contacts"]):
            constraints = [index for index, (kind, identity) in enumerate(zip(
                arrays["efc_type"], arrays["efc_id"]))
                if kind == 7 and identity == contact_index]
            if not constraints:
                continue
            start = constraints[0]
            dimension = int(contact["dim"])
            force = arrays["efc_force"][start:start + dimension]
            friction = contact["friction"]
            scaled = [force[0] / contact["mu"]] + [
                force[index] / friction[index - 1]
                for index in range(1, dimension)
            ]
            tangent_norm = math.sqrt(sum(value * value for value in scaled[1:]))
            metrics.append({
                "contact": contact_index,
                "state": arrays["efc_state"][start],
                "muN": contact["mu"] * scaled[0],
                "tangentNorm": tangent_norm,
                "margin": contact["mu"] * scaled[0] - tangent_norm,
                "scaledForce": scaled,
            })
        return metrics
    cone_state_valid = all(
        engine_array_valid_at_phase(
            field, label, source.get("nisland"),
            source["model"].get("sparse_jacobian")) and
        engine_array_valid_at_phase(
            field, label, wasm.get("nisland"),
            wasm["model"].get("sparse_jacobian"))
        for field in ("efc_state", "efc_force"))
    if cone_state_valid:
        source_cone = cone_metrics(source)
        wasm_cone = cone_metrics(wasm)
        if source_cone != wasm_cone:
            fields["ellipticConeClassification"] = {
                "source": source_cone,
                "wasm": wasm_cone,
            }
    if label.endswith(".phase.probe_comVel"):
        actual = source["arrays"]["cdof_dot"]
        expected = wasm["arrays"]["cdof_dot"]
        dof_differences = [index for index, (left, right) in enumerate(
            zip(actual, expected)) if left != right]

        def reconstruct_comvel(engine: dict[str, object]) -> tuple[list[float], list[float], dict[int, list[float]]]:
            arrays = engine["arrays"]
            model = engine["model"]
            body_count = len(model["body_parentid"])
            computed_cvel = [0.0] * (6 * body_count)
            computed_cdof_dot = [0.0] * len(arrays["cdof_dot"])
            pre_cross_velocity: dict[int, list[float]] = {}

            def cross_motion(velocity: list[float], axis: list[float]) -> list[float]:
                output = [
                    -velocity[2] * axis[1] + velocity[1] * axis[2],
                    velocity[2] * axis[0] - velocity[0] * axis[2],
                    -velocity[1] * axis[0] + velocity[0] * axis[1],
                    -velocity[2] * axis[4] + velocity[1] * axis[5],
                    velocity[2] * axis[3] - velocity[0] * axis[5],
                    -velocity[1] * axis[3] + velocity[0] * axis[4],
                ]
                output[3] += -velocity[5] * axis[1] + velocity[4] * axis[2]
                output[4] += velocity[5] * axis[0] - velocity[3] * axis[2]
                output[5] += -velocity[4] * axis[0] + velocity[3] * axis[1]
                return output

            for body in range(1, body_count):
                parent = int(model["body_parentid"][body])
                velocity = computed_cvel[6 * parent:6 * parent + 6].copy()
                body_dof = int(model["body_dofadr"][body])
                dof_count = int(model["body_dofnum"][body])
                local = 0
                while local < dof_count:
                    dof = body_dof + local
                    joint = int(model["dof_jntid"][dof])
                    joint_type = int(model["jnt_type"][joint])
                    if joint_type == 0:  # free: translation, then ball rotation
                        for component in range(6):
                            velocity[component] += sum(
                                arrays["cdof"][6 * (dof + axis) + component] *
                                arrays["qvel"][dof + axis]
                                for axis in range(3))
                        for rotation in range(3):
                            rotation_dof = dof + 3 + rotation
                            axis = arrays["cdof"][6 * rotation_dof:
                                                  6 * rotation_dof + 6]
                            pre_cross_velocity[rotation_dof] = velocity.copy()
                            computed_cdof_dot[6 * rotation_dof:
                                              6 * rotation_dof + 6] = cross_motion(
                                                  velocity, axis)
                        for component in range(6):
                            velocity[component] += sum(
                                arrays["cdof"][6 * (dof + 3 + axis) + component] *
                                arrays["qvel"][dof + 3 + axis]
                                for axis in range(3))
                        local += 6
                    elif joint_type == 1:  # ball
                        for rotation in range(3):
                            rotation_dof = dof + rotation
                            axis = arrays["cdof"][6 * rotation_dof:
                                                  6 * rotation_dof + 6]
                            pre_cross_velocity[rotation_dof] = velocity.copy()
                            computed_cdof_dot[6 * rotation_dof:
                                              6 * rotation_dof + 6] = cross_motion(
                                                  velocity, axis)
                        for component in range(6):
                            velocity[component] += sum(
                                arrays["cdof"][6 * (dof + axis) + component] *
                                arrays["qvel"][dof + axis]
                                for axis in range(3))
                        local += 3
                    else:
                        axis = arrays["cdof"][6 * dof:6 * dof + 6]
                        pre_cross_velocity[dof] = velocity.copy()
                        computed_cdof_dot[6 * dof:6 * dof + 6] = cross_motion(
                            velocity, axis)
                        for component in range(6):
                            velocity[component] += (
                                arrays["cdof"][6 * dof + component] *
                                arrays["qvel"][dof])
                        local += 1
                computed_cvel[6 * body:6 * body + 6] = velocity
            return computed_cvel, computed_cdof_dot, pre_cross_velocity

        source_cvel, source_cdof_dot, source_pre_cross = reconstruct_comvel(source)
        wasm_cvel, wasm_cdof_dot, wasm_pre_cross = reconstruct_comvel(wasm)
        mappings = []
        for index in dof_differences:
            dof, component = divmod(index, 6)
            body = next((body_index for body_index, (start, count) in enumerate(
                zip(wasm["model"]["body_dofadr"],
                    wasm["model"]["body_dofnum"]))
                         if start <= dof < start + count), None)
            if body is None:
                continue
            axis_start = 6 * dof
            source_axis = source["arrays"]["cdof"][axis_start:axis_start + 6]
            wasm_axis = wasm["arrays"]["cdof"][axis_start:axis_start + 6]
            source_velocity = source_pre_cross.get(dof)
            wasm_velocity = wasm_pre_cross.get(dof)
            if source_velocity is None or wasm_velocity is None:
                continue
            mappings.append({
                "dof": dof,
                "component": component,
                "body": body,
                "sourceOutput": actual[index],
                "wasmOutput": expected[index],
                "sourceOperands": {
                    "velocityBeforeCross": source_velocity,
                    "axis": source_axis,
                    "scalarCrossMotion": source_cdof_dot[index],
                },
                "wasmOperands": {
                    "velocityBeforeCross": wasm_velocity,
                    "axis": wasm_axis,
                    "scalarCrossMotion": wasm_cdof_dot[index],
                },
            })
        source_final_deltas = [
            abs(left - right) for left, right in zip(
                source_cvel, source["arrays"]["cvel"])]
        wasm_final_deltas = [
            abs(left - right) for left, right in zip(
                wasm_cvel, wasm["arrays"]["cvel"])]
        if mappings:
            print("SYNCHRONIZED CROSS-MOTION INPUTS " + json.dumps(
                {"label": label, "differences": mappings,
                 "reconstructedFinalCvelMaxAbs": {
                     "source": max(source_final_deltas, default=0.0),
                     "wasm": max(wasm_final_deltas, default=0.0)},
                 "reconstructedCdotMaxAbs": {
                     "source": max((abs(a-b) for a, b in zip(
                         source_cdof_dot, actual)), default=0.0),
                     "wasm": max((abs(a-b) for a, b in zip(
                         wasm_cdof_dot, expected)), default=0.0)}},
                sort_keys=True))
    if label.endswith("phase.comPos"):
        source_cinert = source["arrays"]["cinert"]
        wasm_cinert = wasm["arrays"]["cinert"]
        differing_cinert = [i for i, (left, right) in enumerate(
            zip(source_cinert, wasm_cinert)) if left != right]
        if differing_cinert:
            index = differing_cinert[0]
            body, component = divmod(index, 10)
            root = source["model"]["body_rootid"][body]
            offset_start, matrix_start = 3*body, 9*body
            source_offset = [source["arrays"]["xipos"][offset_start+i] -
                             source["arrays"]["subtree_com"][3*root+i]
                             for i in range(3)]
            wasm_offset = [wasm["arrays"]["xipos"][offset_start+i] -
                           wasm["arrays"]["subtree_com"][3*root+i]
                           for i in range(3)]
            inertia_start = 3*body
            print("FIRST INERTCOM OUTPUT SPLIT " + json.dumps({
                "label": label, "body": body, "component": component,
                "sourceOutput": source_cinert[10*body:10*body+10],
                "wasmOutput": wasm_cinert[10*body:10*body+10],
                "sourceInputs": {
                    "inertia": source["model"]["body_inertia"][
                        inertia_start:inertia_start+3],
                    "mass": source["model"]["body_mass"][body],
                    "rotation": source["arrays"]["ximat"][
                        matrix_start:matrix_start+9],
                    "xipos": source["arrays"]["xipos"][
                        offset_start:offset_start+3],
                    "subtreeCom": source["arrays"]["subtree_com"][
                        3*root:3*root+3], "offset": source_offset},
                "wasmInputs": {
                    "inertia": wasm["model"]["body_inertia"][
                        inertia_start:inertia_start+3],
                    "mass": wasm["model"]["body_mass"][body],
                    "rotation": wasm["arrays"]["ximat"][
                        matrix_start:matrix_start+9],
                    "xipos": wasm["arrays"]["xipos"][
                        offset_start:offset_start+3],
                    "subtreeCom": wasm["arrays"]["subtree_com"][
                        3*root:3*root+3], "offset": wasm_offset}},
                sort_keys=True))
    print(f"ENGINE DIAGNOSTIC {label}: " + json.dumps(
        {name: value for name, value in fields.items()
         if value.get("differentCount", 0) or value.get("maxAbs", 0) or
         "source" in value or "sourceLength" in value}, sort_keys=True))


def report_phase_value_origin(source: dict[str, object],
                              wasm: dict[str, object],
                              previous_source: dict[str, object],
                              previous_wasm: dict[str, object],
                              label: str) -> None:
    """Separate newly-produced phase differences from carried/stale values.

    MuJoCo keeps many mjData arrays between calls. A phase snapshot therefore
    contains both outputs produced by that phase and values left by an earlier
    phase/substep. This diagnostic does not change parity assertions; it labels
    a currently unequal array as new, updated-existing, or unchanged/carried
    by comparing each engine's array with its own immediately preceding
    snapshot.
    """
    if os.environ.get("NW_MARBLE_DIAGNOSTIC_PHASE_UPDATES") != "1":
        return

    categories: dict[str, list[str]] = {
        "new": [], "updatedExisting": [], "carried": [],
    }
    source_arrays = source["arrays"]
    wasm_arrays = wasm["arrays"]
    previous_source_arrays = previous_source["arrays"]
    previous_wasm_arrays = previous_wasm["arrays"]
    for name in sorted(source_arrays.keys() & wasm_arrays.keys()):
        if not (
                engine_array_valid_at_phase(
                    name, label, source.get("nisland"),
                    source["model"].get("sparse_jacobian")) and
                engine_array_valid_at_phase(
                    name, label, wasm.get("nisland"),
                    wasm["model"].get("sparse_jacobian"))):
            continue
        source_values = source_arrays[name]
        wasm_values = wasm_arrays[name]
        if not isinstance(source_values, list) or not isinstance(wasm_values, list):
            continue
        current_differs = source_values != wasm_values
        if not current_differs:
            continue

        old_source = previous_source_arrays.get(name)
        old_wasm = previous_wasm_arrays.get(name)
        if not isinstance(old_source, list) or not isinstance(old_wasm, list):
            categories["new"].append(name)
            continue
        previous_differs = old_source != old_wasm
        source_changed = source_values != old_source
        wasm_changed = wasm_values != old_wasm
        if not previous_differs:
            categories["new"].append(name)
        elif source_changed or wasm_changed:
            categories["updatedExisting"].append(name)
        else:
            categories["carried"].append(name)

    if any(categories.values()):
        summary = {
            f"{name}Count": len(fields)
            for name, fields in categories.items()
        }
        summary.update({
            name: fields[:16]
            for name, fields in categories.items()
            if fields
        })
        print("PHASE VALUE ORIGIN " + label + ": " + json.dumps(
            summary, sort_keys=True))


def close(actual: float, expected: float, tolerance: float,
          context: str, maxima: dict[str, float],
          exceedances: dict[str, dict[str, object]]) -> None:
    global first_exceedance
    delta = abs(actual - expected)
    field = context.split(".")[-1]
    maxima[field] = max(maxima.get(field, 0.0), delta)
    if not math.isfinite(actual) or not math.isfinite(expected) or delta > tolerance:
        if first_exceedance is None:
            first_exceedance = {
                "context": context,
                "source": actual,
                "wasm": expected,
                "delta": delta,
                "tolerance": tolerance,
            }
        item = exceedances.setdefault(field, {
            "count": 0,
            "maxDelta": -1.0,
            "tolerance": tolerance,
            "worstContext": "",
            "source": 0.0,
            "wasm": 0.0,
        })
        item["count"] += 1
        if not math.isfinite(delta):
            item["maxDelta"] = "non-finite"
            item["worstContext"] = context
            item["source"] = str(actual)
            item["wasm"] = str(expected)
        elif item["maxDelta"] != "non-finite" and delta > item["maxDelta"]:
            item["maxDelta"] = delta
            item["worstContext"] = context
            item["source"] = actual
            item["wasm"] = expected


def compare_snapshot(actual: dict[str, object], expected: dict[str, object],
                     event_index: int, maxima: dict[str, float],
                     exceedances: dict[str, dict[str, object]],
                     contact_mismatches: list[dict[str, object]],
                     continue_contact_mismatch: bool = False) -> None:
    prefix = f"event[{event_index}]"
    if len(actual["marbles"]) != len(expected["marbles"]):
        raise AssertionError(f"{prefix}.marbles: count differs")
    for index, (source, wasm) in enumerate(zip(actual["marbles"], expected["marbles"])):
        stem = f"{prefix}.marble[{index}]"
        if len(source["values"]) != 13 or len(wasm["values"]) != 13:
            raise AssertionError(
                f"{stem}.values: expected 13 components, "
                f"source={len(source['values'])}, WASM={len(wasm['values'])}")
        if source["state"] != wasm["state"] or source["over"] != wasm["over"]:
            raise AssertionError(
                f"{stem}: source state/over={source['state']}/{source['over']}, "
                f"WASM={wasm['state']}/{wasm['over']}")
        for value_index, (source_value, wasm_value) in enumerate(
                zip(source["values"], wasm["values"])):
            if value_index < 3:
                tolerance = POSITION_TOLERANCE
            elif value_index < 6:
                tolerance = VELOCITY_TOLERANCE
            elif value_index < 10:
                tolerance = QUATERNION_TOLERANCE
            else:
                tolerance = ANGULAR_VELOCITY_TOLERANCE
            close(source_value, wasm_value, tolerance,
                  f"{stem}.value[{value_index}]", maxima, exceedances)
    for field in ("roll", "pitch", "elapsed", "struck", "nudgeDue"):
        tolerance = (ANGULAR_VELOCITY_TOLERANCE if field == "struck" else
                     TIME_TOLERANCE if field in ("elapsed", "nudgeDue") else
                     1e-10)
        close(actual[field], expected[field], tolerance,
              f"{prefix}.{field}", maxima, exceedances)
    for field in ("home", "lost", "cupped", "lostThisStep"):
        if actual[field] != expected[field]:
            raise AssertionError(
                f"{prefix}.{field}: source={actual[field]}, WASM={expected[field]}")
    if "contacts" in actual and "contacts" in expected:
        source_contacts = sorted((item["geom1"], item["geom2"])
                                 for item in actual["contacts"])
        wasm_contacts = sorted((item["geom1"], item["geom2"])
                               for item in expected["contacts"])
        if source_contacts != wasm_contacts:
            contact_mismatches.append({
                "event": event_index,
                "source": source_contacts,
                "wasm": wasm_contacts,
            })
            if not continue_contact_mismatch:
                raise AssertionError(
                    f"{prefix}.contacts: native pairs={source_contacts}, "
                    f"WASM pairs={wasm_contacts}")


def summarize_snapshot_deltas(actual: dict[str, object],
                              expected: dict[str, object],
                              event_index: int) -> dict[str, object]:
    """Return compact per-event continuous-state deltas for drift analysis."""
    fields = {
        "position": range(0, 3),
        "linearVelocity": range(3, 6),
        "quaternion": range(6, 10),
        "angularVelocity": range(10, 13),
    }
    maxima: dict[str, tuple[float, int, int]] = {
        name: (0.0, -1, -1) for name in fields
    }
    for marble_index, (source_marble, wasm_marble) in enumerate(
            zip(actual["marbles"], expected["marbles"])):
        for name, indices in fields.items():
            for value_index in indices:
                delta = abs(source_marble["values"][value_index] -
                            wasm_marble["values"][value_index])
                if delta > maxima[name][0]:
                    maxima[name] = (delta, marble_index, value_index)
    row: dict[str, object] = {"event": event_index}
    for name, (delta, marble_index, value_index) in maxima.items():
        row[name] = {"maxAbs": delta, "marble": marble_index,
                     "valueIndex": value_index}
    for name in ("roll", "pitch", "elapsed", "struck", "nudgeDue"):
        row[name] = {"abs": abs(float(actual[name]) - float(expected[name]))}
    if "contacts" in actual and "contacts" in expected:
        source_pairs = sorted((item["geom1"], item["geom2"])
                              for item in actual["contacts"])
        wasm_pairs = sorted((item["geom1"], item["geom2"])
                            for item in expected["contacts"])
        row["contacts"] = {
            "samePairs": source_pairs == wasm_pairs,
            "sourceCount": len(source_pairs),
            "wasmCount": len(wasm_pairs),
            "sourceOnly": [list(pair) for pair in
                           sorted(set(source_pairs) - set(wasm_pairs))],
            "wasmOnly": [list(pair) for pair in
                         sorted(set(wasm_pairs) - set(source_pairs))],
        }
    return row


def write_state_delta_rows(destination: Path,
                           rows: list[dict[str, object]]) -> None:
    """Persist collected rows, including a focused replay's partial prefix."""
    destination.write_text("".join(
        json.dumps(row, sort_keys=True) + "\n" for row in rows))


def sync_source_from_wasm_snapshot(sim, snapshot: dict[str, object]) -> None:
    """Replace source wrapper state to isolate one backend step from prior drift."""
    if len(sim.marbles) != len(snapshot["marbles"]):
        raise AssertionError("cannot synchronize different marble counts")
    for marble, source_state in zip(sim.marbles, snapshot["marbles"]):
        (marble.x, marble.y, marble.z, marble.vx, marble.vy, marble.vz,
         marble.qw, marble.qx, marble.qy, marble.qz,
         marble.wx, marble.wy, marble.wz) = source_state["values"]
        marble.state = source_state["state"]
        hole_index = source_state["over"]
        marble.over = None if hole_index is None else sim.tray.holes[hole_index]
    sim.roll = snapshot["roll"]
    sim.pitch = snapshot["pitch"]
    sim.elapsed = snapshot["elapsed"]
    sim.struck_this_step = snapshot["struck"]
    sim.cupped_this_step = snapshot["cupped"]
    sim.lost_this_step = snapshot["lostThisStep"]
    if "qaccWarmstart" in snapshot:
        sim._data.qacc_warmstart[:] = snapshot["qaccWarmstart"]
    engine = snapshot.get("engine")
    if engine is not None:
        for field in ENGINE_DIAGNOSTIC_FIELDS:
            # Older retained traces predate newly-added diagnostic arrays.
            # Those arrays were not captured by the WASM side and therefore
            # cannot be synchronized; leave the native allocator value alone
            # rather than turning a valid historical trace into a harness
            # failure.
            if field not in engine["arrays"]:
                continue
            values = engine["arrays"][field]
            target = getattr(sim._data, field).ravel()
            if target.size != len(values):
                raise AssertionError(
                    f"cannot synchronize engine array {field}: "
                    f"native size={target.size}, WASM size={len(values)}")
            target[:] = values
        model = engine["model"]
        for field in ("M_rownnz", "M_rowadr", "M_colind"):
            actual = getattr(sim._model, field).tolist()
            if actual != model[field]:
                raise AssertionError(
                    f"native/WASM sparse mass layout mismatch in {field}")
        sim._model.opt.gravity[:] = model["gravity"]
        sim._model.opt.timestep = model["timestep"]
        for field in ("geom_contype", "geom_conaffinity"):
            getattr(sim._model, field)[:] = model[field]


def sync_source_engine_from_wasm_snapshot(
        sim, engine: dict[str, object], *,
        include_solver_outputs: bool = False) -> None:
    """Copy a captured MuJoCo phase into native data before an isolated step."""
    data = sim._data
    data.time = engine["time"]
    data.ncon = engine["ncon"]
    data.nefc = engine["nefc"]
    for field in ENGINE_DIAGNOSTIC_FIELDS:
        if (field in ENGINE_SOLVER_OUTPUT_FIELDS and
                not include_solver_outputs):
            continue
        # Keep old diagnostic traces usable after the engine snapshot schema
        # grows. Missing fields are deliberately not overwritten.
        if field not in engine["arrays"]:
            continue
        values = engine["arrays"][field]
        target = getattr(data, field).ravel()
        if target.size != len(values):
            raise AssertionError(
                f"cannot synchronize engine array {field}: "
                f"native size={target.size}, WASM size={len(values)}")
        target[:] = values
    awake = engine.get("awake")
    if awake is not None:
        for field in ("nbody_awake", "nparent_awake", "nv_awake"):
            setattr(data, field, awake[field])
        for field in ("body_awake", "body_awake_ind", "parent_awake_ind",
                      "dof_awake_ind"):
            getattr(data, field)[:] = awake[field]
    for field, value in engine.get("flags", {}).items():
        setattr(data, field, value)
    contacts = engine["contacts"]
    if len(contacts) != int(data.ncon):
        raise AssertionError(
            f"captured contact count {len(contacts)} != ncon {data.ncon}")
    for index, source in enumerate(contacts):
        target = data.contact[index]
        target.geom1 = source["geom1"]
        target.geom2 = source["geom2"]
        target.dist = source["dist"]
        target.pos[:] = source["pos"]
        target.frame[:] = source["frame"]
        target.dim = source["dim"]
        target.mu = source["mu"]
        target.friction[:] = source["friction"]
    model = engine["model"]
    sim._model.opt.gravity[:] = model["gravity"]
    sim._model.opt.timestep = model["timestep"]
    mismatched_arrays = [
        field for field in ENGINE_DIAGNOSTIC_FIELDS
        if include_solver_outputs or field not in ENGINE_SOLVER_OUTPUT_FIELDS
        if field in engine["arrays"]
        if getattr(data, field).ravel().tolist() != engine["arrays"][field]
    ]
    mismatched_contacts = []
    for index, expected in enumerate(contacts):
        actual = data.contact[index]
        for field in ("geom1", "geom2", "dim"):
            if int(getattr(actual, field)) != expected[field]:
                mismatched_contacts.append((index, field))
        for field in ("dist", "mu"):
            if float(getattr(actual, field)) != expected[field]:
                mismatched_contacts.append((index, field))
        for field in ("pos", "frame", "friction"):
            if getattr(actual, field).tolist() != expected[field]:
                mismatched_contacts.append((index, field))
    if mismatched_arrays or mismatched_contacts:
        mismatch_details = {}
        for field in mismatched_arrays:
            actual = getattr(data, field).ravel().tolist()
            expected = engine["arrays"][field]
            mismatch_details[field] = [
                (index, actual[index], expected[index])
                for index in range(min(len(actual), len(expected)))
                if actual[index] != expected[index]][:8]
        raise AssertionError(
            "native engine failed exact WASM solver-input synchronization: "
            f"arrays={mismatched_arrays}, details={mismatch_details}, "
            f"contacts={mismatched_contacts}")


def main() -> int:
    global MUJOCO_API, RNE_TRACE_LIBRARY, NOSLIP_TRACE_LIBRARY, FREE_SOLVE_LIBRARY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--require-maintained-browser-runtime", action="store_true",
                        help="require the trace's core and MuJoCo files to match the current physics manifest")
    parser.add_argument("--provenance-json", type=Path,
                        help="write the browser artifacts and active native MuJoCo wheel identity")
    parser.add_argument("--native-rne-trace-lib", type=Path,
                        help="optional temporary MuJoCo build exporting mj_rne_trace")
    parser.add_argument("--native-noslip-trace-lib", type=Path,
                        help="temporary clean-source MuJoCo library exporting no-slip residual traces")
    parser.add_argument("--results-only", action="store_true",
                        help="compare terminal outcome/result without per-frame snapshots")
    parser.add_argument("--sync-before-event", type=int,
                        help="diagnostically copy the previous WASM snapshot into native before this event")
    parser.add_argument("--diagnostic-sync-every-event", action="store_true",
                        help="copy each previous WASM snapshot into native before replaying the next event; skips terminal-result acceptance")
    parser.add_argument("--diagnostic-sync-every-substep", action="store_true",
                        help="compare and synchronize native state after each instrumented physics substep; skips terminal-result acceptance")
    parser.add_argument("--diagnostic-split-step", action="store_true",
                        help="compare MuJoCo state after mj_step1 before mj_step2; use a trace captured with NW_MARBLE_PLAY_TRACE_SPLIT_STEP=1")
    parser.add_argument("--diagnostic-phase-step", action="store_true",
                        help="replay mj_step1 as its public forward-dynamics phases and compare each phase; requires an opt-in phase trace")
    parser.add_argument("--diagnostic-newton-trace", action="store_true",
                        help="capture native and WASM Newton iteration states; requires a matching diagnostic MuJoCo library and NW_MARBLE_PLAY_TRACE_NEWTON=1 trace")
    parser.add_argument("--diagnostic-preparation-jsonl", type=Path,
                        help="write native initialized preparation captures with exact-input whole-solver qualification; requires --diagnostic-validate-solver-trace-lib")
    parser.add_argument("--diagnostic-validate-solver-trace-lib", action="store_true",
                        help="run the instrumented solver on a copied MjData and compare its outputs exactly with the active Python MuJoCo wheel; requires --diagnostic-newton-trace and --diagnostic-sync-before-fwdconstraint")
    parser.add_argument("--diagnostic-validate-solver-trace-event", type=int,
                        help="limit --diagnostic-validate-solver-trace-lib and its exact-input sync to one event")
    parser.add_argument("--diagnostic-solver-output-json", type=Path,
                        help="write exact-input active-wheel solver outputs for comparison with a diagnostic WASM build")
    parser.add_argument("--diagnostic-solver-output-event", type=int,
                        help="capture active-wheel and browser solver outputs for one synchronized event")
    parser.add_argument("--diagnostic-solver-output-substep", type=int,
                        help="substep to capture with --diagnostic-solver-output-event")
    parser.add_argument("--diagnostic-sync-before-fwdconstraint", action="store_true",
                        help="replace native engine state with the captured WASM fwdAcceleration snapshot before fwdConstraint; diagnostic only")
    parser.add_argument("--diagnostic-noslip-residual-trace", action="store_true",
                        help="capture clean-source native no-slip residual operands after syncing fwdAcceleration; requires an instrumented native library")
    parser.add_argument("--diagnostic-sync-before-implicit", action="store_true",
                        help="replace native engine state with the captured WASM checkAcc snapshot before mj_implicit; diagnostic only")
    parser.add_argument("--diagnostic-probe-free-solve", action="store_true",
                        help="compare read-only native free-joint solve probes at checkAcc without synchronizing state")
    parser.add_argument("--diagnostic-sync-before-step1", action="store_true",
                        help="replace native engine state with the captured WASM mj_step1 input before each instrumented substep; diagnostic only")
    parser.add_argument("--diagnostic-sync-before-rne", action="store_true",
                        help="replace the isolated native probe data with the captured WASM reference-constraint snapshot before mj_rne")
    parser.add_argument("--diagnostic-stop-after-event", type=int,
                        help="stop successfully after capturing/comparing this event; skips terminal-result acceptance")
    parser.add_argument("--diagnostic-continue-contact-mismatches", action="store_true",
                        help="record contact-set differences and continue numeric analysis; not an acceptance mode")
    parser.add_argument("--diagnostic-state-delta-jsonl", type=Path,
                        help="write per-event max native/WASM state deltas for drift analysis")
    parser.add_argument("--diagnostic-contact-event", type=int, action="append",
                        default=[], help="also print full contact geometry for this event; repeatable")
    args = parser.parse_args()
    if args.diagnostic_preparation_jsonl and not args.diagnostic_validate_solver_trace_lib:
        parser.error("preparation captures require exact active-wheel solver-library validation")
    if ((args.diagnostic_solver_output_event is None) !=
            (args.diagnostic_solver_output_substep is None)):
        parser.error("solver output event and substep must be specified together")
    if args.diagnostic_solver_output_event is not None:
        if args.diagnostic_solver_output_json is None:
            parser.error("solver output event/substep requires --diagnostic-solver-output-json")
        if not (args.diagnostic_phase_step and
                args.diagnostic_sync_before_fwdconstraint):
            parser.error("solver output capture requires --diagnostic-phase-step and --diagnostic-sync-before-fwdconstraint")
        if args.diagnostic_solver_output_event < 0 or args.diagnostic_solver_output_substep < 0:
            parser.error("solver output event and substep must be nonnegative")
    source_root = args.source_root.resolve()
    if not (source_root / "neural_workshop/marblemaze.py").is_file():
        raise SystemExit(f"not an original Neural Workshop checkout: {source_root}")
    sys.path.insert(0, str(source_root))
    import mujoco
    free_solve_library_path = os.environ.get("NW_MARBLE_FREE_SOLVE_LIBRARY")
    if free_solve_library_path:
        FREE_SOLVE_LIBRARY = ctypes.CDLL(free_solve_library_path)
        FREE_SOLVE_LIBRARY.mj_copyData.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        FREE_SOLVE_LIBRARY.mj_copyData.restype = ctypes.c_void_p
        FREE_SOLVE_LIBRARY.mjd_smooth_vel.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        FREE_SOLVE_LIBRARY.mjd_smooth_vel.restype = None
        FREE_SOLVE_LIBRARY.mjd_freeBias_vel.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
            ctypes.POINTER(ctypes.c_double)]
        FREE_SOLVE_LIBRARY.mjd_freeBias_vel.restype = None
        if hasattr(FREE_SOLVE_LIBRARY, "mjd_freeBias_vel_trace"):
            FREE_SOLVE_LIBRARY.mjd_freeBias_vel_trace.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                ctypes.POINTER(ctypes.c_double)]
            FREE_SOLVE_LIBRARY.mjd_freeBias_vel_trace.restype = None
        if hasattr(FREE_SOLVE_LIBRARY, "mjd_freeJoint_qDeriv_probe"):
            FREE_SOLVE_LIBRARY.mjd_freeJoint_qDeriv_probe.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                ctypes.POINTER(ctypes.c_double)]
            FREE_SOLVE_LIBRARY.mjd_freeJoint_qDeriv_probe.restype = None
        FREE_SOLVE_LIBRARY.mjd_freeMhat.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_double,
            ctypes.POINTER(ctypes.c_double)]
        FREE_SOLVE_LIBRARY.mjd_freeMhat.restype = ctypes.c_int
        FREE_SOLVE_LIBRARY.mju_factorLU6.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_int)]
        FREE_SOLVE_LIBRARY.mju_factorLU6.restype = ctypes.c_int
        FREE_SOLVE_LIBRARY.mju_solveLU6.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_int)]
        FREE_SOLVE_LIBRARY.mju_solveLU6.restype = None
        FREE_SOLVE_LIBRARY.mj_deleteData.argtypes = [ctypes.c_void_p]
        FREE_SOLVE_LIBRARY.mj_deleteData.restype = None
        FREE_SOLVE_LIBRARY.mju_addToScl.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
            ctypes.c_double, ctypes.c_int]
        FREE_SOLVE_LIBRARY.mju_addToScl.restype = None
        FREE_SOLVE_LIBRARY.mj_integratePos.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double), ctypes.c_double]
        FREE_SOLVE_LIBRARY.mj_integratePos.restype = None
    if args.native_rne_trace_lib is not None:
        RNE_TRACE_LIBRARY = ctypes.CDLL(str(args.native_rne_trace_lib.resolve()))
        if args.diagnostic_newton_trace:
            RNE_TRACE_LIBRARY.mj_rne_trace_size.argtypes = [ctypes.c_void_p]
            RNE_TRACE_LIBRARY.mj_rne_trace_size.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_rne_trace.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_double)]
            RNE_TRACE_LIBRARY.mj_rne_trace.restype = None
            RNE_TRACE_LIBRARY.mj_solver_trace_run.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p]
            RNE_TRACE_LIBRARY.mj_solver_trace_run.restype = None
            RNE_TRACE_LIBRARY.mj_solver_trace_size.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_solver_trace_records.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_solver_trace_copy.argtypes = [
                ctypes.POINTER(ctypes.c_double)]
            RNE_TRACE_LIBRARY.mj_solver_trace_copy.restype = None
            RNE_TRACE_LIBRARY.mj_solver_sparse_input_size.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_solver_sparse_input_copy.argtypes = [
                ctypes.POINTER(ctypes.c_double)]
            RNE_TRACE_LIBRARY.mj_solver_sparse_input_copy.restype = None
            RNE_TRACE_LIBRARY.mj_solver_constraint_input_size.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_solver_constraint_input_copy.argtypes = [
                ctypes.POINTER(ctypes.c_double)]
            RNE_TRACE_LIBRARY.mj_solver_constraint_input_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY,
                       "mj_solver_constraint_iteration_trace_size"):
                RNE_TRACE_LIBRARY.mj_solver_constraint_iteration_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_solver_constraint_iteration_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_solver_constraint_iteration_trace_copy.restype = None
            RNE_TRACE_LIBRARY.mj_constraint_update_trace_size.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_constraint_update_trace_copy.argtypes = [
                ctypes.POINTER(ctypes.c_double)]
            RNE_TRACE_LIBRARY.mj_constraint_update_trace_copy.restype = None
            RNE_TRACE_LIBRARY.mj_constraint_state_trace_size.restype = ctypes.c_int
            RNE_TRACE_LIBRARY.mj_constraint_state_trace_copy.argtypes = [
                ctypes.POINTER(ctypes.c_double)]
            RNE_TRACE_LIBRARY.mj_constraint_state_trace_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY, "mj_noslip_trace_size"):
                RNE_TRACE_LIBRARY.mj_noslip_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_noslip_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_noslip_trace_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY, "mj_jaref_trace_size"):
                RNE_TRACE_LIBRARY.mj_jaref_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_jaref_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_jaref_trace_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY, "mj_jv_trace_size"):
                RNE_TRACE_LIBRARY.mj_jv_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_jv_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_jv_trace_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY, "mj_jaref_update_trace_size"):
                RNE_TRACE_LIBRARY.mj_jaref_update_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_jaref_update_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_jaref_update_trace_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY, "mj_noslip_step_trace_size"):
                RNE_TRACE_LIBRARY.mj_noslip_step_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_noslip_step_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_noslip_step_trace_copy.restype = None
            if hasattr(RNE_TRACE_LIBRARY, "mj_noslip_contact_trace_size"):
                RNE_TRACE_LIBRARY.mj_noslip_contact_trace_size.restype = ctypes.c_int
                RNE_TRACE_LIBRARY.mj_noslip_contact_trace_copy.argtypes = [
                    ctypes.POINTER(ctypes.c_double)]
                RNE_TRACE_LIBRARY.mj_noslip_contact_trace_copy.restype = None
    if args.diagnostic_newton_trace and RNE_TRACE_LIBRARY is None:
        raise SystemExit("--diagnostic-newton-trace requires --native-rne-trace-lib")
    if args.diagnostic_validate_solver_trace_lib and not (
            args.diagnostic_newton_trace and
            args.diagnostic_sync_before_fwdconstraint):
        raise SystemExit(
            "--diagnostic-validate-solver-trace-lib requires "
            "--diagnostic-newton-trace and "
            "--diagnostic-sync-before-fwdconstraint")
    if (args.diagnostic_validate_solver_trace_event is not None and
            not args.diagnostic_validate_solver_trace_lib):
        raise SystemExit(
            "--diagnostic-validate-solver-trace-event requires "
            "--diagnostic-validate-solver-trace-lib")
    if args.native_noslip_trace_lib is not None:
        NOSLIP_TRACE_LIBRARY = ctypes.CDLL(
            str(args.native_noslip_trace_lib.resolve()))
    if args.diagnostic_noslip_residual_trace:
        if NOSLIP_TRACE_LIBRARY is None or not hasattr(
                NOSLIP_TRACE_LIBRARY, "mj_noslip_residual_trace_run"):
            raise SystemExit(
                "--diagnostic-noslip-residual-trace requires "
                "--native-noslip-trace-lib exporting "
                "mj_noslip_residual_trace_run")
        if not args.diagnostic_sync_before_fwdconstraint:
            raise SystemExit(
                "--diagnostic-noslip-residual-trace requires "
                "--diagnostic-sync-before-fwdconstraint")
        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_run.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p]
        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_run.restype = None
        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_size.restype = ctypes.c_int
        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_copy.argtypes = [
            ctypes.POINTER(ctypes.c_double)]
        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_copy.restype = None
    MUJOCO_API = mujoco
    from neural_workshop import marblemaze as source
    from marble_source_capture import float32_abi_tray

    if mujoco.__version__ != "3.12.0":
        raise SystemExit(
            f"source parity requires MuJoCo 3.12.0, got {mujoco.__version__}")
    trace = json.loads(args.trace.read_text())
    if trace.get("version") != 1:
        raise SystemExit("unsupported Marble play trace version")
    native_runtime = None
    if (args.require_maintained_browser_runtime or args.provenance_json is not None or
            args.diagnostic_preparation_jsonl is not None):
        browser_runtime = trace.get("runtimeProvenance")
        if not isinstance(browser_runtime, dict):
            raise SystemExit("trace is missing runtimeProvenance")
        native_runtime = native_mujoco_provenance(mujoco)
        if args.require_maintained_browser_runtime:
            manifest_path = Path(__file__).resolve().parents[1] / "docs" / "marble-physics-manifest.json"
            manifest = json.loads(manifest_path.read_text())
            project_root = manifest_path.parents[2]
            try:
                promoted_artifact = current_promoted_artifact(manifest)
            except ValueError as error:
                raise SystemExit(str(error)) from error
            current_artifact = manifest["currentArtifact"]["artifact"]
            core_identity = browser_runtime.get("coreWasm", {})
            mujoco_identity = browser_runtime.get("mujoco", {})
            expected_core_path = (project_root / promoted_artifact["path"]).resolve()
            expected_js = next((item for item in manifest["browser"]["runtimeFiles"]
                                if item["path"].endswith("/mujoco.js")), None)
            expected_wasm = next((item for item in manifest["browser"]["runtimeFiles"]
                                  if item["path"].endswith("/mujoco.wasm")), None)
            if expected_js is None or expected_wasm is None:
                raise SystemExit("physics manifest is missing the maintained MuJoCo pair")
            expected_js_path = (project_root / expected_js["path"]).resolve()
            expected_wasm_path = (project_root / expected_wasm["path"]).resolve()
            expected_browser_files = (
                (core_identity, "path", expected_core_path),
                (core_identity, "sha256", promoted_artifact["sha256"]),
                (mujoco_identity, "jsPath", expected_js_path),
                (mujoco_identity, "jsSha256", expected_js["sha256"]),
                (mujoco_identity, "wasmPath", expected_wasm_path),
                (mujoco_identity, "wasmSha256", expected_wasm["sha256"]),
            )
            for identity, field, expected in expected_browser_files:
                actual = identity.get(field)
                if field.endswith("Path") or field == "path":
                    actual = Path(actual).resolve() if isinstance(actual, str) else None
                if actual != expected:
                    raise SystemExit(
                        f"browser trace provenance mismatch for {field}: "
                        f"expected {expected}, got {actual}")
            if mujoco_identity.get("maintainedFilesMatchManifest") is not True:
                raise SystemExit(
                    "browser trace did not use the maintained MuJoCo JS/WASM pair")
            for path, expected_hash in (
                    (expected_core_path, promoted_artifact["sha256"]),
                    (expected_js_path, expected_js["sha256"]),
                    (expected_wasm_path, expected_wasm["sha256"])):
                if sha256_path(path) != expected_hash:
                    raise SystemExit(
                        f"maintained runtime file changed after trace capture: {path}")
        provenance_report = {
            "schema": "neural-workshop.marble-comparison-provenance.v1",
            "browser": browser_runtime,
            "native": native_runtime,
            "reference": {
                "sourceRoot": str(source_root),
                "marbleSource": str(Path(source.__file__).resolve()),
                "marbleSourceSha256": sha256_path(Path(source.__file__).resolve()),
            },
        }
        print("NATIVE RUNTIME PROVENANCE: " + json.dumps(native_runtime, sort_keys=True))
        if args.provenance_json is not None:
            args.provenance_json.parent.mkdir(parents=True, exist_ok=True)
            args.provenance_json.write_text(
                json.dumps(provenance_report, indent=2, sort_keys=True) + "\n")
    if args.diagnostic_preparation_jsonl:
        preparation_input = {"path": str(args.trace.resolve()),
                             "sha256": sha256_path(args.trace),
                             "runtimeProvenance": trace["runtimeProvenance"]}
        args.diagnostic_preparation_jsonl.parent.mkdir(parents=True, exist_ok=True)
        args.diagnostic_preparation_jsonl.write_text("")
    rung = int(trace["rung"])
    board_seed = int(trace["boardSeed"])
    tray = float32_abi_tray(source.deal(rung, seed=board_seed))
    time_limit_ms = int(trace.get("timeLimitMs", 0))
    deadline = time_limit_ms / 1000.0 if time_limit_ms > 0 else tray.seconds
    sim = source.Simulation(tray)
    nudge_due = 0.0
    maxima: dict[str, float] = {}
    exceedances: dict[str, dict[str, object]] = {}
    contact_mismatches: list[dict[str, object]] = []
    state_delta_rows: list[dict[str, object]] = []

    for event_index, event in enumerate(trace["events"]):
        validate_solver_trace_now = (
            args.diagnostic_validate_solver_trace_lib and
            (args.diagnostic_validate_solver_trace_event is None or
             event_index == args.diagnostic_validate_solver_trace_event))
        sync_this_event = (
            event_index == args.sync_before_event or
            ((args.diagnostic_sync_every_event or args.diagnostic_sync_every_substep)
             and event_index > 0))
        if sync_this_event:
            if event_index == 0 or "state" not in trace["events"][event_index - 1]:
                raise SystemExit("diagnostic sync requires a preceding full-state trace event")
            sync_source_from_wasm_snapshot(
                sim, trace["events"][event_index - 1]["state"])
            if args.sync_before_event == event_index:
                print(f"Synchronized native wrapper state from WASM snapshot before event[{event_index}]")
                expected_engine = trace["events"][event_index - 1]["state"].get(
                    "engine")
                if expected_engine is not None:
                    actual_engine = source_engine_snapshot(sim)
                    sync_deltas = {}
                    for field in ENGINE_DIAGNOSTIC_FIELDS:
                        if field not in expected_engine["arrays"]:
                            continue
                        expected = expected_engine["arrays"][field]
                        actual = actual_engine["arrays"][field]
                        differences = [(index, left, right)
                                       for index, (left, right) in enumerate(
                                           zip(actual, expected))
                                       if left != right]
                        if differences:
                            sync_deltas[field] = {
                                "differentCount": len(differences),
                                "firstDifferences": differences[:3],
                            }
                    print("SYNCHRONIZED ENGINE ARRAY DELTAS: " +
                          json.dumps(sync_deltas, sort_keys=True))
        native_engine_substeps: list[dict[str, object]] = []
        native_step1_substeps: list[dict[str, object]] = []
        native_step1_inputs: list[dict[str, object]] = []
        native_step1_phases: list[list[dict[str, object]]] = []
        native_step2_phases: list[list[dict[str, object]]] = []
        native_newton_traces: list[list[float]] = []
        native_noslip_residual_traces: list[list[float]] = []
        original_substep = None
        original_mj_step = None
        if (args.diagnostic_phase_step and "engineStep1Phases" in event) or (
                args.diagnostic_split_step and "engineStep1Substeps" in event):
            original_mj_step = source.mujoco.mj_step

            def split_native_step(model: object, data: object) -> None:
                if args.diagnostic_sync_before_step1:
                    substep_index = len(native_step1_inputs)
                    try:
                        wasm_input = event["engineStep1Inputs"][substep_index]
                    except (KeyError, IndexError, TypeError) as exc:
                        raise AssertionError(
                            "step1 input sync requires captured "
                            "engineStep1Inputs") from exc
                    sync_source_engine_from_wasm_snapshot(sim, wasm_input)
                    print(
                        "SYNCHRONIZED BEFORE STEP1 "
                        f"event[{event_index}].substep[{substep_index}]: "
                        "native data replaced with matching WASM step1 input")
                native_step1_inputs.append(source_engine_snapshot(sim))
                if args.diagnostic_phase_step and "engineStep1Phases" in event:
                    phases: list[dict[str, object]] = []

                    def capture_phase(name: str) -> None:
                        engine = source_engine_snapshot(sim)
                        phase = {"phase": name, "engine": engine}
                        if name == "fwdPosition":
                            # Freeze collision results before later diagnostic
                            # solver-input synchronization replaces contacts.
                            owners = [item["engine"] for item in
                                      event["engineStep1Phases"][len(native_step1_phases)]
                                      if item["phase"] == name]
                            if len(owners) != 1:
                                raise AssertionError("unique collision phase owner required")
                            print("PRE-SYNC COLLISION GEOMETRY "
                                  f"event[{event_index}].substep[{len(native_step1_phases)}]: "
                                  + json.dumps({
                                      "source": contact_geometry_summary(engine["contacts"]),
                                      "wasm": contact_geometry_summary(owners[0]["contacts"]),
                                      "geomTypes": sim._model.geom_type.tolist(),
                                      "sourceOperands": {
                                          key: engine[group][key]
                                          for group, key in (("arrays", "geom_xpos"),
                                                             ("arrays", "geom_xmat"),
                                                             ("model", "geom_size"))},
                                      "wasmOperands": {
                                          key: owners[0][group][key]
                                          for group, key in (("arrays", "geom_xpos"),
                                                             ("arrays", "geom_xmat"),
                                                             ("model", "geom_size"))},
                                  }, sort_keys=True))
                        if name == "probe_rneBias" and RNE_TRACE_LIBRARY is not None:
                            trace_values = capture_instrumented_rne_trace(sim)
                            nv = int(sim._model.nv)
                            body_count = int(sim._model.nbody)
                            qfrc_start = 36 * body_count
                            compiled_result = trace_values[qfrc_start:qfrc_start + nv]
                            actual_result = engine["arrays"]["qfrc_bias"]
                            phase["compiledRneTrace"] = trace_values
                            phase["compiledRneResultMismatch"] = {
                                "differentCount": sum(a != b for a, b in zip(
                                    compiled_result, actual_result)),
                                "maxAbs": max((abs(a - b) for a, b in zip(
                                    compiled_result, actual_result)), default=0.0),
                            }
                            # The auxiliary dylib must first reproduce the
                            # installed native engine at this exact state.
                            # A materially different result means its local
                            # arrays cannot be attributed to backend parity.
                            phase["compiledRneTraceValid"] = (
                                phase["compiledRneResultMismatch"]["maxAbs"]
                                <= 1e-12)
                            projection_start = qfrc_start + nv
                            dof_projections = {}
                            for dof in (4, 10):
                                if dof >= nv:
                                    continue
                                offset = projection_start + 12 * dof
                                axis = trace_values[offset:offset + 6]
                                force = trace_values[offset + 6:offset + 12]
                                products = [a * b for a, b in zip(axis, force)]
                                dof_projections[str(dof)] = {
                                    "axis": axis,
                                    "bodyForce": force,
                                    "products": products,
                                    "nativeGroupedDot":
                                        ((products[0] + products[2]) +
                                         (products[1] + products[3])) +
                                        (products[4] + products[5]),
                                    "compiledTraceQfrcBias":
                                        trace_values[qfrc_start + dof],
                                    "pythonWheelQfrcBias": actual_result[dof],
                                }
                            print("NATIVE RNE DOT INPUTS "
                                  f"event[{event_index}].substep["
                                  f"{len(native_step1_phases)}]: "
                                  + json.dumps(dof_projections, sort_keys=True))
                        phases.append(phase)

                    source.mujoco.mj_checkPos(model, data)
                    capture_phase("checkPos")
                    source.mujoco.mj_checkVel(model, data)
                    capture_phase("checkVel")
                    # Isolate the two adjacent position kernels, then rerun
                    # the official combined position stage before continuing.
                    source.mujoco.mj_kinematics(model, data)
                    capture_phase("kinematics")
                    source.mujoco.mj_comPos(model, data)
                    capture_phase("comPos")
                    source.mujoco.mj_fwdPosition(model, data)
                    capture_phase("fwdPosition")
                    source.mujoco.mj_sensorPos(model, data)
                    capture_phase("sensorPos")
                    probe_data = MUJOCO_API.MjData(model)
                    MUJOCO_API.mj_copyData(probe_data, model, data)
                    live_data = sim._data
                    sim._data = probe_data
                    try:
                        capture_phase("probe_input")
                        MUJOCO_API.mj_comVel(model, probe_data)
                        capture_phase("probe_comVel")
                        MUJOCO_API.mj_passive(model, probe_data)
                        capture_phase("probe_passive")
                        MUJOCO_API.mj_referenceConstraint(model, probe_data)
                        capture_phase("probe_referenceConstraint")
                        if args.diagnostic_sync_before_rne:
                            step_index = len(native_step1_phases)
                            try:
                                wasm_rne_input = event["engineStep1Phases"][
                                    step_index][9]["engine"]
                            except (KeyError, IndexError, TypeError) as exc:
                                raise AssertionError(
                                    "RNE-input sync requires a captured "
                                    "probe_referenceConstraint phase") from exc
                            sync_source_engine_from_wasm_snapshot(sim, wasm_rne_input)
                            print(
                                "SYNCHRONIZED BEFORE RNE "
                                f"event[{event_index}].substep[{step_index}]: "
                                "isolated native probe now has matching WASM "
                                "reference-constraint input")
                        MUJOCO_API.mj_rne(model, probe_data, 0,
                                          probe_data.qfrc_bias)
                        capture_phase("probe_rneBias")
                        probe_data.qacc[:] = 0
                        MUJOCO_API.mj_rnePostConstraint(model, probe_data)
                        capture_phase("probe_rnePostConstraint_zeroacc")
                    finally:
                        sim._data = live_data
                    source.mujoco.mj_fwdVelocity(model, data)
                    capture_phase("fwdVelocity")
                    source.mujoco.mj_sensorVel(model, data)
                    capture_phase("sensorVel")
                    native_step1_phases.append(phases)
                else:
                    source.mujoco.mj_step1(model, data)
                native_step1_substeps.append(source_engine_snapshot(sim))
                if args.diagnostic_phase_step and "engineStep2Phases" in event:
                    phases = []

                    def capture_step2_phase(name: str) -> None:
                        phase = {"phase": name,
                                 "engine": source_engine_snapshot(sim)}
                        if name == "checkAcc" and FREE_SOLVE_LIBRARY is not None:
                            phase["bodyXmat"] = [
                                float(value) for value in np.asarray(data.xmat).ravel()]
                        phases.append(phase)

                    source.mujoco.mj_fwdActuation(model, data)
                    capture_step2_phase("fwdActuation")
                    source.mujoco.mj_fwdAcceleration(model, data)
                    capture_step2_phase("fwdAcceleration")
                    residual_input_state = None
                    if (args.diagnostic_sync_before_fwdconstraint and
                            (not args.diagnostic_validate_solver_trace_lib or
                             validate_solver_trace_now)):
                        step_index = len(native_step2_phases)
                        try:
                            wasm_input = event["engineStep2Phases"][step_index][1]["engine"]
                        except (KeyError, IndexError, TypeError) as exc:
                            raise AssertionError(
                                "solver-input sync requires a captured "
                                "fwdAcceleration phase") from exc
                        sync_source_engine_from_wasm_snapshot(
                            sim, wasm_input, include_solver_outputs=True)
                        body_xmat = named_phase(event, step_index, "checkAcc").get(
                            "bodyXmat")
                        if body_xmat is not None:
                            wasm_joint_body_ids = event["engineStep2Phases"][
                                step_index][4].get("jointBodyIds")
                            if wasm_joint_body_ids is not None and list(
                                    map(int, sim._model.jnt_bodyid)) != wasm_joint_body_ids:
                                raise AssertionError(
                                    "native/WASM joint-to-body ordering differs: "
                                    f"native={list(map(int, sim._model.jnt_bodyid))}, "
                                    f"wasm={wasm_joint_body_ids}")
                            sim._data.xmat[:] = np.asarray(body_xmat).reshape(
                                sim._data.xmat.shape)
                            if np.asarray(sim._data.xmat).ravel().tolist() != body_xmat:
                                raise AssertionError(
                                    "native xmat did not retain synchronized WASM values")
                        assert_exact_solver_input_snapshot(
                            sim, wasm_input,
                            f"event[{event_index}].substep[{step_index}]")
                        print(
                            "VERIFIED EXACT SOLVER INPUT "
                            f"event[{event_index}].substep[{step_index}]: "
                            "all active data arrays, counts, flags, contacts, "
                            "model arrays, and solver options match bitwise")
                        print(
                            "SYNCHRONIZED BEFORE FWDCONSTRAINT "
                            f"event[{event_index}].substep[{step_index}]: "
                            "native data replaced with matching WASM "
                            "fwdAcceleration snapshot")
                    if args.diagnostic_noslip_residual_trace:
                        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_run(
                            ctypes.c_void_p(int(model._address)),
                            ctypes.c_void_p(int(data._address)))
                        size = int(
                            NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_size())
                        values = (ctypes.c_double * size)()
                        NOSLIP_TRACE_LIBRARY.mj_noslip_residual_trace_copy(values)
                        native_noslip_residual_traces.append(list(values))
                    elif (args.diagnostic_newton_trace and
                          ("newtonTraces" in event or
                           validate_solver_trace_now)):
                        trace_data = data
                        if validate_solver_trace_now:
                            active_input = source_engine_snapshot(sim)
                            trace_data = MUJOCO_API.MjData(model)
                            MUJOCO_API.mj_copyData(trace_data, model, data)
                            copied_input = source_engine_snapshot_for_data(
                                sim, trace_data)
                            input_mismatches = {
                                field: {
                                    "activeLength": len(active_input["arrays"][field]),
                                    "copyLength": len(copied_input["arrays"][field]),
                                }
                                for field in ENGINE_DIAGNOSTIC_FIELDS
                                if active_input["arrays"][field] !=
                                copied_input["arrays"][field]
                            }
                            for field in ("time", "ncon", "nefc", "nisland",
                                          "nidof", "awake", "contacts"):
                                if active_input[field] != copied_input[field]:
                                    input_mismatches[field] = {
                                        "active": active_input[field],
                                        "copy": copied_input[field],
                                    }
                            if input_mismatches:
                                raise AssertionError(
                                    "active wheel solver shadow copy changed "
                                    "the exact synchronized input: "
                                    f"{json.dumps(input_mismatches, sort_keys=True)}")
                        model_pointer = ctypes.c_void_p(int(model._address))
                        data_pointer = ctypes.c_void_p(int(trace_data._address))
                        RNE_TRACE_LIBRARY.mj_solver_trace_run(
                            model_pointer, data_pointer)
                        residual_input_states = capture_native_noslip_input_states()
                        residual_input_state = (residual_input_states[0]
                                                if residual_input_states else None)
                        trace_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_trace_size())
                        trace_buffer = (ctypes.c_double * trace_size)()
                        RNE_TRACE_LIBRARY.mj_solver_trace_copy(trace_buffer)
                        sparse_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_sparse_input_size())
                        sparse_buffer = (ctypes.c_double * sparse_size)()
                        RNE_TRACE_LIBRARY.mj_solver_sparse_input_copy(
                            sparse_buffer)
                        constraint_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_constraint_input_size())
                        constraint_buffer = (ctypes.c_double * constraint_size)()
                        RNE_TRACE_LIBRARY.mj_solver_constraint_input_copy(
                            constraint_buffer)
                        if hasattr(RNE_TRACE_LIBRARY,
                                   "mj_solver_constraint_iteration_trace_size"):
                            iteration_size = int(
                                RNE_TRACE_LIBRARY
                                .mj_solver_constraint_iteration_trace_size())
                            iteration_buffer = (
                                ctypes.c_double * iteration_size)()
                            RNE_TRACE_LIBRARY.mj_solver_constraint_iteration_trace_copy(
                                iteration_buffer)
                        else:
                            iteration_buffer = ()
                        chol_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_chol_solve_size())
                        chol_solve_buffer = (ctypes.c_double * chol_size)()
                        RNE_TRACE_LIBRARY.mj_solver_chol_solve_copy(
                            chol_solve_buffer)
                        hessian_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_hessian_size())
                        hessian_buffer = (ctypes.c_double * hessian_size)()
                        RNE_TRACE_LIBRARY.mj_solver_hessian_copy(
                            hessian_buffer)
                        cone_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_cone_trace_size())
                        cone_buffer = (ctypes.c_double * cone_size)()
                        RNE_TRACE_LIBRARY.mj_solver_cone_trace_copy(
                            cone_buffer)
                        solve_stage_size = int(
                            RNE_TRACE_LIBRARY.mj_solver_dense_solve_trace_size())
                        solve_stage_buffer = (
                            ctypes.c_double * solve_stage_size)()
                        RNE_TRACE_LIBRARY.mj_solver_dense_solve_trace_copy(
                            solve_stage_buffer)
                        constraint_update_size = int(
                            RNE_TRACE_LIBRARY.mj_constraint_update_trace_size())
                        constraint_update_buffer = (
                            ctypes.c_double * constraint_update_size)()
                        RNE_TRACE_LIBRARY.mj_constraint_update_trace_copy(
                            constraint_update_buffer)
                        state_size = int(
                            RNE_TRACE_LIBRARY.mj_constraint_state_trace_size())
                        state_buffer = (ctypes.c_double * state_size)()
                        RNE_TRACE_LIBRARY.mj_constraint_state_trace_copy(
                            state_buffer)
                        if hasattr(RNE_TRACE_LIBRARY,
                                   "mj_noslip_trace_size"):
                            noslip_size = int(
                                RNE_TRACE_LIBRARY.mj_noslip_trace_size())
                            noslip_buffer = (ctypes.c_double * noslip_size)()
                            RNE_TRACE_LIBRARY.mj_noslip_trace_copy(
                                noslip_buffer)
                        else:
                            noslip_buffer = ()
                        if hasattr(RNE_TRACE_LIBRARY, "mj_jaref_trace_size"):
                            jaref_size = int(
                                RNE_TRACE_LIBRARY.mj_jaref_trace_size())
                            jaref_buffer = (ctypes.c_double * jaref_size)()
                            RNE_TRACE_LIBRARY.mj_jaref_trace_copy(
                                jaref_buffer)
                        else:
                            jaref_buffer = ()
                        if hasattr(RNE_TRACE_LIBRARY, "mj_jv_trace_size"):
                            jv_size = int(RNE_TRACE_LIBRARY.mj_jv_trace_size())
                            jv_buffer = (ctypes.c_double * jv_size)()
                            RNE_TRACE_LIBRARY.mj_jv_trace_copy(jv_buffer)
                        else:
                            jv_buffer = ()
                        if hasattr(RNE_TRACE_LIBRARY,
                                   "mj_jaref_update_trace_size"):
                            jaref_update_size = int(
                                RNE_TRACE_LIBRARY.mj_jaref_update_trace_size())
                            jaref_update_buffer = (
                                ctypes.c_double * jaref_update_size)()
                            RNE_TRACE_LIBRARY.mj_jaref_update_trace_copy(
                                jaref_update_buffer)
                        else:
                            jaref_update_buffer = ()
                        if hasattr(RNE_TRACE_LIBRARY,
                                   "mj_noslip_step_trace_size"):
                            noslip_step_size = int(
                                RNE_TRACE_LIBRARY.mj_noslip_step_trace_size())
                            noslip_step_buffer = (
                                ctypes.c_double * noslip_step_size)()
                            RNE_TRACE_LIBRARY.mj_noslip_step_trace_copy(
                                noslip_step_buffer)
                        else:
                            noslip_step_buffer = ()
                        if hasattr(RNE_TRACE_LIBRARY,
                                   "mj_noslip_contact_trace_size"):
                            noslip_contact_size = int(
                                RNE_TRACE_LIBRARY.
                                mj_noslip_contact_trace_size())
                            noslip_contact_buffer = (
                                ctypes.c_double * noslip_contact_size)()
                            RNE_TRACE_LIBRARY.mj_noslip_contact_trace_copy(
                                noslip_contact_buffer)
                        else:
                            noslip_contact_buffer = ()
                        preparation_capture = capture_native_preparations(RNE_TRACE_LIBRARY)
                        native_newton_traces.append({
                            "records": int(
                                RNE_TRACE_LIBRARY.mj_solver_trace_records()),
                            "modelDisableFlags": int(model.opt.disableflags),
                            "modelSolver": int(model.opt.solver),
                            "dataConstraintCount": int(data.nefc),
                            "values": list(trace_buffer),
                            "sparseInput": list(sparse_buffer),
                            "constraintInput": list(constraint_buffer),
                            "constraintIterationTrace": list(iteration_buffer),
                            **preparation_capture,
                            **capture_native_evaluations(RNE_TRACE_LIBRARY, preparation_capture),
                            **capture_native_gauss(RNE_TRACE_LIBRARY),
                            **capture_native_cost(RNE_TRACE_LIBRARY),
                            **iteration_trace_metadata(RNE_TRACE_LIBRARY),
                            "residualInputState": residual_input_state,
                            "residualInputStates": residual_input_states,
                            "cholSolveInput": list(chol_solve_buffer),
                            "hessianTrace": list(hessian_buffer),
                            "coneTrace": list(cone_buffer),
                            "denseSolveStages": list(solve_stage_buffer),
                            "constraintUpdateTrace": list(
                                constraint_update_buffer),
                            "constraintStateTrace": list(state_buffer),
                            "noSlipTrace": list(noslip_buffer),
                            "jarefTrace": list(jaref_buffer),
                            "jvTrace": list(jv_buffer),
                            "jarefUpdateTrace": list(jaref_update_buffer),
                            "noSlipStepTrace": list(noslip_step_buffer),
                            "noSlipContactTrace": list(noslip_contact_buffer),
                            "noSlipCostChangeProbe": no_slip_cost_change_probes(
                                list(noslip_contact_buffer)),
                        })
                        if validate_solver_trace_now:
                            trace_library_output = source_engine_snapshot_for_data(
                                sim, trace_data)
                            source.mujoco.mj_fwdConstraint(model, data)
                            active_wheel_output = source_engine_snapshot(sim)
                            if args.diagnostic_solver_output_json:
                                with args.diagnostic_solver_output_json.open(
                                        "a", encoding="utf-8") as output_file:
                                    output_file.write(json.dumps({
                                        "event": event_index,
                                        "substep": step_index,
                                        "arrays": {
                                            field: active_wheel_output["arrays"][field]
                                            for field in sorted(
                                                ENGINE_SOLVER_OUTPUT_FIELDS)
                                        },
                                    }, separators=(",", ":")) + "\n")
                            output_differences = {}
                            for field in sorted(ENGINE_SOLVER_OUTPUT_FIELDS):
                                left = trace_library_output["arrays"][field]
                                right = active_wheel_output["arrays"][field]
                                differing = [
                                    index for index, (a, b) in enumerate(
                                        zip(left, right))
                                    if not exact_solver_value_equal(a, b)]
                                if len(left) != len(right) or differing:
                                    output_differences[field] = {
                                        "traceLength": len(left),
                                        "wheelLength": len(right),
                                        "differentCount": len(differing) +
                                            abs(len(left) - len(right)),
                                        "first": [
                                            {"index": index,
                                             "traceLibrary": left[index],
                                             "pythonWheel": right[index]}
                                            for index in differing[:8]],
                                    }
                            print(
                                "INSTRUMENTED SOLVER LIBRARY VS ACTIVE "
                                "PYTHON WHEEL "
                                f"event[{event_index}].substep[{step_index}]: "
                                + json.dumps({
                                    "exactInputCopy": True,
                                    "solverOutputsExactlyEqual":
                                        not output_differences,
                                    "outputDifferences": output_differences,
                                }, sort_keys=True))
                            if args.diagnostic_preparation_jsonl:
                                capture = native_newton_traces[-1]
                                if "prepareTrace" not in capture:
                                    raise AssertionError("native library lacks initialized preparation recorder")
                                with args.diagnostic_preparation_jsonl.open(
                                        "a", encoding="utf-8") as output_file:
                                    output_file.write(json.dumps({
                                        "schema": "neural-workshop.marble-preparation-qualified.v1",
                                        "event": event_index, "substep": step_index,
                                        "exactInputCopy": True,
                                        "solverOutputsExactlyEqual": not output_differences,
                                        "outputDifferences": output_differences,
                                        "inputTrace": preparation_input,
                                        "nativeWheel": native_runtime,
                                        "diagnosticLibrary": {
                                            "path": str(args.native_rne_trace_lib.resolve()),
                                            "sha256": sha256_path(args.native_rne_trace_lib)},
                                        "trace": {k: capture[k] for k in (
                                            "prepareTrace", "prepareTraceSchema", "prepareTraceCalls",
                                            "prepareTraceOverflow", "prepareTraceInvalid",
                                            "constraintIterationTrace", "constraintIterationTraceSchema",
                                            "constraintIterationTraceOverflow",
                                            "evalTrace", "evalTraceSchema", "evalTraceCalls",
                                            "evalTraceOverflow", "evalTraceInvalid") if k in capture},
                                    }, separators=(",", ":"), allow_nan=False)+"\n")
                    else:
                        source.mujoco.mj_fwdConstraint(model, data)
                    capture_step2_phase("fwdConstraint")
                    if (args.diagnostic_solver_output_event == event_index and
                            args.diagnostic_solver_output_substep == step_index):
                        try:
                            browser_solver_output = event[
                                "engineStep2Phases"][step_index][2]["engine"]
                        except (KeyError, IndexError, TypeError) as exc:
                            raise AssertionError(
                                "solver output capture requires the matching "
                                "browser fwdConstraint phase") from exc
                        native_solver_output = phases[-1]["engine"]
                        output_fields = sorted(ENGINE_SOLVER_OUTPUT_FIELDS)
                        browser_arrays = browser_solver_output["arrays"]
                        native_arrays = native_solver_output["arrays"]
                        missing = [field for field in output_fields
                                   if field not in browser_arrays or
                                   field not in native_arrays]
                        if missing:
                            raise AssertionError(
                                "solver output capture is missing diagnostic "
                                f"arrays: {missing}")
                        output_differences = {}
                        for field in output_fields:
                            left = native_arrays[field]
                            right = browser_arrays[field]
                            differing = [index for index, (a, b) in enumerate(
                                zip(left, right))
                                if not exact_solver_value_equal(a, b)]
                            if len(left) != len(right) or differing:
                                output_differences[field] = {
                                    "nativeLength": len(left),
                                    "browserLength": len(right),
                                    "differentCount": len(differing) +
                                        abs(len(left) - len(right)),
                                    "first": [
                                        {"index": index, "native": left[index],
                                         "browser": right[index]}
                                        for index in differing[:8]],
                                }
                        solver_input = event["engineStep2Phases"][step_index][1][
                            "engine"]
                        solver_input_bytes = json.dumps(
                            solver_input, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode()
                        solver_output_record = {
                            "schema": "neural-workshop.marble-solver-output.v1",
                            "event": event_index,
                            "substep": step_index,
                            "solverInputSha256": hashlib.sha256(
                                solver_input_bytes).hexdigest(),
                            "solverInputCounts": {
                                field: solver_input[field]
                                for field in ("time", "ncon", "nefc", "nisland",
                                              "nidof")},
                            "exactSolverInputVerified": True,
                            "solverOutputsExactlyEqual": not output_differences,
                            "outputDifferences": output_differences,
                            "runtimeProvenance": {
                                "browser": trace.get("runtimeProvenance"),
                                "native": native_runtime,
                            },
                            "outputs": {
                                "nativeActiveWheel": {
                                    field: native_arrays[field]
                                    for field in output_fields},
                                "browserWasm": {
                                    field: browser_arrays[field]
                                    for field in output_fields},
                            },
                        }
                        args.diagnostic_solver_output_json.parent.mkdir(
                            parents=True, exist_ok=True)
                        args.diagnostic_solver_output_json.write_text(
                            json.dumps(solver_output_record, indent=2,
                                       sort_keys=True, allow_nan=False) + "\n")
                        print(
                            "CAPTURED EXACT-INPUT ACTIVE-WHEEL SOLVER OUTPUT "
                            f"event[{event_index}].substep[{step_index}]: " +
                            json.dumps({
                                "path": str(args.diagnostic_solver_output_json),
                                "solverInputSha256": solver_output_record[
                                    "solverInputSha256"],
                                "solverOutputsExactlyEqual": not output_differences,
                                "differentFields": sorted(output_differences),
                            }, sort_keys=True))
                    data.flg_rnepost = 0
                    source.mujoco.mj_sensorAcc(model, data)
                    capture_step2_phase("sensorAcc")
                    source.mujoco.mj_checkAcc(model, data)
                    capture_step2_phase("checkAcc")
                    if (args.diagnostic_sync_before_implicit or
                            args.diagnostic_probe_free_solve):
                        step_index = len(native_step2_phases)
                        try:
                            wasm_input = named_phase(event, step_index, "checkAcc")["engine"]
                        except (KeyError, IndexError, TypeError, ValueError) as exc:
                            raise AssertionError(
                                "integrator-input sync requires a captured "
                                "checkAcc phase") from exc
                        if args.diagnostic_sync_before_implicit:
                            sync_source_engine_from_wasm_snapshot(sim, wasm_input)
                            print(
                                "SYNCHRONIZED BEFORE MJ_IMPLICIT "
                                f"event[{event_index}].substep[{step_index}]: "
                                "native data replaced with matching WASM "
                                "checkAcc snapshot")
                        else:
                            print(
                                "UNSYNCHRONIZED FREE-JOINT PROBE "
                                f"event[{event_index}].substep[{step_index}]: "
                                "native live checkAcc state compared with WASM")
                        if FREE_SOLVE_LIBRARY is not None:
                            native_probe = capture_free_joint_solve_probe(sim)
                            native_derivative = capture_free_joint_derivative_probe(sim)
                            wasm_probe = named_phase(event, step_index, "checkAcc").get(
                                "freeJointSolveProbe", [])
                            if len(native_probe) != len(wasm_probe):
                                raise AssertionError(
                                    "free-joint probe length mismatch: "
                                    f"native={len(native_probe)}, wasm={len(wasm_probe)}")
                            labels = ("A", "LU", "pivot", "qacc")
                            widths = (36, 36, 6, 6)
                            report = []
                            for joint_index in range(len(native_probe) // 84):
                                offset = joint_index * 84
                                for label, width, relative in zip(
                                        labels, widths, (0, 36, 72, 78)):
                                    left = native_probe[offset + relative:
                                                        offset + relative + width]
                                    right = wasm_probe[offset + relative:
                                                         offset + relative + width]
                                    differing = [i for i, (a, b) in enumerate(
                                        zip(left, right)) if a != b]
                                    report.append({
                                        "joint": joint_index,
                                        "field": label,
                                        "differentCount": len(differing),
                                        "maxAbs": max((abs(left[i] - right[i])
                                                       for i in differing), default=0.0),
                                        "first": [{"index": i, "native": left[i],
                                                   "wasm": right[i]}
                                                  for i in differing[:4]],
                                    })
                            probe_label = ("MATCHED" if args.diagnostic_sync_before_implicit
                                           else "UNSYNCHRONIZED")
                            print(f"{probe_label} FREE-JOINT SOLVE PROBE "
                                  f"event[{event_index}].substep[{step_index}]: "
                                  + json.dumps(report, sort_keys=True))
                            wasm_derivative = named_phase(event, step_index, "checkAcc").get(
                                "freeJointDerivativeProbe", [])
                            if len(native_derivative) != len(wasm_derivative):
                                raise AssertionError(
                                    "free-joint derivative probe length mismatch: "
                                    f"native={len(native_derivative)}, "
                                    f"wasm={len(wasm_derivative)}")
                            derivative_report = []
                            for joint_index in range(len(native_derivative) // 72):
                                for label, relative in (("qDeriv", 0), ("freeBias", 36)):
                                    start = joint_index * 72 + relative
                                    left = native_derivative[start:start + 36]
                                    right = wasm_derivative[start:start + 36]
                                    differing = [i for i, (a, b) in enumerate(
                                        zip(left, right)) if a != b]
                                    derivative_report.append({
                                        "joint": joint_index,
                                        "field": label,
                                        "differentCount": len(differing),
                                        "maxAbs": max((abs(left[i] - right[i])
                                                       for i in differing), default=0.0),
                                        "first": [{"index": i, "native": left[i],
                                                   "wasm": right[i]}
                                                  for i in differing[:4]],
                                    })
                            print(f"{probe_label} FREE-JOINT DERIVATIVE PROBE "
                                  f"event[{event_index}].substep[{step_index}]: "
                                  + json.dumps(derivative_report, sort_keys=True))
                            native_bias_trace = capture_free_bias_intermediate_probe(sim)
                            wasm_bias_trace = named_phase(event, step_index, "checkAcc").get(
                                "freeBiasIntermediateProbe", [])
                            if len(native_bias_trace) != len(wasm_bias_trace):
                                raise AssertionError(
                                    "free-bias intermediate probe length mismatch: "
                                    f"native={len(native_bias_trace)}, "
                                    f"wasm={len(wasm_bias_trace)}")
                            stages = (("R", 0, 9), ("Xi", 9, 9),
                                      ("inertia", 18, 3), ("s", 21, 3),
                                      ("qvel_rot", 24, 3), ("w", 27, 3),
                                      ("Xi_I", 30, 9), ("Iw", 39, 9),
                                      ("ws", 48, 3), ("Iww", 51, 3),
                                      ("w_dot_s", 54, 1), ("K", 55, 9),
                                      ("lin", 64, 9), ("C", 73, 9),
                                      ("tmp", 82, 9), ("rot", 91, 9))
                            bias_report = []
                            for joint_index in range(len(native_bias_trace) // 100):
                                base = joint_index * 100
                                for name, relative, width in stages:
                                    left = native_bias_trace[base + relative:
                                                            base + relative + width]
                                    right = wasm_bias_trace[base + relative:
                                                           base + relative + width]
                                    differing = [i for i, (a, b) in enumerate(
                                        zip(left, right)) if a != b]
                                    bias_report.append({
                                        "joint": joint_index,
                                        "stage": name,
                                        "differentCount": len(differing),
                                        "maxAbs": max((abs(left[i] - right[i])
                                                       for i in differing), default=0.0),
                                        "first": [{"index": i, "native": left[i],
                                                   "wasm": right[i]}
                                                  for i in differing[:2]],
                                    })
                            print(f"{probe_label} FREE-BIAS INTERMEDIATE PROBE "
                                  f"event[{event_index}].substep[{step_index}]: "
                                  + json.dumps(bias_report, sort_keys=True))
                            nv = int(sim._model.nv)
                            nq = int(sim._model.nq)
                            native_acc = [0.0] * nv
                            free_index = 0
                            for joint, joint_type in enumerate(sim._model.jnt_type):
                                if int(joint_type) != 0:
                                    continue
                                adr = int(sim._model.jnt_dofadr[joint])
                                local = free_index * 84 + 78
                                native_acc[adr:adr + 6] = native_probe[local:local + 6]
                                free_index += 1
                            acc_array = (ctypes.c_double * nv)(*native_acc)
                            next_vel = (ctypes.c_double * nv)(
                                *(float(value) for value in sim._data.qvel))
                            FREE_SOLVE_LIBRARY.mju_addToScl(
                                next_vel, acc_array,
                                float(sim._model.opt.timestep), nv)
                            next_pos = (ctypes.c_double * nq)(
                                *(float(value) for value in sim._data.qpos))
                            FREE_SOLVE_LIBRARY.mj_integratePos(
                                ctypes.c_void_p(int(sim._model._address)),
                                next_pos, next_vel,
                                float(sim._model.opt.timestep))
                            native_advance = [*native_acc, *next_vel, *next_pos]
                            wasm_advance = named_phase(event, step_index, "checkAcc").get(
                                "freeJointAdvanceProbe", [])
                            if len(native_advance) != len(wasm_advance):
                                raise AssertionError(
                                    "free-joint advance probe length mismatch: "
                                    f"native={len(native_advance)}, "
                                    f"wasm={len(wasm_advance)}")
                            fields = (("qacc", 0, nv), ("qvelNext", nv, nv),
                                      ("qposNext", 2 * nv, nq))
                            advance_report = []
                            for name, start, width in fields:
                                left = native_advance[start:start + width]
                                right = wasm_advance[start:start + width]
                                differing = [i for i, (a, b) in enumerate(
                                    zip(left, right)) if a != b]
                                advance_report.append({
                                    "field": name,
                                    "differentCount": len(differing),
                                    "maxAbs": max((abs(left[i] - right[i])
                                                   for i in differing), default=0.0),
                                    "first": [{"index": i, "native": left[i],
                                               "wasm": right[i]}
                                              for i in differing[:4]],
                                })
                            print("MATCHED FREE-JOINT ADVANCE PROBE "
                                  f"event[{event_index}].substep[{step_index}]: "
                                  + json.dumps(advance_report, sort_keys=True))
                    source.mujoco.mj_implicit(model, data)
                    capture_step2_phase("implicit")
                    native_step2_phases.append(phases)
                else:
                    source.mujoco.mj_step2(model, data)

            source.mujoco.mj_step = split_native_step
        if "engineSubsteps" in event:
            original_substep = sim._substep

            def capture_native_substep(dt: float) -> None:
                original_substep(dt)
                engine = source_engine_snapshot(sim)
                native_engine_substeps.append(engine)
                if args.diagnostic_sync_every_substep:
                    substep_index = len(native_engine_substeps) - 1
                    wasm_states = event.get("substepStates", [])
                    if substep_index >= len(wasm_states):
                        raise AssertionError(
                            f"event[{event_index}] lacks full state for substep[{substep_index}]")
                    wasm_state = wasm_states[substep_index]
                    source_state = source_snapshot(
                        sim, nudge_due,
                        include_contacts=trace.get("contactDiagnostics", False),
                        include_engine=True)
                    compare_snapshot(source_state, wasm_state, event_index,
                                     maxima, exceedances, contact_mismatches,
                                     args.diagnostic_continue_contact_mismatches)
                    compare_engine_snapshot(
                        source_state["engine"], wasm_state["engine"],
                        f"event[{event_index}].substep[{substep_index}]")
                    sync_source_from_wasm_snapshot(sim, wasm_state)

            sim._substep = capture_native_substep
        if event["kind"] == "level":
            sim.level()
        elif event["kind"] == "frame":
            dt = float(event["dt"])
            piece = min(dt, 0.05)
            held = tuple(event["held"])
            if held:
                nudge_due += piece
                while nudge_due >= 1 / 60.:
                    nudge_due -= 1 / 60.
                    for direction in held:
                        sim.tilt(direction)
            else:
                nudge_due = 0.0
            left = piece
            while left > 0.0:
                bite = min(left, 1 / 60.)
                sim.step(bite)
                left -= bite
        else:
            raise SystemExit(f"unknown replay event {event['kind']!r}")
        if original_substep is not None:
            sim._substep = original_substep
            wasm_substeps = event["engineSubsteps"]
            if len(native_engine_substeps) != len(wasm_substeps):
                raise AssertionError(
                    f"event[{event_index}] engine substep count differs: "
                    f"native={len(native_engine_substeps)}, WASM={len(wasm_substeps)}")
            for substep_index, (native_engine, wasm_engine) in enumerate(
                    zip(native_engine_substeps, wasm_substeps)):
                compare_engine_snapshot(native_engine, wasm_engine,
                                        f"event[{event_index}].substep[{substep_index}]")
        if original_mj_step is not None:
            source.mujoco.mj_step = original_mj_step
            if args.diagnostic_phase_step and "engineStep1Phases" in event:
                wasm_phases = event["engineStep1Phases"]
                if len(native_step1_phases) != len(wasm_phases):
                    raise AssertionError(
                        f"event[{event_index}] phase-step substep count differs: "
                        f"native={len(native_step1_phases)}, WASM={len(wasm_phases)}")
                for substep_index, (native_phases, wasm_phases_for_step) in enumerate(
                        zip(native_step1_phases, wasm_phases)):
                    if len(native_phases) != len(wasm_phases_for_step):
                        raise AssertionError(
                            f"event[{event_index}] substep[{substep_index}] phase count differs")
                    previous_native = native_step1_inputs[substep_index]
                    previous_wasm = event["engineStep1Inputs"][substep_index]
                    for native_phase, wasm_phase in zip(
                            native_phases, wasm_phases_for_step):
                        if native_phase["phase"] != wasm_phase["phase"]:
                            raise AssertionError(
                                f"event[{event_index}] phase ordering differs")
                        compare_engine_snapshot(
                            native_phase["engine"], wasm_phase["engine"],
                            f"event[{event_index}].substep[{substep_index}]."
                            f"phase.{native_phase['phase']}")
                        report_phase_value_origin(
                            native_phase["engine"], wasm_phase["engine"],
                            previous_native, previous_wasm,
                            f"event[{event_index}].substep[{substep_index}]."
                            f"phase.{native_phase['phase']}")
                        previous_native = native_phase["engine"]
                        previous_wasm = wasm_phase["engine"]
                        if (native_phase["phase"] == "probe_referenceConstraint" and
                                substep_index < len(event.get(
                                    "rneInputSnapshots", []))):
                            compare_engine_snapshot(
                                native_phase["engine"],
                                event["rneInputSnapshots"][substep_index],
                                f"event[{event_index}].substep[{substep_index}]."
                                "exact_wasm_rne_input")
                        if (native_phase["phase"] == "probe_rneBias" and
                                substep_index < len(event.get("rneAwakeStates", []))):
                            wasm_awake = event["rneAwakeStates"][substep_index]
                        else:
                            wasm_awake = None
                        if (wasm_awake is not None and
                                native_phase["engine"].get("awake") != wasm_awake):
                            print(
                                "RNE AWAKE-MAP DIFFERENCE "
                                f"event[{event_index}].substep[{substep_index}]: "
                                + json.dumps({
                                    "native": native_phase["engine"].get("awake"),
                                    "wasm": wasm_awake,
                                }, sort_keys=True))
                        if (native_phase["phase"] == "probe_rneBias" and
                                RNE_TRACE_LIBRARY is not None and
                                native_phase.get("compiledRneTraceValid")):
                            if (event.get("rneTraces") and
                                    substep_index < len(event["rneTraces"])):
                                compare_compiled_rne_traces(
                                    native_phase["compiledRneTrace"],
                                    event["rneTraces"][substep_index],
                                    len(sim._model.body_parentid), int(sim._model.nv),
                                    f"event[{event_index}].substep[{substep_index}]."
                                    "probe_rneBias", native_phase["engine"],
                                    event.get("rneInputSnapshots", [])[substep_index]
                                    if substep_index < len(event.get(
                                        "rneInputSnapshots", []))
                                    else wasm_phase["engine"])
                            wasm_projection = wasm_phase.get("rneProjectionTrace")
                            if wasm_projection is not None:
                                stage_differences = []
                                native_trace = native_phase["compiledRneTrace"]
                                body_count = len(sim._model.body_parentid)
                                for body in range(1, body_count):
                                    for stage in range(6):
                                        start = 36 * body + 6 * stage
                                        native_values = native_trace[start:start + 6]
                                        wasm_values = wasm_projection[start:start + 6]
                                        differing = [
                                            component for component, (left, right)
                                            in enumerate(zip(native_values, wasm_values))
                                            if left != right]
                                        if differing:
                                            stage_differences.append({
                                                "body": body,
                                                "stage": stage,
                                                "components": differing,
                                                "native": native_values,
                                                "wasm": wasm_values,
                                            })
                                print("RNE BODY-FORCE STAGE DIFFERENCES "
                                      f"event[{event_index}].substep["
                                      f"{substep_index}]: "
                                      + json.dumps(stage_differences,
                                                   sort_keys=True))
                                qfrc_start = 36 * len(sim._model.body_parentid)
                                native_projection_start = qfrc_start + int(sim._model.nv)
                                projection_comparison = {}
                                for dof in (4, 10):
                                    wasm_qfrc_bias = wasm_phase["engine"]["arrays"].get(
                                        "qfrc_bias", [])
                                    if dof >= len(wasm_qfrc_bias):
                                        continue
                                    native_offset = native_projection_start + 12 * dof
                                    wasm_offset = (36 * len(sim._model.body_parentid) +
                                                   int(sim._model.nv) + 12 * dof)
                                    native_fields = [
                                        native_phase["compiledRneTrace"][qfrc_start + dof],
                                        *native_phase["compiledRneTrace"][
                                            native_offset:native_offset + 12],
                                    ]
                                    wasm_fields = [
                                        wasm_qfrc_bias[dof],
                                        *wasm_projection[wasm_offset:wasm_offset + 12],
                                    ]
                                    projection_comparison[str(dof)] = {
                                        "native": native_fields,
                                        "wasm": wasm_fields,
                                        "exactMatch": native_fields == wasm_fields,
                                        "differentIndices": [
                                            i for i, (left, right) in enumerate(
                                                zip(native_fields, wasm_fields))
                                            if left != right],
                                    }
                                print("RNE PROJECTION OPERAND COMPARISON "
                                      f"event[{event_index}].substep["
                                      f"{substep_index}]: "
                                      + json.dumps(projection_comparison,
                                                   sort_keys=True))
                        elif (native_phase["phase"] == "probe_rneBias" and
                              event.get("rneTraces") and
                              not native_phase.get("compiledRneTraceValid", True)):
                            mismatch = native_phase["compiledRneResultMismatch"]
                            print(
                                "SKIP INVALID COMPILED RNE TRACE "
                                f"event[{event_index}].substep[{substep_index}]: "
                                f"instrumented result differs from installed "
                                f"native qfrc_bias by max {mismatch['maxAbs']:.6g}")
                        if ((event_index <= 3 or event_index in (5, 6, 195)) and
                                native_phase["phase"] == "probe_rneBias"):
                            compare_rne_bias_reconstruction(
                                native_phase["engine"], wasm_phase["engine"],
                                f"event[{event_index}].substep[{substep_index}]")
            if args.diagnostic_phase_step and "engineStep2Phases" in event:
                wasm_phases = event["engineStep2Phases"]
                if len(native_step2_phases) != len(wasm_phases):
                    raise AssertionError(
                        f"event[{event_index}] phase-step2 substep count differs: "
                        f"native={len(native_step2_phases)}, WASM={len(wasm_phases)}")
                for substep_index, (native_phases, wasm_phases_for_step) in enumerate(
                        zip(native_step2_phases, wasm_phases)):
                    if len(native_phases) != len(wasm_phases_for_step):
                        raise AssertionError(
                            f"event[{event_index}] substep[{substep_index}] step2 phase count differs")
                    previous_native = native_step1_substeps[substep_index]
                    previous_wasm = event["engineStep1Substeps"][substep_index]
                    for native_phase, wasm_phase in zip(
                            native_phases, wasm_phases_for_step):
                        if native_phase["phase"] != wasm_phase["phase"]:
                            raise AssertionError(
                                f"event[{event_index}] step2 phase ordering differs")
                        compare_engine_snapshot(
                            native_phase["engine"], wasm_phase["engine"],
                            f"event[{event_index}].substep[{substep_index}]."
                            f"phase2.{native_phase['phase']}")
                        report_phase_value_origin(
                            native_phase["engine"], wasm_phase["engine"],
                            previous_native, previous_wasm,
                            f"event[{event_index}].substep[{substep_index}]."
                            f"phase2.{native_phase['phase']}")
                        previous_native = native_phase["engine"]
                        previous_wasm = wasm_phase["engine"]
                if args.diagnostic_newton_trace and "newtonTraces" in event:
                    wasm_newton_traces = event.get("newtonTraces", [])
                    if len(native_newton_traces) != len(wasm_newton_traces):
                        raise AssertionError(
                            f"event[{event_index}] Newton trace count differs: "
                            f"native={len(native_newton_traces)}, "
                            f"WASM={len(wasm_newton_traces)}")
                    for substep_index, (native_trace, wasm_trace) in enumerate(
                            zip(native_newton_traces, wasm_newton_traces)):
                        if (native_trace["records"] == 0 and
                                wasm_trace["records"] == 0):
                            continue
                        compare_compiled_newton_traces(
                            native_trace, wasm_trace,
                            f"event[{event_index}].substep[{substep_index}]")
                if args.diagnostic_noslip_residual_trace:
                    wasm_newton_traces = event.get("newtonTraces", [])
                    if len(native_noslip_residual_traces) != len(wasm_newton_traces):
                        raise AssertionError(
                            f"event[{event_index}] no-slip trace count differs: "
                            f"native={len(native_noslip_residual_traces)}, "
                            f"WASM={len(wasm_newton_traces)}")
                    field_names = ("island", "iteration", "row", "dim",
                                   "component", "b", "dot", "R", "force",
                                   "residual", "native_fused")
                    for substep_index, (native_values, wasm_trace) in enumerate(
                            zip(native_noslip_residual_traces,
                                wasm_newton_traces)):
                        wasm_values = wasm_trace.get("noSlipResidualTrace", [])
                        if len(native_values) != len(wasm_values):
                            raise AssertionError(
                                f"event[{event_index}] substep[{substep_index}] "
                                "no-slip residual scalar count differs: "
                                f"native={len(native_values)}, "
                                f"WASM={len(wasm_values)}")
                        differences = []
                        counts = [0] * 11
                        for offset in range(0, len(native_values), 11):
                            left = native_values[offset:offset + 11]
                            right = wasm_values[offset:offset + 11]
                            for field_index, (native_value, wasm_value) in enumerate(
                                    zip(left, right)):
                                if native_value != wasm_value:
                                    counts[field_index] += 1
                                    if len(differences) < 12:
                                        differences.append({
                                            "record": offset // 11,
                                            "field": field_names[field_index],
                                            "native": native_value,
                                            "wasm": wasm_value})
                        print(
                            "NO-SLIP RESIDUAL OPERAND COMPARISON "
                            f"event[{event_index}].substep[{substep_index}]: "
                            + json.dumps({
                                "records": len(native_values) // 11,
                                "differenceCounts": dict(zip(field_names, counts)),
                                "firstDifferences": differences},
                                sort_keys=True))
            wasm_step1 = event["engineStep1Substeps"]
            wasm_step1_inputs = event.get("engineStep1Inputs", [])
            if len(native_step1_inputs) != len(wasm_step1_inputs):
                raise AssertionError(
                    f"event[{event_index}] step1 input capture count differs: "
                    f"native={len(native_step1_inputs)}, "
                    f"WASM={len(wasm_step1_inputs)}")
            for substep_index, (native_engine, wasm_engine) in enumerate(
                    zip(native_step1_inputs, wasm_step1_inputs)):
                compare_engine_snapshot(
                    native_engine, wasm_engine,
                    f"event[{event_index}].substep[{substep_index}].before_step1")
            if len(native_step1_substeps) != len(wasm_step1):
                raise AssertionError(
                    f"event[{event_index}] step1 capture count differs: "
                    f"native={len(native_step1_substeps)}, WASM={len(wasm_step1)}")
            for substep_index, (native_engine, wasm_engine) in enumerate(
                    zip(native_step1_substeps, wasm_step1)):
                compare_engine_snapshot(
                    native_engine, wasm_engine,
                    f"event[{event_index}].substep[{substep_index}].after_step1")
        if not args.results_only and "state" in event:
            current_snapshot = source_snapshot(
                sim, nudge_due,
                include_contacts=trace.get("contactDiagnostics", False),
                include_engine="engine" in event["state"])
            compare_snapshot(current_snapshot, event["state"], event_index,
                             maxima, exceedances, contact_mismatches,
                             args.diagnostic_continue_contact_mismatches)
            if args.diagnostic_state_delta_jsonl is not None:
                state_delta_rows.append(summarize_snapshot_deltas(
                    current_snapshot, event["state"], event_index))
            if "engine" in event["state"]:
                compare_engine_snapshot(current_snapshot["engine"],
                                        event["state"]["engine"],
                                        f"event[{event_index}].frame-end")
            diagnostic_events = set(range(212, 218))
            diagnostic_events.update(args.diagnostic_contact_event)
            if args.sync_before_event is not None or args.diagnostic_sync_every_event:
                if args.sync_before_event is not None:
                    diagnostic_events.update((args.sync_before_event,
                                              args.sync_before_event + 1))
            if trace.get("contactDiagnostics", False) and event_index in diagnostic_events:
                print(f"CONTACT DIAGNOSTIC event[{event_index}]: " + json.dumps({
                    "native": current_snapshot["contacts"],
                    "wasm": event["state"]["contacts"],
                }, sort_keys=True))
            if args.sync_before_event == event_index:
                print("SYNCHRONIZED STEP STATE DELTAS: " + json.dumps([
                    [actual - expected for actual, expected in zip(
                        source_marble["values"], wasm_marble["values"])]
                    for source_marble, wasm_marble in zip(
                        current_snapshot["marbles"], event["state"]["marbles"])
                ]))
        if args.diagnostic_stop_after_event == event_index:
            if args.diagnostic_state_delta_jsonl is not None:
                write_state_delta_rows(args.diagnostic_state_delta_jsonl,
                                       state_delta_rows)
            print(f"Stopped after diagnostic event[{event_index}] by request")
            return 0

    if args.diagnostic_sync_every_event or args.diagnostic_sync_every_substep:
        mode = "per-substep" if args.diagnostic_sync_every_substep else "per-event"
        print(f"Diagnostic {mode} synchronization complete; terminal outcome/result acceptance intentionally skipped.")
        if exceedances:
            print(f"{sum(item['count'] for item in exceedances.values())} values exceeded the declared per-field parity tolerances")
            return 1
        if contact_mismatches:
            print(f"FAIL: {len(contact_mismatches)} isolated events have different contact sets")
            return 1
        print(f"PASS: each isolated event stayed within declared per-field tolerances; maximum deltas={maxima}")
        return 0

    if not sim.settled and sim.elapsed < deadline:
        raise AssertionError(
            f"trace ended unsettled at {sim.elapsed!r}s before "
            f"the {deadline!r}s source deadline")
    source_outcome = ("timeout" if trace["outcome"] == "timeout" else
                      "won" if sim.won and sim.settled else
                      "physical-loss" if sim.lost > 0 and sim.settled else
                      "unsettled")
    source_result = {
        "elapsedMs": math.floor(sim.elapsed * 1000 + 0.5),
        "home": sim.home,
        "lost": sim.lost,
        "verdict": int(source_outcome == "won"),
        "scoreWin": int(sim.lost == 0),
    }
    if source_outcome != trace["outcome"]:
        raise AssertionError(
            f"terminal outcome differs: source={source_outcome}, "
            f"WASM={trace['outcome']}")
    if source_result != trace["result"]:
        raise AssertionError(
            f"result row differs: source={source_result}, WASM={trace['result']}")

    if args.diagnostic_state_delta_jsonl is not None:
        write_state_delta_rows(args.diagnostic_state_delta_jsonl,
                               state_delta_rows)
    if not args.results_only:
        verdict = "FAIL" if exceedances or contact_mismatches else "PASS"
        print(
            f"{verdict}: original Python Marble Simulation replayed {len(trace['events'])} "
            f"input/frame events on rung {rung}, board seed {board_seed}; "
            f"outcome={source_outcome}, home={sim.home}, lost={sim.lost}, "
            f"elapsed={sim.elapsed:.6f}s, maximum numeric deltas={maxima}")
    if contact_mismatches:
        print("CONTACT-SET MISMATCHES: " + json.dumps(
            {"count": len(contact_mismatches),
             "first": contact_mismatches[0],
             "last": contact_mismatches[-1]}, sort_keys=True))
    if exceedances:
        print("FIRST NUMERIC PARITY EXCEEDANCE: " +
              json.dumps(first_exceedance, sort_keys=True))
        print("NUMERIC PARITY EXCEEDANCES: " + json.dumps(exceedances, sort_keys=True))
        raise SystemExit(
            f"{sum(item['count'] for item in exceedances.values())} values exceeded "
            "the declared per-field parity tolerances")
    if contact_mismatches:
        raise SystemExit(f"{len(contact_mismatches)} events have different contact sets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
