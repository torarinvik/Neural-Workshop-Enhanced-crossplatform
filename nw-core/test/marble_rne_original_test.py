import copy
import hashlib
import json
import math
from pathlib import Path
import unittest

from marble_rne_original import OriginalRNE,validated_engine,selected_inputs,FIELDS

ROOT=Path(__file__).resolve().parent


def engine_document():
    return dict(model=dict(body_parentid=[0,0],body_dofadr=[-1,0],body_dofnum=[0,6],
        gravity=[0.,0.,-9.8],disableflags=0,options=dict(enableflags=0,disableflags=0)),
        arrays=dict(cinert=[0.]*20,cvel=[0.]*12,cdof=[0.]*36,cdof_dot=[0.]*36,
            qvel=[0.]*6,qfrc_bias=[0.]*6))


def trace_document():
    before=engine_document();after=copy.deepcopy(before);after["arrays"]["qfrc_bias"]=[1.,2.,3.,4.,5.,6.]
    raw=[0.]*150;raw[72:78]=after["arrays"]["qfrc_bias"]
    return dict(events=[dict(rneTraces=[raw],engineStep1Phases=[[
        dict(phase="probe_referenceConstraint",engine=before),dict(phase="probe_rneBias",engine=after)]])])


class RneInputTests(unittest.TestCase):
    def test_complete_owners_and_actual_assigned_return(self):
        rows=selected_inputs(trace_document());self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]["event"],rows[0]["substep"]),(0,0))
        self.assertEqual(rows[0]["captured"],[1.,2.,3.,4.,5.,6.])
        self.assertEqual(validated_engine(rows[0]["engine"]),(2,6))

    def test_every_complete_operand_validated_before_any_native_pointer(self):
        original=OriginalRNE.__new__(OriginalRNE)
        for field in FIELDS+("qfrc_bias",):
            for value in (True,math.nan,math.inf,"1",None):
                engine=engine_document();engine["arrays"][field][-1]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    original.evaluate(None,None,engine)
            engine=engine_document();engine["arrays"][field].pop()
            with self.assertRaises(ValueError):original.evaluate(None,None,engine)

    def test_missing_containers_flags_gravity_and_sleep_reject(self):
        for field in ("model","arrays"):
            e=engine_document();e[field]=None
            with self.assertRaises(ValueError):validated_engine(e)
        for name,value in (("enableflags",None),("enableflags",True),("enableflags",16),
                ("enableflags",2147483648),("disableflags",-1),("disableflags",128)):
            e=engine_document();e["model"]["options"][name]=value
            with self.subTest(name=name,value=value),self.assertRaises(ValueError):validated_engine(e)
        e=engine_document();e["model"]["gravity"]=[0.,0.]
        with self.assertRaises(ValueError):validated_engine(e)

    def test_parent_and_complete_dof_ownership_reject(self):
        for name,values in (("body_parentid",[0,1]),("body_parentid",[1,0]),
                ("body_dofadr",[-1,-1]),("body_dofadr",[-1,1]),("body_dofnum",[0,7]),
                ("body_dofnum",[0,5]),("body_dofnum",[True,6])):
            e=engine_document();e["model"][name]=values
            with self.subTest(name=name,values=values),self.assertRaises(ValueError):validated_engine(e)

    def test_duplicate_missing_mutated_and_disagreeing_outputs_reject(self):
        for count in (0,2):
            t=trace_document();p=t["events"][0]["engineStep1Phases"][0]
            p[:]=[p[0]]+[copy.deepcopy(p[1]) for _ in range(count)]
            with self.assertRaises(ValueError):selected_inputs(t)
        for field in FIELDS:
            t=trace_document();t["events"][0]["engineStep1Phases"][0][1]["engine"]["arrays"][field][-1]=1.
            with self.assertRaises(ValueError):selected_inputs(t)
        t=trace_document();t["events"][0]["rneTraces"][0][72]=0.
        with self.assertRaises(ValueError):selected_inputs(t)


class RneFixtureTests(unittest.TestCase):
    def fixture(self):return json.loads((ROOT/"fixtures/marble_rne_bias_family_rejected.json").read_text())

    def test_before_after_full_actual_original_bias_evidence(self):
        f=self.fixture()
        self.assertEqual(f["before"]["counts"],dict(boundaries=20,differentBoundaries=10,differentValues=21,modelDifferentBoundaries=0,modelDifferentValues=0))
        self.assertEqual(f["after"]["counts"],dict(boundaries=20,differentBoundaries=0,differentValues=0,modelDifferentBoundaries=0,modelDifferentValues=0))
        self.assertFalse(f["originalPrivateIntermediatesCaptured"])
        self.assertFalse(f["capturedBrowserZeroSignsQualified"])

    def test_complete_compiled_returns_and_unchanged_acceleration_mode(self):
        p=self.fixture()["compiledProof"]
        self.assertEqual(p["counts"],dict(captured=20,synthetic=1000))
        self.assertEqual(p["layouts"],{"0":334,"1":353,"2":333})
        self.assertEqual(p["differences"],0);self.assertEqual(p["first"],[])
        self.assertEqual(p["accelerationControlMatches"],1020)
        self.assertFalse(p["flagAcceleration"])

    def test_bias_only_platform_guarded_additive_patch(self):
        f=self.fixture();p=(ROOT/"repro/marble_rne_bias_family_candidate.patch").read_text()
        self.assertEqual(hashlib.sha256(p.encode()).hexdigest(),f["deltaPatch"]["sha256"])
        self.assertEqual(p.count("diff --git"),1);self.assertEqual(p.count("+    if (!flg_acc)"),3)
        self.assertIn("+static mjtNum marble_rne_dot",p)
        self.assertIn("+        out[c] = mj_marble_wheel_fma",p)
        self.assertNotIn("-fno-builtin",p)

    def test_local_family_qualification_is_not_game_acceptance(self):
        f=self.fixture();r=f["rejection"]
        self.assertFalse(r["promoted"]);self.assertTrue(r["ordinaryUnsynchronized"])
        self.assertEqual(r["numericExceedances"],110690)
        self.assertEqual(r["contactSets"]["count"],105)
        self.assertEqual(r["firstNumeric"]["context"],"event[195].marble[0].value[10]")
        self.assertEqual(r["firstNumeric"]["delta"],4.996572333659799e-7)
        self.assertFalse(f["physicsComparison"]["claimedRecorderNeutrality"])
        self.assertFalse(f["physicsComparison"]["exactlyUnchanged"])

    def test_current_whole_solver_all_nonstat_outputs_stay_cleared(self):
        f=json.loads((ROOT/"fixtures/marble_rne_family_whole_solver.json").read_text())
        self.assertEqual(f["counts"],dict(exactInputOriginalQualifiedBoundaries=20,
            allOutputNonzeroExactBoundaries=17,statisticDifferentBoundaries=3,
            statisticDifferentValues=3,otherOutputDifferentBoundaries=0))
        self.assertEqual(len(f["fieldsCompared"]),21)
        self.assertFalse(f["ordinaryTrajectoryAcceptance"]);self.assertTrue(f["synchronizationUsed"])
        self.assertFalse(f["promoted"])


if __name__=="__main__":unittest.main()
