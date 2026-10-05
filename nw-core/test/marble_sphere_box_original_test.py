import unittest
from marble_sphere_box_original import outside_model


class OutsideSphereBoxModelTest(unittest.TestCase):
    def operands(self, position):
        return [position, [1.,0.,0.,0.,1.,0.,0.,0.,1.], [.1,0.,0.],
                [0.,0.,0.], [1.,0.,0.,0.,1.,0.,0.,0.,1.], [1.,1.,1.]]

    def test_axis_contact(self):
        result = outside_model(self.operands([1.05,0.,0.]))
        self.assertAlmostEqual(result[0],-.05)
        self.assertEqual(result[4:7],[-1.,0.,0.])
        self.assertEqual(result[7:],[0.,0.,0.])

    def test_inside_not_qualified(self):
        with self.assertRaises(ValueError):
            outside_model(self.operands([0.,0.,0.]))


if __name__ == "__main__":
    unittest.main()
