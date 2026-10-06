#!/usr/bin/env python3
"""Keep Elisa source includes bound to the selected latest runtime checkout.

The port used to carry relative includes into the historical Elisa-core
checkout.  That made Stage0 appear healthy while Stage1 compiled a different
runtime (or failed when the old checkout was unavailable).  Every runtime
include in the port must resolve from its owning source file into the selected
latest Elisa-compiler checkout.
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path


INCLUDE_RE = re.compile(r"^\s*include\s+\"([^\"]*elisacore_std/[^\"]+)\"")
ROOT_MARKER = "@ELISA_STAGE1_ROOT@"


class RuntimeIncludeProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = Path(__file__).resolve().parents[1]
        cls.stage1_root = Path(
            os.environ.get("ELISA_STAGE1_ROOT", str(cls.core.parent.parent / "Elisa-compiler-latest"))
        ).resolve()

    def test_all_port_runtime_includes_resolve_into_latest_checkout(self) -> None:
        failures: list[str] = []
        sources = [
            path
            for directory in (self.core / "src", self.core / "test")
            for path in directory.rglob("*.elisa")
        ]
        for source in sorted(sources):
            for line_number, line in enumerate(
                source.read_text(encoding="utf-8").splitlines(), start=1
            ):
                match = INCLUDE_RE.match(line)
                if match is None:
                    continue
                include = match.group(1)
                expected_prefix = f"{ROOT_MARKER}/elisacore_std/"
                if not include.startswith(expected_prefix):
                    failures.append(
                        f"{source}:{line_number}: runtime include must use the selected-root marker: {include}"
                    )
                    continue
                relative = include[len(f"{ROOT_MARKER}/"):]
                target = (self.stage1_root / relative).resolve()
                try:
                    target.relative_to(self.stage1_root / "elisacore_std")
                except ValueError:
                    failures.append(
                        f"{source}:{line_number}: runtime include escapes latest checkout: {include}"
                    )
                    continue
                if not target.is_file():
                    failures.append(
                        f"{source}:{line_number}: runtime include does not exist: {target}"
                    )
        self.assertEqual([], failures, "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
