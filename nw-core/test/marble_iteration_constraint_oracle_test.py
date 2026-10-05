import copy
import math
import unittest

from marble_iteration_constraint_oracle import captures


def record(phase=0,nefc=3,nv=6,cost=.125):
    h=[2,phase,0,0,nefc,1,nv,0,cost if phase else 0,int(bool(phase))]
    arrays=[2.]*nefc+[.5]*nefc+[-.25]*nefc+[7]*nefc+[0]*nefc
    arrays += [0]*nefc+[.25]*nefc+[0]*nefc+[0]*nv+[3,.5,.5,.5,.005,.00006,.00006]
    return h+arrays


def document(values=None):
    return dict(constraintIterationTraceSchema=2,
        constraintIterationTraceOverflow=False,
        constraintIterationTrace=record()+record(1) if values is None else values)


class AllPrimalCaptureTests(unittest.TestCase):
    def test_all_pairs_are_retained_not_only_first(self):
        rows=captures(document((record()+record(1))*3))
        self.assertEqual([r["pair"] for r in rows],[0,1,2])
        c=rows[0]["capture"]
        self.assertEqual(c.jar,[-.25]*3)
        self.assertEqual(c.D,[2.]*3)
        self.assertEqual(c.cost_after,[.125])
        self.assertEqual(c.aref,[])
        self.assertEqual(c.qfrc_after,[])
        self.assertEqual(c.nv,6)

    def test_only_explicit_nonoverflowed_s2_can_be_called(self):
        for field,value in (("constraintIterationTraceSchema",1),
                ("constraintIterationTraceSchema",True),
                ("constraintIterationTraceOverflow",True),
                ("constraintIterationTraceOverflow",None)):
            d=document();d[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):captures(d)
        self.assertEqual(captures(document([])),[])

    def test_missing_reordered_or_duplicate_output_phase_is_rejected(self):
        for values in (record(),record(1)+record(),record(1)+record(1)):
            with self.assertRaises(ValueError):captures(document(values))

    def test_mutated_static_operands_and_dimensions_do_not_pass(self):
        for index in (2,3,4,5,6,7,10,13,16,19,22,-1):
            a,b=record(),record(1);b[index]+=1
            with self.subTest(index=index),self.assertRaises(ValueError):captures(document(a+b))

    def test_actual_block_contact_integer_and_impedance_inputs_are_validated(self):
        for index,value in ((10,0),(13,-1),(19,8),(22,1),(25,1.5),(-7,4),(-6,-.5)):
            a,b=record(),record(1);a[index]=b[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):
                captures(document(a+b))

    def test_every_truncation_nonfinite_value_and_capacity_is_rejected(self):
        values=record()+record(1)
        for end in range(1,len(values)):
            with self.subTest(end=end),self.assertRaises(ValueError):
                captures(document(values[:end]))
        for value in (True,None,math.nan,math.inf,"1"):
            values=record()+record(1);values[-1]=value
            with self.assertRaises(ValueError):captures(document(values))
        with self.assertRaises(ValueError):captures(document([0.]*300001))
