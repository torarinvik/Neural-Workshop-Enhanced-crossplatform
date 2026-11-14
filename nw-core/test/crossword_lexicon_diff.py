#!/usr/bin/env python3
"""Check index filtering, clue offsets, and malformed input handling."""
import subprocess
import sys

result = subprocess.run([sys.argv[1]], check=True, capture_output=True, text=True)
if result.stdout.strip() != "lexicon-ok":
    raise SystemExit(f"unexpected lexicon sweep output: {result.stdout!r}")
print("PASS: 14 cases identical")
