#!/usr/bin/env bash
# The full gate: everything that must be green before this work is merged
# anywhere. Designed to be run unattended (nightly, or before a merge), NOT as
# an inner loop — the slow tiers below take the better part of an hour.
#
#   scripts/gate.sh          fast + medium tiers (a few minutes)
#   scripts/gate.sh --full   every tier, including the multi-hour stage1
#                            semantic differential
#
# Tier boundaries are chosen by wall clock, not by importance: the fast tier is
# what you can afford on every change, the slow tier is what you can only
# afford overnight.
set -uo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/env.sh"

FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

failures=0
step() {
    local name="$1"; shift
    printf '\n=== %s\n' "$name"
    if "$@"; then
        printf '    OK\n'
    else
        printf '    FAILED\n'
        failures=$((failures + 1))
    fi
}

# --- fast: the port's own differential suites --------------------------------

step "nw-core differential suites (both stages)" \
    "$ROOT/scripts/check.sh"

step "nw-core WebAssembly build + differential" \
    "$ROOT/scripts/build_wasm.sh"

# --- medium: the compilers -----------------------------------------------

step "stage0 fast test suite" \
    make -C "$ELISA_CORE/compiler" test

# The parity smokes that cover the areas this port has touched. The full
# run_all.sh is in the slow tier: its semantic_internal_diff.sh step replays
# ~2400 tests one compilation at a time and runs for hours.
smokes() {
    local ok=0
    for smoke in try_fallible catch_exhaustive match_expr match_pattern \
                 match_exhaustive enum_constructor enum_tail_payload \
                 atomic_payload scalar_match_arm legacy_error_syntax; do
        local script="$ELISA_STAGE1_ROOT/test/parity/${smoke}_smoke.sh"
        [[ -f "$script" ]] || continue
        if ELISA_CORE="$ELISA_CORE" bash "$script" >/dev/null 2>&1; then
            printf '    %-24s ok\n' "$smoke"
        else
            printf '    %-24s FAILED\n' "$smoke"
            ok=1
        fi
    done
    return $ok
}
step "stage1 targeted parity smokes" smokes

step "runtime drift (vendored std == canonical)" \
    env ELISA_CORE="$ELISA_CORE" bash "$ELISA_STAGE1_ROOT/scripts/check_runtime_drift.sh"

# --- slow: only with --full --------------------------------------------------

if (( FULL )); then
    step "stage0 full native-runtime suite (~8 min)" \
        make -C "$ELISA_CORE/compiler" test-full

    step "stage1 self-host fixpoint (gen3 == gen4)" \
        env ELISA_CORE="$ELISA_CORE" bash "$ELISA_STAGE1_ROOT/test/parity/self_host_gen3_smoke.sh"

    # Hours. This is the one that catches semantic divergence between the two
    # compilers across stage0's entire internal suite.
    step "stage1 full parity gate (HOURS)" \
        env ELISA_CORE="$ELISA_CORE" bash "$ELISA_STAGE1_ROOT/test/parity/run_all.sh"
else
    printf '\n(skipping the slow tier: stage0 test-full, self-host fixpoint,\n'
    printf ' and the stage1 semantic differential. Run with --full.)\n'
fi

printf '\n'
if (( failures )); then
    printf 'GATE FAILED: %d step(s)\n' "$failures"
    exit 1
fi
printf 'GATE GREEN\n'
