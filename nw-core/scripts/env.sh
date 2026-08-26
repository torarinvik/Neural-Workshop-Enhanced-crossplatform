# Pinned toolchain for the Neural Workshop port. Source this before building.
#
# The compilers are OURS: built by scripts/build-toolchain.sh into nw-core/
# toolchain/, from the nw-port branches under ../worktrees. Nothing else writes
# to them.
#
# We deliberately do NOT use ~/.elisac/elisac. That binary is shared, and it is
# rebuilt behind our backs: elisa-core installs git hooks that reinstall it on
# every commit, merge and checkout in ANY worktree of the repository, from
# whatever branch that worktree is on. Two sessions were spent chasing results
# that turned out to come from someone else's compiler.

NW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
NW_CORE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# Overridable so a scratch INTEGRATION checkout can be verified with the same
# suites without editing this file: set either variable before sourcing.
export ELISA_CORE="${ELISA_CORE:-$NW_ROOT/worktrees/elisa-core-nw}"
export ELISA_STAGE1_ROOT="${ELISA_STAGE1_ROOT:-$NW_ROOT/worktrees/elisa-compiler-nw}"

export ELISACORE_BIN="${ELISACORE_BIN:-$NW_CORE/toolchain/elisac-stage0}"
export ELISA_STAGE1_BIN="${ELISA_STAGE1_BIN:-$NW_CORE/toolchain/elisac-stage1}"
export ELISA_RUNTIME_OBJ="${ELISA_RUNTIME_OBJ:-$NW_CORE/toolchain/elisacore_runtime.o}"

# Refuse to run on a half-built toolchain rather than let a script fall through
# to its own `${ELISAC:-$HOME/.elisac/elisac}` default -- which is exactly how a
# suite once compared the other agent's compiler against itself and passed.
for _nw_tool in "$ELISACORE_BIN" "$ELISA_STAGE1_BIN" "$ELISA_RUNTIME_OBJ"; do
    if [[ ! -e "$_nw_tool" ]]; then
        echo "nw-core: missing $_nw_tool" >&2
        echo "nw-core: run ./scripts/build-toolchain.sh first" >&2
        unset _nw_tool
        return 1 2>/dev/null || exit 1
    fi
done
unset _nw_tool

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
