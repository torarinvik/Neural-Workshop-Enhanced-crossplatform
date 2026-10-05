"""Validate the bounded direct-wheel constraint-update diagnostic."""
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from marble_constraint_update_oracle import (
    Contact, Kernels, MjContact312, captured_difference, captured_updates, replay,
    wheel_order_update,
)
from marble_cone_update_oracle import difference


def fixture():
    # Three elliptic rows for one dim=3 contact; distinct sentinels validate
    # recorder order and prevent accidentally passing aref instead of jar.
    return [0, 0, 3, 1, 0, 1, 2,
            -1, 2, 3,  # jar
            4, 5, 6,   # D
            7, 8, 9,   # R
            10, 11, 12,  # aref (not an impl argument)
            7, 7, 7,   # types
            0, 0, 0,   # ids
            1, 2, 3,   # initial states
            13, 14, 15,  # initial force
            3, .08, .08, .08, .001, .001, .001,  # contact
            16, 17, 18,  # output force
            4, 4, 4,    # output states
            19, 20, 21]  # cost, qfrc (not produced by impl)


class ConstraintCaptureTests(unittest.TestCase):
    def test_decodes_every_operand_and_multiple_calls(self):
        values = fixture()
        captures = captured_updates(values + values)
        self.assertEqual(len(captures), 2)
        c = captures[0]
        self.assertEqual((c.ne, c.nf, c.nefc, c.nv), (0, 0, 3, 2))
        self.assertEqual(c.jar, [-1, 2, 3])
        self.assertEqual(c.D, [4, 5, 6])
        self.assertEqual(c.R, [7, 8, 9])
        self.assertEqual(c.aref, [10, 11, 12])
        self.assertEqual(c.types, [7] * 3)
        self.assertEqual(c.contacts[0].friction, [.08, .08, .001, .001, .001])
        self.assertEqual(c.force_after, [16, 17, 18])
        self.assertEqual(c.cost_after, [19])
        self.assertEqual(c.qfrc_after, [20, 21])

    def test_rejects_truncations_and_trailing_data(self):
        values = fixture()
        for size in range(1, len(values)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                captured_updates(values[:size])
        self.assertEqual(captured_updates([]), [])
        with self.assertRaises(ValueError):
            captured_updates(values + [0])

    def test_rejects_unsafe_dimensions_flags_and_values(self):
        for index, bad in ((0, 4), (1, 4), (2, 65537), (3, -1), (4, 2),
                           (5, .5), (6, 513), (7, True), (8, float("nan")),
                           (9, float("inf")), (10, 0), (13, -1), (19, 8),
                           (22, 1), (22, -1), (31, 2), (32, -1), (33, -1),
                           (41, 5)):
            values = fixture()
            values[index] = bad
            with self.subTest(index=index, bad=bad), self.assertRaises(ValueError):
                captured_updates(values)

    def test_rejects_inconsistent_or_out_of_bounds_elliptic_blocks(self):
        for index, bad in ((20, 6), (23, 1), (31, 6), (32, 0)):
            values = fixture()
            values[index] = bad
            with self.subTest(index=index), self.assertRaises(ValueError):
                captured_updates(values)

    def test_rejects_incomplete_frictionloss_capture(self):
        values = fixture()
        values[0:2] = [1, 1]
        with self.assertRaisesRegex(ValueError, "omits frictionloss"):
            captured_updates(values)

    def test_empty_constraint_call_and_absent_cost_have_exact_layouts(self):
        c = captured_updates([0, 0, 0, 0, 0, 0, 0])[0]
        self.assertEqual(c.force_after, [])
        self.assertEqual(c.cost_after, [])
        self.assertEqual(c.qfrc_after, [])
        c = captured_updates([0, 0, 0, 0, 0, 1, 0, 0])[0]
        self.assertEqual(c.cost_after, [0])

    def test_noncontact_rows_do_not_require_contact_ids(self):
        # One equality row, no contact and no qfrc output. Negative id is valid.
        values = [1, 0, 1, 0, 0, 1, 0,
                  -1, 2, .5, 0, 0, -1, 0, 0, 2, 1, 1]
        c = captured_updates(values)[0]
        self.assertEqual(c.ids, [-1])
        self.assertEqual(c.force_after, [2])

    def test_wrong_library_version_is_rejected_before_contact_abi_calls(self):
        library = Mock()
        library.mj_version.return_value = 3011000
        with patch("marble_constraint_update_oracle.ctypes.CDLL", return_value=library):
            with self.assertRaisesRegex(ValueError, "requires MuJoCo 3.12.0"):
                Kernels(Path("not-used.dylib"))
        library.mj_constraintUpdate_impl.assert_not_called()

    def test_zero_sign_loss_is_not_misclassified_as_nonzero_arithmetic(self):
        result = captured_difference([-0.0, 1.0], [0, 1.0000000000000002])
        self.assertFalse(result["exact"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["zeroSignOnlyCount"], 1)
        self.assertEqual(result["nonzeroDifferenceCount"], 1)
        self.assertEqual(result["firstNonzero"]["index"], 1)

    def test_native_contact_layout_matches_pinned_wheel_header(self):
        self.assertEqual(ctypes.sizeof(MjContact312), 584)
        for field, offset in (("pos", 8), ("friction", 112), ("mu", 232),
                              ("H", 240), ("dim", 528), ("geom", 540),
                              ("efc_address", 576)):
            self.assertEqual(getattr(MjContact312, field).offset, offset)

    def test_initial_hessians_are_validated_before_native_calls(self):
        capture = captured_updates(fixture())[0]
        kernels = Mock(spec=Kernels)
        kernels.routine = Mock()
        invalid = [[], [[0]*35], [[0]*37], [[float("nan")]*36], [[True]*36]]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                Kernels.update(kernels, capture, initial_contact_hessians=values)
        kernels.routine.assert_not_called()


class RecordedWheelTests(unittest.TestCase):
    @staticmethod
    def fixture():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "marble_constraint_update_oracle.json").read_text())

    @staticmethod
    def synthetic_contacts():
        base = captured_updates(fixture())[0]
        rng = random.Random(261001)
        for dim in (1, 3, 4, 6):
            for case in range(256):
                n = 3*dim
                contacts = [Contact(dim, rng.uniform(.01, 2),
                                    [rng.uniform(.001, 2) for _ in range(5)])
                            for _ in range(3)]
                jar = [rng.uniform(-2, 2)*2**rng.randrange(-8, 8) for _ in range(n)]
                d = [rng.uniform(.1, 20) for _ in range(n)]
                yield dim, case, replace(
                    base, nefc=n, nv=0, jar=jar, D=d,
                    R=[1/v for v in d], types=[7]*n,
                    ids=[i for i in range(3) for _ in range(dim)],
                    state_before=[0]*n, force_before=[0]*n,
                    contacts=contacts, has_cost=True)

    def test_reduced_capture_layout_and_neutrality_provenance(self):
        document = self.fixture()
        self.assertEqual([e["sourceEvent"] for e in document["events"]], [17, 18, 216])
        self.assertFalse(document["provenance"]["zeroSignsCaptured"])
        for event in document["events"]:
            self.assertEqual(len(event["newtonTraces"]), 4)
            for record in event["newtonTraces"]:
                self.assertEqual(len(captured_updates(record["constraintUpdateTrace"])), 2)

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_wheel_order_model_on_bounded_synthetic_contact_matrix(self):
        document = self.fixture()
        if platform.machine() != document["provenance"]["nativeArchitecture"]:
            self.skipTest("fixture is for the original arm64 wheel")
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         document["provenance"]["referenceSha256"])
        kernels = Kernels(library)
        for dim, case, capture in self.synthetic_contacts():
            native = kernels.update(capture)
            modeled = wheel_order_update(capture, kernels.norm, math.fma)
            for field in native:
                with self.subTest(dim=dim, case=case, field=field):
                    self.assertTrue(difference(native[field], modeled[field])["exact"])

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_cone_hessian_model_on_explicitly_initialized_inputs(self):
        document = self.fixture()
        if platform.machine() != document["provenance"]["nativeArchitecture"]:
            self.skipTest("fixture is for the original arm64 wheel")
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         document["provenance"]["referenceSha256"])
        kernels = Kernels(library)
        captures = [(f"dim={dim}/case={case}", c)
                    for dim, case, c in self.synthetic_contacts()]
        for event in document["events"]:
            for step, record in enumerate(event["newtonTraces"]):
                captures.extend((f"event={event['sourceEvent']}/step={step}/call={call}", c)
                                for call, c in enumerate(captured_updates(
                                    record["constraintUpdateTrace"])))
        active_dimensions = set()
        for label, capture in captures:
            # The original recordings omit H. These are new constructed inputs,
            # not a claim about the live wheel's unrecorded incoming H cache.
            initial = [[36*i+j+.25 for j in range(36)]
                       for i in range(len(capture.contacts))]
            for enabled in (False, True):
                c = replace(capture, hessian=enabled)
                native = kernels.update(c, include_contact_hessians=True,
                                        initial_contact_hessians=initial)
                modeled = wheel_order_update(
                    c, kernels.norm, math.fma, include_contact_hessians=True,
                    initial_contact_hessians=initial)
                for field in native:
                    with self.subTest(capture=label, hessian=enabled, field=field):
                        self.assertTrue(difference(native[field], modeled[field])["exact"],
                                        difference(native[field], modeled[field]))
                if not enabled:
                    self.assertEqual(native["contactHessians"],
                                     [v for h in initial for v in h])
                else:
                    for i, state in enumerate(native["state"]):
                        if state == 4:
                            active_dimensions.add(c.contacts[c.ids[i]].dim)
        self.assertEqual(active_dimensions, {3, 4, 6})

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_original_wheel_reproduces_expected_diagnostic_differences(self):
        document = self.fixture()
        provenance = document["provenance"]
        if platform.machine() != provenance["nativeArchitecture"]:
            self.skipTest("fixture is for the original arm64 wheel")
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         provenance["referenceSha256"],
                         "use the exact wheel; do not silently change expectations")
        kernels = Kernels(library)
        import mujoco
        self.assertEqual(mujoco.__version__, "3.12.0")
        native_contact = mujoco.MjContact()
        base = native_contact.pos.ctypes.data - MjContact312.pos.offset
        for field in ("pos", "frame", "friction", "solref", "solreffriction",
                      "solimp", "H", "geom", "flex", "elem", "vert"):
            with self.subTest(abi_field=field):
                self.assertEqual(getattr(native_contact, field).ctypes.data - base,
                                 getattr(MjContact312, field).offset)
        for expected in document["expectedReplay"]:
            event, step, call = (expected[k] for k in ("event", "substep", "call"))
            capture = captured_updates(document["events"][event]["newtonTraces"][step][
                "constraintUpdateTrace"])[call]
            with self.subTest(event=event, substep=step, call=call):
                self.assertEqual(replay(capture, kernels), expected["result"])
                self.assertEqual(kernels.update(capture), expected["wheelOutput"])
                modeled = wheel_order_update(capture, kernels.norm, math.fma)
                for field, values in expected["wheelOutput"].items():
                    self.assertTrue(difference(values, modeled[field])["exact"],
                                    f"wheel-order model differs at {event}/{step}/{call}/{field}")


if __name__ == "__main__":
    unittest.main()
