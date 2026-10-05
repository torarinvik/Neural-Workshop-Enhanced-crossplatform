import unittest
import math
import random

from marble_rne_cross_oracle import CrossOracle, ProjectionOracle, MotionOracle
from marble_source_play_trace import reconstruct_rne_bias


class CrossOracleTests(unittest.TestCase):
    def setUp(self):
        self.oracle = CrossOracle()

    def test_exact_integer_cross_force_and_identity_projection(self):
        self.assertEqual(self.oracle.evaluate(
            [2, 3, 4, 0, 0, 0, 0, 0, 0, 5], [1, 2, 3, 4, 5, 6]),
            [6, -6, 2, -15, 30, -15])

    def test_zero_velocity_clears_previous_result(self):
        inertia = [2, 3, 4, 0, 0, 0, 0, 0, 0, 5]
        self.oracle.evaluate(inertia, [1, 2, 3, 4, 5, 6])
        self.assertEqual(self.oracle.evaluate(inertia, [0]*6), [0]*6)

    def test_native_order_reconstruction_matches_original(self):
        rng = random.Random(260927)
        for case in range(1000):
            inertia = [rng.uniform(-1, 1)*2**rng.randrange(-20, 20) for _ in range(10)]
            velocity = [rng.uniform(-1, 1)*2**rng.randrange(-20, 20) for _ in range(6)]
            engine = {"model": {"body_dofadr": [0, 0], "body_dofnum": [0, 0],
                                 "body_parentid": [0, 0], "gravity": [0, 0, 0]},
                      "arrays": {"cinert": [0]*10 + inertia, "cvel": [0]*6 + velocity,
                                 "cdof": [], "cdof_dot": [], "qvel": []}}
            actual = reconstruct_rne_bias(engine, fma=math.fma,
                                          fused_kernels=frozenset({"inert", "cross"}))
            self.assertEqual(actual["cross_velocity"],
                             self.oracle.evaluate(inertia, velocity), f"case {case}")

    def test_bad_dimensions_and_nonfinite_rejected(self):
        for inertia, velocity in (([0]*9, [0]*6), ([0]*10, [0]*5),
                                  ([float("nan")]*10, [0]*6)):
            with self.assertRaises(ValueError):
                self.oracle.evaluate(inertia, velocity)


class MotionOracleTests(unittest.TestCase):
    def test_original_fused_motion_order(self):
        oracle = MotionOracle()
        rng = random.Random(260929)
        for case in range(1000):
            v = [rng.uniform(-1, 1)*2**rng.randrange(-20, 20) for _ in range(6)]
            a = [rng.uniform(-1, 1)*2**rng.randrange(-20, 20) for _ in range(6)]
            f = math.fma
            expected = [f(-v[2], a[1], v[1]*a[2]),
                        f(v[2], a[0], -v[0]*a[2]),
                        f(-v[1], a[0], v[0]*a[1]),
                        f(-v[2], a[4], v[1]*a[5]) + f(-v[5], a[1], v[4]*a[2]),
                        f(v[2], a[3], -v[0]*a[5]) + f(v[5], a[0], -v[3]*a[2]),
                        f(-v[1], a[3], v[0]*a[4]) + f(-v[4], a[0], v[3]*a[1])]
            self.assertEqual(oracle.evaluate(v, a), expected, f"case {case}")


class ProjectionOracleTests(unittest.TestCase):
    def test_original_arm64_fused_pair_order(self):
        oracle = ProjectionOracle()
        rng = random.Random(260928)
        for case in range(1000):
            axis = [rng.uniform(-1, 1)*2**rng.randrange(-20, 20) for _ in range(6)]
            force = [rng.uniform(-1, 1)*2**rng.randrange(-20, 20) for _ in range(6)]
            expected = ((math.fma(axis[0], force[0], axis[2]*force[2]) +
                         math.fma(axis[1], force[1], axis[3]*force[3])) +
                        math.fma(axis[4], force[4], axis[5]*force[5]))
            self.assertEqual(oracle.evaluate(axis, force), expected, f"case {case}")

    def test_basis_axes_and_integer_dot(self):
        oracle = ProjectionOracle()
        force = [2, -3, 5, 7, -11, 13]
        for i in range(6):
            axis = [int(j == i) for j in range(6)]
            self.assertEqual(oracle.evaluate(axis, force), force[i])
        self.assertEqual(oracle.evaluate([1, 2, 3, 4, 5, 6], force), 62)
        self.assertEqual(oracle.evaluate([0]*6, force), 0)


if __name__ == "__main__":
    unittest.main()
