#!/usr/bin/env bash
# Run the same browser-facing ABI and controller checks against any built core
# artifact, including stage0 and stage1. The tests accept NWCORE_WASM_PATH so
# no artifact is copied over another compiler's output to run the matrix.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WASM_PATH="${1:-${NWCORE_WASM_PATH:-$ROOT/build/nwcore.wasm}}"
if [[ "$WASM_PATH" != /* ]]; then
    WASM_PATH="$(cd -- "$(dirname -- "$WASM_PATH")" && pwd)/$(basename -- "$WASM_PATH")"
fi
if [[ ! -f "$WASM_PATH" ]]; then
    echo "test_wasm_artifact.sh: missing WASM artifact: $WASM_PATH" >&2
    exit 2
fi
export NWCORE_WASM_PATH="$WASM_PATH"

# Several differential fixtures intentionally import sibling modules from
# nw-core/test. Make the public script independent of its caller's working
# directory instead of relying on gate.sh to have already changed into ROOT.
cd "$ROOT"

# The reference venv selected by scripts/env.sh intentionally contains the
# original application's runtime dependencies, but not necessarily Pillow.
# Resolve a Python that can read the committed diagnostic PNGs instead of
# allowing the visual regression to fail with an opaque ModuleNotFoundError.
IMAGE_PYTHON="${PYTHON_IMAGE_BIN:-}"
if [[ -z "$IMAGE_PYTHON" ]]; then
    for candidate in python3 /usr/bin/python3; do
        if "$candidate" -c 'from PIL import Image' >/dev/null 2>&1; then
            IMAGE_PYTHON="$candidate"
            break
        fi
    done
fi
if [[ -z "$IMAGE_PYTHON" ]]; then
    echo "test_wasm_artifact.sh: Marble pixel regression requires Pillow" >&2
    echo "set PYTHON_IMAGE_BIN to a Python interpreter with PIL.Image" >&2
    exit 2
fi

node "$ROOT/test/result_store_test.mjs"
node "$ROOT/test/wasm_diff.mjs"
node "$ROOT/test/task_game_input_smoke.mjs"
node "$ROOT/test/monkey_ladder_state_frame_smoke.mjs"
node "$ROOT/test/monkey_ladder_run_smoke.mjs"
node "$ROOT/test/monkey_ladder_browser_contract_test.mjs"
node "$ROOT/test/nback3d_game_smoke.mjs"
python3 "$ROOT/test/nback3d_live_diff.py"
node "$ROOT/test/nback3d_browser_contract_test.mjs"
node "$ROOT/test/tetris_complete_run_smoke.mjs"
node "$ROOT/test/sokoban_game_smoke.mjs" "$WASM_PATH"
node "$ROOT/test/sokoban_browser_contract_test.mjs"
NWCORE_WASM_PATH="$WASM_PATH" node "$ROOT/test/sokoban3d_game_smoke.mjs"
node "$ROOT/test/sokoban3d_browser_contract_test.mjs"
NWCORE_WASM_PATH="$WASM_PATH" node "$ROOT/test/youarehere_game_smoke.mjs"
node "$ROOT/test/youarehere_browser_contract_test.mjs"
node "$ROOT/test/counting_game_smoke.mjs"
node "$ROOT/test/counting_browser_contract_test.mjs"
node "$ROOT/test/mrtime_game_smoke.mjs"
node "$ROOT/test/mrtime_browser_contract_test.mjs"
node "$ROOT/test/hanoi_game_smoke.mjs"
node "$ROOT/test/maze_game_smoke.mjs"
node "$ROOT/test/ninarow_game_smoke.mjs"
node "$ROOT/test/wasm_wide_integer_test.mjs"
node "$ROOT/test/numberology_game_smoke.mjs"
python3 "$ROOT/test/numberology_exact_oracle.py" --check
node "$ROOT/test/numberology_exact_game_test.mjs"
node "$ROOT/test/numberology_paging_test.mjs"
node "$ROOT/test/numberology_paging_web_test.mjs"
python3 "$ROOT/test/numberology_session_oracle.py" --check
node "$ROOT/test/numberology_session_replay_test.mjs"
node "$ROOT/test/numberology_browser_contract_test.mjs"
node "$ROOT/test/numberology_browser_options_test.mjs"
node "$ROOT/test/numberology_browser_integration_test.mjs"
node "$ROOT/test/numberology_browser_results_test.mjs"
node "$ROOT/test/inthedark_game_smoke.mjs"
node "$ROOT/test/fog_game_smoke.mjs"
node "$ROOT/test/concentration_game_smoke.mjs"
node "$ROOT/test/recognition_game_smoke.mjs"
node "$ROOT/test/trivia_game_smoke.mjs"
node "$ROOT/test/removals_game_smoke.mjs"
node "$ROOT/test/custody_game_smoke.mjs"
node "$ROOT/test/ncupmonte_game_smoke.mjs"
node "$ROOT/test/reflex_game_smoke.mjs"
node "$ROOT/test/tracking_game_smoke.mjs"
node "$ROOT/test/lookout_game_smoke.mjs"
node "$ROOT/test/pursuit_game_smoke.mjs"
node "$ROOT/test/donkey_game_smoke.mjs"
node "$ROOT/test/overrun_game_smoke.mjs"
node "$ROOT/test/two_hands_browser_contract_test.mjs"
node "$ROOT/test/two_hands_game_smoke.mjs"
node "$ROOT/test/buzzwire_game_smoke.mjs"
node "$ROOT/test/outofsight_game_smoke.mjs"
node "$ROOT/test/graphmapping_game_smoke.mjs"
node "$ROOT/test/graphmapping_browser_contract_test.mjs"
node "$ROOT/test/crossedwires_game_smoke.mjs"
node "$ROOT/test/crossedwires_browser_contract_test.mjs"
node "$ROOT/test/crossedwires_original_replay_test.mjs"
node "$ROOT/test/sudoku_game_smoke.mjs"
node "$ROOT/test/sudoku_browser_contract_test.mjs"
node "$ROOT/test/sudoku_original_replay_test.mjs"
node "$ROOT/test/ravens_game_smoke.mjs"
node "$ROOT/test/ravens_browser_contract_test.mjs"
node "$ROOT/test/jigsaw_game_smoke.mjs"
node "$ROOT/test/jigsaw_browser_contract_test.mjs"
node "$ROOT/test/go_game_smoke.mjs"
node "$ROOT/test/go_browser_contract_test.mjs"
node "$ROOT/test/go_original_replay_test.mjs"
node "$ROOT/test/algebra_game_smoke.mjs"
node "$ROOT/test/algebra_exact_game_test.mjs"
node "$ROOT/test/algebra_feedback_test.mjs"
python3 "$ROOT/test/algebra_working_oracle.py" --check
node "$ROOT/test/algebra_working_test.mjs"
node "$ROOT/test/algebra_multiline_test.mjs"
node "$ROOT/test/algebra_options_game_test.mjs"
node "$ROOT/test/algebra_score_game_test.mjs"
node "$ROOT/test/algebra_input_events_test.mjs"
node "$ROOT/test/algebra_browser_contract_test.mjs"
python3 "$ROOT/scripts/generate_scramble_seed.py" --check
node "$ROOT/test/scramble_game_smoke.mjs"
node "$ROOT/test/scramble_seed_game_test.mjs"
node "$ROOT/test/scramble_corpus_game_test.mjs"
node "$ROOT/test/scramble_browser_corpus_test.mjs"
node "$ROOT/test/scramble_lifecycle_test.mjs"
node "$ROOT/test/scramble_browser_contract_test.mjs"
node "$ROOT/test/scramble_input_events_test.mjs"
python3 "$ROOT/test/scrabble_seed_integrity.py"
node "$ROOT/test/scrabble_game_smoke.mjs"
node "$ROOT/test/scrabble_browser_contract_test.mjs"
node "$ROOT/test/scrabble_browser_index_test.mjs"
node "$ROOT/test/crossword_game_smoke.mjs"
node "$ROOT/test/crossword_browser_contract_test.mjs"
node "$ROOT/test/crossword_original_replay_test.mjs"
node "$ROOT/test/syllogism_game_smoke.mjs"
node "$ROOT/test/syllogism_feedback_test.mjs"
python3 "$ROOT/test/syllogism_session_oracle.py" --check
node "$ROOT/test/syllogism_session_replay_test.mjs"
node "$ROOT/test/syllogism_browser_contract_test.mjs"
node "$ROOT/test/syllogism_browser_options_test.mjs"
node "$ROOT/test/chess_game_smoke.mjs"
node "$ROOT/test/chess_browser_contract_test.mjs"
node "$ROOT/test/verbal_game_smoke.mjs"
node "$ROOT/test/verbal_browser_contract_test.mjs"
node "$ROOT/test/runtime_protocol_v1_smoke.mjs"
node "$ROOT/test/marble_maze_browser_test.mjs"
node "$ROOT/test/marble_options_matrix_test.mjs"
node "$ROOT/test/marble_ui_source_contract_test.mjs"
node "$ROOT/test/marble_renderer_contract_test.mjs"
"$IMAGE_PYTHON" "$ROOT/test/marble_source_abi_fixture_test.py"
"$IMAGE_PYTHON" "$ROOT/test/marble_render_pair_contract_test.py"
"$IMAGE_PYTHON" "$ROOT/test/marble_browser_pair_metadata_test.py"
"$IMAGE_PYTHON" "$ROOT/test/marble_render_pair_test.py" \
    "$ROOT/output/playwright/marble-shadow-span-source-dynamic-912-canvas.png" \
    "$ROOT/output/playwright/marble-shadow-span-912-canvas.png" \
    --pixel-threshold 10
node "$ROOT/test/marble_maze_mujoco_test.mjs"
node "$ROOT/test/marble_generated_session_test.mjs"
node "$ROOT/test/marble_generated_play_session_test.mjs"
node "$ROOT/test/marble_multi_trial_session_test.mjs"
node "$ROOT/test/marble_board_abi_test.mjs"
node "$ROOT/test/marble_source_reference_diff.mjs"
node "$ROOT/test/marble_trajectory_reference_diff.mjs"
if [[ -n "${NWCORE_STAGE0_WASM_PATH:-}" && -n "${NWCORE_STAGE1_WASM_PATH:-}" ]]; then
    node "$ROOT/test/marble_cross_compiler_parity_test.mjs"
fi
