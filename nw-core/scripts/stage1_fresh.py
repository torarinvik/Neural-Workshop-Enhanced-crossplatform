#!/usr/bin/env python3
"""Reject a Stage1 product older than changed compiler source content.

Filesystem mtimes are not a reliable source boundary on the shared compiler
checkout: tracked files can be touched by another build without changing
their bytes. Git content state is authoritative for those files.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def generated_probe(path: Path) -> bool:
    name = path.name
    return name == "fmt_probe.elisa" or (name.startswith("fmt_") and name.endswith("_probe.elisa"))


def tracked(root: Path, relative: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def changed(root: Path, relative: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", relative],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode != 0


def committed_head_is_newer(root: Path, product: Path) -> bool:
    """Reject a product predating the checkout's current committed HEAD.

    Git checkout/commit operations can preserve or backdate source mtimes, so a
    product can outlive every source file even though a newer committed compiler
    is selected.  The commit timestamp is only a conservative additional guard;
    the normal per-file mtime/content checks remain below.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%ct", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return False
    try:
        head_ns = int(result.stdout.strip()) * 1_000_000_000
        return head_ns > product.stat().st_mtime_ns
    except (ValueError, OSError):
        return False


def stale_source(root: Path, product: Path) -> Path | None:
    if committed_head_is_newer(root, product):
        # A synthetic marker keeps the existing caller contract while making
        # the diagnostic explicit enough to trigger a reseed.
        return root / ".git/HEAD"
    for base_name in ("src", "elisacore_std"):
        base = root / base_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in (".elisa", ".elisai"):
                continue
            if generated_probe(path) or path.stat().st_mtime_ns <= product.stat().st_mtime_ns:
                continue
            relative = path.relative_to(root).as_posix()
            if not tracked(root, relative) or changed(root, relative):
                return path
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit("usage: stage1_fresh.py COMPILER_ROOT PRODUCT")
    root, product = Path(argv[1]).resolve(), Path(argv[2]).resolve()
    stale = stale_source(root, product)
    if stale is None:
        return 0
    print(stale)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
