import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import unittest

from marble_inertia_original import (OriginalInertia,captures,compare,qualified_row,
    synthetic_inputs,validated,wheel_inertia)
from marble_primal_eval_oracle import REFERENCE_SHA256

ROOT=Path(__file__).resolve().parent


class InertiaFixtureTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/"fixtures/marble_inertia_native_order_rejected.json").read_text())

    def test_actual_original_before_and_current_captured_returns(self):
        f=self.fixture();self.assertEqual(f["referenceSha256"],REFERENCE_SHA256)
        expected=dict(calls=120,accelerationCalls=60,velocityCalls=60,differentCalls=0,
            nonzeroDifferentValues=0,zeroSignOnlyCalls=0,modelDifferentCalls=0)
        self.assertEqual(f["after"]["counts"],expected)
        self.assertEqual(f["before"]["counts"],dict(expected,differentCalls=42,nonzeroDifferentValues=66))
        self.assertFalse(f["capturedBrowserZeroSigns"])
        self.assertFalse(f["originalPrivateRneIntermediatesCaptured"])
        w=f["before"]["firstWitness"]
        self.assertEqual((w["captured"]["event"],w["captured"]["substep"],w["captured"]["body"]),(0,0,1))
        self.assertEqual(w["actualOriginal"][1],-7.50413793389272e-18)
        self.assertEqual(w["captured"]["result"][1],-7.504137933892721e-18)

    def test_actual_compiled_bit_proof_and_prior_producer_regressions(self):
        f=self.fixture();p=f["compiledProof"]
        self.assertEqual(p["counts"],dict(captured=120,synthetic=1000,rejected=12))
        self.assertEqual(p["differences"],0);self.assertEqual(p["first"],[])
        for name,calls in (("cost",134),("gauss",125),("qcqp2",18)):
            self.assertEqual(f["otherCurrentLocalProducerRegressions"][name]["counts"]["calls"],calls)
        self.assertEqual(f["otherCurrentLocalProducerRegressions"]["generic"]["counts"]["steps"],1286)
        for r in f["compiledProducerRegressions"].values():
            self.assertEqual(r["proof"]["differences"],0);self.assertEqual(r["proof"]["first"],[])
            self.assertEqual(r["proof"]["runtime"],p["runtime"])

    def test_physical_change_is_not_neutrality_or_full_game_acceptance(self):
        f=self.fixture();s=f["after"]["physicsComparison"]
        self.assertFalse(s["claimedRecorderNeutrality"]);self.assertFalse(s["exactlyUnchanged"])
        self.assertEqual(s["events"],7601)
        self.assertEqual(s["firstDifference"],["events[0].engineStep1Inputs[1].arrays.qacc[4]",0,-4.9679927381240586e-27])
        r=f["rejection"];self.assertFalse(r["promoted"]);self.assertTrue(r["ordinaryUnsynchronized"])
        self.assertEqual(r["numericExceedances"],110690)
        self.assertEqual((r["contactSets"]["count"],r["contactSets"]["first"]["event"],r["contactSets"]["last"]["event"]),(105,463,1966))
        self.assertEqual(r["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(r["firstNumeric"]["delta"],4.996572333659799e-7)

    def test_shared_platform_guarded_patch_and_prevalidated_real_probe(self):
        f=self.fixture();patch=(ROOT/"repro/marble_inertia_native_order_candidate.patch").read_text()
        self.assertEqual(hashlib.sha256(patch.encode()).hexdigest(),f["deltaPatch"]["sha256"])
        self.assertEqual(patch.count("diff --git"),2)
        self.assertIn("+#ifdef __EMSCRIPTEN__",patch)
        self.assertIn("size != 17",patch);self.assertIn("mju_mulInertVec(output, packet+1, packet+11);",patch)
        self.assertIn("SHARED helper",patch);self.assertNotIn("-fno-builtin",patch)
        self.assertEqual(len(f["sharedHelperOtherCallers"]),3)

    def test_new_inputs_keep_all_physical_whole_solver_outputs_qualified(self):
        f=json.loads((ROOT/"fixtures/marble_inertia_whole_solver.json").read_text())
        self.assertEqual(f["counts"],dict(exactInputOriginalQualifiedBoundaries=20,
            allOutputNonzeroExactBoundaries=17,statisticDifferentBoundaries=3,
            statisticDifferentValues=3,otherOutputDifferentBoundaries=0))
        self.assertEqual(len(f["fieldsCompared"]),21)
        d=[b for b in f["boundaries"] if b["allOutputNonzeroDifferences"]]
        self.assertEqual([(b["event"],b["substep"]) for b in d],[(17,1),(18,2),(216,2)])
        self.assertTrue(all(set(b["allOutputNonzeroDifferences"])=={"solver_stats"} for b in d))
        self.assertTrue(f["synchronizationUsed"]);self.assertFalse(f["ordinaryTrajectoryAcceptance"])
        self.assertFalse(f["promoted"]);self.assertFalse(f["originalPrivateIntermediatesCaptured"])

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_frozen_witness_model_matches_actual_original_bits(self):
        w=self.fixture()["before"]["firstWitness"];c=w["captured"]
        bits=lambda a:[struct.pack("!d",v).hex() for v in a]
        self.assertEqual(bits(wheel_inertia(c["inertia"],c["vector"])),bits(w["actualOriginal"]))


def trace_document():
    inertia=[1.,1.,1.,0.,0.,0.,0.,0.,0.,1.]
    a=[1.,2.,3.,4.,5.,6.];v=[-1.,-2.,-3.,-4.,-5.,-6.]
    values=[0.]*72;values[36:42]=a;values[42:48]=a;values[48:54]=v
    engine=dict(model=dict(body_parentid=[0,0],options=dict(enableflags=0)),
        arrays=dict(qvel=[],cinert=[0.]*10+inertia,cvel=[0.]*6+v))
    return dict(events=[dict(rneTraces=[values],engineStep1Phases=[[
        dict(phase="probe_rneBias",engine=engine)]])])


class InertiaPacketTests(unittest.TestCase):
    def test_complete_actual_stage_offsets_and_owner(self):
        rows=captures(trace_document())
        self.assertEqual(len(rows),2)
        self.assertEqual([r["stage"] for r in rows],["acceleration","velocity"])
        self.assertEqual(rows[0]["vector"],[1.,2.,3.,4.,5.,6.])
        self.assertEqual(rows[0]["vector"],rows[0]["result"])
        self.assertEqual(rows[1]["vector"],rows[1]["result"])
        self.assertTrue(all((r["event"],r["substep"],r["body"])==(0,0,1) for r in rows))

    def test_truncated_dimensions_and_missing_duplicate_owner_reject(self):
        for field in ("cinert","cvel","qvel"):
            doc=trace_document();engine=doc["events"][0]["engineStep1Phases"][0][0]["engine"]
            engine["arrays"][field].append(0.)
            with self.subTest(field=field),self.assertRaises(ValueError):captures(doc)
        for count in (0,2):
            doc=trace_document();owner=doc["events"][0]["engineStep1Phases"][0][0]
            doc["events"][0]["engineStep1Phases"][0]=[copy.deepcopy(owner) for _ in range(count)]
            with self.assertRaises(ValueError):captures(doc)
        doc=trace_document();doc["events"][0]["rneTraces"][0].pop()
        with self.assertRaises(ValueError):captures(doc)

    def test_sleep_metadata_and_parent_ownership_are_explicit(self):
        for flags in (None,True,-1,1<<4,2147483648):
            doc=trace_document();model=doc["events"][0]["engineStep1Phases"][0][0]["engine"]["model"]
            model["options"]["enableflags"]=flags
            with self.subTest(flags=flags),self.assertRaises(ValueError):captures(doc)
        for parents in ([0,2],[0,-1],[0,1.5],[0,True],[0,1],[1,0]):
            doc=trace_document();doc["events"][0]["engineStep1Phases"][0][0]["engine"]["model"]["body_parentid"]=parents
            with self.assertRaises(ValueError):captures(doc)

    def test_malformed_containers_reject_before_native_calls(self):
        bad=[None,{},dict(events=None),dict(events=[None])]
        for field in ("rneTraces","engineStep1Phases"):
            doc=trace_document();doc["events"][0][field]=None;bad.append(doc)
        for field in ("engine","model","arrays","options"):
            doc=trace_document();owner=doc["events"][0]["engineStep1Phases"][0][0]
            if field=="engine":owner["engine"]=None
            elif field=="options":owner["engine"]["model"]["options"]=None
            else:owner["engine"][field]=None
            bad.append(doc)
        doc=trace_document();doc["events"][0]["engineStep1Phases"][0]=[None];bad.append(doc)
        for doc in bad:
            with self.subTest(doc=doc),self.assertRaises(ValueError):captures(doc)

    def test_entire_finite_capture_checked_before_native_callback(self):
        class Forbidden:
            def multiply(self,*args):raise AssertionError("must prevalidate every packet")
        for value in (True,math.inf,math.nan,"1",None):
            doc=trace_document();second=copy.deepcopy(doc["events"][0]);second["rneTraces"][0][-1]=value
            doc["events"].append(second)
            with self.subTest(value=value),self.assertRaises(ValueError):compare(doc,Forbidden())

    def test_direct_original_arrays_validated_before_any_pointer_call(self):
        original=OriginalInertia.__new__(OriginalInertia)
        def forbidden(*args):raise AssertionError("native must not run")
        original.routine=forbidden
        for operands in (([1.]*9,[1.]*6),([1.]*10,[1.]*5),
                ([True]+[0.]*9,[1.]*6),([0.]*10,[math.inf]+[1.]*5)):
            with self.assertRaises(ValueError):original.multiply(*operands)

    def test_synthetic_coverage_is_deterministic_bounded_and_complete(self):
        a=list(synthetic_inputs());self.assertEqual(len(a),1000)
        self.assertEqual(a,list(synthetic_inputs()))
        for operands in a:validated(*operands)
        for count in (True,0,11,10001):
            with self.assertRaises(ValueError):list(synthetic_inputs(count))

    @unittest.skipUnless(hasattr(math,"fma"),"requires correctly rounded fma")
    def test_identity_model_retains_all_components(self):
        row=captures(trace_document())[0]
        self.assertEqual(wheel_inertia(row["inertia"],row["vector"]),row["vector"])


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class ActualOriginalInertiaTests(unittest.TestCase):
    def test_thousand_actual_original_returns_match_reconstructed_order_including_zero_signs(self):
        original=OriginalInertia(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for i,operands in enumerate(synthetic_inputs()):
            with self.subTest(i=i):qualified_row(original,*operands,"synthetic",str(i))


if __name__=="__main__":unittest.main()
