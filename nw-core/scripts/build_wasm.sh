#!/usr/bin/env bash
# Build the nw-core WebAssembly module and run its differential test.
#
# Stage0's LLVM backend already emits wasm32 objects: no compiler change was
# needed for the browser path, only host imports for the runtime's libc calls
# (see shells/web/elisa-wasm-runtime.js).
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! source "$ROOT/scripts/env.sh"; then
    echo "build_wasm.sh: pinned environment could not be loaded" >&2
    exit 1
fi
cd "$ROOT"
OBJECT="${NW_WASM_OBJECT:-$ROOT/build/nwcore_wasm.o}"
ARTIFACT="${NW_WASM_ARTIFACT:-$ROOT/build/nwcore.wasm}"
BINDINGS_OUT="${NW_WASM_BINDINGS_OUT:-${ARTIFACT%.wasm}}"
mkdir -p "$(dirname -- "$OBJECT")" "$(dirname -- "$ARTIFACT")" \
    "$(dirname -- "$BINDINGS_OUT")"

python3 "$ROOT/test/wasm_runtime_include_test.py"
WASM_SOURCE_TMP="$(mktemp "$ROOT/src/wasm/wasm_exports_stage0.XXXXXX")"
WASM_SOURCE="${WASM_SOURCE_TMP}.elisa"
mv -- "$WASM_SOURCE_TMP" "$WASM_SOURCE"
trap 'rm -f -- "$WASM_SOURCE"' EXIT INT TERM HUP
python3 "$ROOT/scripts/prepare_wasm_exports.py" \
    "$ROOT/src/wasm/wasm_exports.elisa" "$WASM_SOURCE" "$ELISA_STAGE1_ROOT"
"$ELISACORE_BIN" -emit obj -O2 -target-triple wasm32-unknown-wasi \
    -o "$OBJECT" "$WASM_SOURCE"
rm -f -- "$WASM_SOURCE"
trap - EXIT INT TERM HUP

# --export-dynamic keeps the `export fn` symbols; -O2 gives everything else
# private linkage, which is what we want for size.
# --export=__heap_base is NOT implied by --export-dynamic: the symbol is
# linker-synthesized, not a definition in the object, so it has to be named.
# Without it the shim has no idea where static data ends.
wasm-ld --no-entry --export-dynamic --allow-undefined --export=__heap_base -z stack-size=8388608 \
    -o "$ARTIFACT" "$OBJECT"

printf 'wasm: %s bytes\n' "$(wc -c < "$ARTIFACT" | tr -d ' ')"

# Typed JS/TS bindings, the web twin of `-emit pymodule-pyi`. Derived from the
# emitted binary, so they cannot drift from what was actually built.
python3 "$ROOT/scripts/gen_wasm_bindings.py" "$ARTIFACT" \
    --out "$BINDINGS_OUT" >/dev/null

bash "$ROOT/scripts/test_wasm_artifact.sh" "$ARTIFACT"
