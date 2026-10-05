#!/usr/bin/env bash
# Build a separate stage1 WebAssembly artifact and run the same artifact-level
# tests as stage0. The stage1 wrapper's stale-source refusal is intentional:
# regenerate the pinned toolchain first if compiler sources have moved on.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! source "$ROOT/scripts/env.sh"; then
    echo "build_stage1_wasm.sh: pinned environment could not be loaded" >&2
    exit 1
fi
mkdir -p "$ROOT/build"

OBJECT="${NW_STAGE1_WASM_OBJECT:-$ROOT/build/nwcore_stage1_wasm.o}"
ARTIFACT="${NW_STAGE1_WASM_ARTIFACT:-$ROOT/build/nwcore-stage1.wasm}"
mkdir -p "$(dirname -- "$OBJECT")" "$(dirname -- "$ARTIFACT")"
python3 "$ROOT/test/wasm_runtime_include_test.py"
WASM_SOURCE_TMP="$(mktemp "$ROOT/src/wasm/wasm_exports_stage1.XXXXXX")"
WASM_SOURCE="${WASM_SOURCE_TMP}.elisa"
mv -- "$WASM_SOURCE_TMP" "$WASM_SOURCE"
trap 'rm -f -- "$WASM_SOURCE"' EXIT INT TERM HUP
python3 "$ROOT/scripts/prepare_wasm_exports.py" \
    "$ROOT/src/wasm/wasm_exports.elisa" "$WASM_SOURCE" "$ELISA_STAGE1_ROOT"
"$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" \
    -emit obj -O2 -target-triple wasm32-unknown-wasi \
    -o "$OBJECT" "$WASM_SOURCE"
rm -f -- "$WASM_SOURCE"
trap - EXIT INT TERM HUP
wasm-ld --no-entry --export-dynamic --allow-undefined --export=__heap_base \
    -o "$ARTIFACT" "$OBJECT"
printf 'stage1 wasm: %s bytes\n' "$(wc -c < "$ARTIFACT" | tr -d ' ')"

bash "$ROOT/scripts/test_wasm_artifact.sh" "$ARTIFACT"
