"""Portable bounded-model contract tests (requires Python math.fma)."""
import math
import unittest
from marble_platform_sincos import bits
from marble_small_sincos_model import SMALL_LIMIT, small_cosine, small_sine


class SmallSinCosTest(unittest.TestCase):
    def test_signed_zero(self):
        for value in (0., -0.):
            self.assertEqual(bits(small_sine(value)), bits(value))
            self.assertEqual(small_cosine(value), 1.)

    def test_original_failure(self):
        self.assertEqual(bits(small_sine(0.019710379478423627)),
                         "3f942e9f87ba42fc")

    def test_reject_unsupported(self):
        for value in (math.nextafter(SMALL_LIMIT, math.inf),
                      math.nextafter(-SMALL_LIMIT, -math.inf), math.inf,
                      -math.inf, math.nan):
            for model in (small_sine, small_cosine):
                with self.subTest(value=value, model=model.__name__):
                    with self.assertRaises(ValueError):
                        model(value)

    def test_seed1_gameplay_rotation(self):
        self.assertEqual(bits(small_sine(.6849294978512117)), "3fe43e68f7a846ed")
        self.assertEqual(bits(small_cosine(.6849294978512117)), "3fe8c867fe1289df")

    def test_boundary_symmetry(self):
        for value in (SMALL_LIMIT, math.nextafter(SMALL_LIMIT, 0.), math.ulp(0.)):
            self.assertEqual(small_sine(-value), -small_sine(value))
            self.assertEqual(bits(small_cosine(-value)), bits(small_cosine(value)))


if __name__ == "__main__":
    unittest.main()
