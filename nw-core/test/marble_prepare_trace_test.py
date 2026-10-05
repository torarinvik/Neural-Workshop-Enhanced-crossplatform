import math
import copy
import json
from pathlib import Path
import unittest

from marble_prepare_trace import (capture_preparations, decode_preparations,
                                  capture_native_preparations, qualified_preparations)


def record(dim=3, row_id=17, nv=6, ordinal=0):
    n = dim
    return ([1, ordinal, 0, nv, n, 0, 0, 0, 1, 79] +
            [0.125]*(4*nv) + [0.25]*n + [0.125]*n + [2.0]*n +
            [7]*n + [row_id]*n + [1.0, 2.0, 3.0] +
            [0, dim, row_id, 7, 9, 0.5]+[0.5]*5+[0.25]*9)


def trace(values, calls=1):
    return {"prepareTraceSchema": 1, "prepareTraceCalls": calls,
            "prepareTraceOverflow": False, "prepareTraceInvalid": False,
            "prepareTrace": values}


class PreparationTraceTests(unittest.TestCase):
    def test_full_active_layout_and_global_id_localization(self):
        for dim in (3, 4, 6):
            rows = capture_preparations(trace(record(dim)))
            self.assertEqual(len(rows), 1)
            c = rows[0]
            self.assertEqual((c["nv"], c["nefc"]), (6, dim))
            self.assertEqual(len(c["inputs"]["jv"]), dim)
            self.assertEqual(c["inputs"]["ids"], [0]*dim)
            self.assertEqual(c["rows"][0]["globalContactId"], 17)
            self.assertEqual(len(c["rows"][0]["quad"]), 9)
            self.assertEqual(c["quadGauss"], [1., 2., 3.])

    def test_scalar_reads_no_elliptic_or_trailing_quad_storage(self):
        values = ([1, 0, -1, 2, 1, 0, 0, 1, 1, 79]+[0.125]*8+
                  [0.25, 0.125, 2., 0, -1]+[1., 2., 3.]+[0, 1, -1, 0, 3, 4., 5., 6.])
        c = capture_preparations(trace(values))[0]
        self.assertEqual(c["rows"][0]["quad"], [4., 5., 6.])
        self.assertEqual(c["inputs"]["contacts"], [])

    def test_empty_constraints_have_only_initialized_gauss(self):
        values = [1, 0, 0, 2, 0, 0, 0, 0, 0, 79]+[0.125]*8+[1., 2., 3.]
        c = capture_preparations(trace(values))[0]
        self.assertEqual(c["rows"], [])
        self.assertEqual(c["inputs"]["jv"], [])
        self.assertEqual(decode_preparations([], 0), [])

    def test_every_truncation_and_trailing_value_is_rejected(self):
        values = record()
        for end in range(len(values)):
            with self.subTest(end=end), self.assertRaises(ValueError):
                decode_preparations(values[:end], 1)
        with self.assertRaises(ValueError):
            decode_preparations(values+[1], 1)

    def test_header_dimension_validity_and_count_errors_rejected(self):
        for index, value in ((0, 2), (1, 1), (2, -2), (3, 0), (3, 513),
                             (4, 65537), (5, 4), (6, 4), (7, 2), (8, 0),
                             (8, 4), (9, 7), (9, 127)):
            values = record()
            values[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                decode_preparations(values, 1)
        for calls in (True, -1, 2, 1000001, None):
            with self.assertRaises(ValueError):
                decode_preparations(record(), calls)

    def test_nonfinite_and_non_numeric_data_rejected(self):
        for value in (math.nan, math.inf, True, "0", None):
            values = record()
            values[-1] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode_preparations(values, 1)

    def test_block_rows_width_types_ids_and_parameters_are_consistent(self):
        # Header + 4*nv + 5*nefc + Gauss[3].
        start = 10+24+15+3
        for index, value in ((start, 1), (start+1, 2), (start+2, 18),
                             (start+3, 0), (start+4, 3), (start+5, 0),
                             (start+6, -0.5), (10+24+9, 6), (10+24+14, 18)):
            values = record()
            values[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                decode_preparations(values, 1)

    def test_call_ordinals_and_metadata_are_not_inferred(self):
        values = record()+record(ordinal=1)
        self.assertEqual(len(decode_preparations(values, 2)), 2)
        for field, value in (("prepareTraceSchema", True), ("prepareTraceSchema", None),
                             ("prepareTraceOverflow", None), ("prepareTraceOverflow", 0),
                             ("prepareTraceInvalid", True), ("prepareTraceInvalid", None)):
            document = trace(record())
            document[field] = value
            with self.assertRaises(ValueError):
                capture_preparations(document)
        for document in (None, [], "trace"):
            with self.assertRaises(ValueError):
                capture_preparations(document)

    def test_native_optional_export_and_copy_boundaries(self):
        self.assertEqual(capture_native_preparations(object()), {})
        class Library:
            mj_solver_prepare_trace_schema = staticmethod(lambda: 1)
            mj_solver_prepare_trace_calls = staticmethod(lambda: 0)
            mj_solver_prepare_trace_overflow = staticmethod(lambda: 0)
            mj_solver_prepare_trace_invalid = staticmethod(lambda: 0)
            mj_solver_prepare_trace_size = staticmethod(lambda: 300001)
            copies = 0
            @classmethod
            def mj_solver_prepare_trace_copy(cls, values):
                cls.copies += 1
        lib = Library()
        with self.assertRaises(ValueError):
            capture_native_preparations(lib)
        self.assertEqual(lib.copies, 0)


class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_prepare_full_oracle.json").read_text())

    def selection(self):
        entry = self.fixture["entries"][0]
        return copy.deepcopy(entry["qualification"]), dict(
            reference_sha256=self.fixture["provenance"]["referenceSha256"],
            diagnostic_sha256=self.fixture["provenance"]["diagnosticLibrarySha256"],
            input_trace_sha256=self.fixture["provenance"]["inputTraces"][entry["matrix"]]["sha256"])

    def test_real_qualified_boundary_decodes(self):
        document, selection = self.selection()
        self.assertGreater(len(qualified_preparations(document, **selection)), 0)

    def test_failed_or_missing_qualification_is_never_a_pass(self):
        for field, value in (("schema", None), ("exactInputCopy", False),
                             ("exactInputCopy", 1), ("solverOutputsExactlyEqual", False),
                             ("solverOutputsExactlyEqual", 1), ("outputDifferences", None),
                             ("outputDifferences", {"qacc": {"differentCount": 1}})):
            document, selection = self.selection()
            document[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                qualified_preparations(document, **selection)

    def test_unverified_active_wheel_is_rejected(self):
        for field in ("loadedInProcess", "wheelRecordMatches"):
            for value in (None, False, 1):
                document, selection = self.selection()
                document["nativeWheel"]["activeEngineLibrary"][field] = value
                with self.assertRaises(ValueError):
                    qualified_preparations(document, **selection)

    def test_all_three_library_input_identities_are_required(self):
        for field in ("reference_sha256", "diagnostic_sha256", "input_trace_sha256"):
            for value in (None, "0"*64, "z"*64, "short"):
                document, selection = self.selection()
                selection[field] = value
                with self.assertRaises(ValueError):
                    qualified_preparations(document, **selection)
        document, selection = self.selection()
        document.pop("inputTrace")
        with self.assertRaises(ValueError):
            qualified_preparations(document, **selection)

    def test_unknown_event_substep_and_version_are_rejected(self):
        for field, value in (("event", True), ("event", -1), ("event", 1000001),
                             ("substep", True), ("substep", -1), ("substep", 4)):
            document, selection = self.selection()
            document[field] = value
            with self.assertRaises(ValueError):
                qualified_preparations(document, **selection)
        document, selection = self.selection()
        document["nativeWheel"]["mujocoVersion"] = "3.13.0"
        with self.assertRaises(ValueError):
            qualified_preparations(document, **selection)


if __name__ == "__main__":
    unittest.main()
