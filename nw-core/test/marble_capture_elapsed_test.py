"""Regression for nonzero next-tray screenshot timing qualification."""
import unittest

from marble_source_capture import capture_elapsed_matches


class CaptureElapsedTest(unittest.TestCase):
    def test_requested_times_and_step_roundoff(self):
        for milliseconds in (0, 1, 200, 1000, 15000):
            elapsed = 0.0
            remaining = milliseconds / 1000.0
            while remaining > 0:
                step = min(1 / 60, remaining)
                elapsed += step
                remaining -= step
            self.assertTrue(capture_elapsed_matches(elapsed, milliseconds))

    def test_wrong_time_and_nonfinite_rejected(self):
        for elapsed in (0.0, 0.199, 0.201, float('nan'), float('inf')):
            self.assertFalse(capture_elapsed_matches(elapsed, 200))


if __name__ == '__main__':
    unittest.main()
