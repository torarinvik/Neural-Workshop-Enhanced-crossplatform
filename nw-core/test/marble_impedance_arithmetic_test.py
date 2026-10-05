"""Regression for the original ARM64 impedance scale evaluation order.

This local expression test is not complete makeImpedance or gameplay parity.
"""
import math
import unittest


class ImpedanceArithmeticTest(unittest.TestCase):
    def test_event1127_contact1(self):
        position = -0.00035537936711282306
        width, midpoint, power = .001, .5, 2.
        minimum, maximum = .9, .95
        x = abs(position / width)
        self.assertLessEqual(x, midpoint)
        y = (1 / midpoint**(power-1)) * x**power
        self.assertEqual(minimum + y*(maximum-minimum), .9126294494569511)
        self.assertEqual(math.fma(y, maximum-minimum, minimum), .912629449456951)


if __name__ == "__main__":
    unittest.main()
