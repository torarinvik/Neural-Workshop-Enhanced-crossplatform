import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import struct
import unittest

from marble_dense_solve_oracle import native_dot
from marble_native_dot_oracle import wheel_dot


def input_matrix():
    rng = random.Random(42002)
    lengths = list(range(81))+[95, 96, 97, 127, 128, 129, 255, 256, 257, 511, 512]
    for n in lengths:
        for _ in range(100):
            yield ([rng.uniform(-1, 1)*2.**rng.randrange(-40, 40) for _ in range(n)],
                   [rng.uniform(-1, 1)*2.**rng.randrange(-40, 40) for _ in range(n)])


class NativeDotValidationTests(unittest.TestCase):
    def test_lengths_are_bounded_before_callback(self):
        called = []
        for a, b in (([], [1.]), ([1.]*513, [1.]*513)):
            with self.assertRaises(ValueError):
                wheel_dot(a, b, fma=lambda *v: called.append(v))
        self.assertEqual(called, [])

    def test_nonfinite_non_numeric_and_non_arrays_rejected(self):
        for a in (None, (1.,), [True], ["1"], [math.nan], [math.inf]):
            with self.assertRaises(ValueError):
                wheel_dot(a, [1.])

    def test_fma_must_be_callable(self):
        with self.assertRaises(ValueError):
            wheel_dot([], [], fma="not a kernel")

    def test_deterministic_matrix_has_9200_cases_and_all_quad_tail_shapes(self):
        lengths = [len(a) for a, _ in input_matrix()]
        self.assertEqual(len(lengths), 9200)
        self.assertTrue({0, 1, 2, 3, 15, 16, 17, 18, 31, 32, 33, 63, 64, 65, 512}
                        .issubset(lengths))


@unittest.skipUnless(hasattr(math, "fma"), "requires correctly rounded math.fma")
class NativeDotOrderTests(unittest.TestCase):
    def test_exact_integer_inputs_cover_empty_quads_chunks_and_tails(self):
        for n in range(81):
            a = [float(i-3) for i in range(n)]
            self.assertEqual(wheel_dot(a, [1.]*n), sum(a))
        self.assertEqual(struct.pack("!d", wheel_dot([], [])), b"\0"*8)

    def test_full_32_chunks_round_products_and_trailing_quads_are_fused(self):
        a = [1.0+2.**-27]*36
        b = [1.0-2.**-27]*36
        calls = []
        def fma(x, y, z):
            calls.append((x, y, z))
            return math.fma(x, y, z)
        wheel_dot(a, b, fma=fma)
        # Exactly four fused tail products, not all 36 products or none.
        self.assertEqual(len(calls), 4)
        self.assertEqual([c[2] for c in calls], [8.]*4)

    def test_zero_and_mixed_signed_zero_inputs(self):
        for n in range(66):
            for sign in (0., -0.):
                self.assertEqual(wheel_dot([sign]*n, [1.]*n), 0.)


class NativeDotLibraryTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original wheel")
    def test_model_matches_original_public_dot_on_all_9200_inputs(self):
        if platform.machine() != "arm64":
            self.skipTest("operation order is specific to the original arm64 wheel")
        path = Path(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c")
        library = ctypes.CDLL(str(path))
        for a, b in input_matrix():
            self.assertEqual(struct.pack("!d", wheel_dot(a, b)),
                             struct.pack("!d", native_dot(library, a, b)), str(len(a)))

    @unittest.skipUnless(os.environ.get("NW_MUJOCO_DIAGNOSTIC_LIBRARY"),
                         "optional matching private native diagnostic rebuild")
    def test_qualified_rebuild_matches_original_model_on_all_9200_inputs(self):
        fixture = json.loads(Path(__file__).with_name("fixtures").joinpath(
            "marble_primal_prepare_full_oracle.json").read_text())
        path = Path(os.environ["NW_MUJOCO_DIAGNOSTIC_LIBRARY"])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         fixture["provenance"]["diagnosticLibrarySha256"])
        library = ctypes.CDLL(str(path))
        for a, b in input_matrix():
            self.assertEqual(struct.pack("!d", wheel_dot(a, b)),
                             struct.pack("!d", native_dot(library, a, b)), str(len(a)))


if __name__ == "__main__":
    unittest.main()
