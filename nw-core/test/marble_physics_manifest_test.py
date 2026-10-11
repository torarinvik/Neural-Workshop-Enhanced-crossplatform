"""Keep the live Marble artifact alias aligned with promoted provenance."""

import hashlib
import json
from pathlib import Path
import sys
import unittest


NW_CORE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = NW_CORE_ROOT.parent
MANIFEST_PATH = NW_CORE_ROOT / "docs" / "marble-physics-manifest.json"
sys.path.insert(0, str(NW_CORE_ROOT / "test"))
from marble_source_play_trace import current_promoted_artifact, maintained_core_identity


class MarblePhysicsManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text())
        cls.clearance = cls.manifest["holeWallVisualClearanceCurrentOct7"]
        cls.previous_clearance = cls.manifest["holeWallVisualClearanceCurrentOct5"]
        cls.current = cls.manifest["currentArtifact"]

    def test_current_artifact_alias_matches_latest_promotion(self):
        promoted = self.clearance["promotedArtifact"]
        gate = self.clearance["latestStage1ArtifactGate"]
        artifact = self.current["artifact"]
        wasm_path = (PROJECT_ROOT / promoted["path"]).resolve()

        self.assertEqual(
            (NW_CORE_ROOT / artifact["wasm"]).resolve(), wasm_path)
        self.assertEqual(artifact["wasmSha256"], promoted["sha256"])
        self.assertEqual(artifact["wasmSha256"], gate["wasmSha256"])
        self.assertEqual(artifact["wasmBytes"], promoted["bytes"])
        self.assertEqual(artifact["wasmBytes"], gate["wasmBytes"])
        self.assertEqual(
            artifact["linkedObjectSha256"], promoted["objectSha256"])

        self.assertEqual(hashlib.sha256(wasm_path.read_bytes()).hexdigest(),
                         promoted["sha256"])
        self.assertEqual(wasm_path.stat().st_size, promoted["bytes"])
        object_path = wasm_path.with_name("nwcore_wasm.o")
        self.assertEqual(hashlib.sha256(object_path.read_bytes()).hexdigest(),
                         promoted["objectSha256"])

    def test_runtime_guard_selects_promotion_by_current_artifact_identity(self):
        self.assertEqual(current_promoted_artifact(self.manifest),
                         self.clearance["promotedArtifact"])
        duplicate = dict(self.manifest)
        duplicate["holeWallVisualClearanceCurrentDuplicate"] = self.clearance
        with self.assertRaisesRegex(ValueError, "exactly one"):
            current_promoted_artifact(duplicate)

    def test_candidate_core_identity_is_exact_and_does_not_promote(self):
        import tempfile

        promoted_before = current_promoted_artifact(self.manifest)
        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate = Path(temporary_directory) / "candidate.wasm"
            candidate.write_bytes(b"isolated candidate wasm")
            actual_path, actual_hash = maintained_core_identity(
                self.manifest, PROJECT_ROOT, candidate)

            self.assertEqual(actual_path, candidate.resolve())
            self.assertEqual(actual_hash,
                             hashlib.sha256(candidate.read_bytes()).hexdigest())
            self.assertEqual(current_promoted_artifact(self.manifest),
                             promoted_before)

    def test_current_compiler_alias_matches_verified_stage1_inputs(self):
        stage1 = self.clearance["latestStage1"]
        current = self.current["compiler"]

        self.assertEqual(current["head"], stage1["selectedCommit"])
        self.assertEqual(current["originMainAtBoundary"],
                         stage1["publishedMainHead"])
        self.assertEqual(current["stage1ProductSha256"],
                         stage1["productSha256"])
        self.assertEqual(current["seedStage0Head"], stage1["stage0Commit"])
        self.assertEqual(current["seedStage0Sha256"],
                         stage1["stage0ProductSha256"])

    def test_strict_source_replay_receipt_is_for_promoted_artifact(self):
        replay = self.current["strictSourcePlayMatrixOct7"]
        self.assertEqual(replay["artifactSha256"],
                         self.clearance["promotedArtifact"]["sha256"])
        self.assertEqual(replay["cases"], 80)
        self.assertEqual(replay["failedCases"], [])
        self.assertEqual(replay["runtimeFilesVerified"], True)

    def test_previous_canonical_replay_remains_exact_historical_evidence(self):
        replay = self.current["artifact"]["latestClearanceArtifactVerificationOct5"][
            "currentCanonicalReplayOct5"]
        promoted = self.previous_clearance["promotedArtifact"]
        trace_path = NW_CORE_ROOT / replay["trace"]
        provenance_path = NW_CORE_ROOT / replay["provenance"]

        self.assertEqual(replay["status"], "pass")
        self.assertEqual(replay["artifactSha256"], promoted["sha256"])
        self.assertEqual(replay["events"], 7601)
        self.assertEqual(replay["boardSeed"], 827307999)
        self.assertEqual(replay["maximumNumericDelta"], 0)
        self.assertEqual(replay["contactsDiscreteStatesAndResult"], "exact")
        self.assertEqual(hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                         replay["traceSha256"])
        self.assertEqual(
            hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
            replay["provenanceSha256"])

        trace = json.loads(trace_path.read_text())
        self.assertEqual(len(trace["events"]), replay["events"])
        self.assertEqual(trace["boardSeed"], replay["boardSeed"])
        self.assertEqual(trace["runtimeProvenance"]["coreWasm"]["sha256"],
                         promoted["sha256"])

    def test_current_canonical_replay_is_exact_for_current_artifact(self):
        replay = self.current["artifact"]["latestClearanceArtifactVerificationOct7"][
            "canonicalReplay"]
        promoted = self.clearance["promotedArtifact"]
        trace_path = NW_CORE_ROOT / replay["trace"]
        provenance_path = NW_CORE_ROOT / replay["provenance"]

        self.assertEqual(replay["status"], "pass")
        self.assertEqual(replay["artifactSha256"], promoted["sha256"])
        self.assertEqual(replay["events"], 7601)
        self.assertEqual(replay["boardSeed"], 827307999)
        self.assertEqual(replay["maximumNumericDelta"], 0)
        self.assertEqual(replay["contactsDiscreteStatesAndResult"], "exact")
        self.assertEqual(hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                         replay["traceSha256"])
        self.assertEqual(
            hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
            replay["provenanceSha256"])

        trace = json.loads(trace_path.read_text())
        self.assertEqual(len(trace["events"]), replay["events"])
        self.assertEqual(trace["boardSeed"], replay["boardSeed"])
        self.assertEqual(trace["result"], replay["result"])
        self.assertEqual(trace["runtimeProvenance"]["coreWasm"]["sha256"],
                         promoted["sha256"])

    def test_current_qualification_receipt_hash_matches_file(self):
        gate = self.clearance["latestStage1ArtifactGate"]
        receipt_path = PROJECT_ROOT / gate["qualificationReceipt"]
        self.assertEqual(hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                         gate["qualificationReceiptSha256"])

    def test_current_visual_matrix_is_exact_and_pixel_acceptance_stays_pending(self):
        visual = self.clearance["latestStage1VisualMatrixOct7"]
        receipt_path = NW_CORE_ROOT / visual["receipt"]
        receipt = json.loads(receipt_path.read_text())
        audit_path = NW_CORE_ROOT / visual["inventoryAudit"]
        audit = json.loads(audit_path.read_text())
        promoted = self.clearance["promotedArtifact"]

        self.assertEqual(hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                         visual["receiptSha256"])
        self.assertEqual(receipt["artifact"]["sha256"], promoted["sha256"])
        self.assertEqual(receipt["requestedMatrixPairs"], 10)
        self.assertEqual(receipt["requestedMatrixSynchronizationFailures"], 0)
        self.assertFalse(receipt["accepted"])
        self.assertFalse(visual["pixelAcceptance"])
        review_sheet = NW_CORE_ROOT / receipt["reviewSheet"]["path"]
        self.assertEqual(hashlib.sha256(review_sheet.read_bytes()).hexdigest(),
                         receipt["reviewSheet"]["sha256"])
        self.assertEqual(visual["reviewSheetSha256"],
                         receipt["reviewSheet"]["sha256"])
        self.assertEqual(len(receipt["pairs"]), 10)
        self.assertEqual(audit["failures"], [])
        self.assertFalse(audit["accepted"])
        self.assertEqual(len(audit["pairs"]), visual["inventoryListedPairs"])
        self.assertEqual(hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                         visual["inventoryAuditSha256"])
        self.assertEqual(
            self.current["artifact"]["latestClearanceArtifactVerificationOct7"][
                "visualMatrix"], visual)
        for pair in receipt["pairs"]:
            self.assertEqual(pair["synchronization"]["failures"], [])
            for key, expected_hash in pair["hashes"].items():
                file_key = {
                    "sourcePng": "source",
                    "sourceMetadata": "sourceMetadata",
                    "browserPng": "browser",
                    "browserDebug": "browserDebug",
                    "browserMetadata": "browserMetadata",
                    "comparison": "comparison",
                }[key]
                file_path = NW_CORE_ROOT / pair[file_key]
                self.assertEqual(hashlib.sha256(file_path.read_bytes()).hexdigest(),
                                 expected_hash, pair["id"] + ":" + key)

    def test_current_clearance_is_six_mm_in_source_and_port_sweeps(self):
        self.assertEqual(self.clearance["geometry"]["holeWallClearanceMetres"],
                         0.006)
        self.assertEqual(
            self.clearance["regression"]["independentSourceSweep"]["boards"],
            8000)
        self.assertAlmostEqual(
            self.clearance["regression"]["boardAbi"][
                "minimumMeasuredHoleClearanceMm"], 6.0)
        self.assertAlmostEqual(
            self.clearance["regression"]["boardAbi"][
                "minimumMeasuredCollarClearanceMm"], 6.0)


if __name__ == "__main__":
    unittest.main()
