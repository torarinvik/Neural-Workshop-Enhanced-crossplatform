#!/usr/bin/env bash
# Build the nwcore CPython extension (+ .pyi stub).
#
# `-emit pymodule-so` is a stage1 feature, and it lives upstream on
# Elisa-compiler `work` (d9eb40df "recover Python module interop", hardened by
# 5e1e8451) -- NOT on the nw-port branches our pinned toolchain is built from.
# So this script drives the upstream driver script, against a stage1 seeded
# from upstream sources into toolchain/elisac-stage1-pymod.
#
# That seed needs a stage0 new enough to parse upstream's syntax (the machine
# `for` iterators postdate our pin), hence toolchain/elisac-stage0-seed, a COPY
# of ~/.elisac/elisac -- copied, not used in place, because the shared binary is
# rebuilt behind our backs by the compiler repo's git hooks.
#
# Neither of these replaces the pinned toolchain: env.sh still decides what
# compiles and verifies the port. They exist only to package it for CPython.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${ELISA_PYMODULE_COMPILER:-/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler}"
OUT="$ROOT/build/pymod"
mkdir -p "$OUT"

# The pymodule toolchain, seeded on first use. Overridable so a scratch build
# can point at another pair without editing this file.
SEED_STAGE0="${ELISA_PYMODULE_STAGE0:-$ROOT/toolchain/elisac-stage0-seed}"
SEED_STAGE1="${ELISA_PYMODULE_STAGE1:-$ROOT/toolchain/elisac-stage1-pymod}"
if [[ ! -x "$SEED_STAGE0" ]]; then
    [[ -x "$HOME/.elisac/elisac" ]] || { echo "no ~/.elisac/elisac to seed from" >&2; exit 1; }
    cp "$HOME/.elisac/elisac" "$SEED_STAGE0"
fi
if [[ ! -x "$SEED_STAGE1" ]]; then
    echo "seeding $SEED_STAGE1 from $UPSTREAM (this takes a few minutes)"
    ELISACORE_BIN="$SEED_STAGE0" ELISA_STAGE1_BIN="$SEED_STAGE1" \
        ELISA_SEED_OUTPUT="$SEED_STAGE1" "$UPSTREAM/scripts/elisac_stage1.sh" --seed
fi
export ELISACORE_BIN="$SEED_STAGE0" ELISA_STAGE1_BIN="$SEED_STAGE1"

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
