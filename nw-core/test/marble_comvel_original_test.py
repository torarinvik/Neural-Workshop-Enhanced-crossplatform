import copy
import hashlib
import json
import math
from pathlib import Path
import unittest

from marble_comvel_original import OriginalComVel, validated_engine, selected_inputs, reconstruct, bit_vectors, INPUTS, OUTPUTS

ROOT = Path(__file__).resolve().parent


def engine_document():
    return dict(model=dict(body_parentid=[0, 0], body_dofadr=[-1, 0], body_dofnum=[0, 6],
                           dof_jntid=[0] * 6, jnt_type=[0], jnt_dofadr=[0],
                           disableflags=0, options=dict(enableflags=0, disableflags=0)),
                arrays=dict(qvel=[0.] * 6, cdof=[0.] * 36, cvel=[0.] * 12, cdof_dot=[0.] * 36))


def trace_document():
    before = engine_document()
    after = copy.deepcopy(before)
    after["arrays"]["cdof_dot"][-1] = 1.
    return dict(events=[dict(engineStep1Phases=[[
        dict(phase="probe_input", engine=before), dict(phase="probe_comVel", engine=after)]])])


class ComVelValidationTests(unittest.TestCase):
    def test_complete_input_and_unique_named_call_owners(self):
        self.assertEqual(validated_engine(engine_document()), (2, 6, 1))
        rows = selected_inputs(trace_document())
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["event"], rows[0]["substep"]), (0, 0))
        self.assertEqual(rows[0]["captured"]["cdof_dot"][-1], 1.)

    def test_all_operands_validate_before_native_pointers(self):
        original = OriginalComVel.__new__(OriginalComVel)
        for field in INPUTS + OUTPUTS:
            for value in (None, "1", True, math.nan, math.inf):
                engine = engine_document()
                engine["arrays"][field][-1] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    original.evaluate(None, None, engine)
            engine = engine_document()
            engine["arrays"][field].pop()
            with self.assertRaises(ValueError):
                original.evaluate(None, None, engine)

    def test_parent_body_and_joint_topology_reject(self):
        invalid = (("body_parentid", [0, 1]), ("body_parentid", [1, 0]),
                   ("body_dofadr", [-1, 1]), ("body_dofnum", [0, 5]),
                   ("body_dofnum", [0, 7]), ("body_dofnum", [True, 6]),
                   ("dof_jntid", [0] * 5), ("dof_jntid", [0] * 5 + [1]),
                   ("jnt_type", [4]), ("jnt_type", [1]),
                   ("jnt_dofadr", [1]), ("jnt_dofadr", [0, 0]))
        for field, values in invalid:
            engine = engine_document()
            engine["model"][field] = values
            with self.subTest(field=field, values=values), self.assertRaises(ValueError):
                validated_engine(engine)

    def test_containers_flags_sleep_and_dimension_bounds_reject(self):
        for field in ("model", "arrays"):
            engine = engine_document()
            engine[field] = None
            with self.assertRaises(ValueError):
                validated_engine(engine)
        for field, value in (("enableflags", None), ("enableflags", True), ("enableflags", 16),
                             ("enableflags", 2147483648), ("disableflags", -1), ("disableflags", 128)):
            engine = engine_document()
            engine["model"]["options"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validated_engine(engine)
        engine = engine_document()
        engine["arrays"]["qvel"] = [0.] * 513
        with self.assertRaises(ValueError):
            validated_engine(engine)

    def test_missing_duplicate_and_mutated_input_owners_reject(self):
        for count in (0, 2):
            trace = trace_document()
            phases = trace["events"][0]["engineStep1Phases"][0]
            phases[:] = [phases[0]] + [copy.deepcopy(phases[1]) for _ in range(count)]
            with self.assertRaises(ValueError):
                selected_inputs(trace)
        for field in INPUTS:
            trace = trace_document()
            trace["events"][0]["engineStep1Phases"][0][1]["engine"]["arrays"][field][-1] = 1.
            with self.assertRaises(ValueError):
                selected_inputs(trace)
        trace = trace_document()
        trace["events"][0]["engineStep1Phases"][0][1]["engine"]["model"]["disableflags"] = 128
        with self.assertRaises(ValueError):
            selected_inputs(trace)

    def test_later_packet_rejects_before_native_evaluation_can_begin(self):
        trace = trace_document()
        later = copy.deepcopy(trace["events"][0])
        later["engineStep1Phases"][0][0]["engine"]["arrays"]["cdof"][-1] = math.nan
        trace["events"].append(later)
        with self.assertRaises(ValueError):
            selected_inputs(trace)

    def test_malformed_event_substep_and_checkpoint_containers_reject(self):
        for trace in (None, {}, dict(events=[None]), dict(events=[dict(engineStep1Phases=None)]),
                      dict(events=[dict(engineStep1Phases=[None])]), dict(events=[dict(engineStep1Phases=[[None]])])):
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                selected_inputs(trace)

    def test_free_joint_zero_velocity_overwrites_prior_output(self):
        engine = engine_document()
        engine["arrays"]["cvel"] = [1.] * 12
        engine["arrays"]["cdof_dot"] = [2.] * 36
        self.assertEqual(reconstruct(engine), dict(cvel=[0.] * 12, cdof_dot=[0.] * 36))


class ComVelFixtureTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "fixtures/marble_comvel_family_rejected.json").read_text())

    def test_complete_original_before_and_after_and_qualified_model(self):
        fixture = self.fixture()
        self.assertEqual(fixture["before"]["counts"]["differentBoundaries"], 8)
        self.assertEqual(fixture["before"]["counts"]["differentValues"], 21)
        self.assertEqual(fixture["before"]["counts"]["cvelDifferentBoundaries"], 0)
        self.assertEqual(fixture["after"]["counts"]["differentBoundaries"], 0)
        matrix = [(e, s) for e in (0, 1, 17, 18, 216) for s in range(4)]
        for report in (fixture["before"], fixture["after"]):
            self.assertEqual([(b["event"], b["substep"]) for b in report["boundaries"]], matrix)
            for boundary in report["boundaries"]:
                self.assertEqual(validated_engine(boundary["input"]), (4, 18, 3))
                self.assertEqual(bit_vectors(reconstruct(boundary["input"])), boundary["actualOriginalBits"])
        self.assertFalse(fixture["capturedBrowserZeroSignsQualified"])
        self.assertFalse(fixture["originalPrivateIntermediatesCaptured"])

    def test_actual_compiled_control_and_complete_candidate_five_layouts(self):
        fixture = self.fixture()
        old, new = (fixture[name]["proof"] for name in ("compiledControl", "compiledCandidate"))
        self.assertEqual(old["differences"], 683)
        self.assertEqual(old["differingCalls"], dict(captured=8, synthetic=675))
        self.assertEqual(old["differentValues"], 2700)
        self.assertEqual(new["differences"], 0)
        self.assertEqual(new["differentValues"], 0)
        self.assertEqual(new["counts"], dict(captured=20, synthetic=1000))
        self.assertEqual(new["layouts"], {"0": 200, "1": 220, "2": 200, "3": 200, "4": 200})
        self.assertTrue(new["completePublicCall"])
        self.assertFalse(new["ordinaryTrajectoryAcceptance"])

    def test_additive_platform_guard_leaves_native_and_single_axis_calls(self):
        fixture = self.fixture()
        patch = (ROOT / "repro/marble_comvel_family_candidate.patch").read_text()
        self.assertEqual(hashlib.sha256(patch.encode()).hexdigest(), fixture["deltaPatch"]["sha256"])
        self.assertEqual(patch.count("diff --git"), 1)
        self.assertIn("+#ifdef __EMSCRIPTEN__", patch)
        self.assertIn("+#define MARBLE_COMVEL_DOF_VEC mju_mulDofVec", patch)
        self.assertIn("+#define MARBLE_COMVEL_CROSS_MOTION mji_crossMotion", patch)
        self.assertIn("+#undef MARBLE_COMVEL_DOF_VEC", patch)
        self.assertNotIn("-        mju_mulDofVec(tmp, d->cdof+6*(bda+j), d->qvel+bda+j, 1);", patch)
        self.assertNotIn("engine_util_spatial.c", patch)

    def test_every_previous_current_and_compiled_producer_stays_cleared(self):
        regressions = self.fixture()["localProducerRegressions"]
        self.assertEqual(set(regressions), {"inertia", "cost", "gauss", "generic", "qcqp2", "rne"})
        for report in regressions.values():
            self.assertEqual(report["compiledProof"]["differences"], 0)
            self.assertEqual(report["compiledProof"]["first"], [])
        self.assertEqual(regressions["rne"]["counts"]["differentBoundaries"], 0)
        self.assertEqual(regressions["rne"]["compiledProof"]["accelerationControlMatches"], 1020)

    def test_fewer_contacts_do_not_waive_worse_full_numeric_rejection(self):
        fixture = self.fixture()
        failure = fixture["rejection"]
        self.assertTrue(failure["ordinaryUnsynchronized"])
        self.assertFalse(failure["promoted"])
        self.assertEqual(failure["numericExceedances"], 111510)
        self.assertGreater(failure["numericExceedances"], 110690)
        self.assertEqual(failure["contactSets"]["count"], 103)
        self.assertEqual(failure["firstNumeric"]["delta"], 4.950429832728531e-7)
        self.assertGreater(failure["firstNumeric"]["delta"], failure["firstNumeric"]["tolerance"])
        self.assertFalse(fixture["physicsComparison"]["exactlyUnchanged"])

    def test_fresh_whole_solver_is_explicitly_synchronized_not_game_pass(self):
        fixture = json.loads((ROOT / "fixtures/marble_comvel_family_whole_solver.json").read_text())
        self.assertEqual(fixture["counts"], dict(exactInputOriginalQualifiedBoundaries=20,
            allOutputNonzeroExactBoundaries=18, statisticDifferentBoundaries=2,
            statisticDifferentValues=2, otherOutputDifferentBoundaries=0))
        self.assertEqual(len(fixture["fieldsCompared"]), 21)
        self.assertTrue(fixture["synchronizationUsed"])
        self.assertFalse(fixture["ordinaryTrajectoryAcceptance"])
        self.assertFalse(fixture["promoted"])


if __name__ == "__main__":
    unittest.main()
