"""Tests for the exact Marble trace-neutrality gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marble_trace_neutrality import first_physics_difference  # noqa: E402
from marble_trace_neutrality import runtime_provenance_error  # noqa: E402
from marble_trace_neutrality import DENSE_UNUSED_JACOBIAN_FIELDS  # noqa: E402


def trace(*, state: float = 1.0, contacts: list[dict[str, int]] | None = None) -> dict:
    return {
        "version": 1,
        "runtimeProvenance": {
            "schema": "neural-workshop.marble-runtime-provenance.v1",
            "coreWasm": {"path": "/runtime/nwcore.wasm", "sha256": "a" * 64},
            "mujoco": {
                "jsPath": "/runtime/mujoco.js",
                "jsSha256": "b" * 64,
                "wasmPath": "/runtime/mujoco.wasm",
                "wasmSha256": "c" * 64,
                "wasmResolution": "test adjacent file",
                "maintainedFilesMatchManifest": True,
            },
        },
        "rung": 16,
        "runSeed": 0,
        "boardSeed": 827307999,
        "timeLimitMs": 120000,
        "contactDiagnostics": False,
        "engineDiagnosticEvents": [0],
        "outcome": "timeout",
        "result": {"elapsedMs": 120017, "home": 0, "lost": 0},
        "events": [{
            "kind": "frame",
            "dt": 1 / 60,
            "held": ["E"],
            "state": {
                "marbles": [{"values": [state]}],
                "engine": {"contacts": contacts or [{"geom1": 0, "geom2": 56}]},
            },
            "newtonTraces": [{"values": [1.0]}],
            "rneTraces": [[2.0]],
            "phases": [{"rneProjectionTrace": [3.0]}],
        }],
    }


class MarbleTraceNeutralityTests(unittest.TestCase):
    @staticmethod
    def dense_trace() -> dict:
        sample = trace()
        sample["events"][0]["state"]["engine"].update({
            "model": {"sparse_jacobian": False},
            "arrays": {"efc_J": [1.0], "qacc": [2.0],
                       **{name: [40] for name in DENSE_UNUSED_JACOBIAN_FIELDS}},
        })
        return sample

    def test_explicit_dense_mode_excludes_only_unused_sparse_indices(self) -> None:
        left, right = self.dense_trace(), self.dense_trace()
        arrays = right["events"][0]["state"]["engine"]["arrays"]
        for name in DENSE_UNUSED_JACOBIAN_FIELDS:
            arrays[name] = [0, 0]
        self.assertIsNone(first_physics_difference(left, right))
        for name in DENSE_UNUSED_JACOBIAN_FIELDS:
            del arrays[name]
        self.assertIsNone(first_physics_difference(left, right))

    def test_dense_mode_preserves_exact_jacobian_and_other_array_checks(self) -> None:
        for name in ("efc_J", "qacc"):
            with self.subTest(name=name):
                left, right = self.dense_trace(), self.dense_trace()
                right["events"][0]["state"]["engine"]["arrays"][name][0] += 0.5
                found = first_physics_difference(left, right)
                self.assertEqual(found[0], f"events[0].state.engine.arrays.{name}[0]")

    def test_sparse_or_uncertain_metadata_does_not_mask_sparse_indices(self) -> None:
        for metadata in (True, None, 0, "false", "missing"):
            with self.subTest(metadata=metadata):
                left, right = self.dense_trace(), self.dense_trace()
                for sample in (left, right):
                    model = sample["events"][0]["state"]["engine"]["model"]
                    if metadata == "missing":
                        del model["sparse_jacobian"]
                    else:
                        model["sparse_jacobian"] = metadata
                right["events"][0]["state"]["engine"]["arrays"]["efc_J_colind"] = [0]
                found = first_physics_difference(left, right)
                self.assertEqual(found[0], "events[0].state.engine.arrays.efc_J_colind[0]")

    def test_different_jacobian_representations_cannot_compare_equal(self) -> None:
        left, right = self.dense_trace(), self.dense_trace()
        right["events"][0]["state"]["engine"]["model"]["sparse_jacobian"] = True
        found = first_physics_difference(left, right)
        self.assertEqual(found, ("events[0].state.engine.model.sparse_jacobian", False, True))

    def test_sparse_named_fields_outside_snapshot_arrays_remain_strict(self) -> None:
        left, right = self.dense_trace(), self.dense_trace()
        left["events"][0]["state"]["engine"]["efc_J_colind"] = [40]
        right["events"][0]["state"]["engine"]["efc_J_colind"] = [0]
        self.assertEqual(first_physics_difference(left, right)[0],
                         "events[0].state.engine.efc_J_colind[0]")

    def test_trace_payloads_are_ignored_but_physics_is_exact(self) -> None:
        left = trace()
        right = trace()
        right["events"][0]["newtonTraces"] = [{"values": [999.0]}]
        right["events"][0]["rneTraces"] = [[-4.0]]
        right["events"][0]["phases"][0]["rneProjectionTrace"] = [-5.0]
        self.assertIsNone(first_physics_difference(left, right))

    def test_first_numeric_state_difference_is_reported(self) -> None:
        difference = first_physics_difference(trace(), trace(state=1.0000000000000002))
        self.assertEqual(difference, ("events[0].state.marbles[0].values[0]", 1.0, 1.0000000000000002))

    def test_contact_identity_difference_is_reported(self) -> None:
        difference = first_physics_difference(
            trace(), trace(contacts=[{"geom1": 0, "geom2": 57}]))
        self.assertEqual(difference, ("events[0].state.engine.contacts[0].geom2", 56, 57))

    def test_missing_state_snapshot_is_reported(self) -> None:
        left = trace()
        right = trace()
        right["events"][0]["state"].pop("engine")
        difference = first_physics_difference(left, right)
        self.assertEqual(difference[0], "events[0].state.engine")
        self.assertEqual(difference[2], "<missing>")

    def test_runtime_provenance_requires_artifact_hashes_and_resolution(self) -> None:
        sample = trace()
        self.assertIsNone(runtime_provenance_error(sample))
        sample["runtimeProvenance"]["mujoco"]["wasmSha256"] = "not-a-hash"
        self.assertIn("SHA-256", runtime_provenance_error(sample))

    def test_runtime_provenance_rejects_missing_metadata(self) -> None:
        sample = trace()
        del sample["runtimeProvenance"]
        self.assertIn("missing", runtime_provenance_error(sample))

    def test_optional_phase_diagnostics_do_not_block_base_trace_neutrality(self) -> None:
        reference = trace()
        candidate = trace()
        candidate["events"][0]["engineStep2Phases"] = [
            {"phase": "fwdAcceleration", "values": [1.0]}]
        self.assertIsNone(first_physics_difference(reference, candidate))

    def test_phase_diagnostics_are_compared_when_both_traces_have_them(self) -> None:
        reference = trace()
        candidate = trace()
        reference["events"][0]["engineStep2Phases"] = [
            {"phase": "fwdAcceleration", "values": [1.0]}]
        candidate["events"][0]["engineStep2Phases"] = [
            {"phase": "fwdAcceleration", "values": [1.0000000000000002]}]
        difference = first_physics_difference(reference, candidate)
        self.assertEqual(
            difference,
            ("events[0].engineStep2Phases[0].values[0]", 1.0,
             1.0000000000000002))


if __name__ == "__main__":
    unittest.main()
