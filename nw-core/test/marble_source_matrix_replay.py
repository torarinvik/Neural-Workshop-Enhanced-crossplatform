"""Strict original replay of all 80 completed generated held-play traces.

Run only after the directory-mode generator finishes. Missing cases, incomplete
event states, mixed artifacts, or any failed replay prevent matrix acceptance.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys


def replay_passed(result):
    """Exit zero alone cannot certify a comparator that omitted its audit."""
    return (result.returncode == 0 and
            any(line.startswith("PASS: original Python Marble Simulation replayed ")
                for line in result.stdout.splitlines()) and
            not any(line.startswith("FAIL:") for line in result.stdout.splitlines()))


def validate_adapter_identity(provenance):
    required = {"marble-maze-mujoco.js", "marble-maze.js", "python-hypot.js"}
    files = provenance.get("adapterFiles", [])
    names = [Path(row["path"]).name for row in files]
    if len(names) != len(required) or set(names) != required:
        raise ValueError("Complete unique adapter-file identities required")
    if any(not Path(row["path"]).is_absolute() or
           not re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", "")) for row in files):
        raise ValueError("Invalid adapter-file path or SHA-256 identity")


def verify_runtime_files(provenance):
    """Bind current qualification to actual bytes, not just recorded claims."""
    validate_adapter_identity(provenance)
    rows = list(provenance["adapterFiles"])
    rows.extend(provenance[key] for key in ("coreWasm", "traceHarness"))
    engine = provenance["mujoco"]
    rows.extend(dict(path=engine[key + "Path"], sha256=engine[key + "Sha256"])
                for key in ("js", "wasm"))
    for row in rows:
        path = Path(row["path"])
        digest = row.get("sha256", "")
        if not path.is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid runtime-file identity")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Runtime file changed since capture: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--verify-runtime-files", action="store_true",
                        help="require recorded runtime files to exist and still match their hashes")
    args = parser.parse_args()
    expected = {(rung, seed) for rung in range(1, 17)
                for seed in (0, 1, 17, 314159, 1073741823)}
    paths = sorted(args.directory.glob("*.json"))
    rows, identity = {}, None
    for path in paths:
        trace = json.loads(path.read_text())
        key = (trace["rung"], trace["runSeed"])
        if key not in expected or key in rows:
            raise ValueError(f"Unexpected/duplicate case: {path}")
        if path.name != f"{key[0]}-{key[1]}.json":
            raise ValueError(f"Filename/case mismatch: {path}")
        if not trace.get("contactDiagnostics"):
            raise ValueError(f"Contact comparisons required: {path}")
        events = trace["events"]
        if not events or any("state" not in event for event in events):
            raise ValueError(f"Incomplete event snapshots: {path}")
        provenance = trace["runtimeProvenance"]
        validate_adapter_identity(provenance)
        if identity is None:
            identity = provenance
        elif identity != provenance:
            raise ValueError(f"Mixed runtime provenance: {path}")
        rows[key] = path
    if set(rows) != expected:
        raise ValueError(f"Incomplete matrix; missing {sorted(expected-set(rows))}")
    if args.verify_runtime_files:
        verify_runtime_files(identity)
    failed = []
    comparator = Path(__file__).with_name("marble_source_play_trace.py")
    for key, path in sorted(rows.items()):
        result = subprocess.run([sys.executable, str(comparator),
                                 "--source-root", str(args.source_root),
                                 "--trace", str(path)], capture_output=True, text=True)
        print(f"CASE {key[0]}:{key[1]} exit={result.returncode}", flush=True)
        print(result.stdout, end="", flush=True)
        print(result.stderr, end="", file=sys.stderr, flush=True)
        if not replay_passed(result):
            failed.append(key)
    # A qualification run must not silently accept files changed while the
    # long original replay was executing.
    if args.verify_runtime_files:
        verify_runtime_files(identity)
    print(json.dumps(dict(cases=len(rows), failed=failed,
                          runtimeProvenance=identity,
                          runtimeFilesVerified=args.verify_runtime_files,
                          promoted=False)), flush=True)
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
