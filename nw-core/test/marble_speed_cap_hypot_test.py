"""Original Python wrapper regression at seed-1 event69/substep3."""
import math
import unittest


class SpeedCapHypotTest(unittest.TestCase):
    def test_original_wrapper_scale(self):
        keep = 1 - .22 / 240
        x, y = -5.281384333465093 * keep, -4.398885466589486 * keep
        speed = math.hypot(x, y)
        self.assertEqual(speed.hex(), "0x1.b77e104adbcaep+2")
        scale = 1 / speed
        self.assertEqual(x * scale, -0.7683835451692359)
        self.assertEqual(y * scale, -0.6399896307856532)
        # Captured JS Math.hypot returns the adjacent lower norm.
        lower = math.nextafter(speed, 0.)
        self.assertEqual(x * (1 / lower), -0.7683835451692361)
        self.assertEqual(y * (1 / lower), -0.6399896307856533)


if __name__ == "__main__":
    unittest.main()
