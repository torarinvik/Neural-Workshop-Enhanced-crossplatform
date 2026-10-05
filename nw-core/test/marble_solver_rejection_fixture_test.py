import hashlib
import json
import math
from pathlib import Path
import unittest

from marble_noslip_residual_oracle import residual, rejected_dot


FIXTURES=Path(__file__).with_name("fixtures")


class RejectedSolverFixtureTests(unittest.TestCase):
    def fixture(self):
        path=FIXTURES/"marble_solver_preparation_eval_rejected.json"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "fa808c9b7696c063085dc6024cd6abed956845f425efaabfc0b176bd5170d0aa")
        return json.loads(path.read_text())

    def test_complete_local_proofs_do_not_certify_rejected_full_replay(self):
        f=self.fixture()
        self.assertEqual(f["compiledEval"]["counts"],dict(fma=1002,eval=5465,rejected=7))
        self.assertEqual(f["compiledEval"]["differences"],0)
        self.assertFalse(f["rejection"]["promoted"])
        self.assertTrue(f["rejection"]["ordinaryUnsynchronized"])
        self.assertEqual(f["rejection"]["replayEvents"],7601)
        self.assertEqual(f["rejection"]["numericExceedances"],117451)
        self.assertEqual(f["rejection"]["contactSets"]["count"],302)

    def test_all_twelve_qualified_whole_outputs_still_differ(self):
        f=self.fixture()
        self.assertEqual({(b["event"],b["substep"]) for b in f["boundaries"]},
                         {(e,s) for e in (17,18,216) for s in range(4)})
        self.assertEqual(f["summary"],dict(qualifiedBoundaries=12,
            wholeSolverDifferentBoundaries=12,preparationCalls=47,preparationValues=753,
            preparationNonzeroDifferences=0,evaluationCalls=129,evaluationNonzeroDifferences=0,
            iterationExactBoundaries=7))
        self.assertTrue(all(b["exactNativeCopyAndWholeOutputQualification"] and
                            b["originalWholeSolverDifferences"] for b in f["boundaries"]))

    def test_initialized_iteration_cost_splits_are_not_waived(self):
        f=self.fixture()
        splits=[b["iterationFirstDifference"] for b in f["boundaries"] if b["iterationFirstDifference"]]
        self.assertEqual(len(splits),5)
        self.assertTrue(all(b["field"]=="cost" for b in splits))
        self.assertEqual(f["rejection"]["firstNumeric"]["context"],"event[195].marble[0].value[10]")

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_first_residual_difference_is_reproduced_at_matched_inputs(self):
        f=self.fixture();rows=f["firstNoSlipResidual"]["rows"]
        self.assertEqual(f["firstNoSlipResidual"]["firstDifferentRow"],5)
        for r in rows:
            a,b=r["ARrow"],r["allforce"]
            self.assertEqual(len(a),18);self.assertEqual(len(b),18)
            self.assertEqual(residual(a,b,r["bias"],r["regularizer"],r["force"]),
                             r["recordedQualifiedNativeResidual"])
            self.assertEqual(math.fma(-r["regularizer"],r["force"],r["bias"]+rejected_dot(a,b)),
                             r["recordedRejectedBrowserResidual"])
        self.assertNotEqual(rows[-1]["originalPublicDot"],rows[-1]["rejectedBrowserDot"])

    def test_candidate_deltas_are_alternatives_on_complete_neutral_base(self):
        path=Path(__file__).with_name("repro")/"marble_solver_preparation_eval_rejected.patch"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "7dca9dacb86a07dd54e33b67dd9ef8500927018a1cdbc2bc32e9a609fa5c8841")
        self.assertIn("mj_marble_eval_probe",path.read_text())

    def residual_fixture(self):
        path=FIXTURES/"marble_solver_residual_order_rejected.json"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "e18c194e88ce4c2c2b6ca8f6f0e60d31f2c3c77e5229f2e464f0f19287e9f636")
        return json.loads(path.read_text())

    def test_second_candidate_retains_all_compiled_proofs_but_is_rejected(self):
        f=self.residual_fixture()
        self.assertFalse(f["rejection"]["promoted"])
        self.assertTrue(f["rejection"]["ordinaryUnsynchronized"])
        self.assertEqual(f["rejection"]["numericExceedances"],115017)
        self.assertEqual(f["rejection"]["contactSets"]["count"],204)
        self.assertEqual(f["rejection"]["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(f["compiledProofs"]["noSlip"]["result"]["counts"],
                         dict(dot=9200,residual=9205,rejected=8))
        self.assertEqual(f["compiledProofs"]["eval"]["result"]["counts"],
                         dict(fma=1002,eval=5465,rejected=7))
        self.assertTrue(all(p["result"]["differences"]==0 for p in f["compiledProofs"].values()))
        self.assertEqual(f["summary"],dict(qualifiedBoundaries=12,
            wholeSolverDifferentBoundaries=11,preparationCalls=47,preparationValues=753,
            preparationNonzeroDifferences=0,evaluationCalls=129,evaluationNonzeroDifferences=0,
            iterationExactBoundaries=5))

    def test_next_force_boundary_inputs_are_identical_without_ignoring_tiny_outputs(self):
        f=self.residual_fixture();b=f["nextNoSlipForceBoundary"]
        self.assertTrue(b["inputsExactlyEqual"])
        for field in b["inputFields"]:
            self.assertEqual(b["qualifiedNative"][field],b["browser"][field])
        self.assertEqual(b["firstDifferentTangent"],4)
        left,right=b["qualifiedNative"]["updatedForce"],b["browser"]["updatedForce"]
        self.assertEqual([i for i,(a,c) in enumerate(zip(left,right)) if a!=c],[4])
        self.assertEqual(left[4],-4.3381008035318497e-39)
        self.assertEqual(right[4],-4.33810080353185e-39)

    def test_second_candidate_patch_is_a_complete_alternative_not_a_v1_delta(self):
        p=Path(__file__).with_name("repro")/"marble_solver_residual_order_rejected.patch"
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),
                         "8b70c1de940deee903745651688f96a3af47572c170aeb1f16a0ff3a9ebc0eb8")
        self.assertIn("residualDotNativeOrder",p.read_text())
        self.assertIn("mj_marble_eval_probe",p.read_text())
        self.assertIn("engine_util_solve.c",p.read_text())
