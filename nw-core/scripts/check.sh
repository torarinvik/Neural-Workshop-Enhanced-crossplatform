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
source "$ROOT/scripts/env.sh"

STAGES="${1:-both}"
BUILD="$ROOT/build"
mkdir -p "$BUILD"

SUITES=(scheduling board nback pyrandom stimulus stats matching)

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
        run_suite "$suite" "$stage" || failures=$((failures + 1))
    done
done

echo
if (( failures )); then
    echo "FAILED: $failures suite run(s)"
    exit 1
fi
echo "All differential suites match the Python reference."
