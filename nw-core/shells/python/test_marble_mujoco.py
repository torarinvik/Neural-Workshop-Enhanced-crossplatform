#!/usr/bin/env python3
"""Native MuJoCo adapter ABI, MJCF, input, and lifecycle regression tests."""
from __future__ import annotations

import math
import gc
import os
from pathlib import Path
import sys
import weakref

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "build" / "pymod"))
sys.path.insert(0, str(HERE))

import mujoco  # noqa: E402
import nwcore  # noqa: E402
from marble_mujoco import (  # noqa: E402
    MuJoCoMarblePhysics,
    build_mjcf,
    decode_board,
)


def load_reference():
    reference = Path(os.environ.get(
        "NEURAL_WORKSHOP_SOURCE_ROOT",
        str(Path(__file__).resolve().parents[5] / "Python Projects" / "neural-workshop-enhanced"),
    ))
    if reference.is_dir():
        sys.path.insert(0, str(reference))
    from neural_workshop import marblemaze  # noqa: PLC0415
    return marblemaze


def main() -> int:
    assert sys.version_info[:3] == (3, 13, 12), sys.version
    assert mujoco.__version__ == "3.12.0", mujoco.__version__
    reference = load_reference()

    # `advance` must preserve the original UI's positive-remainder behavior;
    # even a sub-nanosecond bite is a real MuJoCo update, and 50 ms leaves a
    # tiny fourth bite after the three nominal 60 Hz steps.
    partition_probe = MuJoCoMarblePhysics.__new__(MuJoCoMarblePhysics)
    partition_probe.nudge_due = 0.0
    bites: list[float] = []
    partition_probe.step = bites.append
    partition_probe.advance(0.05)
    assert len(bites) == 4 and all(bite > 0.0 for bite in bites), bites
    assert abs(sum(bites) - 0.05) < 1e-15, bites
    partition_probe.advance(0.5e-9)
    assert len(bites) == 5 and bites[-1] == 0.5e-9, bites

    seeds = (0, 1, 17, 314159, 1073741823)
    cases = 0
    for rung in range(1, 17):
        for seed in seeds:
            source_tray = reference.deal(rung, seed)
            board = decode_board(nwcore.marble_board(rung, seed))
            count = len(source_tray.starts)
            assert build_mjcf(board, count) == reference._mjcf(source_tray, count), (
                f"MJCF mismatch at rung={rung} seed={seed}"
            )
            model = mujoco.MjModel.from_xml_string(build_mjcf(board, count))
            data = mujoco.MjData(model)
            try:
                assert model.nq == count * 7
                assert model.nv == count * 6
            finally:
                del data
                del model
            cases += 1

    payload = nwcore.marble_board(1, 17)
    try:
        decode_board(payload[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError("truncated board accepted")

    board = decode_board(payload)
    class PartialModel:
        pass

    class FailingBinding:
        class MjModel:
            @staticmethod
            def from_xml_string(_xml):
                instance = PartialModel()
                failing_binding.model_ref = weakref.ref(instance)
                return instance

        @staticmethod
        def MjData(_model):
            raise MemoryError("injected MjData allocation failure")

    failing_binding = FailingBinding()
    partial = MuJoCoMarblePhysics(board, failing_binding)
    try:
        partial.step(1 / 60)
    except MemoryError:
        pass
    else:
        raise AssertionError("injected partial MuJoCo allocation failure was ignored")
    gc.collect()
    assert failing_binding.model_ref() is None, "partial model leaked after MjData construction failed"
    partial.close()

    oracle_tray = reference.deal(1, 17)
    oracle = reference.Simulation(oracle_tray)
    parity = MuJoCoMarblePhysics(board, mujoco)
    try:
        oracle.tilt(reference.TILT_EAST)
        parity.tilt("E")
        for _ in range(120):
            oracle.step(1 / 60)
            parity.step(1 / 60)
            for native, source in zip(parity.marbles, oracle.marbles):
                for field in ("x", "y", "z", "vx", "vy", "vz",
                              "wx", "wy", "wz", "qw", "qx", "qy", "qz"):
                    tolerance = 1e-8 if field in ("x", "y", "z") else 1e-7
                    assert abs(getattr(native, field) - getattr(source, field)) <= tolerance, (
                        f"source trajectory mismatch at {field}: "
                        f"{getattr(native, field)} != {getattr(source, field)}"
                    )
    finally:
        parity.close()
        oracle._model = oracle._data = None

    physics = MuJoCoMarblePhysics(board, mujoco)
    try:
        assert physics.elapsed == 0 and len(physics.marbles) == len(board.starts)
        for _ in range(15):
            physics.advance(1 / 60, {"E"})
        assert abs(physics.roll - 0.09) < 1e-12
        assert abs(physics.elapsed - 0.25) < 1e-12
        assert physics.nudge_due < 1e-12
        assert any(abs(marble.x - board.starts[0].x) > 1e-8
                   for marble in physics.marbles[:1])
        assert all(math.isfinite(value) for state in physics.snapshot()
                   for value in state[:-1])
        physics.advance(0.025, ())
        assert physics.nudge_due == 0
        assert physics.elapsed > 0.25
        model_ref = weakref.ref(physics.model)
        data_ref = weakref.ref(physics.data)
        physics.reset()
        assert physics.model is None and physics.data is None
        assert physics.elapsed == 0 and physics.roll == 0 and physics.pitch == 0
        gc.collect()
        assert model_ref() is None and data_ref() is None, "MuJoCo model/data survive reset"
    finally:
        physics.close()

    print(f"PASS: native MuJoCo adapter; source MJCF exact for {cases} board cases; input and cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
