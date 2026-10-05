#!/usr/bin/env bash
# Replay a real feedback-steered WASM held-input trace in the original Python
# MuJoCo Simulation and compare every frame, state transition, and result row.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${NEURAL_WORKSHOP_SOURCE_ROOT:-$ROOT/../../../Python Projects/neural-workshop-enhanced}"
if [[ -x "$SOURCE_ROOT/.venv/bin/python3" ]]; then
    DEFAULT_REFERENCE_PYTHON="$SOURCE_ROOT/.venv/bin/python3"
else
    DEFAULT_REFERENCE_PYTHON="$ROOT/build/marble-oracle-venv/bin/python"
fi
REFERENCE_PYTHON="${NW_MARBLE_REFERENCE_PYTHON:-$DEFAULT_REFERENCE_PYTHON}"

if [[ ! -x "$REFERENCE_PYTHON" ]]; then
    echo "missing Marble reference Python: $REFERENCE_PYTHON" >&2
    echo "Set NW_MARBLE_REFERENCE_PYTHON to Python with MuJoCo 3.12.0 installed." >&2
    exit 2
fi
if [[ ! -f "$SOURCE_ROOT/neural_workshop/marblemaze.py" ]]; then
    echo "missing original Neural Workshop source: $SOURCE_ROOT" >&2
    echo "Set NEURAL_WORKSHOP_SOURCE_ROOT to the reference checkout." >&2
    exit 2
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/marble-source-play-parity.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM HUP
PROVENANCE_OUTPUT="${NW_MARBLE_PROVENANCE_JSON:-$WORK/provenance.json}"

NW_MARBLE_PLAY_CASE="${NW_MARBLE_PLAY_CASE:-1:17}" \
NW_MARBLE_PLAY_TRACE_PATH="$WORK/trace.json" \
    node "$ROOT/test/marble_generated_play_session_test.mjs"
"$REFERENCE_PYTHON" "$ROOT/test/marble_source_play_trace.py" \
    --source-root "$SOURCE_ROOT" --trace "$WORK/trace.json" \
    --require-maintained-browser-runtime \
    --provenance-json "$PROVENANCE_OUTPUT"
