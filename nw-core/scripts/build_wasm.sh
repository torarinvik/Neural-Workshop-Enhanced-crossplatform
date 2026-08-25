#!/usr/bin/env bash
# Build the nw-core WebAssembly module and run its differential test.
#
# Stage0's LLVM backend already emits wasm32 objects: no compiler change was
# needed for the browser path, only host imports for the runtime's libc calls
# (see shells/web/elisa-wasm-runtime.js).
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
mkdir -p "$ROOT/build"

"$ELISACORE_BIN" -emit obj -O2 -target-triple wasm32-unknown-wasi \
    -o "$ROOT/build/nwcore_wasm.o" "$ROOT/src/wasm/wasm_exports.elisa"

# --export-dynamic keeps the `export fn` symbols; -O2 gives everything else
# private linkage, which is what we want for size.
wasm-ld --no-entry --export-dynamic --allow-undefined \
    -o "$ROOT/build/nwcore.wasm" "$ROOT/build/nwcore_wasm.o"

printf 'wasm: %s bytes\n' "$(wc -c < "$ROOT/build/nwcore.wasm" | tr -d ' ')"
node "$ROOT/test/wasm_diff.mjs"
