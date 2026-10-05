#!/usr/bin/env python3
"""Mutation-focused checks for the differential verdict validator."""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_result.py"
SPEC = importlib.util.spec_from_file_location("check_result", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
check_result = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_result)


class CheckResultTests(unittest.TestCase):
    def test_counted_pass_requires_successful_process_exit(self):
        result = check_result.validate(0, "warning on a previous line\nPASS: 12 cases identical\n")
        self.assertTrue(result["passed"])
        self.assertEqual(result["case_count"], 12)

    def test_checker_that_did_not_run_is_not_a_pass(self):
        result = check_result.validate(-1, "")
        self.assertFalse(result["passed"])
        self.assertEqual(result["error"], "checker was not run")

    def test_pass_text_cannot_hide_nonzero_exit(self):
        result = check_result.validate(7, "PASS: 12 cases identical\n")
        self.assertFalse(result["passed"])
        self.assertEqual(result["error"], "checker exited with status 7")

    def test_real_process_printing_pass_then_exiting_nonzero_fails(self):
        process = subprocess.run(
            [sys.executable, "-c",
             "import sys; print('PASS: 12 cases identical', flush=True); sys.exit(7)"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 7)
        self.assertEqual(process.stdout, "PASS: 12 cases identical\n")
        result = check_result.validate(process.returncode, process.stdout)
        self.assertFalse(result["passed"])
        self.assertEqual(result["case_count"], 12)
        self.assertEqual(result["error"], "checker exited with status 7")

    def test_zero_cases_is_not_a_pass(self):
        result = check_result.validate(0, "PASS: 0 cases identical\n")
        self.assertFalse(result["passed"])
        self.assertEqual(result["error"], "checker reported zero cases")

    def test_missing_or_unrecognized_verdict_fails_closed(self):
        for stdout in ("", "PASS: no cases found\n", "PASS: 4 cases\nwarning after result\n"):
            with self.subTest(stdout=stdout):
                self.assertFalse(check_result.validate(0, stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
