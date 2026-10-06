#!/usr/bin/env bash
# Build the nwcore CPython extension (+ .pyi stub).
#
# Build the CPython extension with the same current, source-fresh Stage1
# checkout used for the production browser artifact. Do not silently fall back
# to the September pymodule seed or another potentially stale compiler tree.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS_ROOT="$(cd -- "$ROOT/../.." && pwd)"
UPSTREAM="${ELISA_PYMODULE_COMPILER:-$PROJECTS_ROOT/Elisa-compiler-port-current-5417885}"
STAGE1_BIN="${ELISA_PYMODULE_STAGE1:-$UPSTREAM/bin/elisac-stage1}"
OUT="$ROOT/build/pymod"
mkdir -p "$OUT"

# Stage0 remains an isolated bootstrap input for the compiler wrapper; Stage1
# itself is the already-built product from the selected latest source tree.
SEED_STAGE0="${ELISA_PYMODULE_STAGE0:-$ROOT/toolchain/elisac-stage0-seed}"
if [[ ! -x "$SEED_STAGE0" ]]; then
    [[ -x "$HOME/.elisac/elisac" ]] || { echo "no ~/.elisac/elisac to seed from" >&2; exit 1; }
    cp "$HOME/.elisac/elisac" "$SEED_STAGE0"
fi
if [[ ! -x "$UPSTREAM/scripts/elisac_stage1.sh" || ! -x "$STAGE1_BIN" ]]; then
    echo "build_pymodule.sh: latest Elisa Stage1 checkout/product missing" >&2
    echo "  checkout: $UPSTREAM" >&2
    echo "  product:  $STAGE1_BIN" >&2
    echo "Set ELISA_PYMODULE_COMPILER and ELISA_PYMODULE_STAGE1 explicitly." >&2
    exit 2
fi
PYTHON_CHECK_BIN="${PYTHON_BIN:-python3}"
stale_source="$("$PYTHON_CHECK_BIN" "$ROOT/scripts/stage1_fresh.py" \
    "$UPSTREAM" "$STAGE1_BIN" 2>/dev/null || true)"
if [[ -n "$stale_source" ]]; then
    echo "build_pymodule.sh: Stage1 product is stale: $stale_source" >&2
    echo "Rebuild the latest Elisa Stage1 product before emitting the Python module." >&2
    exit 2
fi
compiler_head="$(git -C "$UPSTREAM" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || true)"
origin_head="$(git -C "$UPSTREAM" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
if [[ -n "$compiler_head" && -n "$origin_head" ]]; then
    behind="$(git -C "$UPSTREAM" -c core.hooksPath=/dev/null \
        rev-list --count "$compiler_head..$origin_head" 2>/dev/null || echo 0)"
    if [[ "$behind" != 0 ]]; then
        echo "build_pymodule.sh: selected compiler is $behind commit(s) behind origin/main" >&2
        echo "  local:  $compiler_head" >&2
        echo "  origin: $origin_head" >&2
        exit 2
    fi
fi
export ELISACORE_BIN="$SEED_STAGE0" ELISA_STAGE1_BIN="$STAGE1_BIN"

# pymodule_exports.elisa includes the runtime SOURCE, so the module object
# already defines the runtime and the prebuilt elisacore_runtime.o must not be
# linked beside it. ELISA_RUNTIME_OBJ takes its place with a shim carrying only
# the optional host hooks the runtime leaves undefined. See the comments in
# scripts/pymodule_runtime_shim.c and src/pymodule_exports.elisa.
SHIM_OBJ="$OUT/pymodule_runtime_shim.o"
cc -c -fPIC -fno-builtin -O2 -o "$SHIM_OBJ" "$ROOT/scripts/pymodule_runtime_shim.c"

cd "$OUT"
PYMODULE_SOURCE_TMP="$(mktemp "$ROOT/src/pymodule_exports_stage1.XXXXXX")"
PYMODULE_SOURCE="${PYMODULE_SOURCE_TMP}.elisa"
mv -- "$PYMODULE_SOURCE_TMP" "$PYMODULE_SOURCE"
trap 'rm -f -- "$PYMODULE_SOURCE"' EXIT INT TERM HUP
"$PYTHON_CHECK_BIN" "$ROOT/scripts/prepare_wasm_exports.py" \
    "$ROOT/src/pymodule_exports.elisa" "$PYMODULE_SOURCE" "$UPSTREAM"
ELISA_RUNTIME_OBJ="$SHIM_OBJ" ELISA_STAGE1_SEMANTIC_GATE=1 \
    "$UPSTREAM/scripts/elisac_stage1.sh" \
    -emit pymodule-so "$PYMODULE_SOURCE"
PYTHON_TEST_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_TEST_BIN" "$ROOT/shells/python/test_marble.py"
echo "built in $OUT"
