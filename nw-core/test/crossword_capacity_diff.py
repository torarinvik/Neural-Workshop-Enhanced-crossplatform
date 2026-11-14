#!/usr/bin/env python3
"""Check that the lexicon can index a full-band-sized input."""
import subprocess
import sys

result = subprocess.run([sys.argv[1]], check=True, capture_output=True, text=True)
if result.stdout.strip() != "capacity-ok":
    raise SystemExit(f"unexpected capacity sweep output: {result.stdout!r}")
print("PASS: 1 cases identical")
