from pathlib import Path
import unittest
from marble_shipping_patch_guard import diagnostic_additions


class ShippingPatchGuardTest(unittest.TestCase):
    def test_diagnostic_candidate_rejected(self):
        patch = Path(__file__).with_name("repro") / "marble_layer29_complete_diagnostic_candidate.patch"
        findings = diagnostic_additions(patch.read_text())
        self.assertTrue(findings)
        self.assertTrue(any(row["symbol"] == "diagnostic header" for row in findings))

    def test_removals_allowed_and_arithmetic_not_classified_as_trace(self):
        patch = "+++ b/src/engine/engine_solver.c\n-mj_constraint_state_trace_begin();\n+value = mj_marble_wheel_fma(x, y, z);\n"
        self.assertEqual(diagnostic_additions(patch), [])

    def test_exports_and_calls_detected(self):
        patch = '+++ b/wasm/bindings.cc\n+function("mj_constraint_update_trace_begin", call);\n+marble_qcqp_trace_record();\n'
        self.assertEqual(len(diagnostic_additions(patch)), 2)

    def test_camelcase_exports_and_derivative_probes(self):
        patch = '+++ b/wasm/bindings.cc\n+function("marbleFreeBiasIntermediateProbe", function_pointer);\n+mjd_freeBias_vel_trace();\n'
        self.assertEqual(len(diagnostic_additions(patch)), 2)

    def test_inline_derivative_trace_macro_detected(self):
        self.assertEqual(len(diagnostic_additions(
            '+++ b/src/engine/engine_derivative.c\n+TRACE_VALUES(lin, 9);\n')), 1)

    def test_recorders_without_trace_suffix_detected(self):
        patch = ("+++ b/src/engine/engine_solver.c\n"
                 "+marbleRecordConstraintInput(ctx);\n"
                 "+marbleRecordGauss(ctx, before, value, partial);\n"
                 "+value = marbleCostRowDot(a, b, n);\n")
        findings = diagnostic_additions(patch)
        self.assertEqual([row["symbol"] for row in findings],
                         ["marbleRecordConstraintInput", "marbleRecordGauss"])


if __name__ == "__main__":
    unittest.main()
