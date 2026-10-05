import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).with_name("repro")))
from generate_marble_solver_probe_inputs import packet, branch_matrix
from marble_primal_eval_oracle_test import empty, scalar, cone


class SolverPacketTests(unittest.TestCase):
    def test_empty_packet_has_exact_header_and_gauss(self):
        self.assertEqual(packet(empty()), [1, 0.5, 0, 0, 0, 0, 2., 3., 4.])

    def test_equality_prefix_and_compact_friction_loss(self):
        data = packet(scalar(nf=1, kind=1))
        self.assertEqual(data[:6], [1, 1., 0, 1, 1, 0])
        self.assertEqual(len(data), 19)
        self.assertEqual(data[13], 2.)

    @unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded fma")
    def test_active_elliptic_quads_only_transport_padding_is_zero(self):
        for dim in (3, 4, 6):
            inputs = cone(0., 4., dim=dim)
            data = packet(inputs)
            self.assertEqual(len(data), 9+9*dim+2)
            q = data[9+6*dim+2:]
            self.assertEqual(q[:9], inputs["rows"][0]["quad"])
            self.assertEqual(q[9:], [0.]*(3*dim-9))

    def test_input_validation_precedes_packing(self):
        for field, value in (("alpha", True), ("ne", 1), ("jv", [1.]),
                             ("rows", None), ("D", [math.inf])):
            inputs = empty()
            inputs[field] = value
            with self.assertRaises(ValueError):
                packet(inputs)

    @unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded fma")
    def test_branch_matrix_is_all_145_previously_qualified_selections(self):
        cases = list(branch_matrix())
        self.assertEqual(len(cases), 145)
        self.assertEqual(len([c for c in cases if c["nf"]]), 18)
        self.assertEqual({c["contacts"][0]["dim"] for c in cases if c["contacts"]}, {3,4,6})
