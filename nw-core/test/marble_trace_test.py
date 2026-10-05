#!/usr/bin/env python3
"""Regression tests for label-aware compiled Marble Newton trace decoding."""

import importlib.util
import json
import ctypes
import math
import os
import random
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("marble_source_play_trace.py")
SPEC = importlib.util.spec_from_file_location("marble_source_play_trace",
                                              MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
marble_trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(marble_trace)


class OriginalInertiaOracleTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),
                         "set NW_MUJOCO_REFERENCE_LIBRARY to the original library")
    def test_fused_reconstruction_matches_original_arm64_routine(self):
        library = ctypes.CDLL(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        scalar = ctypes.c_double
        routine = library.mju_mulInertVec
        routine.argtypes = [ctypes.POINTER(scalar)] * 3
        routine.restype = None
        rng = random.Random(260926)
        for case in range(1000):
            inertia = [rng.uniform(-1, 1) * 2**rng.randrange(-30, 30)
                       for _ in range(10)]
            velocity = [rng.uniform(-1, 1) * 2**rng.randrange(-30, 30)
                        for _ in range(6)]
            engine = {"model": {"body_dofadr": [0, 0],
                                 "body_dofnum": [0, 0],
                                 "body_parentid": [0, 0],
                                 "gravity": [0, 0, 0]},
                      "arrays": {"cvel": [0]*6 + velocity,
                                 "cinert": [0]*10 + inertia,
                                 "cdof": [], "cdof_dot": [], "qvel": []}}
            actual = marble_trace.reconstruct_rne_bias(
                engine, fma=math.fma, fused_kernels=frozenset({"inert"}))
            expected = (scalar*6)()
            routine(expected, (scalar*10)(*inertia), (scalar*6)(*velocity))
            self.assertEqual(actual["inertial_velocity"], list(expected),
                             f"original-library mismatch at case {case}")


class ExactSolverOutputTests(unittest.TestCase):
    def test_signed_zero_is_not_an_exact_match(self):
        self.assertFalse(marble_trace.exact_solver_value_equal(0.0, -0.0))
        self.assertFalse(marble_trace.exact_solver_value_equal(-0.0, 0.0))
        self.assertTrue(marble_trace.exact_solver_value_equal(-0.0, -0.0))
        self.assertTrue(marble_trace.exact_solver_value_equal(0, 0.0))

    def test_no_tolerance_or_nonfinite_pass(self):
        self.assertFalse(marble_trace.exact_solver_value_equal(
            1.0, math.nextafter(1.0, 2.0)))
        for value in (float("nan"), float("inf"), -float("inf")):
            self.assertFalse(marble_trace.exact_solver_value_equal(value, value))
        self.assertTrue(marble_trace.exact_solver_value_equal(3, 3))


class PublicSnapshotValidationTests(unittest.TestCase):
    def setUp(self):
        marble_trace.first_exceedance = None

    @staticmethod
    def snapshot():
        return {
            "marbles": [{"values": [0.0] * 13, "state": "rolling", "over": None}],
            **{key: 0 for key in ("roll", "pitch", "elapsed", "struck", "nudgeDue",
                                  "home", "lost", "cupped", "lostThisStep")},
        }

    def test_missing_or_extra_components_fail_even_when_both_sides_match(self):
        for source_count, wasm_count in ((13, 12), (12, 13), (12, 12), (14, 14)):
            with self.subTest(source_count=source_count, wasm_count=wasm_count):
                source, wasm = self.snapshot(), self.snapshot()
                source["marbles"][0]["values"] = [0.0] * source_count
                wasm["marbles"][0]["values"] = [0.0] * wasm_count
                with self.assertRaisesRegex(AssertionError, "13 components"):
                    marble_trace.compare_snapshot(source, wasm, 7, {}, {}, [])

    def test_nonfinite_then_finite_breach_keeps_nonfinite_failure(self):
        maxima, exceedances = {}, {}
        marble_trace.close(float("nan"), 0.0, 1e-7,
                           "event[0].marble[0].value[10]", maxima, exceedances)
        marble_trace.close(1.0, 0.0, 1e-7,
                           "event[1].marble[0].value[10]", maxima, exceedances)
        self.assertEqual(exceedances["value[10]"]["count"], 2)
        self.assertEqual(exceedances["value[10]"]["maxDelta"], "non-finite")
        self.assertEqual(exceedances["value[10]"]["worstContext"],
                         "event[0].marble[0].value[10]")

    def test_complete_equal_snapshot_passes(self):
        maxima, exceedances = {}, {}
        marble_trace.compare_snapshot(self.snapshot(), self.snapshot(), 0,
                                      maxima, exceedances, [])
        self.assertEqual(exceedances, {})
        self.assertIn("value[12]", maxima)


class NewtonRecordPayloadTests(unittest.TestCase):
    def test_prepare_uv_is_named_as_accumulation_not_objective_cost(self):
        result = marble_trace.newton_record_payload(
            25042, [25042, 0, 0, 1, 6, 6, 0.25, 0.125, 0])
        self.assertEqual(result["kind"], "primal_prepare_tangent_accumulation")
        self.assertEqual(result["payload"], {
            "UV_partial_sum": 0.25, "VV_partial_sum": 0.125, "reserved": 0})

    def test_prepare_after_tangent_is_not_a_line_search_zone_probe(self):
        result = marble_trace.newton_record_payload(
            910013, [910013, 0, 0, 1, 6, 6, 0.25, 0.125, 0.5])
        self.assertEqual(result["kind"], "primal_prepare_bottom_polynomial")
        self.assertEqual(result["payload"], {
            "quad_linear_after": 0.25, "quad_quadratic_after": 0.125,
            "DJ_tangent": 0.5})

    def test_contact_eval_label_does_not_call_normal_component_cost(self):
        decoded = marble_trace.newton_record_payload(
            601000, [601000, 0.5, 1, 1, 6, 6, -0.7, 1e-6, 3])
        self.assertEqual(decoded["kind"], "elliptic_N_Tsqr")
        self.assertEqual(decoded["payload"], {
            "normal_component": -0.7,
            "tangential_squared": 1e-6,
            "contact_id": 3,
        })

    def test_solver_result_label_names_actual_objective_fields(self):
        decoded = marble_trace.newton_record_payload(
            3001, [3001, 0.5, 1, 1, 6, 6, -12.2, -2e-15, 24.4])
        self.assertEqual(decoded["kind"], "line_search_result")
        self.assertEqual(decoded["payload"], {
            "objective_cost": -12.2,
            "first_derivative": -2e-15,
            "second_derivative": 24.4,
        })

    def test_bottom_zone_probe_decodes_derivative_term_not_cost(self):
        decoded = marble_trace.newton_record_payload(
            900003, [900003, 0.5, 1, 1, 6, 6, 0, -2.3, 22])
        self.assertEqual(decoded["kind"], "elliptic_zone_probe")
        self.assertEqual(decoded["payload"], {
            "first_derivative_before": 0,
            "first_derivative_increment": -2.3,
            "second_derivative_after_increment": 22,
        })

    def test_elliptic_intermediate_label_decodes_return_value(self):
        decoded = marble_trace.newton_record_payload(
            9010009, [9010009, 0.5, 1, 1, 6, 6, -13.4, 2, 2])
        self.assertEqual(decoded["kind"], "elliptic_cost_intermediate")
        self.assertEqual(decoded["payload"], {
            "elliptic_cost_delta": -13.4,
            "initial_zone": 2,
            "alpha_zone": 2,
        })

    def test_later_standard_evaluation_labels_remain_zone_probes(self):
        decoded = marble_trace.newton_record_payload(
            1200001, [1200001, 0.5, 4, 1, 6, 6, 0.01, -0.2, 0])
        self.assertEqual(decoded["kind"], "elliptic_zone_probe")
        self.assertEqual(decoded["payload"], {
            "tangent_norm": 0.01,
            "top_zone_margin": -0.2,
            "reserved": 0,
        })


class EllipticCostOperandPairTests(unittest.TestCase):
    def test_joins_exact_operands_for_same_evaluation_and_constraint(self):
        native = [
            {"eval": 1, "row": 0, "field": 1, "alpha": 0.5,
             "contactId": 7, "cost": -0.2},
            {"eval": 1, "row": 0, "field": 2, "alpha": 0.5,
             "contactId": 7, "cost": -0.3},
            {"eval": 2, "row": 0, "field": 1, "alpha": 0.75,
             "contactId": 7, "cost": 9.0},
        ]
        wasm = [dict(record) for record in native]
        paired = marble_trace.elliptic_cost_operand_pair(
            9010001, native, wasm)
        self.assertEqual(paired, {
            "evaluation": 1,
            "constraintRow": 0,
            "native": {"alpha": 0.5, "contactId": 7,
                       "values": {"U0": -0.2, "V0": -0.3}},
            "wasm": {"alpha": 0.5, "contactId": 7,
                     "values": {"U0": -0.2, "V0": -0.3}},
            "equalInputs": True,
        })

    def test_reports_operand_mismatch_and_rejects_other_probe_labels(self):
        native = [{"eval": 1, "row": 0, "field": 1, "alpha": 0.5,
                   "contactId": 7, "cost": -0.2}]
        wasm = [{**native[0], "cost": -0.1}]
        paired = marble_trace.elliptic_cost_operand_pair(
            9010001, native, wasm)
        self.assertFalse(paired["equalInputs"])
        self.assertIsNone(marble_trace.elliptic_cost_operand_pair(
            9010002, native, wasm))


class NoSlipTraceDecoderTests(unittest.TestCase):
    def test_jaref_decoder_keeps_operands_separate_from_result(self):
        values = [2, 1, 2, 0, 0.1, 0.2, 0.3, 1.0, 2.0, 4.5]
        decoded, error = marble_trace.decode_jaref_trace(values)
        self.assertIsNone(error)
        self.assertEqual(decoded, [{
            "island": 2,
            "nefc": 1,
            "nv": 2,
            "sparse": 0,
            "qacc": [0.1, 0.2],
            "aref": [0.3],
            "J": [1.0, 2.0],
            "Jaref": [4.5],
        }])

    def test_jaref_decoder_rejects_truncated_or_sparse_records(self):
        _, truncated = marble_trace.decode_jaref_trace([0, 1, 1, 0, 0.2])
        _, sparse = marble_trace.decode_jaref_trace([0, 1, 1, 1, 0.2, 0.3, 0.4])
        self.assertIn("invalid record", truncated)
        self.assertIn("invalid record", sparse)

    def test_jaref_update_decoder_keeps_before_direction_and_after(self):
        values = [3, 2, 0.5, 1.0, 2.0, 0.1, 0.2, 1.05, 2.1]
        decoded, error = marble_trace.decode_jaref_update_trace(values)
        self.assertIsNone(error)
        self.assertEqual(decoded, [{
            "island": 3,
            "nefc": 2,
            "alpha": 0.5,
            "before": [1.0, 2.0],
            "direction": [0.1, 0.2],
            "after": [1.05, 2.1],
        }])

    def test_jv_decoder_keeps_search_jacobian_and_result(self):
        values = [4, 1, 2, 0, 0.5, -0.25, 1.0, 2.0, 1.0]
        decoded, error = marble_trace.decode_jv_trace(values)
        self.assertIsNone(error)
        self.assertEqual(decoded, [{
            "island": 4,
            "nefc": 1,
            "nv": 2,
            "sparse": 0,
            "search": [0.5, -0.25],
            "J": [1.0, 2.0],
            "Jv": [1.0],
        }])

    def test_step_decoder_preserves_reduction_and_state_decision_fields(self):
        values = [0, 1, 2, 3.5, 0.25, 0.875, 4, 1,
                  7, 0.1, 0, 4,
                  9, 0.2, 3, 3]
        decoded, error = marble_trace.decode_noslip_steps(values)
        self.assertIsNone(error)
        self.assertEqual(decoded, [{
            "island": 0,
            "iteration": 1,
            "nefc": 2,
            "rawImprovement": 3.5,
            "scale": 0.25,
            "improvement": 0.875,
            "nactive": 4,
            "nchange": 1,
            "rows": [
                {"row": 7, "force": 0.1, "oldState": 0, "state": 4},
                {"row": 9, "force": 0.2, "oldState": 3, "state": 3},
            ],
        }])

    def test_summary_decoder_names_active_set_change(self):
        native = [0, 0, 2, 0.1, 0, 0, 4, 0.2, 0, 5, 0.3, 0,
                  0, 0, 2, 0.05, 0, 0, 4, 0.2, 0, 5, 0.3, 0]
        wasm = [0, 0, 2, 0.1, 0, 0, 4, 0.2, 0, 5, 0.3, 0,
                0, 0, 2, 0.05, 6, 6, 4, 0.2, 0, 5, 0.3, 0]
        decoded, error = marble_trace.decode_noslip_summary(wasm)
        self.assertIsNone(error)
        self.assertEqual(len(decoded), 2)
        self.assertEqual(decoded[1]["iteration"], 0)
        self.assertEqual(
            marble_trace.first_record_difference(
                marble_trace.decode_noslip_summary(native)[0], decoded),
            {"record": 1, "field": "nactive", "native": 0, "wasm": 6})
        self.assertEqual(
            marble_trace.first_noslip_active_set_difference(
                marble_trace.decode_noslip_summary(native)[0], decoded),
            {"record": 1, "iteration": 0, "field": "nactive",
             "native": 0, "wasm": 6})

    def test_contact_decoder_handles_variable_tangent_width(self):
        # Current contact records include costChange before the appended
        # bias/regularizer/tangent-force vectors.
        values = [0, 1, 4, 2, 7, 0.5, 0.1, 0.2, 0.3, 0.4, 0.5,
                  1.0, 2.0, 3.0, 4.0, 5.0, 0.9, 6.0, 7.0, 8.0]
        decoded, error = marble_trace.decode_noslip_contacts(values)
        self.assertIsNone(error)
        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0]["contactId"], 7)
        self.assertEqual(decoded[0]["normal"], 0.5)
        self.assertEqual(decoded[0]["residual"], [1.0])
        self.assertEqual(decoded[0]["updatedForce"], [5.0])
        self.assertEqual(decoded[0]["costChange"], 0.9)
        self.assertEqual(decoded[0]["bias"], [6.0])
        self.assertEqual(decoded[0]["regularizer"], [7.0])
        self.assertEqual(decoded[0]["tangentForce"], [8.0])

    def test_decoders_report_truncated_or_invalid_records(self):
        _, summary_error = marble_trace.decode_noslip_summary([0, 1, 2])
        _, contact_error = marble_trace.decode_noslip_contacts(
            [0, 1, 4, 2, 7, 0.5, 0, 0, 0, 0, 0])
        self.assertEqual(summary_error, "truncated header at offset 0")
        self.assertIn("invalid record at offset 0", contact_error)


class SnapshotDeltaSummaryTests(unittest.TestCase):
    def test_contact_diagnostic_keeps_geometry_not_only_contact_pairs(self):
        contact = {
            "geom1": 56, "geom2": 29, "dist": -0.000126,
            "pos": [0.26, 0.298, 0.0071],
            "frame": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                      0.0, 0.0, 1.0],
            "dim": 4, "mu": 0.3, "friction": [0.3, 0.3, 0.005, 0.005, 0.005],
            "solver": "elliptic",
        }
        summary = marble_trace.contact_geometry_summary([contact])
        self.assertEqual(summary, [{
            key: contact[key] for key in (
                "geom1", "geom2", "dist", "pos", "frame", "dim", "mu",
                "friction")
        }])

    def test_summary_reports_per_field_maximum_and_location(self):
        actual = {
            "marbles": [{"values": [0.0] * 13},
                        {"values": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}],
            "roll": 0.1, "pitch": 0.0, "elapsed": 1.0,
            "struck": 0.0, "nudgeDue": 0.0,
            "contacts": [{"geom1": 0, "geom2": 8},
                         {"geom1": 0, "geom2": 9}],
        }
        expected = {
            "marbles": [{"values": [0.0] * 13},
                        {"values": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}],
            "roll": 0.0, "pitch": 0.0, "elapsed": 1.0,
            "struck": 0.0, "nudgeDue": 0.0,
            "contacts": [{"geom1": 0, "geom2": 8},
                         {"geom1": 0, "geom2": 10}],
        }
        actual["marbles"][1]["values"][11] = 2e-7
        actual["marbles"][0]["values"][2] = -3e-8
        row = marble_trace.summarize_snapshot_deltas(actual, expected, 196)
        self.assertEqual(row["event"], 196)
        self.assertEqual(row["position"], {
            "maxAbs": 3e-8, "marble": 0, "valueIndex": 2})
        self.assertEqual(row["angularVelocity"], {
            "maxAbs": 2e-7, "marble": 1, "valueIndex": 11})
        self.assertEqual(row["roll"], {"abs": 0.1})
        self.assertEqual(row["contacts"], {
            "samePairs": False, "sourceCount": 2, "wasmCount": 2,
            "sourceOnly": [[0, 9]], "wasmOnly": [[0, 10]],
        })

    def test_state_delta_writer_persists_partial_prefix_as_jsonl(self):
        rows = [{"event": 0, "position": {"maxAbs": 1e-9}},
                {"event": 1, "position": {"maxAbs": 2e-9}}]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "partial.jsonl"
            marble_trace.write_state_delta_rows(destination, rows)
            self.assertEqual([json.loads(line)
                              for line in destination.read_text().splitlines()], rows)


class EnginePhaseValidityTests(unittest.TestCase):
    def test_island_scratch_is_not_compared_before_position_phase(self):
        label = "event[0].substep[0].phase.comPos"
        self.assertFalse(marble_trace.engine_array_valid_at_phase(
            "map_dof2idof", label, nisland=3))
        self.assertFalse(marble_trace.engine_array_valid_at_phase(
            "iacc", label, nisland=3))
        self.assertTrue(marble_trace.engine_array_valid_at_phase(
            "qpos", label))
        self.assertTrue(marble_trace.engine_array_valid_at_phase(
            "map_dof2idof", "event[0].substep[0].phase.probe_rneBias",
            nisland=3))

    def test_island_maps_and_solver_outputs_follow_their_initialization_phases(self):
        position_label = "event[0].substep[0].phase.fwdPosition"
        label = "event[0].substep[0].phase2.fwdConstraint"
        self.assertTrue(marble_trace.engine_array_valid_at_phase(
            "map_dof2idof", position_label, nisland=3))
        self.assertTrue(marble_trace.engine_array_valid_at_phase(
            "map_dof2idof", label, nisland=3))
        self.assertFalse(marble_trace.engine_array_valid_at_phase(
            "iacc", position_label, nisland=3))
        self.assertFalse(marble_trace.engine_array_valid_at_phase(
            "iacc", "event[0].substep[0].phase2.fwdAcceleration", nisland=3))
        self.assertTrue(marble_trace.engine_array_valid_at_phase(
            "iacc", label, nisland=3))

    def test_island_maps_are_invalid_when_no_islands_were_built(self):
        for phase in ("comPos", "fwdPosition", "probe_rneBias",
                      "fwdConstraint"):
            with self.subTest(phase=phase):
                self.assertFalse(marble_trace.engine_array_valid_at_phase(
                    "map_dof2idof", f"event[0].phase.{phase}", nisland=0))

    def test_island_arrays_require_explicit_island_count(self):
        self.assertFalse(marble_trace.engine_array_valid_at_phase(
            "map_dof2idof", "event[0].substep[0]"))

    def test_phase2_initialization_matrix_does_not_take_full_step_fast_path(self):
        phases = ("step2_input", "fwdActuation", "fwdAcceleration",
                  "fwdConstraint", "sensorAcc", "checkAcc", "implicit")
        for index, phase in enumerate(phases):
            label = f"event[0].substep[0].phase2.{phase}"
            for field in ("qacc_smooth", "qfrc_smooth"):
                with self.subTest(phase=phase, field=field):
                    self.assertEqual(marble_trace.engine_array_valid_at_phase(
                        field, label, nisland=3), index >= 2)
            for field in ("efc_force", "qacc", "iacc", "iefc_force", "solver_stats"):
                with self.subTest(phase=phase, field=field):
                    self.assertEqual(marble_trace.engine_array_valid_at_phase(
                        field, label, nisland=3), index >= 3)
            for field in ("qpos", "qfrc_bias", "efc_aref", "map_dof2idof"):
                with self.subTest(phase=phase, field=field):
                    self.assertTrue(marble_trace.engine_array_valid_at_phase(
                        field, label, nisland=3))

    def test_solver_fast_path_cannot_expose_inactive_island_scratch(self):
        for count in (None, 0):
            for label in ("event[0].substep[0]",
                          "event[0].substep[0].phase2.fwdConstraint"):
                for field in ("iacc", "iefc_force", "solver_stats"):
                    with self.subTest(count=count, label=label, field=field):
                        self.assertFalse(marble_trace.engine_array_valid_at_phase(
                            field, label, nisland=count))
                self.assertTrue(marble_trace.engine_array_valid_at_phase(
                    "qacc", label, nisland=count))

    def test_non_phase_snapshots_still_compare_island_state(self):
        self.assertTrue(marble_trace.engine_array_valid_at_phase(
            "map_dof2idof", "event[0].substep[0]", nisland=3))


if __name__ == "__main__":
    unittest.main()
