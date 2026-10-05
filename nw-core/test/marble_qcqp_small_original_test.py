import math
import os
import struct
import unittest

from marble_qcqp_small_original import OriginalQCQPSmall, synthetic_inputs, validated, wheel_qcqp2


class SmallQCQPValidationTests(unittest.TestCase):
    def test_complete_finite_operands_and_only_two_or_three_dimensions(self):
        valid=([1.,0.,0.,1.],[1.,1.],[1.,1.],1.,2)
        validated(*valid)
        for index,value in ((0,[1.]),(1,[1.]),(2,[1.,0.]),(3,-1.),(3,math.inf),
                            (3,True),(4,True),(4,5)):
            args=list(valid);args[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):validated(*args)

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_rank_failure_and_interior_have_actual_stop_branches(self):
        rank=wheel_qcqp2([0.]*4,[1.,2.],[1.,1.],1.)
        self.assertEqual(rank["rawForce"],[0.,0.]);self.assertFalse(rank["active"])
        self.assertEqual(rank["steps"][0]["reason"],"rank")
        inside=wheel_qcqp2([1.,0.,0.,1.],[0.,0.],[1.,1.],1.)
        self.assertFalse(inside["active"]);self.assertEqual(inside["steps"][0]["reason"],"value")


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalSmallQCQPTests(unittest.TestCase):
    def test_qcqp2_model_matches_actual_public_original_on_thousand_inputs(self):
        original=OriginalQCQPSmall(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for case,args in enumerate(synthetic_inputs(2)):
            actual=original.solve(*args,2);model=wheel_qcqp2(*args)
            self.assertEqual(actual["active"],model["active"],case)
            self.assertEqual([struct.pack("!d",v) for v in actual["rawForce"]],
                [struct.pack("!d",v) for v in model["rawForce"]],case)

    def test_invalid_operands_do_not_invoke_native_code(self):
        original=OriginalQCQPSmall(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        def forbidden(*args):raise AssertionError("native call must not occur")
        original.routines={2:forbidden,3:forbidden}
        for args in (([0.]*4,[0.]*2,[1.,0.],1.,2),
                ([0.]*4,[0.]*2,[1.]*2,math.nan,2),([0.]*4,[0.]*2,[1.]*2,1.,True)):
            with self.assertRaises(ValueError):original.solve(*args)


if __name__=="__main__":unittest.main()
