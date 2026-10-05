import unittest
from marble_quaternion_original import normalize4_model


class QuaternionNormalizationTest(unittest.TestCase):
    def test_zero_fallback(self):
        self.assertEqual(normalize4_model([0.]*4),(0.,[1.,0.,0.,0.]))

    def test_unit_unchanged(self):
        self.assertEqual(normalize4_model([1.,0.,0.,0.]),(1.,[1.,0.,0.,0.]))

    def test_rescale(self):
        self.assertEqual(normalize4_model([0.,2.,0.,0.]),(2.,[0.,1.,0.,0.]))

    def test_invalid(self):
        for q in ([1.]*3,[float("nan")]*4):
            with self.assertRaises(ValueError):normalize4_model(q)


if __name__=="__main__":unittest.main()
