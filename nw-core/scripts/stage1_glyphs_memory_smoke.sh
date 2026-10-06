#!/usr/bin/env bash
# Guard the Glyphs import-only regression at the production optimization levels.
# This catches optimizer blow-ups even when no Glyphs function survives DCE.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! source "$ROOT/scripts/env.sh"; then
    echo "stage1_glyphs_memory_smoke.sh: pinned environment could not be loaded" >&2
    exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT INT TERM HUP

SOURCE_ROOT="$WORK/source"
python3 "$ROOT/scripts/prepare_runtime_sources.py" \
    "$ROOT" "$SOURCE_ROOT" "$ELISA_STAGE1_ROOT"
SOURCE="$SOURCE_ROOT/test/repro/stage1_glyphs_compile_memory.elisa"
for optimization in O1 O2; do
    OUTPUT="$WORK/glyphs-$optimization.ll"
    "$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" \
        -emit llvm "-$optimization" -o "$OUTPUT" "$SOURCE"
    if [[ ! -s "$OUTPUT" ]]; then
        echo "stage1 Glyphs $optimization compile produced no LLVM module" >&2
        exit 1
    fi
done

echo "stage1 Glyphs import-only compile passed at -O1 and -O2 under the default RSS guard"
