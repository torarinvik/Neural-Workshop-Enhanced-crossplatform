#!/usr/bin/env python3
"""Hash a compiler checkout's tracked edits and non-ignored untracked files."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "core.hooksPath=/dev/null", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def fingerprint(root: Path) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    status = git_bytes(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    diff = git_bytes(root, "diff", "--binary", "HEAD", "--no-ext-diff", "--no-renames", "--")
    digest.update(b"status\0")
    digest.update(status)
    digest.update(b"diff\0")
    digest.update(diff)

    untracked = git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw_path in sorted(path for path in untracked.split(b"\0") if path):
        path = root / os.fsdecode(raw_path)
        digest.update(b"untracked\0")
        digest.update(raw_path)
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(b"other\0")
    return digest.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: source_fingerprint.py REPOSITORY")
    print(fingerprint(Path(sys.argv[1])))
