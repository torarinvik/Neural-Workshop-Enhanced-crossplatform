#!/usr/bin/env python3
"""Hash a compiler checkout's tracked edits and non-ignored untracked files."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def generated_probe_path(raw_path: bytes) -> bool:
    """Return whether a compiler-emitted formatting probe is ephemeral.

    Stage1's formatting self-checks materialize these fixtures under the
    compiler checkout while a build is running. They are inputs to neither
    the compiler product nor the port, so their mtimes/content must not make a
    quiescent-build fingerprint change.
    """
    path = Path(os.fsdecode(raw_path))
    name = path.name
    return name == "fmt_probe.elisa" or (
        name.startswith("fmt_") and name.endswith("_probe.elisa")
    )


def filtered_status(status: bytes) -> bytes:
    records = []
    for record in status.split(b"\0"):
        if not record:
            continue
        text = os.fsdecode(record)
        path_text = text[3:].split("\t", 1)[-1] if len(text) >= 3 else text
        if generated_probe_path(os.fsencode(path_text)):
            continue
        records.append(record)
    return b"\0".join(records) + (b"\0" if records else b"")


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
    status = filtered_status(git_bytes(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
    diff = git_bytes(root, "diff", "--binary", "HEAD", "--no-ext-diff", "--no-renames", "--")
    digest.update(b"status\0")
    digest.update(status)
    digest.update(b"diff\0")
    digest.update(diff)

    untracked = git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw_path in sorted(path for path in untracked.split(b"\0")
                           if path and not generated_probe_path(path)):
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
