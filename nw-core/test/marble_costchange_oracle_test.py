import json
import hashlib
import math
import os
from pathlib import Path
import struct
import unittest

from marble_costchange_oracle import (qualified_row,synthetic_inputs,wheel_quadratic)
from marble_costchange_trace import OriginalCostPrimitives
from marble_primal_eval_oracle import REFERENCE_SHA256

ROOT=Path(__file__).resolve().parent


class CostBoundaryFixtureTests(unittest.TestCase):
    def test_neutral_assigned_cost_scope_and_actual_public_mismatches(self):
        f=json.loads((ROOT/"fixtures/marble_costchange_boundary.json").read_text())
        self.assertEqual(f["counts"],dict(calls=134,capturedRestoredCalls=0,
            composedBeforeDifferent=3,composedFinalDifferent=3,composedRestoredDifferent=0,
            dotDifferent=0,fiveTangentCalls=114,quadraticDifferent=22,
            threeTangentCalls=0,twoTangentCalls=20))
        self.assertEqual(f["neutrality"],dict(events=7601,exact=True,existingAssignedDiagnosticsExact=True))
        self.assertEqual(f["referenceSha256"],REFERENCE_SHA256)
        self.assertFalse(f["originalPrivateCostChangeCaptured"])
        self.assertFalse(f["capturedBrowserZeroSigns"])
        w=f["witnesses"][0]
        self.assertEqual((w["event"],w["substep"],w["ordinal"]),(1,1,0))
        self.assertNotEqual(w["actualOriginalPublic"]["quadratic"],w["captured"]["quadratic"])
        self.assertEqual(w["actualOriginalPublic"]["dot"],w["captured"]["dot"])

    def test_observer_patch_is_additive_bounded_and_keeps_original_branch(self):
        patch=(ROOT/"repro/marble_initialized_costchange_trace.patch").read_text()
        self.assertEqual(patch.count("diff --git"),3)
        self.assertIn("#define MARBLE_COSTCHANGE_CAPACITY 300000",patch)
        self.assertIn("marbleCostBegin(d, island, iter, i, dim, marble_qcqp_trace_calls);",patch)
        self.assertIn("if (change > 1e-10)",patch)
        self.assertIn("marble_quadratic = mju_mulVecMatVec(delta, A, delta, dim);",patch)
        self.assertNotIn("-fno-builtin",patch)
        self.assertNotIn("truncated",patch)

    def test_actual_compiled_primitive_proof_and_current_operands_are_exact(self):
        f=json.loads((ROOT/"fixtures/marble_quadratic_native_order_rejected.json").read_text())
        self.assertEqual(f["compiledProof"]["counts"],dict(captured=134,synthetic=1000,rejected=18))
        self.assertEqual(f["compiledProof"]["dimensions"],{"2":354,"3":333,"5":447})
        self.assertEqual(f["compiledProof"]["differences"],0)
        self.assertEqual(f["compiledProof"]["first"],[])
        c=f["after"]["counts"]
        self.assertEqual(c["calls"],134)
        self.assertEqual((c["twoTangentCalls"],c["fiveTangentCalls"]),(20,114))
        self.assertTrue(all(v==0 for k,v in c.items() if k not in ("calls","twoTangentCalls","fiveTangentCalls")))
        self.assertFalse(f["originalPrivateCostChangeCaptured"])
        self.assertEqual(f["capturedThreeTangentCalls"],0)
        self.assertEqual(f["syntheticThreeTangentCalls"],333)

    def test_local_correction_is_not_a_neutral_observer_or_full_game_acceptance(self):
        f=json.loads((ROOT/"fixtures/marble_quadratic_native_order_rejected.json").read_text())
        self.assertEqual(f["after"]["physicsComparison"],dict(claimed=False,arithmeticCandidate=True,
            exact=True,events=7601,firstPhysicsDifference=None))
        r=f["rejection"]
        self.assertFalse(r["promoted"]);self.assertTrue(r["ordinaryUnsynchronized"])
        self.assertEqual(r["replayEvents"],7601)
        self.assertEqual(r["numericExceedances"],114869)
        self.assertEqual((r["contactSets"]["count"],r["contactSets"]["first"]["event"],
            r["contactSets"]["last"]["event"]),(162,443,2536))
        self.assertEqual(r["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(r["firstNumeric"]["delta"],8.252424372745537e-7)

    def test_current_input_gauss_and_both_qcqp_routes_stay_qualified(self):
        f=json.loads((ROOT/"fixtures/marble_quadratic_native_order_rejected.json").read_text())
        g=f["otherLocalProducerRegressions"]
        self.assertEqual(g["gauss"]["counts"]["calls"],125)
        self.assertEqual((g["genericQCQP"]["counts"]["groups"],g["genericQCQP"]["counts"]["steps"]),(114,1286))
        self.assertEqual(g["qcqp2"]["counts"]["calls"],18)
        for report in g.values():
            self.assertTrue(all(v==0 for k,v in report["counts"].items()
                if k not in ("calls","groups","steps","twoTangentCalls")))

    def test_retained_patches_are_additive_and_arithmetic_is_platform_guarded(self):
        f=json.loads((ROOT/"fixtures/marble_quadratic_native_order_rejected.json").read_text())
        for field,name in (("observerPatch","marble_initialized_costchange_trace.patch"),
                           ("deltaPatch","marble_quadratic_native_order_candidate.patch")):
            patch=(ROOT/"repro"/name).read_text()
            self.assertEqual(hashlib.sha256(patch.encode()).hexdigest(),f[field]["sha256"])
        patch=(ROOT/"repro/marble_quadratic_native_order_candidate.patch").read_text()
        self.assertEqual(patch.count("diff --git"),2)
        self.assertIn("+#ifdef __EMSCRIPTEN__",patch)
        self.assertIn("+    if (length < 2 || length > 42) return result;",patch)
        self.assertIn("output[0] = mju_mulVecMatVec(left, matrix, right, n);",patch)
        self.assertIn("res = mj_marble_wheel_fma(vec1[i], row, res);",patch)
        self.assertNotIn("-fno-builtin",patch)

    def test_latest_original_whole_solver_clears_nonstat_outputs_but_not_game(self):
        f=json.loads((ROOT/"fixtures/marble_costchange_whole_solver.json").read_text())
        self.assertEqual(f["counts"],dict(exactInputOriginalQualifiedBoundaries=20,
            allOutputNonzeroExactBoundaries=18,statisticDifferentBoundaries=2,
            statisticDifferentValues=2,otherOutputDifferentBoundaries=0))
        self.assertEqual(f["referenceSha256"],REFERENCE_SHA256)
        self.assertEqual(len(f["fieldsCompared"]),21)
        self.assertIn("qacc",f["fieldsCompared"]);self.assertIn("efc_force",f["fieldsCompared"])
        self.assertEqual([(b["event"],b["substep"]) for b in f["boundaries"]],
            [(e,s) for e in (0,1,17,18,216) for s in range(4)])
        differences=[b for b in f["boundaries"] if b["allOutputNonzeroDifferences"]]
        self.assertEqual([(b["event"],b["substep"]) for b in differences],[(17,1),(18,2)])
        self.assertTrue(all(set(b["allOutputNonzeroDifferences"])=={"solver_stats"} for b in differences))
        self.assertTrue(f["synchronizationUsed"])
        self.assertFalse(f["ordinaryTrajectoryAcceptance"]);self.assertFalse(f["promoted"])
        self.assertFalse(f["capturedBrowserZeroSigns"])
        self.assertFalse(f["originalPrivateIntermediatesCaptured"])


class QuadraticModelTests(unittest.TestCase):
    def test_shape_and_finite_validation_precedes_fma(self):
        for operands in (([1.],[1.],[1.]),([1.,2.],[1.],[1.,2.]),
                ([1.,2.],[1.]*4,[True,2.]),([math.inf,2.],[1.]*4,[1.,2.])):
            with self.assertRaises(ValueError):wheel_quadratic(*operands)
        for count in (True,0,5,10001):
            with self.assertRaises(ValueError):list(synthetic_inputs(count))

    def test_synthetic_inputs_are_deterministic_complete_and_cover_all_dimensions(self):
        a=list(synthetic_inputs());b=list(synthetic_inputs())
        self.assertEqual(a,b);self.assertEqual(len(a),1000)
        self.assertEqual({len(v[0]) for v in a},{2,3,5})
        self.assertTrue(any(v[0]!=v[2] for v in a))
        self.assertTrue(any(v[1][1]!=v[1][len(v[0])] for v in a))

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_frozen_witness_reconstructed_return_matches_original_actual_bits(self):
        f=json.loads((ROOT/"fixtures/marble_costchange_boundary.json").read_text())
        for w in f["witnesses"]:
            c=w["captured"]
            model=wheel_quadratic(c["delta"],c["matrix"],c["delta"])
            self.assertEqual(struct.pack("!d",model),struct.pack("!d",w["actualOriginalPublic"]["quadratic"]))


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalQuadraticTests(unittest.TestCase):
    def test_all_thousand_asymmetric_correlated_scaled_and_signed_zero_inputs(self):
        original=OriginalCostPrimitives(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for i,operands in enumerate(synthetic_inputs()):
            with self.subTest(i=i):
                row=qualified_row(original,*operands,"synthetic",str(i))
                self.assertEqual(row["referenceSha256"],REFERENCE_SHA256)

    def test_frozen_boundary_witnesses_match_actual_public_original(self):
        original=OriginalCostPrimitives(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        f=json.loads((ROOT/"fixtures/marble_costchange_boundary.json").read_text())
        for w in f["witnesses"]:
            c=w["captured"]
            actual=original.evaluate(c["delta"],c["matrix"],c["residual"])
            self.assertEqual({k:struct.pack("!d",v) for k,v in actual.items()},
                {k:struct.pack("!d",v) for k,v in w["actualOriginalPublic"].items()})


if __name__=="__main__":unittest.main()
