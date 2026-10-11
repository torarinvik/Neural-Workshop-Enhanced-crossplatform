# Pinned toolchain for the Neural Workshop port. Source this before building.
#
# The compilers are OURS: built by scripts/build-toolchain.sh into nw-core/
# toolchain/, from the selected Elisa-core and latest Elisa-compiler checkouts.
# Nothing else writes to the port-owned binaries.
#
# We deliberately do NOT use ~/.elisac/elisac. That binary is shared, and it is
# rebuilt behind our backs: elisa-core installs git hooks that reinstall it on
# every commit, merge and checkout in ANY worktree of the repository, from
# whatever branch that worktree is on. Two sessions were spent chasing results
# that turned out to come from someone else's compiler.

NW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
NW_CORE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# The differential oracle is the frozen original application's own virtual
# environment, not whichever `python3` happens to be first on the host PATH.
# Keep Homebrew first for git/clang and the post-upgrade macOS toolchain, but
# put the reference venv ahead of it for every Python invocation made by the
# check/build scripts.  Without this, a clean Xcode license still produces
# misleading failures such as `ModuleNotFoundError: pyglet`.
# macOS can leave /usr/bin/python3 and /usr/bin/git as xcrun shims after an
# OS/Xcode upgrade.  If the Command Line Tools license has not been accepted,
# every differential suite then fails before Python or Git starts, even though
# the port's actual dependencies are intact.  Prefer the installed Homebrew
# toolchain when it exists; do not overwrite a caller's explicit choice.
if [[ -d /opt/homebrew/bin ]]; then
    case ":${PATH:-}:" in
        :/opt/homebrew/bin:*) ;;
        *) PATH="/opt/homebrew/bin:${PATH:-}"; export PATH ;;
    esac
fi
if [[ -z "${DEVELOPER_DIR+x}" && -d /Library/Developer/CommandLineTools ]]; then
    export DEVELOPER_DIR=/Library/Developer/CommandLineTools
fi

NW_REFERENCE_PYTHON_DIR="$NW_ROOT/original-neural-workshop-enhanced/.venv/bin"
if [[ -x "$NW_REFERENCE_PYTHON_DIR/python3" ]]; then
    PATH="$NW_REFERENCE_PYTHON_DIR:${PATH:-}"
    export PATH
fi

# Keep the driver, runtime audit, and toolchain builder on the pinned port
# worktrees when they are available. Fall back to the conventional checkouts
# for machines that do not have those worktrees. Both selections are overridable
# for isolated candidate builds.
DEFAULT_ELISA_CORE="$NW_ROOT/../../Go projects/Elisa-core"
if [[ ! -d "$DEFAULT_ELISA_CORE/compiler" && -d "$NW_ROOT/stage0-elisa-compiler/compiler" ]]; then
    DEFAULT_ELISA_CORE="$NW_ROOT/stage0-elisa-compiler"
fi
DEFAULT_ELISA_STAGE1_ROOT="$NW_ROOT/../Elisa-compiler-port-current-23a0"
if [[ ! -d "$DEFAULT_ELISA_STAGE1_ROOT" && -d "$NW_ROOT/stage1-elisa-compiler" ]]; then
    DEFAULT_ELISA_STAGE1_ROOT="$NW_ROOT/stage1-elisa-compiler"
fi
export ELISA_CORE="${ELISA_CORE:-$DEFAULT_ELISA_CORE}"
export ELISA_STAGE1_ROOT="${ELISA_STAGE1_ROOT:-$DEFAULT_ELISA_STAGE1_ROOT}"

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
