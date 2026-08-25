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
cd "$OUT"
ELISA_STAGE1_SEMANTIC_GATE=1 "$UPSTREAM/scripts/elisac_stage1.sh" \
    -emit pymodule-so "$ROOT/src/pymodule_exports.elisa"
echo "built in $OUT"
