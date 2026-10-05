import json
import math
import os
from pathlib import Path
import unittest

from marble_qcqp_original import OriginalQCQP5,validated,synthetic_inputs,probe_packet


class QCQPInputTests(unittest.TestCase):
    def inputs(self):
        return [1.]*25,[0.]*5,[1.]*5,1.

    def test_all_native_array_widths_are_fixed_before_call(self):
        for i,length in ((0,24),(0,26),(1,4),(2,6)):
            values=list(self.inputs());values[i]=[1.]*length
            with self.assertRaises(ValueError):validated(*values)

    def test_nonfinite_or_non_numeric_inputs_are_rejected(self):
        for value in (True,"1",math.nan,math.inf):
            values=list(self.inputs());values[1]=[value]*5
            with self.assertRaises(ValueError):validated(*values)

    def test_zero_negative_scaling_or_negative_radius_are_rejected(self):
        for value in (0.,-1.):
            values=list(self.inputs());values[2]=[value]*5
            with self.assertRaises(ValueError):validated(*values)
        values=list(self.inputs());values[3]=-1.
        with self.assertRaises(ValueError):validated(*values)

    def test_radius_is_a_finite_number_not_a_boolean(self):
        for value in (True,math.inf,math.nan):
            values=list(self.inputs());values[3]=value
            with self.assertRaises(ValueError):validated(*values)

    def test_probe_packet_is_fixed_dimension_and_preserves_input_order(self):
        matrix,rhs,mu,radius=self.inputs()
        packet=probe_packet(matrix,rhs,mu,radius)
        self.assertEqual(len(packet),38)
        self.assertEqual(packet[:3],[1,5,radius])
        self.assertEqual(packet[3:28],matrix)
        self.assertEqual(packet[28:33],rhs)
        self.assertEqual(packet[33:38],mu)

    def test_synthetic_probe_matrix_is_deterministic_and_whole_validated(self):
        self.assertEqual(list(synthetic_inputs()),list(synthetic_inputs()))
        self.assertEqual(len(list(synthetic_inputs())),1000)
        for inputs in synthetic_inputs():self.assertEqual(len(probe_packet(*inputs)),38)


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class OriginalQCQPTests(unittest.TestCase):
    def test_direct_original_constrained_raw_force_on_captured_five_tangent_inputs(self):
        f=json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_solver_residual_order_rejected.json").read_text())
        c=f["nextNoSlipForceBoundary"]
        a=c["qualifiedNative"]
        original=OriginalQCQP5(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        output=original.solve(a["matrix"],a["rhs"],a["mu"],a["normal"])
        self.assertEqual(output,c["actualOriginalQCQP"])
        self.assertTrue(output["active"])
        self.assertNotEqual(output["rawForce"],a["updatedForce"])

    def test_unconstrained_zero_rhs_has_no_projection(self):
        original=OriginalQCQP5(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        matrix=[1. if i==j else 0. for i in range(5) for j in range(5)]
        output=original.solve(matrix,[0.]*5,[1.]*5,1.)
        self.assertFalse(output["active"])
        self.assertEqual(output["rawForce"],[0.]*5)

    def test_decomposed_driver_matches_direct_original_constrained_witness(self):
        f=json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_solver_residual_order_rejected.json").read_text())
        a=f["nextNoSlipForceBoundary"]["qualifiedNative"]
        original=OriginalQCQP5(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        inputs=(a["matrix"],a["rhs"],a["mu"],a["normal"])
        direct=original.solve(*inputs);model=original.decomposed(*inputs)
        self.assertEqual(direct,{k:model[k] for k in ("active","rawForce")})
        self.assertTrue(model["steps"])
        self.assertEqual(model["steps"][0]["lambdaBefore"],0.)

    def test_decomposed_driver_has_bounded_deterministic_direct_original_matrix(self):
        original=OriginalQCQP5(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        counts=dict(active=0,inactive=0,rank=0)
        for case,(matrix,rhs,scaling,radius) in enumerate(synthetic_inputs()):
            # Symmetric positive definite matrices, correlated/off-diagonal and
            # multiscale diagonal terms. Do not feed indefinite inputs to a
            # guessed solver or infer arbitrary-magnitude correctness.
            direct=original.solve(matrix,rhs,scaling,radius)
            model=original.decomposed(matrix,rhs,scaling,radius)
            with self.subTest(case=case):
                self.assertEqual(direct,{k:model[k] for k in ("active","rawForce")})
            counts["active" if direct["active"] else "inactive"]+=1
            counts["rank"]+=model["steps"][-1]["reason"]=="rank"
            self.assertLessEqual(len(model["steps"]),20)
        self.assertTrue(all(counts.values()))
