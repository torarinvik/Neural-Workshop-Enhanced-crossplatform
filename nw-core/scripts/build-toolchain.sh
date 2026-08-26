#!/usr/bin/env bash
# Build the port's OWN compilers, into the port's own folder.
#
#   ./scripts/build-toolchain.sh          # build whatever is missing or stale
#   ./scripts/build-toolchain.sh --force  # rebuild all three regardless
#
# Why this exists rather than using ~/.elisac/elisac: that binary is shared,
# and it is rebuilt behind our backs. Elisa-core installs git hooks that
# reinstall it on every commit, merge and checkout in ANY worktree of the
# repository, so another agent committing in their tree silently swaps the
# compiler under our feet -- and it is built from THEIR branch, not ours.
# Two sessions were spent chasing results that came from that.
#
# Ours are built here, from the branches in ../worktrees, and nothing else
# writes to them. Three artefacts, because stage1 bootstraps through stage0:
#
#   elisac-stage0        Go + cgo over the LLVM C API
#   elisacore_runtime.o  the runtime, compiled by stage0
#   elisac-stage1        the self-hosted compiler, seeded by stage0
set -euo pipefail

HERE="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NW_ROOT="$(cd -- "$HERE/../.." && pwd)"
CORE="${ELISA_CORE:-$NW_ROOT/worktrees/elisa-core-nw}"
STAGE1_ROOT="${ELISA_STAGE1_ROOT:-$NW_ROOT/worktrees/elisa-compiler-nw}"
# Overridable so a candidate toolchain (an integration branch, say) can be built
# and tested without disturbing the verified one.
OUT="${ELISA_TOOLCHAIN_OUT:-$HERE/../toolchain}"

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

mkdir -p "$OUT"
export ELISACORE_BIN="$OUT/elisac-stage0"
export ELISA_STAGE1_BIN="$OUT/elisac-stage1"
export ELISA_RUNTIME_OBJ="$OUT/elisacore_runtime.o"

# `git -c core.hooksPath=` on every read: elisa-core's hooks fire on git
# operations and reinstall the SHARED binary. Reading a commit id must not have
# side effects on someone else's toolchain.
head_of() { git -C "$1" -c core.hooksPath=/dev/null rev-parse --short HEAD 2>/dev/null || echo unknown; }
branch_of() { git -C "$1" -c core.hooksPath=/dev/null rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown; }

core_head="$(head_of "$CORE")"
stage1_head="$(head_of "$STAGE1_ROOT")"
stamp="$OUT/PROVENANCE"
want="stage0 $(branch_of "$CORE") $core_head
stage1 $(branch_of "$STAGE1_ROOT") $stage1_head"

if (( ! FORCE )) && [[ -x "$ELISACORE_BIN" && -x "$ELISA_STAGE1_BIN" && -f "$ELISA_RUNTIME_OBJ" ]] \
   && [[ -f "$stamp" ]] && [[ "$(cat "$stamp")" == "$want" ]]; then
    echo "toolchain up to date:"
    sed 's/^/  /' "$stamp"
    exit 0
fi

echo "==> stage0  (go build, from $CORE @ $core_head)"
go build -C "$CORE/compiler" -o "$ELISACORE_BIN" ./src

echo "==> runtime (stage0 -emit obj)"
"$STAGE1_ROOT/scripts/build_runtime_object.sh" >/dev/null

echo "==> stage1  (seeded by stage0, from $STAGE1_ROOT @ $stage1_head)"
# The seed compiles the whole self-hosted compiler with stage0: a minute or
# two, and several thousand advisory warnings about its own sources. Only real
# errors are worth showing here.
"$STAGE1_ROOT/scripts/elisac_stage1.sh" --seed 2>&1 | grep -v "warning:" | sed 's/^/    /'

printf '%s\n' "$want" > "$stamp"
echo
echo "wrote:"
ls -la "$OUT" | sed 's/^/  /'
echo
echo "provenance:"
sed 's/^/  /' "$stamp"
