import copy
import json
import math
import os
from pathlib import Path
import random
import struct
import unittest
from unittest.mock import patch

from marble_primal_eval_oracle import (OriginalEval, check_layout, evaluate,
                                      validated_inputs)
from marble_primal_prepare_oracle import prepare_rows
from marble_eval_trace import capture_evaluations, qualified_evaluations
from marble_constraint_update_oracle import captured_difference


def empty():
    return dict(alpha=0.5, ne=0, nf=0, gauss=[2., 3., 4.], jaref=[], jv=[],
                D=[], R=[], frictionloss=[], types=[], ids=[], contacts=[], rows=[])


def scalar(start=0.5, end=-0.25, *, kind=3, ne=0, nf=0):
    return dict(alpha=1., ne=ne, nf=nf, gauss=[3., 1., 2.], jaref=[start],
                jv=[end-start], D=[2.], R=[0.5], frictionloss=[2.] if nf else [],
                types=[kind], ids=[-1], contacts=[],
                rows=[dict(row=0, dim=1, quad=[start*start, 2*start*(end-start),
                                              (end-start)**2])])


def cone(start, end, *, dim=3, mu=1., alpha=1., zero_tangent=False):
    tangents = [0.]* (dim-1) if zero_tangent else [1.]+[0.]*(dim-2)
    inputs = dict(jaref=[start/mu]+tangents, jv=[(end-start)/(mu*alpha)]+[0.]*(dim-1),
                  D=[2.]*dim, types=[7]*dim, ids=[0]*dim,
                  contacts=[dict(dim=dim, mu=mu, friction=[1.]*5)])
    return dict(alpha=alpha, ne=0, nf=0, gauss=[3., 1., 2.], R=[0.5]*dim,
                frictionloss=[], rows=prepare_rows(**inputs), **inputs)


def random_inputs(count=5000):
    rng = random.Random(42002105)
    for _ in range(count):
        ne, nf = rng.randrange(3), rng.randrange(3)
        types = [0]*ne+[1]*nf+[rng.randrange(2, 7) for _ in range(rng.randrange(4))]
        ids = [-1]*len(types)
        contacts = []
        for _ in range(rng.randrange(1, 4)):
            dim = rng.choice((3, 4, 6))
            contacts.append(dict(dim=dim, mu=rng.uniform(0.1, 3.),
                                 friction=[rng.uniform(0.2, 2.) for _ in range(5)]))
            types += [7]*dim
            ids += [len(contacts)-1]*dim
        n = len(types)
        inputs = dict(jaref=[rng.uniform(-3., 3.) for _ in range(n)],
                      jv=[rng.uniform(-3., 3.) for _ in range(n)],
                      D=[2.**rng.uniform(-3., 3.) for _ in range(n)],
                      types=types, ids=ids, contacts=contacts)
        yield dict(alpha=rng.uniform(-2., 2.), ne=ne, nf=nf,
                   gauss=[rng.uniform(-1., 1.), rng.uniform(-1., 1.), rng.uniform(0.1, 10.)],
                   R=[1/v for v in inputs["D"]], frictionloss=[rng.uniform(0.1, 2.) for _ in range(nf)],
                   rows=prepare_rows(**inputs), **inputs)


def bits(values):
    return [struct.pack("!d", v) for v in values]


class EvalValidationTests(unittest.TestCase):
    def test_exact_original_layout_guard(self):
        check_layout()

    def test_arrays_and_dimensions_are_bounded_before_callback(self):
        calls = []
        for key, value in (("alpha", True), ("alpha", math.nan), ("ne", True),
                           ("nf", 1), ("gauss", []), ("jv", [1.]), ("D", [-1.]),
                           ("types", [0.5]), ("contacts", None), ("rows", None)):
            inputs = empty()
            inputs[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                evaluate(**inputs, fma=lambda *a: calls.append(a))
        self.assertEqual(calls, [])

    def test_scalar_row_indices_and_active_coefficients_are_checked(self):
        for key, value in (("row", True), ("row", 0.), ("row", 1),
                           ("dim", 3), ("dim", True), ("quad", [1.]*9),
                           ("quad", [math.inf, 0., 1.])):
            inputs = scalar()
            inputs["rows"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validated_inputs(**inputs)

    @unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded fma")
    def test_elliptic_groups_and_consumed_contacts_are_checked(self):
        for key, value in (("types", [7, 7, 3]), ("ids", [0, 0, 1]),
                           ("R", [-1., 0.5, 0.5]), ("ne", 1)):
            inputs = cone(0., 1.)
            inputs[key] = value
            with self.assertRaises(ValueError):
                validated_inputs(**inputs)
        for key, value in (("dim", 2), ("dim", 3.), ("mu", 0.), ("mu", math.nan)):
            inputs = cone(0., 1.)
            inputs["contacts"][0][key] = value
            with self.assertRaises(ValueError):
                validated_inputs(**inputs)

    def test_private_bridge_rejects_another_library_before_loading(self):
        with patch("marble_primal_eval_oracle.sys.platform", "darwin"), \
                patch("marble_primal_eval_oracle.platform.machine", return_value="arm64"), \
                patch("marble_primal_eval_oracle.ctypes.CDLL") as load:
            with self.assertRaises(ValueError):
                OriginalEval(Path(__file__))
            load.assert_not_called()

    def test_private_bridge_rejects_wrong_target_before_loading(self):
        with patch("marble_primal_eval_oracle.platform.machine", return_value="x86_64"), \
                patch("marble_primal_eval_oracle.ctypes.CDLL") as load:
            with self.assertRaises(ValueError):
                OriginalEval("not-a-library")
            load.assert_not_called()


@unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded fma")
class EvalOrderTests(unittest.TestCase):
    def test_shifted_gauss_does_not_read_constant(self):
        inputs = empty()
        self.assertEqual(evaluate(**inputs)["result"], [2.5, 7., 8.])
        inputs["gauss"][0] = 1e200
        self.assertEqual(evaluate(**inputs)["result"], [2.5, 7., 8.])

    def test_equality_inequality_and_friction_branches(self):
        self.assertEqual(evaluate(**scalar(ne=1, kind=0))["stages"][0]["kind"], "equality")
        for start in (-2., 0., 2.):
            for end in (-2., 0., 2.):
                self.assertEqual(evaluate(**scalar(start, end, nf=1, kind=1))["stages"][0]["zones"],
                                 [int(math.copysign(1, start)) if start else 0,
                                  int(math.copysign(1, end)) if end else 0])
        for end in (-1., 0., 1.):
            self.assertEqual(evaluate(**scalar(-0.5, end))["stages"][0]["active"], end < 0)

    def test_all_nine_elliptic_zone_transitions(self):
        states = {1: 4., 2: -4., 3: 0.}
        for a, start in states.items():
            for b, end in states.items():
                self.assertEqual(evaluate(**cone(start, end))["stages"][0]["zones"], [a, b])

    def test_convexity_clamp_reports_actual_raw_value(self):
        inputs = empty()
        inputs["gauss"] = [1., 0., -2.]
        value = evaluate(**inputs)
        self.assertEqual((value["rawSecond"], value["result"][2]), (-4., 1e-15))
        self.assertTrue(value["convexityClamped"])


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY") and hasattr(math, "fma"),
                     "set original wheel path and use correctly rounded fma")
class OriginalEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = OriginalEval(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])

    def assert_original(self, inputs):
        self.assertEqual(bits(evaluate(**inputs)["result"]), bits(self.original.evaluate(**inputs)),
                         str(inputs))

    def test_all_nine_friction_and_elliptic_zone_transitions(self):
        for start in (-2., 0., 2.):
            for end in (-2., 0., 2.):
                self.assert_original(scalar(start, end, nf=1, kind=1))
        for dim in (3, 4, 6):
            for mu in (0.5, 1., 2.):
                for start in (-4., 0., 4.):
                    for end in (-4., 0., 4.):
                        self.assert_original(cone(start, end, dim=dim, mu=mu))

    def test_scalar_boundaries_and_degenerate_tangents(self):
        self.assert_original(empty())
        for start in (-1., 0., 1.):
            for end in (-1., 0., 1.):
                self.assert_original(scalar(start, end, kind=0, ne=1))
                self.assert_original(scalar(start, end, kind=1, nf=1))
                self.assert_original(scalar(start, end))
        for dim in (3, 4, 6):
            for start in (-4., 0., 4.):
                for end in (-4., 0., 4.):
                    self.assert_original(cone(start, end, dim=dim, zero_tangent=True))

    def test_5000_deterministic_mixed_constraint_inputs(self):
        for inputs in random_inputs():
            self.assert_original(inputs)

    def test_all_320_retained_prepared_inputs_against_actual_original(self):
        fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_eval_full_oracle.json").read_text())
        count = 0
        for entry in fixture["entries"]:
            groups = [(entry["qualification"]["trace"], entry["nativeComparisons"])]
            if "browserTrace" in entry:
                groups.append((entry["browserTrace"], entry["browserComparisons"]))
            for trace, expected in groups:
                for capture, checked in zip(capture_evaluations(trace), expected):
                    actual = self.original.evaluate(**capture["inputs"])
                    self.assertEqual([v.hex() for v in bits(actual)], checked["originalResultBits"])
                    self.assert_original(capture["inputs"])
                    count += 1
        self.assertEqual(count, 320)


class EvalFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_eval_full_oracle.json").read_text())

    def selection(self, entry):
        p = self.fixture["provenance"]
        return dict(reference_sha256=p["referenceSha256"],
                    diagnostic_sha256=p["diagnosticLibrarySha256"],
                    input_trace_sha256=p["inputTraces"][entry["matrix"]]["sha256"])

    def test_every_native_boundary_is_explicitly_qualified_before_eval_decode(self):
        count = 0
        for entry in self.fixture["entries"]:
            decoded = qualified_evaluations(entry["qualification"], **self.selection(entry))
            self.assertEqual(len(decoded), len(entry["nativeComparisons"]))
            count += len(decoded)
        self.assertEqual(count, 191)

    def test_failed_whole_output_or_identity_qualification_is_rejected(self):
        entry = self.fixture["entries"][0]
        for field, value in (("solverOutputsExactlyEqual", False), ("exactInputCopy", None),
                             ("outputDifferences", {"qacc": {"differentCount": 1}})):
            doc = copy.deepcopy(entry["qualification"])
            doc[field] = value
            with self.assertRaises(ValueError):
                qualified_evaluations(doc, **self.selection(entry))
        selection = self.selection(entry)
        selection["reference_sha256"] = "0"*64
        with self.assertRaises(ValueError):
            qualified_evaluations(entry["qualification"], **selection)

    def test_native_whole_output_pass_does_not_falsely_certify_intermediate_identity(self):
        differences = []
        for entry in self.fixture["entries"]:
            for item in entry["nativeComparisons"]:
                if item["capturedComparison"]["nonzeroDifferenceCount"]:
                    differences.append((entry["qualification"]["event"],
                                        entry["qualification"]["substep"], item["ordinal"],
                                        item["capturedComparison"]["firstNonzero"]["index"]))
        self.assertEqual(differences, [(17, 2, 9, 2)])

    def test_neutrality_and_bridge_scope_are_explicit(self):
        p = self.fixture["provenance"]
        self.assertTrue(p["exactPhysicsNeutrality"])
        self.assertEqual(p["neutralEvents"], 7601)
        self.assertEqual(p["originalBridge"]["privateEvalOffset"], 0x105808)
        self.assertEqual(p["originalBridge"]["contextBytes"], 632)
        self.assertFalse(p["capturedBrowserZeroSigns"])
        self.assertEqual(self.fixture["summary"]["browserDifferentCalls"], 50)
        self.assertEqual(self.fixture["summary"]["browserNonzeroDifferences"], 75)

    @unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded fma")
    def test_all_models_and_retained_difference_counts(self):
        count = native_bad = browser_bad = 0
        for entry in self.fixture["entries"]:
            groups = [("native", entry["qualification"]["trace"], entry["nativeComparisons"])]
            if "browserTrace" in entry:
                groups.append(("browser", entry["browserTrace"], entry["browserComparisons"]))
            for name, trace, checked in groups:
                captures = capture_evaluations(trace)
                self.assertEqual(len(captures), len(checked))
                for c, expected in zip(captures, checked):
                    modeled = evaluate(**c["inputs"])
                    self.assertEqual([b.hex() for b in bits(modeled["result"])], expected["originalResultBits"])
                    self.assertEqual(captured_difference(modeled["result"], c["result"]),
                                     expected["capturedComparison"])
                    self.assertEqual(captured_difference([modeled["rawSecond"]], [c["rawSecond"]]),
                                     expected["rawSecondComparison"])
                    count += 1
                    bad = expected["capturedComparison"]["nonzeroDifferenceCount"] > 0
                    native_bad += bad and name == "native"
                    browser_bad += bad and name == "browser"
        self.assertEqual((count, native_bad, browser_bad), (320, 1, 50))
