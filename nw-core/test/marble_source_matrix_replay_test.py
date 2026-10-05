"""Fail-closed acceptance checks for complete source matrix replay."""
from subprocess import CompletedProcess
import unittest
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from marble_source_matrix_replay import replay_passed, validate_adapter_identity, verify_runtime_files


class ReplayAcceptanceTest(unittest.TestCase):
    def test_runtime_bytes_must_match(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            def identity(name):
                path = root / name
                path.write_bytes(b"fixture")
                return dict(path=str(path), sha256=hashlib.sha256(b"fixture").hexdigest())
            engine_js, engine_wasm = identity("mujoco.js"), identity("mujoco.wasm")
            provenance = dict(adapterFiles=[identity(name) for name in
                ("marble-maze-mujoco.js", "marble-maze.js", "python-hypot.js")],
                coreWasm=identity("core.wasm"), traceHarness=identity("harness.mjs"),
                mujoco=dict(jsPath=engine_js["path"], jsSha256=engine_js["sha256"],
                            wasmPath=engine_wasm["path"], wasmSha256=engine_wasm["sha256"]))
            verify_runtime_files(provenance)
            Path(engine_wasm["path"]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed since capture"):
                verify_runtime_files(provenance)
            Path(engine_wasm["path"]).unlink()
            with self.assertRaises(OSError):
                verify_runtime_files(provenance)

    def test_adapter_identity_required(self):
        with self.assertRaises(ValueError):
            validate_adapter_identity({})

    def test_adapter_identity(self):
        rows = [dict(path="/runtime/" + name, sha256="a"*64) for name in
                ("marble-maze-mujoco.js", "marble-maze.js", "python-hypot.js")]
        validate_adapter_identity(dict(adapterFiles=rows))
        rows[2]["sha256"] = "not-a-hash"
        with self.assertRaises(ValueError):
            validate_adapter_identity(dict(adapterFiles=rows))

    def test_positive_audit_required(self):
        self.assertFalse(replay_passed(CompletedProcess([], 0, "", "")))
        self.assertFalse(replay_passed(CompletedProcess([], 0, "Stopped after diagnostic event", "")))

    def test_nonzero_rejected(self):
        self.assertFalse(replay_passed(CompletedProcess(
            [], 1, "PASS: original Python Marble Simulation replayed 640 events", "")))

    def test_conflicting_verdict_rejected(self):
        self.assertFalse(replay_passed(CompletedProcess(
            [], 0, "FAIL: mismatch\nPASS: original Python Marble Simulation replayed 640 events", "")))

    def test_completed_replay(self):
        self.assertTrue(replay_passed(CompletedProcess(
            [], 0, "PASS: original Python Marble Simulation replayed 640 events", "")))


if __name__ == "__main__":
    unittest.main()
