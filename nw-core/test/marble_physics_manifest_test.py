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
from marble_source_play_trace import current_promoted_artifact


class MarblePhysicsManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text())
        cls.clearance = cls.manifest["holeWallVisualClearanceCurrentOct6"]
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

    def test_runtime_guard_selects_promotion_by_current_artifact_identity(self):
        self.assertEqual(current_promoted_artifact(self.manifest),
                         self.clearance["promotedArtifact"])
        duplicate = dict(self.manifest)
        duplicate["holeWallVisualClearanceCurrentDuplicate"] = self.clearance
        with self.assertRaisesRegex(ValueError, "exactly one"):
            current_promoted_artifact(duplicate)

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
        replay = self.current["strictSourcePlayMatrixOct6"]
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
        replay = self.current["artifact"]["latestClearanceArtifactVerificationOct6"][
            "currentCanonicalReplayOct6"]
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
        self.assertEqual(trace["inputTraceReplay"]["sha256"],
                         replay["inputTraceSha256"])

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
