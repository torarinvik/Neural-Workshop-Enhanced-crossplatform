import math
import unittest
from marble_free_bias_model import cross, dot, matmul, transpose


class BiasModelTests(unittest.TestCase):
    def test_identity_products_and_transpose(self):
        identity=[1.,0.,0.,0.,1.,0.,0.,0.,1.]
        a=[float(i) for i in range(9)]
        self.assertEqual(matmul(identity,a),a)
        self.assertEqual(matmul(a,identity),a)
        self.assertEqual(transpose(transpose(a)),a)

    def test_cross_orientation(self):
        self.assertEqual(cross([1.,0.,0.],[0.,1.,0.]),[0.,0.,1.])

    def test_fused_cancellation_order_is_observable(self):
        a=[1.+2**-27,1.,0.];b=[1.-2**-27,-1.,0.]
        self.assertEqual(dot(a,b),-2**-54)
        self.assertEqual(a[0]*b[0]+a[1]*b[1],0.)
