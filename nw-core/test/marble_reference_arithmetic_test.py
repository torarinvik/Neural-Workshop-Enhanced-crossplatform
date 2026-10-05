import math
import unittest
from marble_reference_arithmetic import reference_acceleration


class ReferenceArithmeticTests(unittest.TestCase):
    def test_original_fused_subtract_preserves_negative_zero(self):
        self.assertEqual(math.copysign(1.,reference_acceleration([1.,2.,3.,4.],0.,0.,0.)),-1.)
    def test_current_first_diagnostic_operands(self):
        result=reference_acceleration([2770.083102493075,105.26315789473685,0.9159340414419861,-79.83493331114161],-.01055587697158532,-.0003991746665557086,0.)
        self.assertEqual(result,2.1239362617724917)

    def test_invalid_operands_reject(self):
        for value in (True,None,"1",math.nan,math.inf):
            with self.assertRaises(ValueError):reference_acceleration([1.,2.,3.,4.],value,0.,0.)
        with self.assertRaises(ValueError):reference_acceleration([1.,2.,3.],0.,0.,0.)

    def test_reference_packet_missing_and_sparse_reject_before_native(self):
        from marble_reference_original import validate
        for engine in (None,{},dict(arrays={},model={},nefc=0),dict(arrays={},model=dict(sparse_jacobian=True),nefc=0)):
            with self.assertRaises(ValueError):validate(engine)
