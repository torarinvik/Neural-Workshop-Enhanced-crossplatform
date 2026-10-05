import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import unittest

from marble_cone_update_oracle import (Kernels, captured_cone, difference, replay,
                                       wheel_order_rank_update)


def fixture():
    # One dim=1 contact in a dense n=2 solver. x[0] is zero, so only k=1
    # is traced. Distinct upper-triangle sentinels catch accidental reshaping.
    before = [2, 91, 0, 3]
    after = [2, 91, 0, 5]
    return [2, 1, *before, 4, 1, 16, 4, 0, 1, 0, 4,
            *before, 1, 2, 0, 4, *after, *after, 0, 4]


class ConeCaptureTests(unittest.TestCase):
    def test_consumes_nonzero_steps_and_preserves_dense_layout(self):
        result = captured_cone(fixture())
        self.assertEqual((result.nv, result.ncone), (2, 1))
        contact = result.contacts[0]
        self.assertEqual((contact.row, contact.dim), (4, 1))
        self.assertEqual(contact.hessian, [16])
        self.assertEqual(contact.factor, [4])
        self.assertEqual(contact.ltj, [0, 4])
        update = contact.updates[0]
        self.assertEqual(update.before, [2, 91, 0, 3])
        self.assertEqual(update.steps, [(1, [0, 4], [2, 91, 0, 5])])

    def test_ncone_counts_rows_and_all_updates_are_required(self):
        # Two dim=1 contacts, not one dim=2 contact. Second update has x=0.
        values = fixture()
        values[1] = 2
        last = [2, 91, 0, 5]
        values.extend([5, 1, 1, 1, 0, 0, 0, 0, *last, *last, 0, 0])
        result = captured_cone(values)
        self.assertEqual([c.row for c in result.contacts], [4, 5])
        self.assertEqual(result.contacts[1].updates[0].steps, [])

    def test_rejects_every_truncation(self):
        values = fixture()
        for size in range(len(values)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                captured_cone(values[:size])

    def test_rejects_trailing_data_overflow_and_nonfinite_values(self):
        for values in (fixture()+[0], [0], [2, 1, float("nan")],
                       [float("inf"), 1], [True, 1], [2.5, 1], [513, 1],
                       [2, 65537]):
            with self.subTest(values=values[:3]), self.assertRaises(ValueError):
                captured_cone(values)

    def test_rejects_discontinuous_factor_and_final_vector(self):
        for index in (14, 26, 31):
            values = copy.copy(fixture())
            values[index] += 1
            with self.subTest(index=index), self.assertRaises(ValueError):
                captured_cone(values)

    def test_rejects_step_dimension_or_order(self):
        for index in (18, 19):
            values = fixture()
            values[index] = 0
            with self.subTest(index=index), self.assertRaises(ValueError):
                captured_cone(values)

    def test_rejects_contact_that_exceeds_row_count(self):
        values = fixture()
        values[7] = 2
        with self.assertRaisesRegex(ValueError, "exceeds cone row count"):
            captured_cone(values)

    def test_exact_comparison_preserves_signed_zero(self):
        result = difference([0.0, 1.0], [-0.0, 1.0])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["first"]["referenceBits"], "0000000000000000")
        self.assertEqual(result["first"]["capturedBits"], "8000000000000000")
        with self.assertRaises(ValueError):
            difference([0], [])


class RecordedWheelTests(unittest.TestCase):
    @staticmethod
    def fixture():
        path = Path(__file__).with_name("fixtures") / "marble_event216_cone_oracle.json"
        return json.loads(path.read_text())

    def test_reduced_production_neutral_capture_is_complete(self):
        document = self.fixture()
        self.assertEqual(document["sourceEvent"], 216)
        self.assertTrue(document["provenance"]["solverInputExact"])
        self.assertTrue(document["provenance"]["solverOutputsExactlyMatchMaintainedArtifact"])
        records = document["events"][0]["newtonTraces"]
        self.assertEqual([len(r["coneTrace"]) for r in records], [0, 1120, 1120, 0])
        for step in (1, 2):
            capture = captured_cone(records[step]["coneTrace"])
            self.assertEqual((capture.nv, capture.ncone), (6, 3))
            self.assertEqual([len(c.updates) for c in capture.contacts], [3])

    def test_rejected_combined_candidate_records_local_success_and_global_failure(self):
        root = Path(__file__).resolve().parents[2]
        document = json.loads((Path(__file__).with_name("fixtures") /
                              "marble_solver_three_primitives_rejected.json").read_text())
        patch = root / document["candidateDelta"]
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(),
                         document["candidateDeltaSha256"])
        self.assertTrue(document["disposition"].startswith("rejected;"))
        hard = document["strictReplay"]
        self.assertEqual((hard["events"], hard["numericExceedances"],
                          hard["contactMismatches"]["count"]), (7601, 116249, 282))
        self.assertEqual(hard["contactMismatches"]["first"]["event"], 461)
        self.assertEqual(hard["firstNumericBreach"]["context"],
                         "event[216].marble[0].value[10]")
        self.assertEqual(document["directWheelHessian"], {
            "calls": 29, "forceMismatchCalls": 0, "hessianMismatchCalls": 0,
            "modelMismatchCalls": 0})
        self.assertEqual(document["directWheelDense"], {
            "calls": 12, "outputMismatchCalls": 0, "modelMismatchCalls": 0})
        self.assertFalse(document["rankEvent216"]["anyReportedMismatch"])
        checks = document["solverLibraryBoundaryChecks"]
        self.assertEqual(len(checks), 8)
        self.assertTrue(all(r["exactInputCopy"] and r["solverOutputsExactlyEqual"] and
                            not r["outputDifferences"] for r in checks))
        boundaries = document["nextInitializedBoundaries"]
        self.assertEqual(len(boundaries), 8)
        self.assertEqual(boundaries[0]["firstInitializedNewtonDifference"]["label"], 25042)
        self.assertTrue(all(r["firstInitializedNewtonDifference"] for r in boundaries))
        self.assertFalse(document["zeroSignsCaptured"])

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_active_wheel_reproduces_recorded_exact_input_outputs(self):
        document = self.fixture()
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        provenance = document["provenance"]
        if platform.machine() != provenance["nativeArchitecture"]:
            self.skipTest("fixture describes the original arm64 wheel, not this architecture")
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         provenance["referenceSha256"],
                         "use the fixture's exact reference wheel; do not silently update expectations")
        kernels = Kernels(library)
        for expected in document["expectedReplay"]:
            step = expected["substep"]
            capture = captured_cone(document["events"][0]["newtonTraces"][step]["coneTrace"])
            with self.subTest(substep=step):
                self.assertEqual(replay(capture, kernels), expected["rows"])


class RankUpdateModelTests(unittest.TestCase):
    def test_simple_update_preserves_upper_triangle_and_skips_zero(self):
        # Exact arithmetic operands permit a stdlib test even without math.fma.
        rank, factor, vector, steps = wheel_order_rank_update(
            [2, 91, 0, 3], [0, 4], 2, fma=lambda a, b, c: a*b+c)
        self.assertEqual((rank, factor, vector), (2, [2, 91, 0, 5], [0, 4]))
        self.assertEqual(steps, [(1, [0, 4], [2, 91, 0, 5])])
        result = wheel_order_rank_update([2, -0.0, 0, 3], [-0.0, 0.0], 2,
                                         fma=lambda a, b, c: a*b+c)
        self.assertTrue(difference(result[1], [2, -0.0, 0, 3])["exact"])
        self.assertTrue(difference(result[2], [-0.0, 0.0])["exact"])
        self.assertEqual(result[3], [])

    def test_clamped_downdate_retains_rank_and_step(self):
        result = wheel_order_rank_update([1], [2], 1, plus=False,
                                         fma=lambda a, b, c: a*b+c)
        self.assertEqual(result, (0, [math.sqrt(1e-15)], [2],
                                   [(0, [2], [math.sqrt(1e-15)])]))

    def test_rejects_unsafe_operands_before_computation(self):
        cases = (([1], [1], True, True), ([1], [1], 0, True),
                 ([1], [1], 513, True), ([1], [1], 1, 1),
                 ([0], [1], 1, True), ([-1], [1], 1, True),
                 ([1, 2], [1], 1, True), ([1], [], 1, True),
                 ([float("nan")], [1], 1, True),
                 ([1], [float("inf")], 1, True), ([True], [1], 1, True))
        for matrix, x, n, plus in cases:
            with self.subTest(n=n, matrix=matrix, x=x), self.assertRaises(ValueError):
                wheel_order_rank_update(matrix, x, n, plus=plus,
                                         fma=lambda a, b, c: a*b+c)


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY") and
                     hasattr(math, "fma"),
                     "set the original wheel and use Python with math.fma")
class NativeRankUpdateModelTests(unittest.TestCase):
    def setUp(self):
        document = RecordedWheelTests.fixture()
        provenance = document["provenance"]
        if platform.machine() != provenance["nativeArchitecture"]:
            self.skipTest("operation-order model describes the original arm64 wheel")
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         provenance["referenceSha256"])
        self.kernels = Kernels(library)
        self.document = document

    def assertModelMatches(self, matrix, x, n, plus=True):
        expected = self.kernels.update(matrix, x, n, plus=plus)
        rank, factor, vector, _ = wheel_order_rank_update(matrix, x, n, plus=plus)
        self.assertEqual(rank, expected[0])
        self.assertTrue(difference(expected[1], factor)["exact"],
                        difference(expected[1], factor))
        self.assertTrue(difference(expected[2], vector)["exact"],
                        difference(expected[2], vector))

    def test_all_six_recorded_rank_updates_match_direct_wheel(self):
        count = 0
        for record in self.document["events"][0]["newtonTraces"]:
            if not record["coneTrace"]:
                continue
            capture = captured_cone(record["coneTrace"])
            for contact in capture.contacts:
                for row, update in enumerate(contact.updates):
                    with self.subTest(call=count):
                        self.assertModelMatches(update.before,
                            contact.ltj[row*capture.nv:(row+1)*capture.nv], capture.nv)
                    count += 1
        self.assertEqual(count, 6)

    def test_synthetic_updates_and_downdates_match_exact_wheel(self):
        rng = random.Random(261001)
        for case in range(512):
            n = (1, 2, 3, 4, 6, 8, 12, 16)[case % 8]
            # Lower factors are nonsingular, with untouched upper sentinels.
            factor = [rng.uniform(-.5, .5) for _ in range(n*n)]
            for k in range(n):
                factor[k*(n+1)] = rng.uniform(1, 10)
            x = [0.0 if rng.randrange(4) == 0 else rng.uniform(-.05, .05)/n
                 for _ in range(n)]
            for plus in (True, False):
                with self.subTest(case=case, n=n, plus=plus):
                    self.assertModelMatches(factor, x, n, plus)

    def test_zero_and_minimum_diagonal_cases_match_exact_wheel(self):
        for matrix, x, plus in (([1], [2], False), ([1e-10], [2e-10], False),
                                 ([1e-310], [2e-310], True), ([1e-310], [0.0], True),
                                 ([2, -0.0, 0.0, 3], [-0.0, 0.0], True),
                                 ([2, -0.0, 0.0, 3], [-0.0, 0.0], False)):
            with self.subTest(matrix=matrix, x=x, plus=plus):
                self.assertModelMatches(matrix, x, len(x), plus)


if __name__ == "__main__":
    unittest.main()
