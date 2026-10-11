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
# Ours are built here, from the selected Elisa-core and Elisa-compiler
# checkouts, and nothing else writes to them. Three artefacts, because stage1
# bootstraps through stage0 and then builds its runtime from the resulting
# product:
#
#   elisac-stage0        Go + cgo over the LLVM C API
#   elisac-stage1        the self-hosted compiler, seeded by stage0
#   elisacore_runtime.o  the runtime, compiled by that stage1 product
set -euo pipefail

HERE="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NW_ROOT="$(cd -- "$HERE/../.." && pwd)"
DEFAULT_CORE="$NW_ROOT/../../Go projects/Elisa-core"
if [[ ! -d "$DEFAULT_CORE/compiler" && -d "$NW_ROOT/stage0-elisa-compiler/compiler" ]]; then
    DEFAULT_CORE="$NW_ROOT/stage0-elisa-compiler"
fi
DEFAULT_STAGE1_ROOT="$NW_ROOT/../Elisa-compiler-port-current-23a0"
if [[ ! -d "$DEFAULT_STAGE1_ROOT" && -d "$NW_ROOT/stage1-elisa-compiler" ]]; then
    DEFAULT_STAGE1_ROOT="$NW_ROOT/stage1-elisa-compiler"
fi
CORE="${ELISA_CORE:-$DEFAULT_CORE}"
STAGE1_ROOT="${ELISA_STAGE1_ROOT:-$DEFAULT_STAGE1_ROOT}"
export ELISA_CORE="$CORE"
export ELISA_STAGE1_ROOT="$STAGE1_ROOT"
export ELISACORE_STRICT_FP=1
export ELISA_STAGE1_SEMANTIC_GATE=1
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
head_of() { git -C "$1" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || echo unknown; }
branch_of() { git -C "$1" -c core.hooksPath=/dev/null rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown; }
source_fingerprint() { python3 "$HERE/source_fingerprint.py" "$1"; }
sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# Stage1 carries a copy of the core runtime. Refuse to replace any compiler
# binary until the copy is either identical or consists only of the reviewed,
# committed latest-compiler deltas accepted by the port provenance check.
if ! ELISA_CORE="$CORE" ELISA_STAGE1_ROOT="$STAGE1_ROOT" \
    bash "$HERE/check_stage1_runtime_provenance.sh"; then
    echo "toolchain build stopped before changing binaries: review stage1 runtime provenance first" >&2
    exit 2
fi

core_head="$(head_of "$CORE")"
stage1_head="$(head_of "$STAGE1_ROOT")"
core_fingerprint="$(source_fingerprint "$CORE")"
stage1_fingerprint="$(source_fingerprint "$STAGE1_ROOT")"
stamp="$OUT/PROVENANCE"
want="$(printf 'stage0_branch=%s\nstage0_commit=%s\nstage0_source_fingerprint=%s\nstage1_branch=%s\nstage1_commit=%s\nstage1_source_fingerprint=%s' \
    "$(branch_of "$CORE")" "$core_head" "$core_fingerprint" \
    "$(branch_of "$STAGE1_ROOT")" "$stage1_head" "$stage1_fingerprint")"

if (( ! FORCE )) && [[ -x "$ELISACORE_BIN" && -x "$ELISA_STAGE1_BIN" && -f "$ELISA_RUNTIME_OBJ" ]] \
   && [[ -f "$stamp" ]] && [[ "$(sed -n '1,6p' "$stamp")" == "$want" ]]; then
    recorded_stage0="$(sed -n '7s/^stage0_sha256=//p' "$stamp")"
    recorded_runtime="$(sed -n '8s/^runtime_sha256=//p' "$stamp")"
    recorded_stage1="$(sed -n '9s/^stage1_sha256=//p' "$stamp")"
    if [[ "$recorded_stage0" == "$(sha256_file "$ELISACORE_BIN")" &&
          "$recorded_runtime" == "$(sha256_file "$ELISA_RUNTIME_OBJ")" &&
          "$recorded_stage1" == "$(sha256_file "$ELISA_STAGE1_BIN")" ]]; then
        echo "toolchain up to date:"
        sed 's/^/  /' "$stamp"
        exit 0
    fi
fi

echo "==> stage0  (go build, from $CORE @ $core_head)"
go build -C "$CORE/compiler" -o "$ELISACORE_BIN" ./src

echo "==> stage1 + runtime (seeded by stage0, then built by stage1, from $STAGE1_ROOT @ $stage1_head)"
# The seed compiles the whole self-hosted compiler with stage0: a minute or
# two, and several thousand advisory warnings about its own sources. Only real
# errors are worth showing here.
# The seed publishes the Stage1 product before building its matching runtime.
# Building that runtime before the seed creates a bootstrap cycle because the
# runtime builder correctly requires the Stage1 product.
"$STAGE1_ROOT/scripts/elisac_stage1.sh" --seed 2>&1 | grep -v "warning:" | sed 's/^/    /'

stamp_tmp="$stamp.$$.tmp"
{
    printf '%s\n' "$want"
    printf 'stage0_sha256=%s\n' "$(sha256_file "$ELISACORE_BIN")"
    printf 'runtime_sha256=%s\n' "$(sha256_file "$ELISA_RUNTIME_OBJ")"
    printf 'stage1_sha256=%s\n' "$(sha256_file "$ELISA_STAGE1_BIN")"
} > "$stamp_tmp"
mv -f "$stamp_tmp" "$stamp"
echo
echo "wrote:"
ls -la "$OUT" | sed 's/^/  /'
echo
echo "provenance:"
sed 's/^/  /' "$stamp"
