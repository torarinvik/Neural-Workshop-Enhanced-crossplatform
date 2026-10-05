import json
import ctypes
import hashlib
import math
import os
from pathlib import Path
import platform
import unittest

from marble_primal_prepare_oracle import prepare, prepare_rows
from marble_prepare_trace import qualified_preparations
from marble_native_dot_oracle import wheel_dot
from marble_dense_solve_oracle import native_dot
from marble_constraint_update_oracle import captured_difference


class PrepareValidationTests(unittest.TestCase):
    @staticmethod
    def scalar():
        return dict(jaref=[0.5], jv=[0.25], D=[2.0], types=[0], ids=[-1], contacts=[])

    @staticmethod
    def cone(dim=3):
        return dict(jaref=[0.25]*dim, jv=[0.125]*dim, D=[2.0]*dim,
                    types=[7]*dim, ids=[0]*dim,
                    contacts=[dict(dim=dim, mu=0.5, friction=[0.5]*5)])

    def test_whole_constraint_selection_validated_before_callback(self):
        calls = []
        inputs = self.cone()
        inputs["ids"][-1] = 1
        with self.assertRaises(ValueError):
            prepare(search=[1.0], Ma=[1.0], Mv=[1.0], qfrc_smooth=[0.0],
                    gauss0=0, dot=lambda *a: calls.append(a), **inputs)
        self.assertEqual(calls, [])

    def test_invalid_capture_selection_rejected(self):
        for key, value in (("jv", []), ("D", [float("nan")]), ("D", [-1]),
                           ("types", [0.5]), ("ids", [True]), ("contacts", None)):
            with self.subTest(key=key):
                inputs = self.scalar()
                inputs[key] = value
                with self.assertRaises(ValueError):
                    prepare_rows(**inputs)

    def test_invalid_contact_and_row_group_rejected(self):
        for field, value in (("dim", 2), ("dim", True), ("dim", 3.0), ("mu", 0),
                             ("mu", float("inf")), ("friction", [0.5]*4),
                             ("friction", [-0.5]*5)):
            inputs = self.cone()
            inputs["contacts"][0][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    prepare_rows(**inputs)
        for key, value in (("types", [7, 7, 1]), ("ids", [0, 0, 1])):
            inputs = self.cone()
            inputs[key] = value
            with self.assertRaises(ValueError):
                prepare_rows(**inputs)

    def test_frictionless_contact_before_elliptic_group_is_not_consumed(self):
        inputs = self.cone()
        inputs["ids"] = [1]*3
        inputs["contacts"].insert(0, dict(dim=1, mu=0, friction=[0.0]*5))
        # This checks contact selection, not fused arithmetic equivalence.
        rows = prepare_rows(**inputs, fma=lambda a, b, c: a*b+c)
        self.assertEqual(rows[0]["dim"], 3)

    def test_velocity_bounds_and_nonfinite_gauss_rejected(self):
        for n in (0, 513):
            with self.assertRaises(ValueError):
                prepare(search=[1.0]*n, Ma=[1.0]*n, Mv=[1.0]*n, qfrc_smooth=[0.0]*n,
                        gauss0=0, dot=lambda a,b: 0, **self.scalar())
        with self.assertRaises(ValueError):
            prepare(search=[1.0], Ma=[1.0], Mv=[1.0], qfrc_smooth=[0.0],
                    gauss0=0, dot=lambda a,b: float("inf"), **self.scalar())


@unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded math.fma")
class PrepareOrderTests(unittest.TestCase):
    def test_scalar_initializes_exactly_three_scaled_coefficients(self):
        rows = prepare_rows(**PrepareValidationTests.scalar())
        self.assertEqual(rows[0]["quad"], [0.25, 0.25, 0.0625])
        self.assertNotIn("tangentStages", rows[0])

    def test_elliptic_active_entries_and_tangent_counts(self):
        for dim in (3, 4, 6):
            rows = prepare_rows(**PrepareValidationTests.cone(dim))
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]["quad"]), 9)
            self.assertEqual(len(rows[0]["bottomStages"]), dim-1)
            self.assertEqual(len(rows[0]["tangentStages"]), dim-1)

    def test_gauss_dot_order_and_constant_preserved(self):
        operands = []
        def dot(a, b):
            operands.append((a.copy(), b.copy()))
            return sum(x*y for x,y in zip(a,b))
        result = prepare(search=[0.5, 0.25], Ma=[2., 3.], Mv=[4., 5.],
                         qfrc_smooth=[0.25, 0.5], gauss0=7.0, dot=dot,
                         **PrepareValidationTests.scalar())
        self.assertEqual(result["quadGauss"], [7.0, 1.5, 1.625])
        self.assertEqual(operands, [([0.5, 0.25], [2., 3.]),
                                   ([0.25, 0.5], [0.5, 0.25]),
                                   ([0.5, 0.25], [4., 5.])])

    def test_fused_uv_matches_all_retained_native_tangent_windows(self):
        fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_prepare_windows.json").read_text())
        checked = different = 0
        for boundary in fixture["entries"]:
            probes = boundary.get("nativeTangentProbes", [])
            if not probes:
                continue
            uv = uu = vv = 0.0
            rounded_uv = 0.0
            U = V = None
            for probe in probes:
                label = probe["label"]
                values = probe["native"]
                if label % 10 == 0:
                    U, V = values[:2]
                elif label % 10 == 1:
                    uu = math.fma(U, U, uu)
                    rounded_uv += values[0]
                    self.assertEqual(uu, values[2])
                elif label % 10 == 2:
                    uv = math.fma(U, V, uv)
                    vv = math.fma(V, V, vv)
                    self.assertEqual([uv, vv], values[:2], str(boundary["event"]))
                    checked += 1
                    different += rounded_uv != uv
        self.assertEqual(checked, 10)
        self.assertGreater(different, 0)

    def test_bottom_polynomials_match_all_eight_native_preparation_windows(self):
        fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_prepare_windows.json").read_text())
        checked = 0
        for entry in fixture["entries"]:
            rows = prepare_rows(**entry["inputs"])
            expected = {}
            for row in rows:
                start = 910000+row["row"]*1000
                inp = entry["inputs"]
                normal_dj = inp["D"][row["row"]]*inp["jaref"][row["row"]]
                expected[start] = row["initial"][1:]+[normal_dj]
                for stage in row["bottomStages"]:
                    k = row["row"]+stage["tangent"]
                    label = start+10*stage["tangent"]
                    expected[label+1] = stage["before"][1:]+[stage["DJ"]]
                    expected[label+2] = [stage["DJ"]]+stage["roundedIncrements"][1:]
                    expected[label+3] = stage["after"][1:]+[stage["DJ"]]
                    expected[label+4] = [inp["jv"][k], inp["D"][k], inp["jaref"][k]]
            for probe in entry["nativeBottomProbes"]:
                self.assertEqual(expected[probe["label"]], probe["slots"],
                                 f"event {entry['event']}/{entry['substep']}/{probe['label']}")
                checked += 1
        self.assertEqual(checked, 195)


@unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded math.fma")
class CompletePreparationFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_prepare_full_oracle.json").read_text())

    def verify(self, dot):
        summary = dict(qualifiedBoundaries=0, preparations=0, initializedOutputs=0,
                       nonzeroDifferences=0, zeroSignOnlyDifferences=0)
        p = self.fixture["provenance"]
        for entry in self.fixture["entries"]:
            captures = qualified_preparations(entry["qualification"],
                reference_sha256=p["referenceSha256"],
                diagnostic_sha256=p["diagnosticLibrarySha256"],
                input_trace_sha256=p["inputTraces"][entry["matrix"]]["sha256"])
            self.assertEqual(len(captures), len(entry["modelComparisons"]))
            summary["qualifiedBoundaries"] += 1
            for c, expected in zip(captures, entry["modelComparisons"]):
                modeled = prepare(**c["inputs"], dot=dot)
                rows = [{"row": a["row"], "dim": a["dim"],
                         "difference": captured_difference(a["quad"], b["quad"])}
                        for a, b in zip(modeled["rows"], c["rows"])]
                actual = {"ordinal": c["ordinal"], "initializedOutputs":
                    3+sum(len(row["quad"]) for row in c["rows"]),
                    "gauss": captured_difference(modeled["quadGauss"], c["quadGauss"]),
                    "rows": rows}
                self.assertEqual(actual, expected, str((entry["matrix"],
                    entry["qualification"]["event"], entry["qualification"]["substep"],
                    c["ordinal"])))
                summary["preparations"] += 1
                summary["initializedOutputs"] += actual["initializedOutputs"]
                for difference in [actual["gauss"]]+[r["difference"] for r in rows]:
                    summary["nonzeroDifferences"] += difference["nonzeroDifferenceCount"]
                    summary["zeroSignOnlyDifferences"] += difference["zeroSignOnlyCount"]
        for field in summary:
            self.assertEqual(summary[field], self.fixture["summary"][field], field)
        return summary

    def test_all_74_complete_native_preparations_and_1167_initialized_outputs(self):
        self.assertEqual(self.verify(wheel_dot), dict(qualifiedBoundaries=20,
            preparations=74, initializedOutputs=1167, nonzeroDifferences=0,
            zeroSignOnlyDifferences=0))

    def test_matrix_is_explicitly_diagnostic_not_trajectory_acceptance(self):
        p = self.fixture["provenance"]
        self.assertIs(p["capturedZeroSigns"], False)
        self.assertIn("not full trajectory acceptance", p["scope"])
        self.assertEqual({entry["matrix"] for entry in self.fixture["entries"]},
                         {"neutral", "rejectedThreePrimitive"})
        self.assertEqual(p["referenceSha256"],
                         "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c")

    def test_real_initialized_schema2_differences_are_retained(self):
        neutral = [e for e in self.fixture["entries"] if e["matrix"] == "neutral"]
        self.assertEqual(len(neutral), 12)
        self.assertEqual(sum(e["nativeIterationRecords"] for e in neutral), 166)
        for e in neutral:
            comparison = e["iterationComparison"]
            self.assertEqual(comparison["schemas"], [2, 2])
            self.assertIs(comparison["comparable"], True)
            self.assertIsNotNone(comparison["firstDifference"])
            self.assertNotIn(comparison["firstDifference"]["field"],
                             ("decode error", "schema/validity"))

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_complete_model_with_actual_original_wheel_dot_callback(self):
        if platform.machine() != self.fixture["provenance"]["nativeArchitecture"]:
            self.skipTest("fixture records the original arm64 wheel")
        path = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         self.fixture["provenance"]["referenceSha256"])
        library = ctypes.CDLL(str(path))
        self.verify(lambda a, b: native_dot(library, a, b))


if __name__ == "__main__":
    unittest.main()
