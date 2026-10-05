import unittest
from marble_frame_original import frame_model


class FrameModelTest(unittest.TestCase):
    def test_default_tangent(self):
        self.assertEqual(frame_model([1.,0.,0.]+[0.]*6),
                         [1.,0.,0.,0.,1.,0.,0.,0.,1.])

    def test_reject_invalid(self):
        for values in ([0.]*9,[1.]*8,[float("nan")]+[0.]*8):
            with self.assertRaises(ValueError):frame_model(values)


if __name__=="__main__":unittest.main()
