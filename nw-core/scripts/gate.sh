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
if ! source "$ROOT/scripts/env.sh"; then
    echo "gate.sh: pinned environment could not be loaded; refusing to run partial checks" >&2
    exit 1
fi

PROJECTS_ROOT="$(cd -- "$ROOT/../.." && pwd)"
LATEST_STAGE1_ROOT="${ELISA_LATEST_STAGE1_ROOT:-$PROJECTS_ROOT/Elisa-compiler-latest-protocol-bound-fix}"
LATEST_STAGE1_BIN="${ELISA_LATEST_STAGE1_BIN:-$LATEST_STAGE1_ROOT/bin/elisac-stage1}"
if [[ ! -x "$LATEST_STAGE1_ROOT/scripts/elisac_stage1.sh" || ! -x "$LATEST_STAGE1_BIN" ]]; then
    echo "gate.sh: latest Elisa Stage1 checkout/product missing" >&2
    echo "  checkout: $LATEST_STAGE1_ROOT" >&2
    echo "  product:  $LATEST_STAGE1_BIN" >&2
    echo "Set ELISA_LATEST_STAGE1_ROOT and ELISA_LATEST_STAGE1_BIN explicitly." >&2
    exit 1
fi
LATEST_STAGE1_STALE_SOURCE="$(python3 "$ROOT/scripts/stage1_fresh.py" \
    "$LATEST_STAGE1_ROOT" "$LATEST_STAGE1_BIN" 2>/dev/null || true)"
if [[ -n "$LATEST_STAGE1_STALE_SOURCE" ]]; then
    echo "gate.sh: latest Elisa Stage1 product is stale: $LATEST_STAGE1_STALE_SOURCE" >&2
    echo "Re-seed/rebuild the latest Elisa compiler product before running the gate." >&2
    exit 1
fi
LATEST_STAGE1_HEAD="$(git -C "$LATEST_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || true)"
LATEST_STAGE1_ORIGIN_HEAD="$(git -C "$LATEST_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
if [[ -n "$LATEST_STAGE1_HEAD" && -n "$LATEST_STAGE1_ORIGIN_HEAD" ]]; then
    LATEST_STAGE1_BEHIND="$(git -C "$LATEST_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-list --count "$LATEST_STAGE1_HEAD..$LATEST_STAGE1_ORIGIN_HEAD" 2>/dev/null || echo 0)"
    if [[ "$LATEST_STAGE1_BEHIND" != 0 ]]; then
        echo "gate.sh: selected Elisa Stage1 checkout is $LATEST_STAGE1_BEHIND commit(s) behind origin/main" >&2
        echo "  local:  $LATEST_STAGE1_HEAD" >&2
        echo "  origin: $LATEST_STAGE1_ORIGIN_HEAD" >&2
        exit 1
    fi
fi

FULL=0
case "${1:-}" in
    "") ;;
    --full) FULL=1 ;;
    *)
        echo "gate.sh: unknown argument '$1' (expected: --full)" >&2
        exit 2
        ;;
esac

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

step "Python-compatible Marble wrapper norm" node "$ROOT/test/python_hypot_test.mjs"
step "Marble raw framebuffer capture contract" node "$ROOT/test/marble_framebuffer_capture_test.mjs"
step "Marble compiled status ownership across window sizes" node "$ROOT/test/marble_chrome_test.mjs"
step "Marble source-compatible glyph advance rounding" node "$ROOT/test/marble_text_metrics_test.mjs"
step "Marble source capture resolved-font evidence" python3 "$ROOT/test/marble_capture_font_test.py"

# --- fast: catalog and verification harness integrity -----------------------

step "reviewed original/Elisa/browser task catalog" \
    python3 "$ROOT/test/catalog_audit.py"

step "generated web task registry matches reviewed manifest" \
    python3 "$ROOT/scripts/generate_task_registry.py" --check

step "web menu stable-ID registry/order matches reviewed task catalog" \
    node "$ROOT/test/task_registry_test.mjs"

step "generic browser submit does not restore canned task grading" \
    node "$ROOT/test/task_submit_no_canned_answers_test.mjs"

step "checker verdict and mutation tests" \
    python3 -m unittest discover -s "$ROOT/test" -p check_result_test.py

step "differential harness isolation, lock, signal, and concurrency tests" \
    bash "$ROOT/test/check_harness_test.sh"

step "compiler source fingerprint tests" \
    python3 -m unittest discover -s "$ROOT/test" -p source_fingerprint_test.py

step "stage1 freshness tests" \
    python3 -m unittest discover -s "$ROOT/test" -p stage1_fresh_test.py

step "Elisa runtime include provenance" \
    env ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
        python3 -m unittest discover -s "$ROOT/test" -p runtime_include_provenance_test.py

step "Marble Newton trace label-aware scalar semantics" \
    python3 -m unittest discover -s "$ROOT/test" -p marble_trace_test.py

# Decoder/fixture gates need only Python's standard library. The separate
# RNE cross oracle requires the original application's NumPy/MuJoCo venv;
# do not accidentally import it through a broad filename glob in this tier.
for marble_oracle_test in marble_constraint_update_oracle_test.py \
        marble_cone_update_oracle_test.py marble_cone_hessian_oracle_test.py \
        marble_dense_solve_oracle_test.py \
        marble_inertia_oracle_test.py marble_iteration_trace_test.py \
        marble_primal_prepare_oracle_test.py marble_prepare_trace_test.py \
        marble_primal_eval_oracle_test.py marble_eval_trace_test.py \
        marble_solver_probe_inputs_test.py marble_noslip_residual_oracle_test.py \
        marble_solver_rejection_fixture_test.py \
        marble_qcqp_original_test.py marble_qcqp_trace_test.py \
        marble_qcqp_boundary_fixture_test.py \
        marble_qcqp_kernel_trace_test.py marble_qcqp_kernel_fixture_test.py \
        marble_iteration_constraint_oracle_test.py marble_gauss_oracle_test.py \
        marble_gauss_trace_test.py marble_gauss_fixture_test.py \
        marble_qcqp_small_original_test.py marble_qcqp2_fixture_test.py \
        marble_costchange_trace_test.py marble_costchange_oracle_test.py \
        marble_inertia_original_test.py \
        marble_rne_original_test.py \
        marble_comvel_original_test.py \
        marble_integrator_readset_test.py \
        marble_free_bias_model_test.py \
        marble_reference_arithmetic_test.py \
        marble_jacobian_original_test.py \
        marble_sphere_box_original_test.py \
        marble_frame_original_test.py \
        marble_quaternion_normalization_test.py \
        marble_small_sincos_model_test.py \
        marble_impedance_arithmetic_test.py \
        marble_source_matrix_replay_test.py \
        marble_shipping_patch_guard_test.py \
        marble_capture_elapsed_test.py \
        marble_physical_capture_test.py \
        marble_visual_evidence_audit_test.py \
        marble_speed_cap_hypot_test.py \
        marble_candidate_build_contract_test.py \
        marble_native_dot_oracle_test.py; do
    step "Marble exact-input oracle decoder: $marble_oracle_test" \
        python3 -m unittest discover -s "$ROOT/test" -p "$marble_oracle_test"
done

step "Marble diagnostic trace neutrality checker" \
    python3 -m unittest discover -s "$ROOT/test" -p marble_trace_neutrality_test.py

step "stage1 runtime provenance against selected stage0 source" \
    env ELISA_CORE="$ELISA_CORE" ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
        bash "$ROOT/scripts/check_stage1_runtime_provenance.sh"

# --- fast: the port's own differential suites --------------------------------

step "nw-core differential suites (both stages)" \
    env ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
        ELISA_STAGE1_BIN="$LATEST_STAGE1_BIN" "$ROOT/scripts/check.sh"

step "nw-core WebAssembly build + differential" \
    env \
        NW_WASM_OBJECT="$ROOT/build/verification/stage0/nwcore_wasm.o" \
        NW_WASM_ARTIFACT="$ROOT/build/verification/stage0/nwcore.wasm" \
        NW_WASM_BINDINGS_OUT="$ROOT/build/verification/stage0/nwcore" \
        "$ROOT/scripts/build_wasm.sh"

step "latest Elisa Stage1 WebAssembly build + matching artifact-level tests" \
    "$ROOT/scripts/build_latest_stage1_wasm.sh"

step "stage1 Glyphs optimizer RSS regression (-O1 and -O2)" \
    env ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
        ELISA_STAGE1_BIN="$LATEST_STAGE1_BIN" \
        bash "$ROOT/scripts/stage1_glyphs_memory_smoke.sh"

# --- medium: the compilers -----------------------------------------------

# env.sh enables strict FP for port parity. The compiler unit tests include
# default-mode IR assertions and set strict FP explicitly where they need it,
# so prevent the port's ambient build setting from leaking into their process.
step "stage0 fast test suite" \
    env -u ELISACORE_STRICT_FP make -C "$ELISA_CORE/compiler" test

# The parity smokes that cover the areas this port has touched. The full
# run_all.sh is in the slow tier: its semantic_internal_diff.sh step replays
# ~2400 tests one compilation at a time and runs for hours.
smokes() {
    local ok=0
    for smoke in try_fallible catch_exhaustive match_expr match_pattern \
                 match_exhaustive enum_constructor enum_tail_payload \
                 atomic_payload scalar_match_arm legacy_error_syntax \
                 wasm32_checked_index wasm32_darray_abi wasm32_sview_strlen \
                 wasm32_debug_referee wasm32_for_bounds_width \
                 qualified_generic_scope module_struct_field_type_collision \
                 module_struct_field_mutable module_struct_return_type \
                 module_struct_namespacing module_type_alias_namespacing \
                 module_struct_field_scope_matrix module_struct_field_ambiguous_external \
                 contextual_wide_i64_comparison region_capacity_const_expression; do
        local script="$LATEST_STAGE1_ROOT/test/parity/${smoke}_smoke.sh"
        [[ -f "$script" ]] || continue
        if ELISA_CORE="$ELISA_CORE" \
           ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
           ELISA_STAGE1_BIN="$LATEST_STAGE1_BIN" \
           bash "$script" >/dev/null 2>&1; then
            printf '    %-24s ok\n' "$smoke"
        else
            printf '    %-24s FAILED\n' "$smoke"
            ok=1
        fi
    done
    return $ok
}
step "stage1 targeted parity smokes" smokes

step "runtime provenance (unknown drift still fails)" \
    env ELISA_CORE="$ELISA_CORE" ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
        bash "$ROOT/scripts/check_stage1_runtime_provenance.sh"

# --- slow: only with --full --------------------------------------------------

if (( FULL )); then
    step "stage0 full native-runtime suite (~8 min)" \
        make -C "$ELISA_CORE/compiler" test-full

    step "stage1 self-host fixpoint (gen3 == gen4)" \
        env ELISA_CORE="$ELISA_CORE" \
            ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
            ELISA_STAGE1_BIN="$LATEST_STAGE1_BIN" \
            bash "$LATEST_STAGE1_ROOT/test/parity/self_host_gen3_smoke.sh"

    # Hours. This is the one that catches semantic divergence between the two
    # compilers across stage0's entire internal suite.
    step "stage1 full parity gate (HOURS)" \
        env ELISA_CORE="$ELISA_CORE" \
            ELISA_STAGE1_ROOT="$LATEST_STAGE1_ROOT" \
            ELISA_STAGE1_BIN="$LATEST_STAGE1_BIN" \
            bash "$LATEST_STAGE1_ROOT/test/parity/run_all.sh"
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
