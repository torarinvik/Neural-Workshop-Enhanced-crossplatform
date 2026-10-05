#!/usr/bin/env python3
"""Ensure compiler source fingerprints change with checkout content."""

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "source_fingerprint.py"
SPEC = importlib.util.spec_from_file_location("source_fingerprint", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
source_fingerprint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source_fingerprint)


def git(root: Path, *args: str, env: dict[str, str]) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "core.hooksPath=/dev/null", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


class SourceFingerprintTests(unittest.TestCase):
    def test_commit_worktree_and_untracked_changes_are_distinguished(self):
        with tempfile.TemporaryDirectory(prefix="nw-fingerprint-") as directory:
            root = Path(directory)
            env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }
            git(root, "init", "-q", env=env)
            (root / "compiler.go").write_text("package compiler\n")
            git(root, "add", "compiler.go", env=env)
            git(root, "commit", "-q", "-m", "baseline", env=env)
            baseline = source_fingerprint.fingerprint(root)

            (root / "compiler.go").write_text("package compiler\n// edit\n")
            edited = source_fingerprint.fingerprint(root)
            self.assertNotEqual(edited, baseline)

            (root / "compiler.go").write_text("package compiler\n")
            (root / "new.elisa").write_text("module New\n")
            untracked = source_fingerprint.fingerprint(root)
            self.assertNotEqual(untracked, baseline)
            self.assertNotEqual(untracked, edited)


if __name__ == "__main__":
    unittest.main()
