#!/usr/bin/env bash
# Build the nwcore CPython extension (+ .pyi stub).
#
# NOTE: `-emit pymodule-so` lives in work that is still UNCOMMITTED on the
# upstream Elisa-compiler worktree, so this script uses that checkout's
# compiler read-only. Once the pymodule exporter lands on a branch we can
# rebase onto, drop UPSTREAM and use elisac_stage1 from env.sh like everything
# else.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${ELISA_PYMODULE_COMPILER:-/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler}"
OUT="$ROOT/build/pymod"
mkdir -p "$OUT"

# pymodule_exports.elisa includes the runtime SOURCE, so the module object
# already defines the runtime and the prebuilt elisacore_runtime.o must not be
# linked beside it. ELISA_RUNTIME_OBJ takes its place with a shim carrying only
# the optional host hooks the runtime leaves undefined. See the comments in
# scripts/pymodule_runtime_shim.c and src/pymodule_exports.elisa.
SHIM_OBJ="$OUT/pymodule_runtime_shim.o"
cc -c -fPIC -fno-builtin -O2 -o "$SHIM_OBJ" "$ROOT/scripts/pymodule_runtime_shim.c"

cd "$OUT"
ELISA_RUNTIME_OBJ="$SHIM_OBJ" ELISA_STAGE1_SEMANTIC_GATE=1 \
    "$UPSTREAM/scripts/elisac_stage1.sh" \
    -emit pymodule-so "$ROOT/src/pymodule_exports.elisa"
echo "built in $OUT"
