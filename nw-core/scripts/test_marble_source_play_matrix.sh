#!/usr/bin/env bash
# Strict per-frame, contact, and result parity against the original Simulation
# for all generated held-input boards. Outcome-only replay is not acceptance.
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
    exit 2
fi
if [[ ! -f "$SOURCE_ROOT/neural_workshop/marblemaze.py" ]]; then
    echo "missing original Neural Workshop source: $SOURCE_ROOT" >&2
    exit 2
fi
EVIDENCE_DIR="${NW_MARBLE_PLAY_EVIDENCE_DIR:-}"
if [[ -n "$EVIDENCE_DIR" && -e "$EVIDENCE_DIR" ]]; then
    echo "evidence destination already exists: $EVIDENCE_DIR" >&2
    exit 2
fi

TRACE_BATCHES="${NW_MARBLE_PLAY_TRACE_BATCHES:-4}"
if [[ ! "$TRACE_BATCHES" =~ ^[1-9][0-9]*$ ]] || (( TRACE_BATCHES > 80 )); then
    echo "NW_MARBLE_PLAY_TRACE_BATCHES must be an integer from 1 to 80" >&2
    exit 2
fi
WORK="$(mktemp -d "${TMPDIR:-/tmp}/marble-source-play-matrix.XXXXXX")"
matrix_passed=0
cleanup_matrix() {
    if [[ "$matrix_passed" == 1 ]]; then
        rm -rf "$WORK"
    else
        echo "Incomplete/failed matrix evidence retained at: $WORK" >&2
    fi
}
trap cleanup_matrix EXIT
mkdir -p "$WORK/traces"
for ((batch = 0; batch < TRACE_BATCHES; batch++)); do
    echo "Generating Marble trace batch $((batch + 1))/$TRACE_BATCHES..."
    NW_MARBLE_PLAY_TRACE_CONTACTS=1 \
    NW_MARBLE_PLAY_TRACE_DIR="$WORK/traces" \
    NW_MARBLE_PLAY_TRACE_BATCH_INDEX="$batch" \
    NW_MARBLE_PLAY_TRACE_BATCH_COUNT="$TRACE_BATCHES" \
        node "$ROOT/test/marble_generated_play_session_test.mjs"
done
echo "Comparing complete generated Marble trajectories with original Python source..."

if ! "$REFERENCE_PYTHON" "$ROOT/test/marble_source_matrix_replay.py" \
    "$WORK/traces" --source-root "$SOURCE_ROOT" --verify-runtime-files \
    > "$WORK/source-replay.log" 2>&1; then
    tail -n 25 "$WORK/source-replay.log" >&2
    exit 1
fi
if [[ -n "$EVIDENCE_DIR" ]]; then
    if [[ -e "$EVIDENCE_DIR" ]]; then
        echo "evidence destination appeared during the run: $EVIDENCE_DIR" >&2
        exit 2
    fi
    mkdir -p "$EVIDENCE_DIR"
    cp -a "$WORK/traces" "$EVIDENCE_DIR/traces"
    cp "$WORK/source-replay.log" "$EVIDENCE_DIR/source-replay.log"
    echo "Preserved source-play evidence at: $EVIDENCE_DIR"
fi
matrix_passed=1
echo "PASS: strict original Python Marble per-frame/contact/result parity (80 generated boards)"
