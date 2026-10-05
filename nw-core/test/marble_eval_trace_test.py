import copy
import math
import unittest

from marble_eval_trace import (capture_evaluations, decode_evaluations,
                               capture_native_evaluations)
from marble_prepare_trace_test import record, trace
from marble_prepare_trace import capture_preparations


def eval_record(*, ordinal=0, preparation=0, dim=3, nv=6, ne=0, nf=0):
    return [1, ordinal, preparation, 0, nv, dim, ne, nf, 0.5, 1., 2., 3., 3.]+[0.5]*dim+[2.]*nf


def document():
    return dict(trace(record()), evalTraceSchema=1, evalTraceCalls=1,
                evalTraceOverflow=False, evalTraceInvalid=False, evalTrace=eval_record())


class EvalTraceTests(unittest.TestCase):
    def test_preparation_identity_and_actual_coefficients_are_preserved(self):
        doc = document()
        c = capture_evaluations(doc)[0]
        self.assertEqual(c["ordinal"], 0)
        self.assertEqual(c["preparationOrdinal"], 0)
        self.assertEqual(c["result"], [1., 2., 3.])
        self.assertEqual(c["inputs"]["gauss"], [1., 2., 3.])
        self.assertEqual(c["inputs"]["rows"][0]["quad"], [0.25]*9)
        self.assertEqual(c["inputs"]["ids"], [0]*3)
        self.assertEqual(c["inputs"]["R"], [0.5]*3)
        self.assertEqual(c["inputs"]["frictionloss"], [])

    def test_multiple_evaluations_can_share_or_advance_preparation(self):
        doc = document()
        doc["prepareTrace"] += record(ordinal=1)
        doc["prepareTraceCalls"] = 2
        doc["evalTrace"] += eval_record(ordinal=1)+eval_record(ordinal=2, preparation=1)
        doc["evalTraceCalls"] = 3
        self.assertEqual([c["preparationOrdinal"] for c in capture_evaluations(doc)], [0, 0, 1])

    def test_scalar_equality_friction_and_inequality_prefix(self):
        prepared = ([1, 0, 0, 2, 3, 1, 1, 0, 3, 79]+[0.125]*8+
                    [-0.5, 0., 0.5]+[0.25]*3+[2.]*3+[0, 1, 3]+[-1]*3+[1., 2., 3.])
        for row, kind in enumerate((0, 1, 3)):
            prepared += [row, 1, -1, kind, 3, 0.25, 0.25, 0.0625]
        doc = dict(trace(prepared), evalTraceSchema=1, evalTraceCalls=1,
                   evalTraceOverflow=False, evalTraceInvalid=False,
                   evalTrace=eval_record(nv=2, ne=1, nf=1))
        inputs = capture_evaluations(doc)[0]["inputs"]
        self.assertEqual((inputs["ne"], inputs["nf"]), (1, 1))
        self.assertEqual(inputs["frictionloss"], [2.])
        self.assertEqual([row["dim"] for row in inputs["rows"]], [1, 1, 1])

    def test_every_truncation_and_trailing_value_is_rejected(self):
        prep = capture_preparations(trace(record()))
        values = eval_record()
        for stop in range(len(values)):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                decode_evaluations(values[:stop], 1, prep)
        with self.assertRaises(ValueError):
            decode_evaluations(values+[1], 1, prep)

    def test_metadata_and_association_are_not_inferred(self):
        for field, value in (("evalTraceSchema", None), ("evalTraceSchema", True),
                             ("evalTraceSchema", 2), ("evalTraceOverflow", None),
                             ("evalTraceOverflow", 0), ("evalTraceInvalid", True),
                             ("evalTraceInvalid", None), ("evalTraceCalls", True),
                             ("evalTraceCalls", 2), ("prepareTraceInvalid", None)):
            doc = document()
            doc[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                capture_evaluations(doc)
        for index, value in ((0, 2), (1, 1), (2, -1), (2, 1), (3, 1),
                             (4, 0), (4, 7), (5, 4), (6, 1), (7, 1),
                             (11, 2.), (12, math.nan), (13, -0.5)):
            doc = document()
            doc["evalTrace"][index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                capture_evaluations(doc)

    def test_convexity_clamp_and_empty_constraints(self):
        prepared = [1, 0, 0, 2, 0, 0, 0, 0, 0, 79]+[0.125]*8+[1., 2., 3.]
        doc = dict(trace(prepared), evalTraceSchema=1, evalTraceCalls=1,
                   evalTraceOverflow=False, evalTraceInvalid=False,
                   evalTrace=eval_record(dim=0, nv=2))
        doc["evalTrace"][11:13] = [1e-15, -4.]
        c = capture_evaluations(doc)[0]
        self.assertEqual(c["rawSecond"], -4.)
        self.assertEqual(c["inputs"]["rows"], [])
        self.assertEqual(decode_evaluations([], 0, []), [])
        with self.assertRaises(ValueError):
            decode_evaluations(eval_record(), 1, [])

    def test_numeric_capacity_and_call_bounds(self):
        for value in (True, "0", None, math.nan, math.inf):
            doc = document()
            doc["evalTrace"][-1] = value
            with self.assertRaises(ValueError):
                capture_evaluations(doc)
        with self.assertRaises(ValueError):
            decode_evaluations([0.]*300001, 0, [])
        for count in (-1, 1000001, None):
            with self.assertRaises(ValueError):
                decode_evaluations([], count, [])

    def test_native_copy_is_optional_and_bounded_before_pointer_use(self):
        self.assertEqual(capture_native_evaluations(object(), {}), {})
        class Library:
            mj_solver_eval_trace_schema = staticmethod(lambda: 1)
            mj_solver_eval_trace_calls = staticmethod(lambda: 0)
            mj_solver_eval_trace_overflow = staticmethod(lambda: 0)
            mj_solver_eval_trace_invalid = staticmethod(lambda: 0)
            mj_solver_eval_trace_size = staticmethod(lambda: 300001)
            copies = 0
            @classmethod
            def mj_solver_eval_trace_copy(cls, values):
                cls.copies += 1
        library = Library()
        with self.assertRaises(ValueError):
            capture_native_evaluations(library, {})
        self.assertEqual(library.copies, 0)
