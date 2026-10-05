"""Reject known Marble diagnostic instrumentation in a proposed shipping patch.

This is a negative guard only: passing does not prove arithmetic parity,
minimality, portability, or visual acceptance. Inspect added lines, not removed
diagnostics, so a cleanup patch can legitimately delete trace instrumentation.
"""
import argparse
import json
from pathlib import Path
import re


DIAGNOSTIC = re.compile(
    r"\b(?:(?:marble|mj|mju|mjd)_[A-Za-z0-9_]*(?:trace|probe)[A-Za-z0-9_]*"
    r"|marble[A-Z][A-Za-z0-9]*(?:Trace|Probe)[A-Za-z0-9]*"
    r"|marbleRecord[A-Za-z0-9_]+|TRACE_VALUES)\b")


def diagnostic_additions(patch):
    findings = []
    current = None
    for number, line in enumerate(patch.splitlines(), 1):
        if line.startswith("+++ b/"):
            current = line[6:]
            if current.startswith("src/engine/marble_") and "trace" in current:
                findings.append(dict(line=number, file=current, symbol="diagnostic header"))
        elif line.startswith("+") and not line.startswith("+++"):
            for symbol in sorted(set(DIAGNOSTIC.findall(line[1:]))):
                findings.append(dict(line=number, file=current, symbol=symbol))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()
    findings = diagnostic_additions(args.patch.read_text())
    print(json.dumps(dict(diagnosticAdditions=findings,
                         scope="known diagnostic additions only; not shipping acceptance"), indent=2))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
