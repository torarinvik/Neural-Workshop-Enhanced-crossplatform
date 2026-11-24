#!/usr/bin/env python3
"""Tests selected-runtime source-tree materialization and path containment."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_runtime_sources import prepare  # noqa: E402


class PrepareRuntimeSourcesTest(unittest.TestCase):
    def make_tree(self, base: Path, include: str) -> tuple[Path, Path, Path]:
        project = base / "port source"
        (project / "src" / "tasks").mkdir(parents=True)
        (project / "test").mkdir()
        (project / "src" / "tasks" / "local.elisa").write_text(
            "def helper() -> i64: return 7\n", encoding="utf-8"
        )
        (project / "test" / "case.elisa").write_text(
            f'include "{include}"\ninclude "../src/tasks/local.elisa"\n',
            encoding="utf-8",
        )
        compiler = base / "selected compiler root"
        runtime = compiler / "elisacore_std"
        runtime.mkdir(parents=True)
        (runtime / "elisacore_runtime.elisa").write_text(
            "# selected runtime\n", encoding="utf-8"
        )
        return project, base / "materialized", compiler

    def test_materializes_selected_runtime_and_preserves_local_include_paths(self):
        with tempfile.TemporaryDirectory(prefix="runtime source tree ") as temporary:
            project, output, compiler = self.make_tree(
                Path(temporary),
                "@ELISA_STAGE1_ROOT@/elisacore_std/elisacore_runtime.elisa",
            )
            wasm = project / "src" / "wasm"
            wasm.mkdir()
            transient = wasm / "wasm_exports_stage1.abcdef.elisa"
            transient.write_text(f'include "{compiler}/elisacore_std/elisacore_runtime.elisa"\n', encoding="utf-8")
            count = prepare(project, output, compiler)
            self.assertFalse((output / "src" / "wasm" / transient.name).exists())

            self.assertEqual(1, count)
            source = (output / "test" / "case.elisa").read_text(encoding="utf-8")
            self.assertIn(
                str(compiler / "elisacore_std" / "elisacore_runtime.elisa"), source
            )
            self.assertIn('include "../src/tasks/local.elisa"', source)
            self.assertIn("@ELISA_STAGE1_ROOT@", (project / "test" / "case.elisa").read_text(encoding="utf-8"))

    def test_rejects_legacy_checkout_and_missing_runtime(self):
        for include, expected in (
            ("../../../Elisa-compiler-latest/elisacore_std/elisacore_runtime.elisa", "selected-root-relative"),
            ("@ELISA_STAGE1_ROOT@/elisacore_std/missing.elisa", "No such file"),
        ):
            with self.subTest(include=include), tempfile.TemporaryDirectory() as temporary:
                project, output, compiler = self.make_tree(Path(temporary), include)
                with self.assertRaisesRegex((ValueError, FileNotFoundError), expected):
                    prepare(project, output, compiler)


if __name__ == "__main__":
    unittest.main()
