import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import unittest

from marble_dense_solve_oracle import (
    captured_dense_stages, captured_solve, native_dot, solve, wheel_order_solve,
)
from marble_cone_update_oracle import difference
from marble_constraint_update_oracle import captured_difference


class CapturedSolveTests(unittest.TestCase):
    def test_reads_mgrad_after_force_acceleration_matrix_and_gradient(self):
        # nv=2, nefc=1: header, force, qacc, Ma, grad, Mgrad, search, Jaref.
        payload = [90, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 91]
        header = [1, 0, 0, 0, 2, 1, 0, 0, 0]
        trace = {"cholSolveInput": [2, -1, 1, 0, 0, 1, 5, 6],
                 "values": [10, *header[1:], *payload, *header, *payload]}
        self.assertEqual(captured_solve(trace),
                         (2, [1, 0, 0, 1], [5, 6], [7, 8]))

    def test_rejects_sparse_and_incomplete_operands_before_native_call(self):
        for operands in ([2, 3], [2, -1, 1], [1.5, -1], [0, -1],
                         [True, -1, 1, 2], [513, -1], [1, -1, 0, 3],
                         [1, -1, 2, float("nan")], [1, -1, 2, float("inf")]):
            with self.subTest(operands=operands), self.assertRaises(ValueError):
                captured_solve({"cholSolveInput": operands, "values": []})

    def test_rejects_truncated_newton_payload(self):
        with self.assertRaisesRegex(ValueError, "truncated Newton record payload"):
            captured_solve({"cholSolveInput": [1, -1, 2, 3],
                            "values": [1, 0, 0, 0, 1, 1, 0, 0, 0]})

    def test_dense_stage_layout_and_bounded_safe_dimensions(self):
        record = {"denseSolveStages": [1, 2, 6, 3, 1.5]}
        self.assertEqual(captured_dense_stages(record), (1, [2], [6], [[3]], [[1.5]]))
        for values in ([True], [0], [513], [1, 2, 6, 3], [1, 2, 6, 3, 1.5, 0],
                       [1, 0, 6, 3, 1.5], [1, 2, float("nan"), 3, 1.5]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                captured_dense_stages({"denseSolveStages": values})

    def test_dense_model_records_each_forward_and_reverse_stage(self):
        model = wheel_order_solve(2, [2, 0, 1, 3], [4, 8],
                                 lambda a, b: sum(x*y for x, y in zip(a, b)),
                                 lambda a, b, c: a*b+c)
        self.assertEqual(model["forward"], [[2, 8], [2, 2]])
        # Preserve the subtraction's binary64 rounding; do not simplify the
        # algebra to the rational 2/3 before evaluating the row.
        first = (2-2/3)/2
        self.assertEqual(model["backward"], [[2, 2/3], [first, 2/3]])
        self.assertEqual(model["result"], [first, 2/3])

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_wheel_dense_model_and_stage_differences_on_twelve_recorded_inputs(self):
        d = json.loads((Path(__file__).with_name("fixtures") /
                        "marble_initialized_hessian_oracle.json").read_text())
        if platform.machine() != d["provenance"]["nativeArchitecture"]:
            self.skipTest("fixture records the original arm64 wheel")
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         d["provenance"]["referenceSha256"])
        kernels = ctypes.CDLL(str(library))
        for expected in d["expectedDense"]:
            event, step = expected["event"], expected["substep"]
            record = d["events"][event]["newtonTraces"][step]
            n, matrix, rhs, forward, backward = captured_dense_stages(record)
            self.assertEqual(captured_solve(record)[:3], (n, matrix, rhs))
            native = solve(kernels, n, matrix, rhs)
            modeled = wheel_order_solve(n, matrix, rhs,
                                       lambda a, b: native_dot(kernels, a, b), math.fma)
            with self.subTest(event=expected["sourceEvent"], step=step):
                # Serialized zero signs are not an acceptance claim. Raw model
                # and direct-wheel results must still match bit for bit.
                self.assertEqual(native, expected["original"])
                self.assertEqual(difference(native, modeled["result"]), expected["model"])
                self.assertEqual([captured_difference(a, b) for a, b in zip(
                    modeled["forward"], forward)], expected["forward"])
                self.assertEqual([captured_difference(a, b) for a, b in zip(
                    modeled["backward"], backward)], expected["backward"])


if __name__ == "__main__":
    unittest.main()
