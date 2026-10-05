"""Regression coverage for validity-aware, constraint-sized scratch captures."""
import math
import unittest

from marble_iteration_trace import (compare_iteration_traces,
                                    decode_iteration_updates,
                                    iteration_trace_metadata)


def record(nefc=3, nv=6, phase=0, validity=0, schema=2, nf=0, contacts=1):
    header = [phase, 0, nf, nefc, contacts, nv, 1,
              1.25 if validity & 1 else 0]
    if schema == 2:
        header = [2] + header + [validity]
    fields = ([2.0]*nefc + [0.5]*nefc + [0.125]*nf + [0.25]*nefc +
              [7]*nefc + [0]*nefc + [0]*nefc + [0.75]*nefc +
              ([0.125] if validity & 2 else [0])*(nefc if schema == 2 else nv) +
              ([0.0625] if validity & 4 else [0])*nv + [0.25]*(7*contacts))
    return header + fields


def trace(values, schema=2, overflow=False):
    return {"constraintIterationTrace": values,
            "constraintIterationTraceSchema": schema,
            "constraintIterationTraceOverflow": overflow}


class IterationTraceTests(unittest.TestCase):
    def test_jv_uses_constraint_rows_on_both_sides_of_velocity_count(self):
        for nefc in (0, 3, 9):
            with self.subTest(nefc=nefc):
                rows, error = decode_iteration_updates(
                    record(nefc=nefc, validity=7, phase=1) +
                    record(nefc=nefc, phase=0, validity=7), schema=2)
                self.assertIsNone(error)
                self.assertEqual(len(rows), 2)
                self.assertEqual(len(rows[0]["fields"]["Jv"]), nefc)
                self.assertEqual(len(rows[0]["fields"]["search"]), 6)

    def test_lifecycle_is_explicit_and_initial_invalid_fields_are_zero(self):
        values = record() + record(phase=1, validity=1) + record(validity=7)
        rows, error = decode_iteration_updates(values, schema=2)
        self.assertIsNone(error)
        self.assertEqual([r["validity"] for r in rows], [
            {"cost": False, "Jv": False, "search": False},
            {"cost": True, "Jv": False, "search": False},
            {"cost": True, "Jv": True, "search": True}])
        result = compare_iteration_traces(trace(values), trace(values))
        self.assertTrue(result["comparable"])
        self.assertIsNone(result["firstDifference"])

    def test_initialized_search_difference_is_not_masked(self):
        a = record(validity=7)
        b = a.copy()
        b[-8] = math.nextafter(b[-8], math.inf)
        result = compare_iteration_traces(trace(a), trace(b))
        self.assertTrue(result["comparable"])
        self.assertEqual(result["firstDifference"]["field"], "search")

    def test_initialized_last_jv_row_is_not_dropped(self):
        a = record(nefc=9, validity=7)
        b = a.copy()
        b[-14] += 0.125
        result = compare_iteration_traces(trace(a), trace(b))
        self.assertEqual(result["firstDifference"]["field"], "Jv")
        self.assertEqual(result["firstDifference"]["firstDifferences"][0][0], 8)

    def test_cost_difference_is_not_masked_after_update(self):
        a = record(phase=1, validity=1)
        b = a.copy()
        b[8] = math.nextafter(b[8], math.inf)
        self.assertEqual(compare_iteration_traces(trace(a), trace(b))[
            "firstDifference"]["field"], "cost")

    def test_invalid_placeholders_rejected(self):
        for index in (8, 10+8*3, 10+8*3+3):
            with self.subTest(index=index):
                values = record()
                values[index] = 0.5
                self.assertIsNotNone(decode_iteration_updates(values, 2)[1])

    def test_invalid_header_and_lifecycle_rejected(self):
        for index, value in ((0, 1), (1, 2), (2, 4), (3, 4), (4, -1),
                             (5, -1), (6, 0), (6, 513), (7, 2),
                             (9, 8), (9, 1.5), (9, 2)):
            with self.subTest(index=index, value=value):
                values = record()
                values[index] = value
                self.assertIsNotNone(decode_iteration_updates(values, 2)[1])
        self.assertIsNotNone(decode_iteration_updates(record(phase=1), 2)[1])

    def test_truncation_at_every_boundary_is_rejected(self):
        values = record(validity=7)
        for end in range(1, len(values)):
            with self.subTest(end=end):
                self.assertIsNotNone(decode_iteration_updates(values[:end], 2)[1])

    def test_non_finite_and_non_numeric_values_rejected(self):
        for value in (float("nan"), float("inf"), True, "1", None):
            with self.subTest(value=value):
                values = record()
                values[-1] = value
                self.assertIsNotNone(decode_iteration_updates(values, 2)[1])
        self.assertIsNotNone(decode_iteration_updates({}, 2)[1])

    def test_unknown_schema_is_rejected(self):
        for schema in (True, "2", 0, 3):
            self.assertIsNotNone(decode_iteration_updates(record(), schema)[1])

    def test_legacy_is_readable_but_never_initialized_parity_evidence(self):
        legacy = record(schema=1, validity=7)
        rows, error = decode_iteration_updates(legacy, 1)
        self.assertIsNone(error)
        self.assertEqual(len(rows[0]["fields"]["Jv"]), 6)
        self.assertIsNone(rows[0]["validity"]["Jv"])
        for other in (trace(legacy, 1), trace(record(validity=7))):
            result = compare_iteration_traces(trace(legacy, 1), other)
            self.assertFalse(result["comparable"])
            self.assertEqual(result["firstDifference"]["field"], "schema/validity")

    def test_overflow_and_missing_status_rejected(self):
        a = trace(record())
        for status in (True, None, 0):
            result = compare_iteration_traces(a, trace(record(), overflow=status))
            self.assertFalse(result["comparable"])
            self.assertEqual(result["firstDifference"]["field"], "decode error")
        b = trace(record())
        del b["constraintIterationTraceOverflow"]
        self.assertFalse(compare_iteration_traces(a, b)["comparable"])

    def test_record_count_and_validity_disagreements_are_visible(self):
        result = compare_iteration_traces(trace(record()), trace(record()+record()))
        self.assertEqual(result["firstDifference"]["field"], "record count")
        result = compare_iteration_traces(trace(record()), trace(record(validity=4)))
        self.assertEqual(result["firstDifference"]["field"], "validity")

    def test_library_metadata_legacy_is_explicit(self):
        self.assertEqual(iteration_trace_metadata(object()), {
            "constraintIterationTraceSchema": 1,
            "constraintIterationTraceOverflow": None})

    def test_library_metadata_schema_two_requires_overflow_export(self):
        class Library:
            @staticmethod
            def mj_solver_constraint_iteration_trace_schema():
                return 2
        with self.assertRaises(AssertionError):
            iteration_trace_metadata(Library())
        Library.mj_solver_constraint_iteration_trace_overflow = staticmethod(lambda: 0)
        self.assertEqual(iteration_trace_metadata(Library())[
            "constraintIterationTraceOverflow"], False)
        Library.mj_solver_constraint_iteration_trace_overflow = staticmethod(lambda: 1)
        with self.assertRaises(AssertionError):
            iteration_trace_metadata(Library())


if __name__ == "__main__":
    unittest.main()
