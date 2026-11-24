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
# Materialize src/ with every runtime include pinned to the selected
# compiler, as check.sh and build_sdl3.sh do: corpus modules include the
# runtime too, not only the export surface.
SOURCE_TREE_PARENT="$(mktemp -d "$ROOT/build/stage1-wasm-sources.XXXXXX")"
SOURCE_TREE="$SOURCE_TREE_PARENT/source"
trap 'rm -rf -- "$SOURCE_TREE_PARENT"' EXIT INT TERM HUP
python3 "$ROOT/scripts/prepare_runtime_sources.py" "$ROOT" "$SOURCE_TREE" "$ELISA_STAGE1_ROOT"
# The unit compiles the runtime from source without defining its arena, so
# Stage1 is told the runtime is the trusted standard library.
ELISA_STAGE1_RUNTIME_STD=1 "$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" \
    -emit obj -O2 -target-triple wasm32-unknown-wasi \
    -o "$OBJECT" "$SOURCE_TREE/src/wasm/wasm_exports.elisa"
rm -rf -- "$SOURCE_TREE_PARENT"
trap - EXIT INT TERM HUP
wasm-ld --no-entry --export-dynamic --allow-undefined --export=__heap_base -z stack-size=8388608 \
    -o "$ARTIFACT" "$OBJECT"
printf 'stage1 wasm: %s bytes\n' "$(wc -c < "$ARTIFACT" | tr -d ' ')"

bash "$ROOT/scripts/test_wasm_artifact.sh" "$ARTIFACT"
