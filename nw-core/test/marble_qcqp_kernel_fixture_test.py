import hashlib
import json
import math
import os
from pathlib import Path
import struct
import unittest

from marble_qcqp_original import OriginalQCQP5

ROOT=Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT/"fixtures"/name).read_text())


class KernelFixtureTests(unittest.TestCase):
    def test_deeper_recorder_is_exactly_neutral_not_an_arithmetic_candidate(self):
        f=fixture("marble_qcqp_kernel_boundary.json")
        self.assertEqual(f["neutrality"],dict(exact=True,events=7601))
        self.assertEqual(f["trace"]["sha256"],
            "4cedfb9858c7b1c221495bbfca27c2745bfc4954a18b77b70da5e27f40edff06")
        self.assertEqual(f["control"]["sha256"],
            "c382da792a8b7cb36465ce66b2c60f2f644a0b8eab26fc68a8f1dc67180589d3")
        self.assertEqual(hashlib.sha256((ROOT/"repro"/"marble_initialized_qcqp_kernel.patch").read_bytes()).hexdigest(),
            "835ff311c9108abb63ec69847b4d432112f2f91ece5c2d6d017719ff8e9aa2ab")
        self.assertFalse(f["capturedBrowserZeroSigns"])

    def test_first_initialized_mismatch_is_value_not_factor_or_solve(self):
        f=fixture("marble_qcqp_kernel_boundary.json")
        self.assertEqual(f["counts"],dict(groups=114,steps=1286,
            modelRawDifferent=0,modelActiveDifferent=0,
            browserRawDifferent=29,initializedStageDifferent=99))
        self.assertEqual(f["firstFields"],dict(value=99))
        w=f["firstRetainedContact"]
        self.assertEqual((w["event"],w["substep"],w["parent"]), (17,0,0))
        self.assertEqual((w["modelDifference"]["iteration"],w["modelDifference"]["field"]), (13,"value"))

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_exact_fused_producer_witness_is_reproducible(self):
        f=fixture("marble_qcqp_kernel_boundary.json")
        for w in f["witnesses"]+[f["firstRetainedContact"]]:
            d=w["modelDifference"];s=d["capturedStep"];p=w["producerProbe"]
            radius=w["contact"]["normal"]
            self.assertEqual(s["value"],s["norm"]-radius*radius)
            self.assertEqual(p["originalResult"],math.fma(-radius,radius,s["norm"]))
            self.assertEqual(d["referenceDriver"],p["originalResult"])
            self.assertNotEqual(s["value"],p["originalResult"])
        w=f["firstRetainedContact"]
        self.assertEqual(struct.pack("!d",w["modelDifference"]["browser"]).hex(),"3f70886dd4eadc34")
        self.assertEqual(struct.pack("!d",w["producerProbe"]["originalResult"]).hex(),"3f70886dd4eadc35")

    def test_local_compiled_success_is_retained_without_promoting_game(self):
        f=fixture("marble_qcqp_fused_radius_rejected.json")
        self.assertEqual(f["compiledProof"]["counts"],dict(captured=114,synthetic=1000,rejected=13))
        self.assertEqual(f["compiledProof"]["differences"],0)
        self.assertEqual(f["compiledProof"]["first"],[])
        self.assertEqual(f["kernel"]["counts"],dict(groups=114,steps=1286,modelRawDifferent=0,
            modelActiveDifferent=0,browserRawDifferent=0,initializedStageDifferent=0,browserActiveDifferent=0))
        c=f["actualOriginalConstraintUpdate"]
        self.assertEqual(c["calls"],38)
        for field in ("forceNonzeroDifferences","stateDifferences","costNonzeroDifferences","referenceModelDifferences"):
            self.assertEqual(c[field],0)
        self.assertFalse(f["rejection"]["promoted"])
        self.assertTrue(f["rejection"]["ordinaryUnsynchronized"])
        self.assertEqual(f["rejection"]["numericExceedances"],111077)
        self.assertEqual(f["rejection"]["contactSets"]["count"],136)
        self.assertEqual(f["rejection"]["contactSets"]["first"]["event"],443)
        self.assertEqual(f["rejection"]["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(f["rejection"]["firstNumeric"]["delta"],8.227014482997674e-7)

    def test_changed_physics_is_explicit_never_labeled_neutral(self):
        f=fixture("marble_qcqp_fused_radius_rejected.json")
        n=f["kernel"]["neutrality"]
        self.assertFalse(n["claimed"]);self.assertFalse(n["exact"])
        self.assertTrue(n["arithmeticCandidate"])
        self.assertEqual(n["events"],7601)
        self.assertEqual(n["firstPhysicsDifference"][0],
            "events[1].engineStep1Inputs[2].arrays.efc_force[1]")
        self.assertNotEqual(n["firstPhysicsDifference"][1],n["firstPhysicsDifference"][2])

    def test_twelve_qualified_boundaries_preserve_remaining_real_splits(self):
        f=fixture("marble_qcqp_fused_radius_rejected.json")
        self.assertEqual(f["summary"],dict(qualifiedBoundaries=12,
            wholeSolverDifferentBoundaries=7,preparationCalls=47,preparationValues=753,
            preparationNonzeroDifferences=0,evaluationCalls=129,evaluationNonzeroDifferences=0,
            iterationExactBoundaries=4,noSlipContactExactBoundaries=5))
        self.assertEqual({(b["event"],b["substep"]) for b in f["boundaries"]},
            {(e,s) for e in (17,18,216) for s in range(4)})
        self.assertTrue(all(b["exactNativeCopyAndWholeOutputQualification"] for b in f["boundaries"]))
        w=f["firstFormerlySplitWrapper"]
        self.assertTrue(w["inputsAndProjectedRetainedOutputEqual"])
        self.assertEqual(w["qualifiedNative"],w["browser"])
        self.assertNotEqual(w["browser"]["oldForce"],
            fixture("marble_qcqp_boundary.json")["firstRetainedContact"]["captured"]["oldForce"])
        costs=[b["iterationFirstDifference"] for b in f["boundaries"] if b["iterationFirstDifference"]]
        self.assertEqual(len(costs),8)
        self.assertTrue(all(c["field"]=="cost" for c in costs))

    def test_delta_is_additive_to_observers_and_contains_only_targeted_physics_site(self):
        f=fixture("marble_qcqp_fused_radius_rejected.json")
        p=ROOT/"repro"/"marble_qcqp_fused_radius_rejected.patch"
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),f["deltaPatch"]["sha256"])
        self.assertEqual(f["deltaPatch"]["sha256"],
            "30e36adf452b2546d27d4395ac4bd487be1db02f2f8caa2809d181da40216efa")
        text=p.read_text()
        self.assertIn("val = mj_marble_wheel_fma(-r, r, marble_norm);",text)
        self.assertIn("mj_marble_qcqp5_probe",text)
        self.assertIn("marbleQCQP5Probe",text)
        self.assertNotIn("-fno-builtin-fma",text)
        self.assertEqual(text.count("diff --git"),2)


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalKernelFixtureTests(unittest.TestCase):
    def test_neutral_witness_driver_outputs_and_first_split_remain_original_qualified(self):
        original=OriginalQCQP5(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        f=fixture("marble_qcqp_kernel_boundary.json")
        for w in f["witnesses"]+[f["firstRetainedContact"]]:
            c=w["contact"];inputs=(c["matrix"],c["rhs"],c["mu"],c["normal"])
            direct=original.solve(*inputs);model=original.decomposed(*inputs)
            self.assertEqual(direct,w["actualOriginalQCQP"])
            self.assertEqual({k:model[k] for k in ("active","rawForce")},direct)
            d=w["modelDifference"];s=model["steps"][d["iteration"]]
            self.assertEqual(s["value"],d["referenceDriver"])
            for name in ("factor","solved","norm","lambdaBefore"):
                self.assertEqual(s[name],d["capturedStep"][name])
