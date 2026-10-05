import math
import struct
import unittest

from marble_noslip_residual_oracle import packet, residual, rejected_dot
from marble_native_dot_oracle import wheel_dot


class ResidualValidationTests(unittest.TestCase):
    def test_empty_packet(self):
        self.assertEqual(packet([], []), [1, 0., 0., 0., 0])

    def test_bounds_and_lengths_before_callback(self):
        calls = []
        for a, b in (([], [1.]), ([0.]*513, [0.]*513)):
            with self.assertRaises(ValueError):
                residual(a, b, 0., 0., 0., fma=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_non_numeric_or_nonfinite_operands(self):
        for a in (None, (1.,), [True], [math.inf], [math.nan], ["1"]):
            with self.assertRaises(ValueError):
                packet(a, [1.])

    def test_nonfinite_scalars(self):
        for values in ((True, 0., 0.), (0., math.inf, 0.), (0., 0., math.nan)):
            with self.assertRaises(ValueError):
                packet([], [], *values)

    def test_fma_must_be_callable(self):
        with self.assertRaises(ValueError):
            residual([], [], 0., 0., 0., fma="not a function")

    def test_historical_three_tail_uses_literal_add_order_not_python_sum(self):
        self.assertEqual(rejected_dot([1e16,1.,-1e16],[1.,1.,1.]),0.)


@unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded fma")
class ResidualOrderTests(unittest.TestCase):
    def test_final_operation_is_fused_after_rounded_bias_addition(self):
        x, y = 1.+2.**-27, 1.-2.**-27
        self.assertEqual(residual([], [], -1., -x, y), math.fma(x, y, -1.))
        self.assertNotEqual(residual([], [], -1., -x, y), x*y-1.)

    def test_dot_packet_preserves_qualified_kernel_order(self):
        for n in range(81):
            a, b = [float(i-3) for i in range(n)], [1.]*n
            self.assertEqual(struct.pack("!d", residual(a, b, 0., 0., 0.)),
                             struct.pack("!d", wheel_dot(a, b)))

    def test_historical_kernel_is_not_original_for_fused_quad(self):
        a = [1.]*4+[1.+2.**-27]*4
        b = [-1.]*4+[1.-2.**-27]*4
        self.assertNotEqual(wheel_dot(a, b), rejected_dot(a, b))
