# Pinned toolchain for the Neural Workshop port. Source this before building.
#
# We deliberately do NOT use ~/.elisac/elisac or the main compiler worktrees —
# another agent works there. Our compilers build from the nw-port worktree
# branches under ../worktrees, so compiler fixes we make are picked up here
# without touching anyone else's environment.

NW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"

export ELISA_CORE="$NW_ROOT/worktrees/elisa-core-nw"
export ELISA_STAGE1_ROOT="$NW_ROOT/worktrees/elisa-compiler-nw"

export ELISACORE_BIN="$ELISA_CORE/compiler/bin/elisac-nw"
export ELISA_STAGE1_BIN="$ELISA_STAGE1_ROOT/bin/elisac-stage1"
export ELISA_RUNTIME_OBJ="$ELISA_STAGE1_ROOT/build/runtime/elisacore_runtime.o"

# Type-check for real: stage1 emits without analysis when the gate is off.
export ELISA_STAGE1_SEMANTIC_GATE=1

elisac_stage1() {
    "$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" "$@"
}
