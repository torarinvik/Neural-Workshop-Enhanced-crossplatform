#!/usr/bin/env bash
# Build every nw-core differential sweep with both compilers and diff each one
# against the original Python module it was ported from.
#
#   scripts/check.sh            both stages
#   scripts/check.sh stage0     stage0 only (fast inner loop)
#   scripts/check.sh stage1     stage1 only
set -uo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
# `set -u -o pipefail` without -e, so the toolchain check has to be explicit:
# without it a missing compiler falls through to whatever a downstream script
# defaults to, which is the shared ~/.elisac/elisac.
source "$ROOT/scripts/env.sh" || exit 1

STAGES="${1:-both}"
# An unrecognised argument used to select NO stage, run NO suite, and still
# print "All differential suites match" and exit 0. `check.sh title` reads as
# "run the title suite" and silently verified nothing at all.
case "$STAGES" in
    both|stage0|stage1) ;;
    *)
        echo "check.sh: unknown argument '$STAGES' (expected: both, stage0, stage1)" >&2
        echo "check.sh: to run one suite, use SUITE=<name>" >&2
        exit 2
        ;;
esac
BUILD="$ROOT/build"
mkdir -p "$BUILD"

SUITES=(pyset scheduling board nback pyrandom stimulus stats matching display config gamemode decimal session maze fogworld numberology ninarow inthedark crossedwires cookiethief custody donkey tetris removals sokoban go twohands buzzwire marblemaze syllogism title menu menurow sudoku youarehere hanoi monkeyladder ncupmonte reflex salesman counting tracking concentration recognition lookout pursuit outofsight overrun mrtime jigsaw sokoban3d verbal scramble scrabble trivia crossword graphmapping ravens chess bigfrac)

# One suite by name, for the inner loop.
if [[ -n "${SUITE:-}" ]]; then
    if [[ " ${SUITES[*]} " != *" $SUITE "* ]]; then
        echo "check.sh: unknown suite '$SUITE'" >&2
        exit 2
    fi
    SUITES=("$SUITE")
fi

# Suites that cannot yet build under stage1. EMPTY -- every suite now builds and
# runs on both stages.
#
# `config` lived here for two separate reasons, both now fixed: the generic
# protocol-impl gap (nw-port stage1 552bddca), and then its own `main` --
# `try read_entire_file_cstr(...) else ""` plus the sview/cstr plumbing around it.
# Verified by building and RUNNING it, not by assuming the second gap went with
# the first:
#   scripts/elisac_stage1.sh -emit exe -O2 -o /tmp/cfg test/config_sweep.elisa
STAGE0_ONLY=()

failures=0
run_suite() {
    local suite="$1" stage="$2" binary="$BUILD/${1}_sweep_${2}"

    if [[ "$stage" == "stage0" ]]; then
        if ! "$ELISACORE_BIN" -emit obj -O2 -o "$BUILD/${suite}_${stage}.o" \
                "$ROOT/test/${suite}_sweep.elisa" 2>"$BUILD/${suite}_${stage}.log"; then
            echo "  ${suite} [${stage}]: COMPILE FAILED (see $BUILD/${suite}_${stage}.log)"
            return 1
        fi
        if ! clang -o "$binary" "$BUILD/${suite}_${stage}.o" 2>>"$BUILD/${suite}_${stage}.log"; then
            echo "  ${suite} [${stage}]: LINK FAILED (see $BUILD/${suite}_${stage}.log)"
            return 1
        fi
    else
        if ! "$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" -emit exe -O2 -o "$binary" \
                "$ROOT/test/${suite}_sweep.elisa" 2>"$BUILD/${suite}_${stage}.log"; then
            echo "  ${suite} [${stage}]: COMPILE FAILED (see $BUILD/${suite}_${stage}.log)"
            return 1
        fi
    fi

    local result
    result="$(python3 "$ROOT/test/${suite}_diff.py" "$binary" 2>&1)"
    if [[ "$result" == PASS* ]]; then
        echo "  ${suite} [${stage}]: ${result}"
        return 0
    fi
    echo "  ${suite} [${stage}]: ${result}"
    return 1
}

for stage in stage0 stage1; do
    [[ "$STAGES" == "both" || "$STAGES" == "$stage" ]] || continue
    echo "== $stage"
    for suite in "${SUITES[@]}"; do
        # :-  because the list is now EMPTY, and bash 3.2 under `set -u` treats
        # ${empty_array[*]} as an unbound variable rather than an empty string.
        if [[ "$stage" == "stage1" ]] && [[ " ${STAGE0_ONLY[*]:-} " == *" $suite "* ]]; then
            echo "  ${suite} [${stage}]: SKIPPED (stage1 cannot build this suite)"
            continue
        fi
        run_suite "$suite" "$stage" || failures=$((failures + 1))
    done
done

echo
if (( failures )); then
    echo "FAILED: $failures suite run(s)"
    exit 1
fi
echo "All differential suites match the Python reference."
