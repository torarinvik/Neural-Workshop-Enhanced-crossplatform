import copy
import math
import unittest

from marble_gauss_trace import capture_gauss,decode_gauss
from marble_iteration_constraint_oracle_test import document


def record(ordinal=0,n=6):
    gauss=n*.125
    return [1,ordinal,0,n,3,3,.125,.125+gauss,gauss]+[1.]*n+[0.]*n+[.25]*n+[0.]*n+[(i+1)*.125 for i in range(n)]


def trace():
    return dict(document(),gaussSchema=1,gaussCalls=1,
        gaussOverflow=False,gaussInvalid=False,gaussTrace=record())


class GaussTraceTests(unittest.TestCase):
    def test_all_assigned_operands_and_partials_are_retained(self):
        g=decode_gauss(record(),1)[0]
        self.assertEqual(g["Ma"],[1.]*6)
        self.assertEqual(g["gauss"],.75)
        self.assertEqual(g["costAfter"],.875)
        self.assertEqual(g["partial"],[.125,.25,.375,.5,.625,.75])

    def test_actual_s2_ownership_and_before_cost_are_required(self):
        rows,pairs=capture_gauss(trace())
        self.assertEqual(len(rows),len(pairs))
        for index in (3,4,6):
            d=trace();d["gaussTrace"][index]+=1
            if index==6:d["gaussTrace"][7]+=1
            with self.assertRaises(ValueError):capture_gauss(d)
        d=trace();d["gaussTrace"]+=record(1);d["gaussCalls"]=2
        with self.assertRaises(ValueError):capture_gauss(d)

    def test_missing_invalid_overflow_or_boolean_schema_cannot_be_defaulted(self):
        for field,value in (("gaussSchema",True),("gaussSchema",2),
                ("gaussOverflow",None),("gaussInvalid",True),("gaussCalls",True)):
            d=trace();d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):capture_gauss(d)

    def test_complete_numeric_packet_and_count_are_checked(self):
        for value in (True,None,math.nan,math.inf,"1"):
            values=record();values[-1]=value
            with self.assertRaises(ValueError):decode_gauss(values,1)
        for count in (True,None,-1,1000001,2):
            with self.assertRaises(ValueError):decode_gauss(record(),count)
        with self.assertRaises(ValueError):decode_gauss([0.]*300001,0)
        self.assertEqual(decode_gauss([],0),[])

    def test_every_truncation_and_trailing_value_is_rejected(self):
        values=record()
        for end in range(len(values)):
            with self.subTest(end=end),self.assertRaises(ValueError):
                decode_gauss(values[:end],1)
        with self.assertRaises(ValueError):decode_gauss(values+[0.],1)

    def test_header_validity_final_partial_and_cost_addition_are_not_inferred(self):
        for index,value in ((0,2),(1,1),(2,-2),(3,513),(4,65537),(5,1),
                            (7,.75),(8,.5),(-1,.5)):
            values=record();values[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):decode_gauss(values,1)

    def test_empty_dof_sum_is_assigned_zero_not_scratch(self):
        g=decode_gauss(record(n=0),1)[0]
        self.assertEqual(g["partial"],[])
        self.assertEqual(g["gauss"],0.)
        values=record(n=0);values[8]=1
        with self.assertRaises(ValueError):decode_gauss(values,1)

    def test_decoder_does_not_assume_a_nonfused_arithmetic_policy(self):
        values=record();values[9]+=1
        # Structural decoding may not overwrite or reconstruct actual sums.
        self.assertEqual(decode_gauss(values,1)[0]["Ma"][0],2.)
