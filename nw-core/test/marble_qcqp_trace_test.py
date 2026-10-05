import math
import unittest

from marble_qcqp_trace import capture_qcqp, decode_qcqp


def record(n=5, active=1, restored=0, normal=1., ordinal=0):
    guarded = normal < 1e-15
    valid = 4 if guarded else 7
    header = [1, ordinal, 0, 0, 0, 0, n+1, 0 if guarded else n,
              valid, -1 if guarded else active, 0 if guarded else active,
              restored, 0. if restored else -1., normal]
    old = [1.]*n
    post = [0.]*n if guarded else [2.]*n
    arrays = [1.]*n + [1.]* (n*n) + [0.]*n + old + [0.]*n
    if not guarded:
        arrays += [3.]*n if active else post
        arrays += post
    return header + arrays + (old if restored else post)


def document(values=None, calls=1):
    return dict(qcqpTraceSchema=1, qcqpTraceCalls=calls,
                qcqpTraceOverflow=False, qcqpTraceInvalid=False,
                qcqpTrace=record() if values is None else values)


class QCQPTraceTests(unittest.TestCase):
    def test_distinct_initialized_raw_projected_and_retained_outputs(self):
        c = capture_qcqp(document())[0]
        self.assertEqual(c["rawForce"], [3.]*5)
        self.assertEqual(c["projectedForce"], [2.]*5)
        self.assertEqual(c["retainedForce"], [2.]*5)
        self.assertTrue(c["active"])
        self.assertFalse(c["restored"])

    def test_three_routes_keep_actual_dimensions_and_contiguous_ordinals(self):
        records = record(2) + record(3, ordinal=1) + record(5, ordinal=2)
        self.assertEqual([c["route"] for c in decode_qcqp(records, 3)], [2, 3, 5])

    def test_normal_guard_does_not_copy_uninitialized_qcqp_arrays(self):
        c = capture_qcqp(document(record(normal=0.)))[0]
        self.assertIsNone(c["rawForce"])
        self.assertIsNone(c["projectedForce"])
        self.assertIsNone(c["active"])
        self.assertEqual(c["retainedForce"], [0.]*5)

    def test_actual_restoration_and_inactive_projection_are_checked(self):
        c = capture_qcqp(document(record(restored=1)))[0]
        self.assertEqual(c["retainedForce"], c["oldForce"])
        c = capture_qcqp(document(record(active=0)))[0]
        self.assertEqual(c["rawForce"], c["projectedForce"])
        for values in (record(restored=1), record(active=0)):
            values[-1] = 99.
            with self.assertRaises(ValueError):
                decode_qcqp(values, 1)

    def test_every_truncation_trailing_value_and_count_mismatch_is_rejected(self):
        values = record()
        for stop in range(len(values)):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                decode_qcqp(values[:stop], 1)
        for v in (values+[1], record(ordinal=1)):
            with self.assertRaises(ValueError): decode_qcqp(v, 1)
        self.assertEqual(decode_qcqp([], 0), [])
        with self.assertRaises(ValueError): decode_qcqp(values, 2)

    def test_all_whole_packet_nonfinite_nonnumeric_and_capacity_errors_reject(self):
        for value in (True, "0", None, math.nan, math.inf):
            values = record(); values[-1] = value
            with self.assertRaises(ValueError): decode_qcqp(values, 1)
        with self.assertRaises(ValueError): decode_qcqp([0.]*300001, 0)
        for count in (None, True, -1, 1000001):
            with self.assertRaises(ValueError): decode_qcqp([], count)

    def test_metadata_flags_are_explicit_not_coerced_or_inferred(self):
        for field, value in (("qcqpTraceSchema", True), ("qcqpTraceSchema", 2),
                ("qcqpTraceOverflow", 0), ("qcqpTraceInvalid", None),
                ("qcqpTraceCalls", True), ("qcqpTraceCalls", 2)):
            doc = document(); doc[field] = value
            with self.assertRaises(ValueError): capture_qcqp(doc)

    def test_route_validity_branch_scaling_and_row_flags_are_consistent(self):
        for index, value in ((0, 2), (2, -2), (3, -1), (4, -1), (5, -1),
                (6, 5), (7, 3), (8, 3), (9, -1), (10, 0), (11, 2),
                (13, 0.), (14, 0.), (14, -1.)):
            values = record(); values[index] = value
            with self.subTest(index=index), self.assertRaises(ValueError):
                decode_qcqp(values, 1)
