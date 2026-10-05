#!/usr/bin/env bash
# Compile and draw the actual native Marble 3D scene in a hidden Pyglet window.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${NEURAL_WORKSHOP_SOURCE_ROOT:-$ROOT/../../../Python Projects/neural-workshop-enhanced}"
if [[ -x "$SOURCE_ROOT/.venv/bin/python3" ]]; then
    REFERENCE_PYTHON="$SOURCE_ROOT/.venv/bin/python3"
else
    REFERENCE_PYTHON="$ROOT/build/marble-oracle-venv/bin/python"
fi
if [[ ! -x "$REFERENCE_PYTHON" ]]; then
    echo "missing Marble reference Python: $REFERENCE_PYTHON" >&2
    exit 2
fi
if [[ ! -f "$SOURCE_ROOT/neural_workshop/marblemaze.py" ]]; then
    echo "missing original Neural Workshop source: $SOURCE_ROOT" >&2
    echo "Set NEURAL_WORKSHOP_SOURCE_ROOT to the reference checkout." >&2
    exit 2
fi

NEURAL_WORKSHOP_SOURCE_ROOT="$SOURCE_ROOT" \
    "$REFERENCE_PYTHON" "$ROOT/shells/python/test_marble_native_render.py"
