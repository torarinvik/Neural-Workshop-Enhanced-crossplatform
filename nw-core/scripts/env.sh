# Pinned toolchain for the Neural Workshop port. Source this before building.
#
# We deliberately do NOT use ~/.elisac/elisac or the main compiler worktrees —
# another agent works there. Our compilers build from the nw-port worktree
# branches under ../worktrees, so compiler fixes we make are picked up here
# without touching anyone else's environment.

NW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"

# Overridable so a scratch INTEGRATION checkout can be verified with the same
# suites without editing this file: set either variable before sourcing.
export ELISA_CORE="${ELISA_CORE:-$NW_ROOT/worktrees/elisa-core-nw}"
export ELISA_STAGE1_ROOT="${ELISA_STAGE1_ROOT:-$NW_ROOT/worktrees/elisa-compiler-nw}"

export ELISACORE_BIN="${ELISACORE_BIN:-$ELISA_CORE/compiler/bin/elisac-nw}"
export ELISA_STAGE1_BIN="${ELISA_STAGE1_BIN:-$ELISA_STAGE1_ROOT/bin/elisac-stage1}"
export ELISA_RUNTIME_OBJ="${ELISA_RUNTIME_OBJ:-$ELISA_STAGE1_ROOT/build/runtime/elisacore_runtime.o}"

# Strict IEEE floating point, both stages. Stage0 stamps LLVM's `contract` flag
# on every FP op by default (clang's -ffp-contract=on), so `a + b * c` may fuse
# into a single-rounding fma; stage1 never has. The two therefore disagreed in
# the last ulp wherever an add cancelled -- Python's `uniform(a, b)` is
# `a + (b - a) * random()`, and for a negative `a` roughly a quarter of all
# draws came out different. This whole port is a bit-exact differential against
# CPython, so relaxed FP is worth nothing here and costs correctness.
export ELISACORE_STRICT_FP=1

# Type-check for real: stage1 emits without analysis when the gate is off.
export ELISA_STAGE1_SEMANTIC_GATE=1

elisac_stage1() {
    "$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" "$@"
}
