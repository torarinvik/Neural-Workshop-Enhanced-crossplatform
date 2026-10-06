#!/usr/bin/env python3
"""Resolve selected Elisa checkout markers in export-source runtime includes."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT_MARKER = "@ELISA_STAGE1_ROOT@"
INCLUDE_RE = re.compile(r'^include "([^"]+)"$', re.MULTILINE)


def prepare(source_path: Path, output_path: Path, compiler_root: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    if ROOT_MARKER not in source:
        raise ValueError(f"no {ROOT_MARKER} runtime include markers in {source_path}")

    runtime_root = (compiler_root / "elisacore_std").resolve(strict=True)
    rendered = source.replace(ROOT_MARKER, compiler_root.resolve(strict=True).as_posix())
    if ROOT_MARKER in rendered:
        raise ValueError(f"unresolved {ROOT_MARKER} marker in {source_path}")

    for include in INCLUDE_RE.findall(rendered):
        if "/elisacore_std/" not in include:
            continue
        include_path = Path(include)
        if not include_path.is_absolute() or not include_path.is_file():
            raise ValueError(f"selected compiler runtime include is missing: {include}")
        if runtime_root not in include_path.resolve().parents:
            raise ValueError(f"runtime include escaped selected compiler tree: {include}")

    output_path.write_text(rendered, encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        raise SystemExit("usage: prepare_wasm_exports.py SOURCE OUTPUT ELISA_STAGE1_ROOT")
    try:
        prepare(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    except (OSError, ValueError) as error:
        print(f"prepare_wasm_exports.py: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
