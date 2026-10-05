import hashlib
import json
import math
import os
from pathlib import Path
import struct
import unittest

from marble_qcqp_small_original import OriginalQCQPSmall,wheel_qcqp2
from marble_primal_eval_oracle import REFERENCE_SHA256

ROOT=Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT/"fixtures"/name).read_text())


class SmallQCQPFixtureTests(unittest.TestCase):
    def test_actual_original_small_route_coverage_is_not_generic_or_three_tangent(self):
        f=fixture("marble_qcqp2_boundary.json")
        self.assertEqual(f["counts"],dict(calls=18,twoTangentCalls=18,threeTangentCalls=0,
            rawDifferent=11,activeDifferent=0,twoTangentModelDifferent=0))
        self.assertEqual(f["referenceSha256"],REFERENCE_SHA256)
        self.assertFalse(f["originalPrivateIntermediatesCaptured"])
        self.assertFalse(f["capturedBrowserZeroSigns"])
        self.assertFalse(f["physicsComparison"]["claimedRecorderNeutrality"])
        self.assertTrue(f["physicsComparison"]["exactlyUnchanged"])

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_reconstructed_witness_final_outputs_are_original_qualified(self):
        for w in fixture("marble_qcqp2_boundary.json")["witnesses"]:
            c=w["captured"]
            model=wheel_qcqp2(c["matrix"],c["rhs"],c["mu"],c["normal"])
            self.assertEqual(model,w["referenceModel"])
            self.assertEqual({k:model[k] for k in ("active","rawForce")},w["actualOriginal"])
            self.assertNotEqual(w["actualOriginal"]["rawForce"],c["rawForce"])
        w=fixture("marble_qcqp2_boundary.json")["witnesses"][0]
        self.assertEqual((w["event"],w["substep"],w["ordinal"]),(17,1,4))

    def test_compiled_actual_two_tangent_producer_matches_frozen_and_new_operands(self):
        f=fixture("marble_qcqp2_native_order_rejected.json")
        self.assertEqual(f["compiledProof"]["counts"],dict(captured=18,synthetic=1000,rejected=13))
        self.assertEqual(f["compiledProof"]["differences"],0)
        self.assertEqual(f["compiledProof"]["first"],[])
        self.assertEqual(f["after"]["counts"],dict(calls=18,twoTangentCalls=18,threeTangentCalls=0,
            rawDifferent=0,activeDifferent=0,twoTangentModelDifferent=0))
        self.assertEqual(f["threeTangentCapturedCalls"],0)
        self.assertFalse(f["threeTangentArithmeticChanged"])
        g=f["otherLocalProducerRegressions"]["gauss"]["counts"]
        self.assertEqual(g["calls"],125)
        self.assertTrue(all(v==0 for k,v in g.items() if k!="calls"))
        q=f["otherLocalProducerRegressions"]["genericQCQP"]["counts"]
        self.assertEqual((q["groups"],q["steps"]),(114,1286))
        self.assertTrue(all(v==0 for k,v in q.items() if k not in ("groups","steps")))

    def test_changed_physics_is_explicit_and_full_game_still_rejected(self):
        f=fixture("marble_qcqp2_native_order_rejected.json")
        c=f["after"]["physicsComparison"]
        self.assertFalse(c["claimedRecorderNeutrality"])
        self.assertFalse(c["exactlyUnchanged"])
        self.assertEqual(c["firstDifference"][0],"events[17].engineStep1Inputs[2].arrays.efc_force[7]")
        r=f["rejection"]
        self.assertFalse(r["promoted"]);self.assertTrue(r["ordinaryUnsynchronized"])
        self.assertEqual(r["replayEvents"],7601)
        self.assertEqual(r["numericExceedances"],114869)
        self.assertEqual(r["contactSets"]["count"],162)
        self.assertEqual((r["contactSets"]["first"]["event"],r["contactSets"]["last"]["event"]),(443,2536))
        self.assertEqual(r["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(r["firstNumeric"]["delta"],8.252424372745537e-7)

    def test_source_patch_adds_only_guarded_two_tangent_sites_and_actual_probe(self):
        f=fixture("marble_qcqp2_native_order_rejected.json")
        text=(ROOT/"repro"/"marble_qcqp2_native_order_candidate.patch").read_text()
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),f["deltaPatch"]["sha256"])
        self.assertEqual(f["deltaPatch"]["sha256"],
            "94ac847cae2291eb9001882a973f11865410b24b3c7219dd8af1025182ac0cea")
        self.assertEqual(text.count("diff --git"),2)
        self.assertIn("*active = mju_QCQP2(output, packet+3, packet+7, packet+9, packet[2]);",text)
        self.assertIn("det = mj_marble_wheel_fma(A11+la, A22+la, -(A12*A12));",text)
        self.assertNotIn("-fno-builtin-fma",text)
        self.assertNotIn("truncated",text)
        self.assertFalse(f["originalPrivateIntermediatesCaptured"])


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalSmallQCQPFixtureTests(unittest.TestCase):
    def test_saved_witnesses_match_actual_public_original(self):
        original=OriginalQCQPSmall(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for w in fixture("marble_qcqp2_boundary.json")["witnesses"]:
            c=w["captured"]
            actual=original.solve(c["matrix"],c["rhs"],c["mu"],c["normal"],2)
            self.assertEqual(actual["active"],w["actualOriginal"]["active"])
            self.assertEqual([struct.pack("!d",v) for v in actual["rawForce"]],
                [struct.pack("!d",v) for v in w["actualOriginal"]["rawForce"]])


if __name__=="__main__":unittest.main()
