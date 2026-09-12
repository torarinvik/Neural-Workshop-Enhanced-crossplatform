#!/usr/bin/env python3
"""Validate one differential checker result and write a machine-readable record."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PASS_LINE = re.compile(r"^PASS:\s+([0-9]+)(?:\s|$)")


def validate(returncode: int, stdout: str) -> dict[str, object]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    verdict = lines[-1] if lines else ""
    match = PASS_LINE.match(verdict)
    cases = int(match.group(1)) if match else None

    if returncode < 0:
        error = "checker was not run"
    elif returncode != 0:
        error = f"checker exited with status {returncode}"
    elif match is None:
        error = "checker did not end with a counted PASS line"
    elif cases == 0:
        error = "checker reported zero cases"
    else:
        error = None

    return {
        "checker_exit": returncode,
        "case_count": cases,
        "verdict": verdict,
        "passed": error is None,
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--checker-exit", type=int, required=True)
    parser.add_argument("--stdout", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--compile-log", type=Path, required=True)
    parser.add_argument("--link-log", type=Path, required=True)
    parser.add_argument("--compile-exit", type=int, default=0)
    parser.add_argument("--link-exit", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checked = validate(args.checker_exit, args.stdout.read_text(errors="replace"))
    if args.compile_exit != 0:
        checked["passed"] = False
        checked["error"] = f"compiler exited with status {args.compile_exit}"
    elif args.link_exit != 0:
        checked["passed"] = False
        checked["error"] = f"linker exited with status {args.link_exit}"

    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "suite": args.suite,
        "stage": args.stage,
        "compile_exit": args.compile_exit if args.compile_exit >= 0 else None,
        "link_exit": args.link_exit if args.link_exit >= 0 else None,
        **checked,
        "checker_exit": checked["checker_exit"] if checked["checker_exit"] >= 0 else None,
        "stdout_log": str(args.stdout),
        "stderr_log": str(args.stderr),
        "compile_log": str(args.compile_log),
        "link_log": str(args.link_log),
    }
    args.output.write_text(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
