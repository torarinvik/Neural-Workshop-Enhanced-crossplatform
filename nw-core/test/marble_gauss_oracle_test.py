import ctypes
import math
import os
import random
import struct
import unittest

from marble_gauss_oracle import GaussContext, OriginalGauss, check_layout, synthetic_inputs, validated, wheel_order


class GaussModelTests(unittest.TestCase):
    def test_exact_context_offsets_are_checked_without_loading_private_code(self):
        check_layout()
        self.assertEqual(ctypes.sizeof(GaussContext),632)
        self.assertEqual(GaussContext.Ma.offset,0x118)
        self.assertEqual(GaussContext.cost.offset,0x230)

    def test_whole_operand_arrays_are_bounded_and_finite(self):
        for arrays in (([1.],[],[1.],[1.]),([1.]*513,)*4,([True],)*4,
                       ([math.nan],)*4,([math.inf],)*4,(["1"],)*4,(None,)*4):
            with self.assertRaises(ValueError):validated(*arrays)
        self.assertEqual(validated([],[],[],[]),0)

    def test_no_silent_nonfused_fallback(self):
        with self.assertRaises(ValueError):wheel_order([],[],[],[],fma=0 if not hasattr(math,"fma") else "invalid")

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_eight_dof_prefix_is_rounded_and_only_tail_is_fused(self):
        for n in (0,1,6,7,8,9,16,18,24,512):
            out=wheel_order([1.]*n,[0.]*n,[2.]*n,[0.]*n)
            self.assertEqual(out["roundedPrefix"],n//8*8)
            self.assertEqual(out["gauss"],float(n))
            self.assertEqual(out["partial"],[float(i+1) for i in range(n)])


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalGaussTests(unittest.TestCase):
    def test_guarded_private_producer_matches_disassembly_order_on_thousand_cases(self):
        original=OriginalGauss(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for case,arrays in enumerate(synthetic_inputs()):
            n=len(arrays[0])
            actual=original.solve(*arrays);expected=wheel_order(*arrays)["gauss"]
            self.assertEqual(struct.pack("!d",actual),struct.pack("!d",expected), (case,n))

    def test_invalid_input_is_rejected_before_any_native_call(self):
        original=OriginalGauss(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        def forbidden(*args):raise AssertionError("native call must not occur")
        original.routine=forbidden
        for values in (None,[True],[math.nan],[1.]*513):
            with self.assertRaises(ValueError):original.solve(values,values,values,values)
