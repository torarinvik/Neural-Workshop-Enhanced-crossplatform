#!/usr/bin/env python3
"""Verify WASM runtime includes resolve to the explicitly selected compiler."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_wasm_exports import prepare  # noqa: E402


class WasmRuntimeIncludeTest(unittest.TestCase):
    def test_resolves_only_to_selected_compiler_even_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="stage1 root ") as temporary:
            base = Path(temporary)
            compiler = base / "selected Elisa compiler"
            runtime = compiler / "elisacore_std"
            runtime.mkdir(parents=True)
            (runtime / "runtime.elisa").write_text("# runtime\n", encoding="utf-8")
            source = base / "wasm_exports.elisa"
            output = base / "wasm_exports.generated.elisa"
            source.write_text(
                'include "@ELISA_STAGE1_ROOT@/elisacore_std/runtime.elisa"\n'
                'include "../local_module.elisa"\n',
                encoding="utf-8",
            )

            prepare(source, output, compiler)

            rendered = output.read_text(encoding="utf-8")
            self.assertIn(
                f'include "{compiler.resolve()}/elisacore_std/runtime.elisa"', rendered
            )
            self.assertIn('include "../local_module.elisa"', rendered)
            self.assertNotIn("@ELISA_STAGE1_ROOT@", rendered)

    def test_rejects_missing_runtime_modules(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            compiler = base / "compiler"
            (compiler / "elisacore_std").mkdir(parents=True)
            source = base / "wasm_exports.elisa"
            source.write_text(
                'include "@ELISA_STAGE1_ROOT@/elisacore_std/missing.elisa"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "runtime include is missing"):
                prepare(source, base / "out.elisa", compiler)

    def test_native_pymodule_uses_selected_stage1_runtime(self):
        with tempfile.TemporaryDirectory(prefix="pymodule selected stage1 ") as temporary:
            base = Path(temporary)
            compiler = base / "selected Elisa compiler"
            runtime = compiler / "elisacore_std"
            runtime.mkdir(parents=True)
            for module in (
                "elisacore_runtime.elisa",
                "elisacore_rng.elisa",
                "elisacore_math.elisa",
                "elisacore_bigint.elisa",
            ):
                (runtime / module).write_text("# selected runtime\n", encoding="utf-8")

            output = base / "pymodule_exports.generated.elisa"
            prepare(ROOT / "src" / "pymodule_exports.elisa", output, compiler)

            rendered = output.read_text(encoding="utf-8")
            for module in (
                "elisacore_runtime.elisa",
                "elisacore_rng.elisa",
                "elisacore_math.elisa",
                "elisacore_bigint.elisa",
            ):
                self.assertIn(
                    f'include "{compiler.resolve()}/elisacore_std/{module}"', rendered
                )
            self.assertNotIn("Elisa-compiler-latest", rendered)
            self.assertIn('include "scheduling.elisa"', rendered)


if __name__ == "__main__":
    unittest.main()
