import hashlib
import json
import math
import os
from pathlib import Path
import struct
import unittest

from marble_gauss_oracle import OriginalGauss, wheel_order
from marble_primal_eval_oracle import REFERENCE_SHA256

ROOT=Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT/"fixtures"/name).read_text())


class GaussFixtureTests(unittest.TestCase):
    def test_all_primal_updates_cover_later_calls_without_sdk_intermediate_assumption(self):
        f=fixture("marble_all_primal_updates.json")
        self.assertEqual(f["counts"],dict(calls=125,laterCalls=106,nonzeroDifferentCalls=0,
            forceDifferences=0,stateDifferences=0,costDifferences=0,
            referenceModelDifferentCalls=0,zeroSignOnlyCalls=10))
        self.assertEqual(f["witnesses"],[])
        self.assertEqual(f["referenceSha256"],REFERENCE_SHA256)
        self.assertFalse(f["originalPrivateIntermediatesCaptured"])
        self.assertIn("excludes Gauss addition",f["scope"])

    def test_initialized_gauss_observer_is_neutral_to_radius_candidate(self):
        f=fixture("marble_gauss_boundary.json")
        self.assertEqual(f["neutrality"],dict(exact=True,events=7601))
        self.assertEqual(f["trace"]["sha256"],
            "273367cba294064400e090f0afb811ac47859ee1ce48bf6e5c47c0655721e804")
        self.assertEqual(f["control"]["sha256"],
            "f76fe3c868b7a73132343b43a14807bfd468cdc0c75ead4cf781567bc25d33c6")
        self.assertEqual(f["counts"],dict(calls=125,originalGaussModelDifferent=0,
            gaussDifferent=43,constraintCostDifferent=0,totalCostDifferent=43,
            partialModelDifferentCalls=48))
        self.assertFalse(f["capturedBrowserZeroSigns"])

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_actual_original_gauss_witness_is_reproducible_not_sdk_cost(self):
        f=fixture("marble_gauss_boundary.json")
        for w in f["witnesses"]:
            c=w["captured"];operands=[c[k] for k in ("Ma","qfrc_smooth","qacc","qacc_smooth")]
            model=wheel_order(*operands)
            self.assertEqual(model,w["referenceModel"])
            self.assertEqual(model["gauss"],w["actualOriginalGauss"])
            self.assertNotEqual(model["gauss"],c["gauss"])
            self.assertEqual(w["actualOriginalConstraintCost"],c["costBefore"])
        w=f["witnesses"][0]
        self.assertEqual((w["event"],w["substep"],w["ordinal"]),(0,1,1))
        self.assertEqual(struct.pack("!d",w["actualOriginalGauss"]).hex(),"3ff2fcd3c02e7f3a")
        self.assertEqual(struct.pack("!d",w["captured"]["gauss"]).hex(),"3ff2fcd3c02e7f39")

    def test_actual_compiled_producer_pass_does_not_claim_gameplay_improvement(self):
        f=fixture("marble_gauss_native_order_rejected.json")
        self.assertEqual(f["compiledProof"]["counts"],dict(captured=125,synthetic=1000,rejected=16))
        self.assertEqual(f["compiledProof"]["differences"],0)
        self.assertEqual(f["compiledProof"]["first"],[])
        self.assertEqual(f["corrected"]["counts"],dict(calls=125,originalGaussModelDifferent=0,
            gaussDifferent=0,constraintCostDifferent=0,totalCostDifferent=0,partialModelDifferentCalls=0))
        self.assertTrue(f["physics"]["exactlyUnchanged"])
        self.assertEqual(f["physics"]["events"],7601)
        self.assertIsNone(f["physics"]["firstDifference"])
        c=f["corrected"]["comparison"]
        self.assertFalse(c["claimed"]);self.assertTrue(c["arithmeticCandidate"])
        self.assertTrue(c["exact"]);self.assertIsNone(c["firstPhysicsDifference"])

    def test_full_original_failure_is_retained_and_candidate_not_promoted(self):
        f=fixture("marble_gauss_native_order_rejected.json")
        r=f["rejection"]
        self.assertFalse(r["promoted"]);self.assertTrue(r["ordinaryUnsynchronized"])
        self.assertEqual(r["replayEvents"],7601)
        self.assertEqual(r["numericExceedances"],111077)
        self.assertEqual(r["contactSets"]["count"],136)
        self.assertEqual((r["contactSets"]["first"]["event"],r["contactSets"]["last"]["event"]),(443,1966))
        self.assertEqual(r["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(r["firstNumeric"]["delta"],8.227014482997674e-7)
        self.assertFalse(f["originalPrivatePartialSumsCaptured"])
        self.assertFalse(f["capturedBrowserZeroSigns"])

    def test_additive_patches_are_immutable_and_no_global_arithmetic_change(self):
        f=fixture("marble_gauss_native_order_rejected.json")
        for key,name,sha in (("recorderPatch","marble_initialized_gauss_trace.patch",
                "0120a1f6a3ecf9082ad2a8525d74676ad9ac3eaa8b1ff16d973a1e2b82b3755e"),
                ("deltaPatch","marble_gauss_native_order_rejected.patch",
                "1262c12ce389d3cc7837f4197561219efcf354a1cf87c887ec2c0e75986a5e16")):
            text=(ROOT/"repro"/name).read_text()
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),sha)
            self.assertEqual(f[key]["sha256"],sha)
            self.assertNotIn("truncated",text)
            self.assertNotIn("-fno-builtin-fma",text)
        delta=(ROOT/"repro"/"marble_gauss_native_order_rejected.patch").read_text()
        self.assertEqual(delta.count("diff --git"),2)
        self.assertIn("const int marble_rounded_prefix = nv >= 8 ? (nv/8)*8 : 0;",delta)
        self.assertIn("mj_marble_gauss_probe",delta)
        self.assertIn("PrimalUpdateConstraint(&ctx, 0);",delta)


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalGaussFixtureTests(unittest.TestCase):
    def test_all_saved_witnesses_match_guarded_actual_original_producer(self):
        original=OriginalGauss(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for w in fixture("marble_gauss_boundary.json")["witnesses"]:
            c=w["captured"]
            actual=original.solve(*(c[k] for k in ("Ma","qfrc_smooth","qacc","qacc_smooth")))
            self.assertEqual(struct.pack("!d",actual),struct.pack("!d",w["actualOriginalGauss"]))


if __name__=="__main__":unittest.main()
