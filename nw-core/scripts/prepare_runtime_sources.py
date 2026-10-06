#!/usr/bin/env python3
"""Materialize src/ and test/ with runtime includes pinned to one compiler tree.

The source tree uses @ELISA_STAGE1_ROOT@ markers so the Stage0 and Stage1
differential builds can compile the exact same selected Elisa runtime without
hard-coding a sibling-checkout directory into repository sources.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


ROOT_MARKER = "@ELISA_STAGE1_ROOT@"
INCLUDE_RE = re.compile(r'^(\s*include\s+")([^"]+)(".*)$', re.MULTILINE)


def prepare(source_root: Path, output_root: Path, compiler_root: Path) -> int:
    source_root = source_root.resolve(strict=True)
    compiler_root = compiler_root.resolve(strict=True)
    runtime_root = (compiler_root / "elisacore_std").resolve(strict=True)
    if output_root.exists():
        raise FileExistsError(f"output tree already exists: {output_root}")

    for name in ("src", "test"):
        source = source_root / name
        if not source.is_dir():
            raise FileNotFoundError(f"source tree is missing {source}")
        shutil.copytree(source, output_root / name)

    replacements = 0
    for source in sorted(output_root.rglob("*.elisa")):
        text = source.read_text(encoding="utf-8")

        def resolve_include(match: re.Match[str]) -> str:
            nonlocal replacements
            include = match.group(2)
            if "elisacore_std/" not in include:
                if ROOT_MARKER in include:
                    raise ValueError(f"runtime marker is not a runtime include: {source}: {include}")
                return match.group(0)
            if not include.startswith(f"{ROOT_MARKER}/elisacore_std/"):
                raise ValueError(f"runtime include is not selected-root-relative: {source}: {include}")

            relative = include[len(f"{ROOT_MARKER}/"):]
            target = (compiler_root / relative).resolve(strict=True)
            try:
                target.relative_to(runtime_root)
            except ValueError as error:
                raise ValueError(f"runtime include escapes selected compiler tree: {source}: {include}") from error
            if not target.is_file():
                raise ValueError(f"selected compiler runtime include is not a file: {source}: {target}")
            replacements += 1
            return f'{match.group(1)}{target.as_posix()}{match.group(3)}'

        rendered = INCLUDE_RE.sub(resolve_include, text)
        if ROOT_MARKER in rendered:
            raise ValueError(f"unresolved runtime marker in {source}")
        source.write_text(rendered, encoding="utf-8")

    return replacements


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        raise SystemExit("usage: prepare_runtime_sources.py NW_CORE_ROOT OUTPUT_ROOT ELISA_STAGE1_ROOT")
    try:
        count = prepare(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    except (OSError, ValueError) as error:
        print(f"prepare_runtime_sources.py: {error}", file=sys.stderr)
        return 2
    print(f"prepared Elisa source tree with {count} selected-runtime includes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
