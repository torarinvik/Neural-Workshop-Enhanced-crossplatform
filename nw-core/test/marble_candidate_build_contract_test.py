"""Candidate builder must reject unsafe destinations before tool/build work."""
from pathlib import Path
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build_marble_diagnostic_candidate.sh"


class CandidateBuildContractTest(unittest.TestCase):
    def test_invalid_destinations(self):
        for arguments in ([], ["relative-output"], [str(SCRIPT.parent)], ["/", "extra"]):
            with self.subTest(arguments=arguments):
                result = subprocess.run(["/bin/bash", str(SCRIPT), *arguments],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn("must not exist", result.stderr)

    def test_syntax(self):
        result = subprocess.run(["/bin/bash", "-n", str(SCRIPT)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_inputs_retained_before_scratch_cleanup(self):
        script = SCRIPT.read_text()
        for receipt in ("candidate.patch", "upstream-commit.txt", "emscripten-version.txt",
                        "cmake-version.txt", "artifact-sha256.txt"):
            self.assertIn(receipt, script)
        self.assertLess(script.index('cp "$PATCH"'), script.index("complete=1"))


if __name__ == "__main__":
    unittest.main()
