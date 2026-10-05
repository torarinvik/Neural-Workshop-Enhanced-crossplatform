"""Validate initialized live-Hessian decoding without requiring native packages."""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import unittest

from marble_cone_hessian_oracle import captured_hessians, replay, selected_captures
from marble_constraint_update_oracle import Kernels


def fixture(call=0, row=0, nefc=3):
    # Schema/header, friction, jar/D/R/force, then exactly dim*dim initialized H.
    return [1, call, row, nefc, 3, 2, 1, .08, -.2, .4, 2, -.232,
            .08, .08, .001, .001, .001,
            -1, 2, 3, 4, 5, 6, .25, .2, 1/6, 1, 2, 3,
            1, 2, 3, 4, 5, 6, 7, 8, 9]


def document():
    return {"events": [{"sourceEvent": 216, "newtonTraces": [{
        "coneHessianUpdateSchema": 1, "coneHessianUpdateCalls": 1,
        "coneHessianUpdateOverflow": False, "coneHessianUpdateTrace": fixture(),
    }]}]}


class HessianCaptureTests(unittest.TestCase):
    def test_layout_and_local_contact_reduction(self):
        records = captured_hessians(fixture(), 1)
        self.assertEqual(len(records), 1)
        h = records[0]
        self.assertEqual((h.call, h.row, h.nefc, h.dim, h.contact_id), (0, 0, 3, 3, 2))
        self.assertEqual(h.force, [1, 2, 3])
        self.assertEqual(h.hessian, list(range(1, 10)))
        local = h.local_call()
        self.assertEqual((local.ne, local.nf, local.nefc, local.nv), (0, 0, 3, 0))
        self.assertEqual(local.ids, [0]*3)
        self.assertEqual(local.types, [7]*3)
        self.assertTrue(local.hessian)
        self.assertEqual(local.jar, [-1, 2, 3])
        self.assertEqual(local.R, [.25, .2, 1/6])
        self.assertEqual(local.contacts[0].mu, .08)

    def test_truncations_and_trailing_values_rejected(self):
        values = fixture()
        for size in range(1, len(values)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                captured_hessians(values[:size], 1)
        with self.assertRaises(ValueError):
            captured_hessians(values+[1], 1)
        self.assertEqual(captured_hessians([], 0), [])

    def test_dimensions_enums_nonfinite_and_impedance_rejected(self):
        for index, value in ((0, 2), (0, True), (1, 1), (2, -1), (3, 2),
                             (3, 65537), (4, 5), (5, -1), (6, 2), (7, 0),
                             (9, 0), (10, -1), (12, -1), (20, 0), (23, 0),
                             (29, float("nan")), (30, float("inf"))):
            values = fixture()
            values[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                captured_hessians(values, 1)

    def test_calls_and_rows_are_strictly_chronological(self):
        self.assertEqual(len(captured_hessians(
            fixture(row=0, nefc=6)+fixture(row=3, nefc=6)+fixture(call=1), 2)), 3)
        for values in (fixture()+fixture(), fixture(call=1)+fixture(call=0),
                       fixture(row=3, nefc=6)+fixture(row=0, nefc=6)):
            with self.assertRaises(ValueError):
                captured_hessians(values, 2)

    def test_missing_or_invalid_total_call_counts_rejected(self):
        for calls in (None, -1, True, 1.0, 1000001, 0):
            with self.subTest(calls=calls), self.assertRaises(ValueError):
                captured_hessians(fixture(), calls)

    def test_selected_records_preserve_source_event_and_validate_all_metadata(self):
        selected = selected_captures(document(), [0])
        self.assertEqual(selected[0][:3], (0, 216, 0))
        for field, value in (("coneHessianUpdateSchema", None),
                             ("coneHessianUpdateSchema", True),
                             ("coneHessianUpdateOverflow", True),
                             ("coneHessianUpdateOverflow", None),
                             ("coneHessianUpdateOverflow", 0),
                             ("coneHessianUpdateCalls", None),
                             ("coneHessianUpdateTrace", None)):
            d = copy.deepcopy(document())
            d["events"][0]["newtonTraces"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                selected_captures(d, [0])

    def test_no_empty_capture_acceptance_or_out_of_range_events(self):
        for d, events in (({"events": []}, [0]), (document(), [-1]), (document(), [1]),
                          ({"events": [{"newtonTraces": []}]}, [0])):
            with self.assertRaises(ValueError):
                selected_captures(d, events)


class RecordedHessianTests(unittest.TestCase):
    @staticmethod
    def fixture():
        return json.loads((Path(__file__).with_name("fixtures") /
                           "marble_initialized_hessian_oracle.json").read_text())

    def test_durable_initialized_capture_count_and_provenance(self):
        d = self.fixture()
        self.assertEqual([e["sourceEvent"] for e in d["events"]], [17, 18, 216])
        self.assertFalse(d["provenance"]["zeroSignsCaptured"])
        captures = selected_captures(d, [0, 1, 2])
        self.assertEqual(len(captures), 29)
        self.assertEqual({c.dim for _, _, _, c in captures}, {3, 6})
        self.assertEqual(len(d["expectedReplay"]), 29)
        self.assertEqual(len(d["expectedDense"]), 12)
        self.assertEqual({(e, s, c.call, c.row) for e, _, s, c in captures},
                         {(r["event"], r["substep"], r["call"], r["row"])
                          for r in d["expectedReplay"]})

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_original_wheel_replays_all_initialized_hessian_records(self):
        d = self.fixture()
        if platform.machine() != d["provenance"]["nativeArchitecture"]:
            self.skipTest("fixture records the original arm64 wheel")
        library = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(library.read_bytes()).hexdigest(),
                         d["provenance"]["referenceSha256"])
        kernels = Kernels(library)
        expected = {(r["event"], r["substep"], r["call"], r["row"]): r["report"]
                    for r in d["expectedReplay"]}
        for event, source_event, step, capture in selected_captures(d, [0, 1, 2]):
            actual = replay(capture, kernels)
            report = {key: actual[key] for key in expected[(event, step, capture.call, capture.row)]}
            with self.subTest(event=source_event, step=step, call=capture.call, row=capture.row):
                self.assertEqual(report, expected[(event, step, capture.call, capture.row)])


if __name__ == "__main__":
    unittest.main()
