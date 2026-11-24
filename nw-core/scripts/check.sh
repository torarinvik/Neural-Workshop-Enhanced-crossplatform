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

# Parse the Numberology sources independently before loading the selected
# runtime. This distinguishes a source syntax regression from runtime/toolchain
# incompatibility in the full Stage0 differential build.
if [[ "${SUITE:-}" == numberology_exact && ( "$STAGES" == "stage0" || "$STAGES" == "both" ) ]]; then
    python3 "$ROOT/test/numberology_syntax_test.py" || exit 1
fi

# Stage0 differential compiles may cause the selected compiler to emit its
# generated fmt_*_probe.elisa fixtures. Establish freshness before that can
# happen, then allow those generated probe mtimes during the Stage1 loop. This
# does not weaken the gate for real compiler edits: the snapshot check below
# still rejects a product older than any non-generated compiler source.
if [[ "$STAGES" == "both" || "$STAGES" == "stage1" ]]; then
    stage1_stale_source="$(python3 "$ROOT/scripts/stage1_fresh.py" \
        "$ELISA_STAGE1_ROOT" "$ELISA_STAGE1_BIN" 2>/dev/null || true)"
    if [[ -n "$stage1_stale_source" ]]; then
        echo "check.sh: latest Stage1 product is stale: $stage1_stale_source" >&2
        exit 2
    fi
fi

# The latest compiler checkout is shared with other Elisa work.  A source edit
# or reseed after the freshness check would otherwise let this long sweep mix
# results from two different compiler products and report an ambiguous failure.
# Capture a content-aware snapshot now; generated formatting probes are already
# excluded by source_fingerprint.py.  The snapshot is checked again after the
# final suite, so a concurrent compiler edit is reported as provenance drift
# rather than being mistaken for a port regression.
STAGE1_SNAPSHOT_HEAD=""
STAGE1_SNAPSHOT_ORIGIN_HEAD=""
STAGE1_SNAPSHOT_FINGERPRINT=""
STAGE1_SNAPSHOT_PRODUCT=""
stage1_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}
if [[ "$STAGES" == "both" || "$STAGES" == "stage1" ]]; then
    STAGE1_SNAPSHOT_HEAD="$(git -C "$ELISA_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || echo unknown)"
    STAGE1_SNAPSHOT_ORIGIN_HEAD="$(git -C "$ELISA_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
    STAGE1_SNAPSHOT_FINGERPRINT="$(python3 "$ROOT/scripts/source_fingerprint.py" "$ELISA_STAGE1_ROOT")"
    STAGE1_SNAPSHOT_PRODUCT="$(stage1_sha256 "$ELISA_STAGE1_BIN")"
fi
# Tests and scratch invocations can provide a private build root; ordinary
# developer and release runs continue to use the repository build directory.
BUILD="${NW_CHECK_BUILD_DIR:-$ROOT/build}"
mkdir -p "$BUILD"

# Several suites still exchange data through fixed /tmp/nw_* oracle paths.
# Serialize all official check.sh runs for this user, including invocations
# from different worktrees, or one run can replace another's fixture between
# compilation and comparison. NW_CHECK_LOCK_PATH is available for isolated
# harness tests; normal runs share a per-user lock in TMPDIR.
CHECK_LOCK="${NW_CHECK_LOCK_PATH:-${TMPDIR:-/tmp}/nw-core-check-${UID}.lock}"
CHECK_LOCK_TOKEN="$$-$RANDOM-$(date +%s)"
process_start() {
    ps -p "$1" -o lstart= 2>/dev/null | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}
path_mtime() {
    stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1" 2>/dev/null || true
}
while ! mkdir "$CHECK_LOCK" 2>/dev/null; do
    owner_pid=""
    owner_start=""
    if [[ -f "$CHECK_LOCK/owner" ]]; then
        owner_pid="$(sed -n '1p' "$CHECK_LOCK/owner")"
        owner_start="$(sed -n '2p' "$CHECK_LOCK/owner")"
    fi
    if [[ "$owner_pid" =~ ^[0-9]+$ && -n "$owner_start" ]]; then
        live_start="$(process_start "$owner_pid")"
        if [[ -z "$live_start" || "$live_start" != "$owner_start" ]]; then
            unlink "$CHECK_LOCK/owner" 2>/dev/null || true
            rmdir "$CHECK_LOCK" 2>/dev/null || true
            continue
        fi
    elif [[ -d "$CHECK_LOCK" ]]; then
        # mkdir and writing the owner record are separate filesystem calls.
        # Recover only a recordless/partial lock that has been idle for 5s;
        # rmdir still refuses to remove any unexpected contents.
        lock_mtime="$(path_mtime "$CHECK_LOCK")"
        now="$(date +%s)"
        if [[ "$lock_mtime" =~ ^[0-9]+$ && "$now" =~ ^[0-9]+$ ]] &&
           (( now - lock_mtime >= 5 )); then
            [[ -e "$CHECK_LOCK/owner" ]] && unlink "$CHECK_LOCK/owner" 2>/dev/null || true
            rmdir "$CHECK_LOCK" 2>/dev/null || true
            continue
        fi
    fi
    sleep 1
done
owner_start="$(process_start "$$")"
printf '%s\n%s\n%s\n' "$$" "$owner_start" "$CHECK_LOCK_TOKEN" > "$CHECK_LOCK/owner"
release_check_lock() {
    if [[ -f "$CHECK_LOCK/owner" ]] &&
       [[ "$(sed -n '3p' "$CHECK_LOCK/owner")" == "$CHECK_LOCK_TOKEN" ]]; then
        unlink "$CHECK_LOCK/owner" 2>/dev/null || true
        rmdir "$CHECK_LOCK" 2>/dev/null || true
    fi
}
on_check_signal() {
    case "$1" in
        INT) exit 130 ;;
        TERM) exit 143 ;;
        HUP) exit 129 ;;
    esac
}
trap release_check_lock EXIT
trap 'on_check_signal INT' INT
trap 'on_check_signal TERM' TERM
trap 'on_check_signal HUP' HUP

RUN_DIR="$(mktemp -d "$BUILD/check.XXXXXX")" || {
    echo "check.sh: could not create an isolated run directory under $BUILD" >&2
    exit 1
}
SOURCE_ROOT="$RUN_DIR/source"
python3 "$ROOT/scripts/prepare_runtime_sources.py" \
    "$ROOT" "$SOURCE_ROOT" "$ELISA_STAGE1_ROOT"

SUITES=(pyset scheduling timing board grid nback pyrandom stimulus stats sessionscore readouttext trialuitext matching display config gamemode decimal session sessionapp maze fogworld numberology ninarow inthedark crossedwires cookiethief cookiethief_game custody donkey tetris removals sokoban sokoban_game go go_rules twohands buzzwire marblemaze syllogism title menu menurow sudoku youarehere hanoi monkeyladder ncupmonte reflex salesman counting tracking concentration recognition lookout pursuit outofsight overrun mrtime jigsaw sokoban3d verbal scramble scrabble trivia crossword graphmapping hidden_rule hidden_wiring ravens chess bigfrac expressions algebra glyphs scene_removals scene_monkeyladder scene_hanoi scene_go scene_ninarow scene_crossedwires scene_ncupmonte scene_sudoku scene_chess scene_algebra scene_numberology scene_verbal scene_scramble scene_trivia scene_tracking scene_sokoban scene_salesman scene_counting scene_syllogism scene_maze scene_inthedark scene_overrun scene_crossword scene_lookout scene_pursuit scene_reflex scene_recognition scene_concentration scene_jigsaw scene_donkey scene_custody scene_cookiethief scene_youarehere scene_sokoban3d scene_scrabble scene_mrtime scene_graphmapping scene_outofsight scene_tetris scene_twohands scene_ravens scene_marblemaze scene_buzzwire scene_taskhub scene_fogofwar scene_trialui scene_notice scene_hud scene_readouts scene_graph scene_field scene_menuchrome trialphase textmetrics screen hudtext)

# One suite by name, for the inner loop.
SUITES+=(crossword_capacity crossword_lexicon hold_it hold_it_audio notebook rooms nearer mirror pov inside touching crossings time_it balance juggler lander beat beat_audio glider catch catch_audio echo_cave echo_cave_audio drone_hoops drone_hoops_sound drone_hoops_audio field_manual field_manual_audio safecracker safecracker_audio stagehand stagehand_audio loading_dock loading_dock_audio gunslinger gunslinger_audio camera camera_render what_next falls sfm drshape drshape_audio drshape_game tuner tuner_audio tuner_recordings tuner_game shadow_play shadow_play_scene captcha captcha_scene signals fold fold_scene beliefs beliefs_scene damkeeper damkeeper_scene sonar sonar_scene gamble gamble_scene dispatch dispatch_scene bluff bluff_scene crossroads crossroads_scene railyard railyard_scene airtraffic airtraffic_scene escort escort_scene sokobanlive sokobanlive_scene kitchen kitchen_scene crane crane_scene ferry ferry_scene docking docking_scene docking_audio rover rover_game rover_audio rover_scene unicycle unicycle_scene unicycle_audio morning_round morning_round_rules morning_round_ride morning_round_words morning_round_audio morning_round_scene heavier heavier_audio heavier_scene full_stop full_stop_audio full_stop_scene missing_word missing_word_audio proofreader proofreader_audio figures_of_speech reading_quiz_audio crazy_cog crazy_cog_audio crazy_cog_scene cipher_lang cipher_abyss_family cipher_abyss_round cipher_abyss_play potter potter_scene conductor conductor_scene tightrope tightrope_scene signpainter signpainter_scene bartender bartender_scene lockpick lockpick_scene airhockey airhockey_scene semaphore semaphore_scene shadowpuppets shadowpuppets_scene nightwatch nightwatch_scene kerbside kerbside_scene steadicam steadicam_scene freekick freekick_scene glove glove_scene byear byear_scene pianotuner pianotuner_scene pianotuner_audio crickethunt crickethunt_scene crickethunt_audio clawmachine clawmachine_scene betweenlines secondthoughts badargument socialsense whichfeeling howstrongly readingpeople whytheyfeel toneofvoice emotionfaces)
# The exact suite uses the current runtime BigInt intrinsics; the pinned
# Stage0 runtime is not yet compatible with that runtime source.
if [[ "${SUITE:-}" == numberology_exact ]]; then
    SUITES+=(numberology_exact)
fi
if [[ "${SUITE:-}" == scramble_real_index ]]; then
    SUITES+=(scramble_real_index)
fi
if [[ "${SUITE:-}" == scrabble_real_index ]]; then
    SUITES+=(scrabble_real_index)
fi
if [[ "${SUITE:-}" == crossword_real_index ]]; then
    SUITES+=(crossword_real_index)
fi
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
# These fixtures depend on current Stage1 display, synth, or region support.
STAGE1_ONLY=(docking_scene docking_audio rover_game rover_audio rover_scene unicycle_scene unicycle_audio morning_round_words morning_round_audio morning_round_scene heavier_audio heavier_scene full_stop full_stop_audio full_stop_scene missing_word missing_word_audio proofreader proofreader_audio figures_of_speech reading_quiz_audio crazy_cog crazy_cog_audio crazy_cog_scene cipher_lang cipher_abyss_family cipher_abyss_round cipher_abyss_play potter potter_scene conductor conductor_scene tightrope tightrope_scene signpainter signpainter_scene bartender bartender_scene lockpick lockpick_scene airhockey airhockey_scene semaphore semaphore_scene shadowpuppets shadowpuppets_scene nightwatch nightwatch_scene kerbside kerbside_scene steadicam steadicam_scene freekick freekick_scene glove glove_scene byear byear_scene pianotuner pianotuner_scene pianotuner_audio crickethunt crickethunt_scene crickethunt_audio clawmachine clawmachine_scene betweenlines secondthoughts badargument socialsense whichfeeling howstrongly readingpeople whytheyfeel toneofvoice emotionfaces)

failures=0
run_suite() {
    local suite="$1" stage="$2" binary="$RUN_DIR/${1}_sweep_${2}"
    local compile_log="$RUN_DIR/${suite}_${stage}.compile.log"
    local link_log="$RUN_DIR/${suite}_${stage}.link.log"
    local stdout_log="$RUN_DIR/${suite}_${stage}.stdout.log"
    local stderr_log="$RUN_DIR/${suite}_${stage}.stderr.log"
    local result_json="$RUN_DIR/${suite}_${stage}.result.json"
    local compile_exit=-1 link_exit=-1 checker_exit=-1
    local -a precision=()
    # Dial ticks are emitted at integral crossings. Match the Python
    # reference without contraction rounding across that boundary.
    # Recorded audio also uses separate multiplies and additions in Python.
    if [[ "$suite" == safecracker || "$suite" == safecracker_audio || "$suite" == tuner_recordings || "$suite" == docking || "$suite" == docking_scene || "$suite" == docking_audio || "$suite" == rover || "$suite" == rover_game || "$suite" == rover_audio || "$suite" == rover_scene || "$suite" == unicycle || "$suite" == unicycle_scene || "$suite" == unicycle_audio || "$suite" == morning_round || "$suite" == morning_round_rules || "$suite" == morning_round_ride || "$suite" == morning_round_words || "$suite" == morning_round_audio || "$suite" == morning_round_scene || "$suite" == heavier || "$suite" == heavier_audio || "$suite" == heavier_scene || "$suite" == full_stop || "$suite" == full_stop_audio || "$suite" == full_stop_scene || "$suite" == missing_word || "$suite" == missing_word_audio || "$suite" == proofreader || "$suite" == proofreader_audio || "$suite" == figures_of_speech || "$suite" == reading_quiz_audio || "$suite" == crazy_cog || "$suite" == crazy_cog_audio || "$suite" == crazy_cog_scene || "$suite" == cipher_abyss_play || "$suite" == potter || "$suite" == potter_scene || "$suite" == conductor || "$suite" == conductor_scene || "$suite" == tightrope || "$suite" == tightrope_scene || "$suite" == signpainter || "$suite" == signpainter_scene || "$suite" == bartender || "$suite" == bartender_scene || "$suite" == lockpick || "$suite" == lockpick_scene || "$suite" == airhockey || "$suite" == airhockey_scene || "$suite" == semaphore || "$suite" == semaphore_scene || "$suite" == shadowpuppets || "$suite" == shadowpuppets_scene || "$suite" == kerbside || "$suite" == steadicam || "$suite" == steadicam_scene || "$suite" == freekick || "$suite" == freekick_scene || "$suite" == glove || "$suite" == glove_scene || "$suite" == byear || "$suite" == byear_scene || "$suite" == pianotuner || "$suite" == pianotuner_scene || "$suite" == pianotuner_audio || "$suite" == crickethunt || "$suite" == crickethunt_scene || "$suite" == crickethunt_audio || "$suite" == clawmachine || "$suite" == clawmachine_scene || "$suite" == betweenlines || "$suite" == secondthoughts || "$suite" == badargument || "$suite" == socialsense || "$suite" == whichfeeling || "$suite" == howstrongly || "$suite" == readingpeople || "$suite" == whytheyfeel || "$suite" == toneofvoice || "$suite" == emotionfaces || "$suite" == kerbside_scene || "$suite" == nightwatch || "$suite" == nightwatch_scene ]]; then
        precision=(env ELISACORE_STRICT_FP=1)
    fi

    if [[ "$stage" == "stage0" ]]; then
        if ${precision[@]+"${precision[@]}"} "$ELISACORE_BIN" -emit obj -O2 -o "$RUN_DIR/${suite}_${stage}.o" \
                "$SOURCE_ROOT/test/${suite}_sweep.elisa" >"$compile_log" 2>&1; then
            compile_exit=0
        else
            compile_exit=$?
        fi
        if (( compile_exit == 0 )); then
            # A standalone sweep needs the same weak profiler-hook fallback as
            # ordinary native executables. Linking the complete runtime object
            # here also pulls in the runtime's native callback ABI, which these
            # sweeps do not use and cannot satisfy.
            if clang -o "$binary" "$RUN_DIR/${suite}_${stage}.o" \
                    "$ELISA_CORE/compiler/runtime/profile_hooks.c" >"$link_log" 2>&1; then
                link_exit=0
            else
                link_exit=$?
            fi
        fi
    else
        if ELISA_ALLOW_STALE_STAGE1=1 ${precision[@]+"${precision[@]}"} "$ELISA_STAGE1_ROOT/scripts/elisac_stage1.sh" -emit exe -O2 -o "$binary" \
                "$SOURCE_ROOT/test/${suite}_sweep.elisa" >"$compile_log" 2>&1; then
            compile_exit=0
            link_exit=0
        else
            compile_exit=$?
        fi
    fi

    if (( compile_exit == 0 && link_exit == 0 )); then
        if python3 "$ROOT/test/${suite}_diff.py" "$binary" >"$stdout_log" 2>"$stderr_log"; then
            checker_exit=0
        else
            checker_exit=$?
        fi
    else
        : > "$stdout_log"
        : > "$stderr_log"
    fi

    local validation
    if validation="$(python3 "$ROOT/scripts/check_result.py" \
            --suite "$suite" --stage "$stage" \
            --checker-exit "$checker_exit" --compile-exit "$compile_exit" \
            --link-exit "$link_exit" --stdout "$stdout_log" \
            --stderr "$stderr_log" --compile-log "$compile_log" \
            --link-log "$link_log" --output "$result_json")"; then
        local cases verdict
        cases="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["case_count"])' "$result_json")"
        verdict="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verdict"])' "$result_json")"
        echo "  ${suite} [${stage}]: ${verdict} (result: $result_json; cases: $cases)"
        return 0
    fi
    echo "  ${suite} [${stage}]: FAILED (result: $result_json)"
    if (( compile_exit != 0 )); then
        sed -n '1,120p' "$compile_log"
    elif (( link_exit != 0 )); then
        sed -n '1,120p' "$link_log"
    else
        sed -n '1,160p' "$stdout_log"
        sed -n '1,160p' "$stderr_log"
    fi
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
        if [[ "$stage" == "stage0" ]] && [[ " ${STAGE1_ONLY[*]} " == *" $suite "* ]]; then
            echo "  ${suite} [${stage}]: SKIPPED (requires current Stage1 runtime modules)"
            continue
        fi
        run_suite "$suite" "$stage" || failures=$((failures + 1))
    done
done

if [[ -n "$STAGE1_SNAPSHOT_FINGERPRINT" ]]; then
    stage1_post_head="$(git -C "$ELISA_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || echo unknown)"
    stage1_post_origin_head="$(git -C "$ELISA_STAGE1_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
    stage1_post_fingerprint="$(python3 "$ROOT/scripts/source_fingerprint.py" "$ELISA_STAGE1_ROOT")"
    stage1_post_product="$(stage1_sha256 "$ELISA_STAGE1_BIN")"
    if [[ "$stage1_post_head" != "$STAGE1_SNAPSHOT_HEAD" ||
          "$stage1_post_origin_head" != "$STAGE1_SNAPSHOT_ORIGIN_HEAD" ||
          "$stage1_post_fingerprint" != "$STAGE1_SNAPSHOT_FINGERPRINT" ||
          "$stage1_post_product" != "$STAGE1_SNAPSHOT_PRODUCT" ]]; then
        echo "check.sh: latest Stage1 compiler provenance changed during the sweep" >&2
        echo "  before: HEAD=$STAGE1_SNAPSHOT_HEAD origin/main=${STAGE1_SNAPSHOT_ORIGIN_HEAD:-<absent>} fingerprint=$STAGE1_SNAPSHOT_FINGERPRINT product=$STAGE1_SNAPSHOT_PRODUCT" >&2
        echo "  after:  HEAD=$stage1_post_head origin/main=${stage1_post_origin_head:-<absent>} fingerprint=$stage1_post_fingerprint product=$stage1_post_product" >&2
        echo "check.sh: rerun only after the shared Elisa compiler checkout is quiescent" >&2
        failures=$((failures + 1))
    fi
fi

echo
if (( failures )); then
    echo "FAILED: $failures suite run(s)"
    exit 1
fi
echo "All differential suites match the Python reference."
