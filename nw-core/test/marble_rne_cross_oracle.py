#!/usr/bin/env python3
"""Isolate original RNE cross-force via a zero-acceleration one-body model.

Run in the original application's MuJoCo Python environment. Only compare
captures whose inertial-velocity products already pass marble_inertia_oracle:
otherwise an upstream product difference can explain a cross-force difference.
"""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np


class CrossOracle:
    def __init__(self):
        self.model = mujoco.MjModel.from_xml_string(
            '<mujoco><option gravity="0 0 0"/><worldbody><body>'
            '<freejoint/><geom type="sphere" size="0.1" mass="1"/>'
            '</body></worldbody></mujoco>')
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        self.data.qvel[:] = 0
        self.data.qacc[:] = 0
        self.data.cdof_dot[:] = 0
        self.data.cdof[:] = np.eye(6)

    def evaluate(self, inertia, velocity):
        if len(inertia) != 10 or len(velocity) != 6:
            raise ValueError("expected 10 inertia and 6 velocity components")
        if not np.isfinite(inertia).all() or not np.isfinite(velocity).all():
            raise ValueError("non-finite input")
        self.data.cinert[1] = inertia
        self.data.cvel[1] = velocity
        result = np.zeros(6)
        mujoco.mj_rne(self.model, self.data, 0, result)
        return result.tolist()


class MotionOracle:
    """Expose cross-motion through original comVel on a zero-speed child joint."""
    def __init__(self):
        self.model = mujoco.MjModel.from_xml_string(
            '<mujoco><worldbody><body><freejoint/><geom size=".1"/>'
            '<body pos="0 0 1"><joint type="hinge"/><geom size=".1"/>'
            '</body></body></worldbody></mujoco>')
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)

    def evaluate(self, velocity, axis):
        if len(velocity) != 6 or len(axis) != 6:
            raise ValueError("expected six velocity and axis components")
        if not np.isfinite(velocity).all() or not np.isfinite(axis).all():
            raise ValueError("non-finite input")
        self.data.cdof[:6] = np.eye(6)
        self.data.cdof[6] = axis
        self.data.qvel[:6] = velocity
        self.data.qvel[6] = 0
        mujoco.mj_comVel(self.model, self.data)
        if not np.array_equal(self.data.cvel[1], velocity):
            raise AssertionError("parent velocity construction changed operands")
        return self.data.cdof_dot[6].tolist()


class ProjectionOracle(CrossOracle):
    """Use identity inertia and a prescribed cdof_dot*qvel force for projection."""
    def evaluate(self, axis, force):
        if len(axis) != 6 or len(force) != 6:
            raise ValueError("expected six axis and force components")
        if not np.isfinite(axis).all() or not np.isfinite(force).all():
            raise ValueError("non-finite input")
        self.data.cvel[:] = 0
        self.data.cinert[1] = [1, 1, 1, 0, 0, 0, 0, 0, 0, 1]
        self.data.qvel[:] = 0
        self.data.qvel[0] = 1
        self.data.cdof_dot[:] = 0
        self.data.cdof_dot[0] = force
        self.data.cdof[:] = axis
        result = np.zeros(6)
        mujoco.mj_rne(self.model, self.data, 0, result)
        return float(result[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--event", type=int, action="append", required=True)
    parser.add_argument("--projection", action="store_true")
    args = parser.parse_args()
    events = json.loads(args.trace.read_text())["events"]
    oracle = CrossOracle()
    projection = ProjectionOracle() if args.projection else None
    failed = False
    for index in args.event:
        if not 0 <= index < len(events):
            parser.error("event outside trace")
        event = events[index]
        traces, phases = event["rneTraces"], event["engineStep1Phases"]
        if not traces or len(traces) != len(phases):
            raise ValueError("missing or mismatched substeps")
        for substep, (trace, checkpoints) in enumerate(zip(traces, phases)):
            matches = [p["engine"] for p in checkpoints if p["phase"] == "probe_rneBias"]
            if len(matches) != 1:
                raise ValueError("expected one RNE checkpoint")
            engine = matches[0]
            arrays = engine["arrays"]
            bodies = len(engine["model"]["body_parentid"])
            if len(trace) != 36*bodies + 13*len(arrays["qvel"]):
                raise ValueError("invalid RNE trace length")
            if projection is not None:
                nv = len(arrays["qvel"])
                base = 36*bodies + nv
                for dof in range(nv):
                    operands = trace[base+12*dof:base+12*dof+12]
                    original = projection.evaluate(operands[:6], operands[6:])
                    wasm = trace[36*bodies+dof]
                    differences = [] if original == wasm else [[dof, original, wasm]]
                    failed |= bool(differences)
                    print(json.dumps({"event": index, "substep": substep,
                                      "dof": dof, "differences": differences}, allow_nan=False))
                continue
            for body in range(1, bodies):
                original = oracle.evaluate(arrays["cinert"][10*body:10*body+10],
                                           arrays["cvel"][6*body:6*body+6])
                wasm = trace[36*body+18:36*body+24]
                differences = [[i, original[i], wasm[i]] for i in range(6)
                               if original[i] != wasm[i]]
                failed |= bool(differences)
                print(json.dumps({"event": index, "substep": substep, "body": body,
                                  "differences": differences}, allow_nan=False))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
