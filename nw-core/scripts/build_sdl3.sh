#!/usr/bin/env bash
# Build the native SDL3 desktop shell.
#
# The SDL shell uses an explicit native export unit rather than the browser
# WASM export surface. The browser unit contains a wasm32 memory intrinsic and
# the full controller registry; native controllers are added to the SDL unit
# with their own lifecycle and frame-buffer ABI.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
mkdir -p "$ROOT/build"

PROJECTS_ROOT="$(cd -- "$ROOT/../.." && pwd)"
LATEST_ROOT="${ELISA_LATEST_STAGE1_ROOT:-$ELISA_STAGE1_ROOT}"
LATEST_BIN="${ELISA_LATEST_STAGE1_BIN:-$ELISA_STAGE1_BIN}"

SDL_CFLAGS="$(pkg-config --cflags sdl3 2>/dev/null || echo "-I/opt/homebrew/include")"
SDL_LIBS="$(pkg-config --libs sdl3 2>/dev/null || echo "-L/opt/homebrew/lib -lSDL3")"

TTF_INPUTS=()
TTF_LIBS=""
if [[ "${NW_SDL_TTF:-0}" == 1 ]]; then
    TTF_LIBS="$(pkg-config --libs sdl3-ttf)"
fi

if [[ -n "${ELISA_SDL_COMPILER:-}" ]]; then
    NATIVE_COMPILER="$ELISA_SDL_COMPILER"
    RUNTIME_ROOT="${ELISA_SDL_RUNTIME_ROOT:-$ELISA_STAGE1_ROOT}"
else
    if [[ ! -x "$LATEST_ROOT/scripts/elisac_stage1.sh" || ! -x "$LATEST_BIN" ]]; then
        echo "build_sdl3.sh: latest Elisa Stage1 checkout/product missing" >&2
        echo "  checkout: $LATEST_ROOT" >&2
        echo "  product:  $LATEST_BIN" >&2
        echo "Set ELISA_SDL_COMPILER for an explicit override, or set" >&2
        echo "ELISA_LATEST_STAGE1_ROOT and ELISA_LATEST_STAGE1_BIN." >&2
        exit 2
    fi
    stale_source="$(python3 "$ROOT/scripts/stage1_fresh.py" \
        "$LATEST_ROOT" "$LATEST_BIN" 2>/dev/null || true)"
    if [[ -n "$stale_source" ]]; then
        echo "build_sdl3.sh: latest Elisa Stage1 product is stale: $stale_source" >&2
        echo "Re-seed/rebuild the latest Elisa compiler product before building." >&2
        exit 2
    fi
    latest_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || true)"
    latest_origin_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
    if [[ -n "$latest_head" && -n "$latest_origin_head" ]]; then
        latest_behind="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-list --count "$latest_head..$latest_origin_head" 2>/dev/null || echo 0)"
        if [[ "$latest_behind" != 0 ]]; then
            echo "build_sdl3.sh: selected Elisa Stage1 checkout is $latest_behind commit(s) behind origin/main" >&2
            exit 2
        fi
    fi
    NATIVE_COMPILER="$LATEST_BIN"
    RUNTIME_ROOT="${ELISA_SDL_RUNTIME_ROOT:-$LATEST_ROOT}"
fi

# The raw Stage1 driver uses these predicates when lowering platform code.
host_system="$(uname -s)"
exe_suffix=""
case "$host_system" in
    Linux) export ELISA_HOST_LINUX=1 ;;
    MINGW*|MSYS*|UCRT*|CYGWIN*)
        export ELISA_HOST_WINDOWS=1
        exe_suffix=".exe"
        ;;
esac
if [[ "$(uname -m)" == x86_64 ]]; then
    export ELISA_HOST_X86_64=1
fi

DESKTOP_BINARY="$ROOT/build/nw-sdl3$exe_suffix"
MARBLE_BINARY="$ROOT/build/nw-sdl3-mujoco$exe_suffix"

printf 'Elisa Stage1 compiler: %s\n' "$NATIVE_COMPILER"

SOURCE_TREE_PARENT="$(mktemp -d "$ROOT/build/sdl3-sources.XXXXXX")"
SOURCE_TREE="$SOURCE_TREE_PARENT/source"
NATIVE_LINK_OBJECT="$SOURCE_TREE_PARENT/nwcore_native_link.o"
trap 'rm -rf -- "$SOURCE_TREE_PARENT"' EXIT INT TERM HUP
RUNTIME_OBJ="${ELISA_SDL_RUNTIME_OBJ:-$RUNTIME_ROOT/build/runtime/elisacore_runtime.o}"
if [[ ! -f "$RUNTIME_OBJ" ]]; then
    echo "build_sdl3.sh: selected Stage1 runtime object is missing: $RUNTIME_OBJ" >&2
    echo "Set ELISA_SDL_RUNTIME_OBJ to the matching elisacore_runtime.o." >&2
    exit 2
fi
python3 "$ROOT/scripts/prepare_runtime_sources.py" \
    "$ROOT" "$SOURCE_TREE" "$RUNTIME_ROOT"

"$NATIVE_COMPILER" -emit obj -O2 -o "$ROOT/build/nwcore_native.o" \
    "$SOURCE_TREE/src/native/sdl_exports.elisa"

if [[ "${NW_SDL_TTF:-0}" == 1 ]]; then
    TTF_OBJECT="$SOURCE_TREE_PARENT/font_ttf.o"
    "$NATIVE_COMPILER" -emit obj -O2 -o "$TTF_OBJECT" "$SOURCE_TREE/src/native/sdl_font_ttf.elisa"
    TTF_INPUTS=("$TTF_OBJECT")
fi

# Keep the original object for inspection and future consumers. The private
# link object redirects the eight common arena/cache cells to the selected
# runtime object's single process-wide definitions.
python3 "$ROOT/scripts/prepare_native_object.py" \
    "$ROOT/build/nwcore_native.o" "$NATIVE_LINK_OBJECT"

RUNTIME_LINK_FLAGS=()
case "$host_system" in
    Darwin) RUNTIME_LINK_FLAGS=(-Wl,-dead_strip) ;;
    Linux) RUNTIME_LINK_FLAGS=(-Wl,--allow-multiple-definition -lm) ;;
    MINGW*|MSYS*|UCRT*|CYGWIN*) RUNTIME_LINK_FLAGS=(-Wl,--allow-multiple-definition) ;;
esac

# Provide a small public surface for native agents without a C entry point.
agent_exports=(nw_glider_agent_create nw_glider_agent_destroy nw_glider_agent_act nw_glider_agent_publish
    nw_lander_agent_create nw_lander_agent_destroy nw_lander_agent_act nw_lander_agent_publish
    nw_juggler_agent_create nw_juggler_agent_destroy nw_juggler_agent_act nw_juggler_agent_publish
    nw_balance_agent_create nw_balance_agent_destroy nw_balance_agent_act nw_balance_agent_publish
    nw_time_it_agent_create nw_time_it_agent_destroy nw_time_it_agent_act nw_time_it_agent_publish nw_time_it_agent_audio
    nw_beat_agent_create nw_beat_agent_destroy nw_beat_agent_act nw_beat_agent_publish nw_beat_agent_audio
    nw_catch_agent_create nw_catch_agent_destroy nw_catch_agent_act nw_catch_agent_publish nw_catch_agent_audio nw_catch_agent_act_mask
    nw_echo_cave_agent_create nw_echo_cave_agent_destroy nw_echo_cave_agent_act nw_echo_cave_agent_publish nw_echo_cave_agent_audio nw_echo_cave_agent_act_mask
    nw_drone_hoops_agent_create nw_drone_hoops_agent_destroy nw_drone_hoops_agent_act nw_drone_hoops_agent_publish nw_drone_hoops_agent_audio nw_drone_hoops_agent_act_mask
    nw_field_manual_agent_create nw_field_manual_agent_destroy nw_field_manual_agent_act nw_field_manual_agent_publish nw_field_manual_agent_audio
    nw_safecracker_agent_create nw_safecracker_agent_destroy nw_safecracker_agent_act nw_safecracker_agent_publish nw_safecracker_agent_audio
    nw_stagehand_agent_create nw_stagehand_agent_destroy nw_stagehand_agent_act nw_stagehand_agent_publish nw_stagehand_agent_audio
    nw_loading_dock_agent_create nw_loading_dock_agent_destroy nw_loading_dock_agent_act nw_loading_dock_agent_publish nw_loading_dock_agent_audio
    nw_gunslinger_agent_create nw_gunslinger_agent_destroy nw_gunslinger_agent_act nw_gunslinger_agent_publish nw_gunslinger_agent_audio
    nw_dr_shape_agent_create nw_dr_shape_agent_destroy nw_dr_shape_agent_act nw_dr_shape_agent_publish nw_dr_shape_agent_audio
    nw_tuner_agent_create nw_tuner_agent_destroy nw_tuner_agent_act nw_tuner_agent_publish nw_tuner_agent_audio
    nw_shadow_play_agent_create nw_shadow_play_agent_destroy nw_shadow_play_agent_act nw_shadow_play_agent_publish nw_shadow_play_agent_audio
    nw_crossings_agent_create nw_crossings_agent_destroy nw_crossings_agent_act nw_crossings_agent_publish
    nw_touching_agent_create nw_touching_agent_destroy nw_touching_agent_act nw_touching_agent_publish
    nw_will_it_fall_agent_create nw_will_it_fall_agent_destroy
    nw_will_it_fall_agent_act nw_will_it_fall_agent_publish
    nw_captcha_agent_create nw_captcha_agent_destroy nw_captcha_agent_act nw_captcha_agent_publish
    nw_signals_agent_create nw_signals_agent_destroy nw_signals_agent_act nw_signals_agent_publish
    nw_fold_it_agent_create nw_fold_it_agent_destroy nw_fold_it_agent_act nw_fold_it_agent_publish
    nw_who_knows_what_agent_create nw_who_knows_what_agent_destroy nw_who_knows_what_agent_act nw_who_knows_what_agent_publish
    nw_sonar_agent_create nw_sonar_agent_destroy nw_sonar_agent_act nw_sonar_agent_publish
    nw_gamble_agent_create nw_gamble_agent_destroy nw_gamble_agent_act nw_gamble_agent_publish
    nw_bluff_agent_create nw_bluff_agent_destroy nw_bluff_agent_act nw_bluff_agent_publish
    nw_explore_exploit_agent_create nw_explore_exploit_agent_destroy nw_explore_exploit_agent_act nw_explore_exploit_agent_publish
    nw_shape_from_motion_agent_create nw_shape_from_motion_agent_destroy
    nw_shape_from_motion_agent_act nw_shape_from_motion_agent_publish
    nw_dam_keeper_agent_create nw_dam_keeper_agent_destroy
    nw_dispatch_agent_create nw_dispatch_agent_destroy
    nw_firebreak_agent_create nw_firebreak_agent_destroy nw_firebreak_agent_act nw_firebreak_agent_publish
    nw_crossroads_agent_create nw_crossroads_agent_destroy nw_crossroads_agent_act nw_crossroads_agent_publish
    nw_railyard_agent_create nw_railyard_agent_destroy nw_railyard_agent_act nw_railyard_agent_publish
    nw_airtraffic_agent_create nw_airtraffic_agent_destroy nw_airtraffic_agent_act nw_airtraffic_agent_publish
    nw_escort_agent_create nw_escort_agent_destroy nw_escort_agent_act nw_escort_agent_publish
    nw_sokobanlive_agent_create nw_sokobanlive_agent_destroy nw_sokobanlive_agent_act nw_sokobanlive_agent_publish
    nw_kitchen_agent_create nw_kitchen_agent_destroy nw_kitchen_agent_act nw_kitchen_agent_publish
    nw_crane_agent_create nw_crane_agent_destroy nw_crane_agent_act nw_crane_agent_publish
    nw_ferry_agent_create nw_ferry_agent_destroy nw_ferry_agent_act nw_ferry_agent_publish
    nw_docking_agent_create nw_docking_agent_destroy nw_docking_agent_act nw_docking_agent_publish
    nw_rover_agent_create nw_rover_agent_destroy nw_rover_agent_act nw_rover_agent_publish
    nw_unicycle_agent_create nw_unicycle_agent_destroy nw_unicycle_agent_act nw_unicycle_agent_publish
    nw_morning_round_agent_create nw_morning_round_agent_destroy nw_morning_round_agent_act nw_morning_round_agent_publish
    nw_heavier_agent_create nw_heavier_agent_destroy nw_heavier_agent_act nw_heavier_agent_publish
    nw_full_stop_agent_create nw_full_stop_agent_destroy nw_full_stop_agent_act nw_full_stop_agent_publish
    nw_missing_word_agent_create nw_missing_word_agent_destroy nw_missing_word_agent_act nw_missing_word_agent_publish
    nw_proofreader_agent_create nw_proofreader_agent_destroy nw_proofreader_agent_act nw_proofreader_agent_publish
    nw_figures_of_speech_agent_create nw_figures_of_speech_agent_destroy nw_figures_of_speech_agent_act nw_figures_of_speech_agent_publish
    nw_which_feeling_agent_create nw_which_feeling_agent_destroy nw_which_feeling_agent_act nw_which_feeling_agent_publish
    nw_how_strongly_agent_create nw_how_strongly_agent_destroy nw_how_strongly_agent_act nw_how_strongly_agent_publish
    nw_reading_people_agent_create nw_reading_people_agent_destroy nw_reading_people_agent_act nw_reading_people_agent_publish
    nw_why_they_feel_agent_create nw_why_they_feel_agent_destroy nw_why_they_feel_agent_act nw_why_they_feel_agent_publish
    nw_tone_of_voice_agent_create nw_tone_of_voice_agent_destroy nw_tone_of_voice_agent_act nw_tone_of_voice_agent_publish
    nw_emotion_agent_create nw_emotion_agent_destroy nw_emotion_agent_act nw_emotion_agent_publish
    nw_social_sense_agent_create nw_social_sense_agent_destroy nw_social_sense_agent_act nw_social_sense_agent_publish
    nw_bad_argument_agent_create nw_bad_argument_agent_destroy nw_bad_argument_agent_act nw_bad_argument_agent_publish
    nw_second_thoughts_agent_create nw_second_thoughts_agent_destroy nw_second_thoughts_agent_act nw_second_thoughts_agent_publish
    nw_between_the_lines_agent_create nw_between_the_lines_agent_destroy nw_between_the_lines_agent_act nw_between_the_lines_agent_publish
    nw_crazy_cog_agent_create nw_crazy_cog_agent_destroy nw_crazy_cog_agent_act nw_crazy_cog_agent_publish
    nw_cipher_abyss_agent_create nw_cipher_abyss_agent_destroy nw_cipher_abyss_agent_act nw_cipher_abyss_agent_publish
    nw_potters_wheel_agent_create nw_potters_wheel_agent_destroy nw_potters_wheel_agent_act nw_potters_wheel_agent_publish
    nw_conductor_agent_create nw_conductor_agent_destroy nw_conductor_agent_act nw_conductor_agent_publish
    nw_tightrope_agent_create nw_tightrope_agent_destroy nw_tightrope_agent_act nw_tightrope_agent_publish
    nw_sign_painter_agent_create nw_sign_painter_agent_destroy nw_sign_painter_agent_act nw_sign_painter_agent_publish
    nw_bartender_agent_create nw_bartender_agent_destroy nw_bartender_agent_act nw_bartender_agent_publish
    nw_lock_pick_agent_create nw_lock_pick_agent_destroy nw_lock_pick_agent_act nw_lock_pick_agent_publish
    nw_air_hockey_agent_create nw_air_hockey_agent_destroy nw_air_hockey_agent_act nw_air_hockey_agent_publish
    nw_semaphore_agent_create nw_semaphore_agent_destroy nw_semaphore_agent_act nw_semaphore_agent_publish
    nw_shadow_puppets_agent_create nw_shadow_puppets_agent_destroy nw_shadow_puppets_agent_act nw_shadow_puppets_agent_publish
    nw_night_watch_agent_create nw_night_watch_agent_destroy nw_night_watch_agent_act nw_night_watch_agent_publish
    nw_kerbside_agent_create nw_kerbside_agent_destroy nw_kerbside_agent_act nw_kerbside_agent_publish
    nw_steadicam_agent_create nw_steadicam_agent_destroy nw_steadicam_agent_act nw_steadicam_agent_publish
    nw_free_kick_agent_create nw_free_kick_agent_destroy nw_free_kick_agent_act nw_free_kick_agent_publish
    nw_glove_agent_create nw_glove_agent_destroy nw_glove_agent_act nw_glove_agent_publish
    nw_by_ear_agent_create nw_by_ear_agent_destroy nw_by_ear_agent_act nw_by_ear_agent_publish
    nw_piano_tuner_agent_create nw_piano_tuner_agent_destroy nw_piano_tuner_agent_act nw_piano_tuner_agent_publish
    nw_cricket_hunt_agent_create nw_cricket_hunt_agent_destroy nw_cricket_hunt_agent_act nw_cricket_hunt_agent_publish
    nw_claw_machine_agent_create nw_claw_machine_agent_destroy nw_claw_machine_agent_act nw_claw_machine_agent_publish
    nw_dam_keeper_agent_act nw_dam_keeper_agent_publish
    nw_dispatch_agent_act nw_dispatch_agent_publish
    nw_inside_or_out_agent_create nw_inside_or_out_agent_destroy
    nw_inside_or_out_agent_act nw_inside_or_out_agent_publish
    nw_point_of_view_agent_create nw_point_of_view_agent_destroy
    nw_point_of_view_agent_act nw_point_of_view_agent_publish nw_same_or_mirror_agent_create nw_same_or_mirror_agent_destroy
    nw_same_or_mirror_agent_act nw_same_or_mirror_agent_publish nw_which_is_nearer_agent_create nw_which_is_nearer_agent_destroy
    nw_which_is_nearer_agent_act nw_which_is_nearer_agent_publish nw_where_was_it_agent_create nw_where_was_it_agent_destroy
    nw_where_was_it_agent_act nw_where_was_it_agent_publish nw_notebook_agent_create nw_notebook_agent_destroy nw_notebook_agent_act
    nw_notebook_agent_publish nw_triage_agent_create nw_triage_agent_destroy nw_triage_agent_act
    nw_triage_agent_publish nw_delay_agent_create nw_delay_agent_destroy
    nw_delay_agent_act nw_delay_agent_publish nw_stop_switch_agent_create
    nw_stop_switch_agent_destroy nw_stop_switch_agent_act nw_stop_switch_agent_publish
    nw_hold_it_agent_create nw_hold_it_agent_destroy nw_hold_it_agent_act
    nw_hold_it_agent_publish nw_hold_it_agent_audio nw_public_outcome_verify_frame)
agent_symbols="$SOURCE_TREE_PARENT/agent-exports"
agent_inputs=()
case "$host_system" in
    Darwin)
        agent_name=libnw-agent.dylib
        printf '_%s\n' "${agent_exports[@]}" > "$agent_symbols"
        agent_flags=(-dynamiclib -Wl,-exported_symbols_list,"$agent_symbols" -Wl,-install_name,@loader_path/"$agent_name")
        ;;
    Linux)
        agent_name=libnw-agent.so
        {
            printf '{ global:\n'
            printf '  %s;\n' "${agent_exports[@]}"
            printf 'local: *; };\n'
        } > "$agent_symbols"
        agent_flags=(-shared -Wl,--version-script,"$agent_symbols" -Wl,-soname,"$agent_name")
        ;;
    MINGW*|MSYS*|UCRT*|CYGWIN*)
        agent_name=nw-agent.dll
        agent_def="$agent_symbols.def"
        printf '%s\n' EXPORTS "${agent_exports[@]}" > "$agent_def"
        agent_inputs=("$agent_def")
        agent_flags=(-shared)
        ;;
esac
cc "${agent_flags[@]}" "${agent_inputs[@]+"${agent_inputs[@]}"}" \
    -o "$SOURCE_TREE_PARENT/$agent_name" "$NATIVE_LINK_OBJECT" "$RUNTIME_OBJ" \
    "${RUNTIME_LINK_FLAGS[@]+"${RUNTIME_LINK_FLAGS[@]}"}" $SDL_LIBS
"${PYTHON_BIN:-python3}" "$ROOT/test/triage_agent_library_test.py" "$SOURCE_TREE_PARENT/$agent_name"
if [[ "${NW_SDL_TTF:-0}" == 1 && ( "$host_system" == Darwin || "$host_system" == Linux ) ]]; then
    "${PYTHON_BIN:-python3}" "$ROOT/test/sdl_captcha_font_test.py" "$NATIVE_LINK_OBJECT" "$TTF_OBJECT" "$RUNTIME_OBJ"
fi
mv -f "$SOURCE_TREE_PARENT/$agent_name" "$ROOT/build/$agent_name"

# Check the SDL header ABI without linking the C replay entry point.
cc -std=c11 $SDL_CFLAGS -fsyntax-only "$ROOT/shells/sdl3/main.c"
features="$SOURCE_TREE/src/native/sdl_desktop_features.elisa"
sdl_defines="$(cc $SDL_CFLAGS -dM -E -x c -include SDL3/SDL_version.h /dev/null)"
sdl_version="$(awk '/^#define SDL_MAJOR_VERSION / { major=$3 }
    /^#define SDL_MINOR_VERSION / { minor=$3 }
    END { print major * 100 + minor }' <<< "$sdl_defines")"
if (( sdl_version >= 304 )); then
    cat > "$features" <<'ELISA'
extern SDL_SavePNG(surface: mutable void&, path: cstr) -> bool
extern SDL_LoadPNG(path: cstr) -> mutable void&?

def sdl_entry_png_writer() -> usize:
    can Unsafe.PointerCast:
        trusted Unsafe.PointerCast:
            save: fn(mutable void&, cstr) -> bool = SDL_SavePNG
            return save.cast[usize]

def sdl_entry_png_loader() -> usize:
    can Unsafe.PointerCast:
        trusted Unsafe.PointerCast:
            load: fn(cstr) -> mutable void&? = SDL_LoadPNG
            return load.cast[usize]
ELISA
else
    cat > "$features" <<'ELISA'
def sdl_entry_png_writer() -> usize:
    return 0.usize()

def sdl_entry_png_loader() -> usize:
    return 0.usize()
ELISA
fi

if [[ "${NW_SDL_TTF:-0}" == 1 ]]; then
    cat >> "$features" <<'ELISA'

extern nw_sdl_attach_font(renderer: mutable void&, primary: usize, fallback: usize) -> i32

def sdl_entry_font() -> usize:
    can Unsafe.PointerCast:
        trusted Unsafe.PointerCast:
            attach: fn(mutable void&, usize, usize) -> i32 = nw_sdl_attach_font
            return attach.cast[usize]
ELISA
else
    cat >> "$features" <<'ELISA'

def sdl_entry_font() -> usize:
    return 0.usize()
ELISA
fi

marble_feature="$SOURCE_TREE/src/native/sdl_desktop_marble_feature.elisa"
cat > "$marble_feature" <<'ELISA'
def sdl_entry_marble(bindings: mutable SDLDesktopBindings&):
    _ = bindings
ELISA
camera_feature="$SOURCE_TREE/src/native/sdl_desktop_camera_feature.elisa"
camera_objcopy=llvm-objcopy
if [[ "$(uname -s)" == Linux ]] && ! command -v "$camera_objcopy" >/dev/null 2>&1; then
    camera_objcopy=objcopy
fi
CAMERA_INPUTS=()
CAMERA_GL_FLAGS=()
WINDOWS_GL_INPUTS=()
case "$host_system" in
    Darwin) CAMERA_GL_FLAGS=(-framework OpenGL) ;;
    Linux) CAMERA_GL_FLAGS=(-lGL -lm) ;;
    MINGW*|MSYS*|UCRT*|CYGWIN*)
        case "$(uname -m)" in
            aarch64|arm64)
                gl_source="$SOURCE_TREE_PARENT/marble_windows_gl.elisa"
                gl_object="$SOURCE_TREE_PARENT/marble_windows_gl.o"
                python3 "$ROOT/scripts/prepare_marble_windows_gl.py" "$SOURCE_TREE/src/native" "$gl_source"
                "$NATIVE_COMPILER" -emit obj -O2 -o "$gl_object" "$gl_source"
                WINDOWS_GL_INPUTS=("$gl_object")
                ;;
            *) WINDOWS_GL_INPUTS=("$ROOT/shells/sdl3/marble_gl_windows.c") ;;
        esac
        ;;
esac
if [[ "${CAMERA_GL_FLAGS[*]:-}${WINDOWS_GL_INPUTS[*]:-}" != "" ]]; then
    printf 'include "./sdl_desktop_camera_entry.elisa"\n' > "$camera_feature"
    "$NATIVE_COMPILER" -emit obj -O2 -o "$SOURCE_TREE_PARENT/camera.o" \
        "$SOURCE_TREE/src/native/sdl_camera_exports.elisa"
    if [[ "${WINDOWS_GL_INPUTS[*]:-}" != "" ]]; then
        # COFF supports renaming defined symbols but cannot localize them.
        llvm-nm -g --defined-only "$SOURCE_TREE_PARENT/camera.o" |
            awk 'NF >= 3 && $NF !~ /^_?nw_sdl_camera_/ { print $NF, "nw_camera_private_" $NF }' > "$SOURCE_TREE_PARENT/camera.rename"
        llvm-objcopy --redefine-syms="$SOURCE_TREE_PARENT/camera.rename" \
            "$SOURCE_TREE_PARENT/camera.o" "$SOURCE_TREE_PARENT/camera_link.o"
    else
        nm -g "$SOURCE_TREE_PARENT/camera.o" | awk '$NF ~ /^_?nw_sdl_camera_/ { print $NF }' > "$SOURCE_TREE_PARENT/camera.exports"
        "$camera_objcopy" --keep-global-symbols="$SOURCE_TREE_PARENT/camera.exports" \
            "$SOURCE_TREE_PARENT/camera.o" "$SOURCE_TREE_PARENT/camera_link.o"
    fi
    CAMERA_INPUTS=("$SOURCE_TREE_PARENT/camera_link.o")
    mkdir -p "$ROOT/build/res"
    cp -R "$ROOT/res/camera" "$ROOT/build/res/"
else
    printf 'def sdl_entry_camera():\n    pass\n' > "$camera_feature"
fi
DESKTOP_ENTRY_OBJECT="$SOURCE_TREE_PARENT/desktop_entry.o"
"$NATIVE_COMPILER" -emit obj -O2 -o "$DESKTOP_ENTRY_OBJECT" \
    "$SOURCE_TREE/src/native/sdl_desktop_entrypoint.elisa"

cc -O2 -std=c11 $SDL_CFLAGS ${TTF_INPUTS[@]+"${TTF_INPUTS[@]}"} \
    -o "$DESKTOP_BINARY" \
    "$DESKTOP_ENTRY_OBJECT" \
    "$NATIVE_LINK_OBJECT" \
    ${WINDOWS_GL_INPUTS[@]+"${WINDOWS_GL_INPUTS[@]}"} \
    ${CAMERA_INPUTS[@]+"${CAMERA_INPUTS[@]}"} ${CAMERA_GL_FLAGS[@]+"${CAMERA_GL_FLAGS[@]}"} \
    "$RUNTIME_OBJ" \
    ${RUNTIME_LINK_FLAGS[@]+"${RUNTIME_LINK_FLAGS[@]}"} \
    $SDL_LIBS $TTF_LIBS

mkdir -p "$ROOT/build/res/misc"
cp -R "$ROOT/res/misc/applause" "$ROOT/res/misc/esc50" "$ROOT/build/res/misc/"

if [[ -n "${NW_MUJOCO_LIBRARY:-}" ]]; then
    mkdir -p "$ROOT/build/res/marblemaze"
    cp "$ROOT/res/marblemaze/"* "$ROOT/build/res/marblemaze/"
    MUJOCO_LIBRARY="$(cd -- "$(dirname -- "$NW_MUJOCO_LIBRARY")" && pwd)/$(basename -- "$NW_MUJOCO_LIBRARY")"
    MUJOCO_HEADERS="${NW_MUJOCO_HEADERS:-$(dirname -- "$MUJOCO_LIBRARY")/include}"
    bash "$ROOT/scripts/prepare_mujoco_layout.sh" "$MUJOCO_HEADERS" \
        "$SOURCE_TREE/src/native/marble_mujoco_layout.elisa"
    "$NATIVE_COMPILER" -emit obj -O2 -o "$SOURCE_TREE_PARENT/mujoco.o" \
        "$SOURCE_TREE/src/native/sdl_mujoco_exports.elisa"
    python3 "$ROOT/scripts/prepare_native_object.py" \
        "$SOURCE_TREE_PARENT/mujoco.o" "$SOURCE_TREE_PARENT/mujoco_link.o"
    MUJOCO_LINK_FLAGS=()
    MUJOCO_GL_INPUTS=()
    case "$host_system" in
        Darwin) MUJOCO_LINK_FLAGS=(-framework OpenGL -Wl,-headerpad_max_install_names) ;;
        MINGW*|MSYS*|UCRT*|CYGWIN*)
            MUJOCO_GL_INPUTS=("${WINDOWS_GL_INPUTS[@]}")
            # An import library and its DLL may live in different directories.
            export PATH="${NW_MUJOCO_DLL_DIR:-$(dirname -- "$MUJOCO_LIBRARY")}:$PATH"
            ;;
        Linux) MUJOCO_LINK_FLAGS=("-Wl,-rpath,$(dirname -- "$MUJOCO_LIBRARY")" -lGL -lm) ;;
    esac
    printf 'include "./sdl_desktop_mujoco_entry.elisa"\n' > "$marble_feature"
    MARBLE_ENTRY_OBJECT="$SOURCE_TREE_PARENT/marble_entry.o"
    "$NATIVE_COMPILER" -emit obj -O2 -o "$MARBLE_ENTRY_OBJECT" \
        "$SOURCE_TREE/src/native/sdl_desktop_entrypoint.elisa"
    cc -O2 -std=c11 $SDL_CFLAGS ${TTF_INPUTS[@]+"${TTF_INPUTS[@]}"} \
        -o "$MARBLE_BINARY" "$MARBLE_ENTRY_OBJECT" \
        ${CAMERA_INPUTS[@]+"${CAMERA_INPUTS[@]}"} \
        ${MUJOCO_GL_INPUTS[@]+"${MUJOCO_GL_INPUTS[@]}"} "$SOURCE_TREE_PARENT/mujoco_link.o" \
        "$RUNTIME_OBJ" "$MUJOCO_LIBRARY" ${RUNTIME_LINK_FLAGS[@]+"${RUNTIME_LINK_FLAGS[@]}"} ${MUJOCO_LINK_FLAGS[@]+"${MUJOCO_LINK_FLAGS[@]}"} $SDL_LIBS $TTF_LIBS
    if [[ "$host_system" == Darwin ]]; then
        install_name="$(otool -D "$MUJOCO_LIBRARY" | sed -n '2p')"
        if [[ "$install_name" != "$MUJOCO_LIBRARY" ]]; then
            install_name_tool -change "$install_name" "$MUJOCO_LIBRARY" "$MARBLE_BINARY"
            codesign --force --sign - "$MARBLE_BINARY"
        fi
    fi
    "$MARBLE_BINARY" --selftest-marble-mujoco
    "$MARBLE_BINARY" --selftest-marble-assets
    "${PYTHON_BIN:-python3}" \
        "$ROOT/test/sdl_event_loop_headless_test.py" "$SOURCE_TREE_PARENT/mujoco_link.o" \
        "$RUNTIME_OBJ" "$MUJOCO_LIBRARY" ${MUJOCO_GL_INPUTS[@]+"${MUJOCO_GL_INPUTS[@]}"}
fi

# Prove it RUNS, not just that it linked. --selftest drives the same decode and
# frame-walk the window path uses, with no SDL_Init, so it works headless -- and
# it checks the pooled STRINGS, not just the command count: the wasm build
# corrupted exactly those while geometry stayed correct, so a check that counted
# commands would have passed straight through that bug.
"$DESKTOP_BINARY" --selftest 180
"$DESKTOP_BINARY" --selftest-long-text
"$DESKTOP_BINARY" --selftest-3d-maze
"$DESKTOP_BINARY" --selftest-taskhub
"$DESKTOP_BINARY" --selftest-taskhub-lifecycle
"$DESKTOP_BINARY" --selftest-sokoban
"$DESKTOP_BINARY" --selftest-monkey-ladder
"$DESKTOP_BINARY" --selftest-nback3d
"$DESKTOP_BINARY" --selftest-tetris
"$DESKTOP_BINARY" --selftest-mr-time
"$DESKTOP_BINARY" --selftest-graph-mapping
"$DESKTOP_BINARY" --selftest-matrix-reasoning
"$DESKTOP_BINARY" --selftest-marble
"$DESKTOP_BINARY" --selftest-in-the-dark
"$DESKTOP_BINARY" --selftest-fog
"$DESKTOP_BINARY" --selftest-removals
"$DESKTOP_BINARY" --selftest-custody
"$DESKTOP_BINARY" --selftest-concentration
"$DESKTOP_BINARY" --selftest-recognition
"$DESKTOP_BINARY" --selftest-trivia
"$DESKTOP_BINARY" --selftest-reflex
"$DESKTOP_BINARY" --selftest-algebra
"$DESKTOP_BINARY" --selftest-syllogism
"$DESKTOP_BINARY" --selftest-algebra-options
"$DESKTOP_BINARY" --selftest-numberology
python3 "$ROOT/test/numberology_sdl_results_test.py" --binary "$DESKTOP_BINARY" \
    --compiler "$NATIVE_COMPILER" --runtime-object "$RUNTIME_OBJ"
python3 "$ROOT/test/syllogism_sdl_options_test.py" \
    --compiler "$NATIVE_COMPILER" --runtime-object "$RUNTIME_OBJ"
"$DESKTOP_BINARY" --selftest-jigsaw
"$DESKTOP_BINARY" --selftest-video-sequence
sequence_profile="$SOURCE_TREE_PARENT/video-sequence-profile"
sequence_library="$sequence_profile/datasets/ucf101"
mkdir -p "$sequence_library"
printf '[DEFAULT]\nVIDEO_SEQUENCE_PIECES = 3\nVIDEO_SEQUENCE_PUZZLES = 1\nVIDEO_SEQUENCE_ADAPTIVE = False\nVIDEO_SEQUENCE_MARK_PLACED = True\n' > "$sequence_profile/config.ini"
NW_DATA_DIRECTORY="$sequence_profile" NW_MEDIA_CONFIGFILE="$sequence_profile/config.ini" \
    "$DESKTOP_BINARY" --selftest-video-sequence-media
if command -v ffmpeg >/dev/null 2>&1; then
    printf 'invalid AVI\n' > "$sequence_library/broken.avi"
    cp "$ROOT/test/fixtures/video_jigsaw_package.avi" "$sequence_library/playable.avi"
    cp "$sequence_library/playable.avi" "$sequence_library/incoming"
    printf 'playable.avi\n' > "$sequence_library/seen.txt"
    NW_DATA_DIRECTORY="$sequence_profile" NW_MEDIA_CONFIGFILE="$sequence_profile/config.ini" \
        "$DESKTOP_BINARY" --selftest-video-sequence-media --with-clips
    test "$(cat "$sequence_library/seen.txt")" = added.avi
fi
NW_DATA_DIRECTORY="$sequence_profile" NW_MEDIA_CONFIGFILE="$sequence_profile/config.ini" \
    "$DESKTOP_BINARY" --selftest-video-sequence-options
next_profile="$SOURCE_TREE_PARENT/what-next-profile"
next_library="$next_profile/datasets/ucf101"
mkdir -p "$next_library"
printf '[DEFAULT]\nWHAT_NEXT_RUNG = 1\nWHAT_NEXT_TRIALS = 1\nWHAT_NEXT_ADAPTIVE = False\n' > "$next_profile/config.ini"
NW_DATA_DIRECTORY="$next_profile" NW_MEDIA_CONFIGFILE="$next_profile/config.ini" \
    "$DESKTOP_BINARY" --selftest-what-next-media
if command -v ffmpeg >/dev/null 2>&1; then
    for colour in red blue; do
        ffmpeg -v error -nostdin -f lavfi -i "color=$colour:size=160x120:rate=15" \
            -t 4 -c:v mjpeg -threads 1 "$next_library/$colour.avi"
    done
    printf 'unrelated.avi\n' > "$next_library/seen.txt"
    NW_DATA_DIRECTORY="$next_profile" NW_MEDIA_CONFIGFILE="$next_profile/config.ini" \
        "$DESKTOP_BINARY" --selftest-what-next-media --with-clips
    test "$(cat "$next_library/seen.txt")" = unrelated.avi
    test -s "$next_library/seen_next.txt"
fi
"$DESKTOP_BINARY" --selftest-sudoku
"$DESKTOP_BINARY" --selftest-task-options
if command -v curl >/dev/null 2>&1; then
    "${PYTHON_BIN:-python3}" "$ROOT/test/sdl_esc50_fetch_test.py" "$DESKTOP_BINARY"
fi
"$DESKTOP_BINARY" --selftest-go
hanoi_fixture="$SOURCE_TREE_PARENT/hanoi-config.ini"
printf '[DEFAULT]\nHANOI_DISKS = 3\nHANOI_ROUNDS = 2\nHANOI_ADAPTIVE = True\n' > "$hanoi_fixture"
"$DESKTOP_BINARY" --selftest-hanoi
NW_MEDIA_CONFIGFILE="$hanoi_fixture" "$DESKTOP_BINARY" --selftest-hanoi-profile
"$DESKTOP_BINARY" --selftest-crossed-wires
"$DESKTOP_BINARY" --selftest-scrabble
"$DESKTOP_BINARY" --selftest-scramble
"$DESKTOP_BINARY" --selftest-crossword
"${PYTHON_BIN:-python3}" "$ROOT/test/sdl_word_corpus_binary_test.py" "$DESKTOP_BINARY"
"${PYTHON_BIN:-python3}" "$ROOT/test/frame_shared_memory_native_test.py" "$NATIVE_LINK_OBJECT" "$RUNTIME_OBJ"
"${PYTHON_BIN:-python3}" "$ROOT/test/sdl_event_loop_headless_test.py" "$NATIVE_LINK_OBJECT" "$RUNTIME_OBJ"
"${PYTHON_BIN:-python3}" "$ROOT/test/sdl_text_dispatch_native_test.py" "$NATIVE_LINK_OBJECT" "$RUNTIME_OBJ"
"${PYTHON_BIN:-python3}" "$ROOT/test/sdl_window_fault_binary_test.py" "$NATIVE_LINK_OBJECT" "$RUNTIME_OBJ"
NW_SDL_BINARY="$DESKTOP_BINARY" "${PYTHON_BIN:-python3}" "$ROOT/test/crossword_native_settings_test.py"
NW_SDL_BINARY="$DESKTOP_BINARY" "${PYTHON_BIN:-python3}" "$ROOT/test/scrabble_native_settings_test.py"
NW_SDL_BINARY="$DESKTOP_BINARY" "${PYTHON_BIN:-python3}" "$ROOT/test/scramble_native_settings_test.py"
"$DESKTOP_BINARY" --selftest-ncup-monte
"$DESKTOP_BINARY" --selftest-moving-targets
"$DESKTOP_BINARY" --selftest-lookout
"$DESKTOP_BINARY" --selftest-pursuit
"$DESKTOP_BINARY" --selftest-out-of-sight
"$DESKTOP_BINARY" --selftest-buzz-wire
"$DESKTOP_BINARY" --selftest-donkey
"$DESKTOP_BINARY" --selftest-count

printf 'built %s\n' "$DESKTOP_BINARY"
printf 'run it with: %s\n' "$DESKTOP_BINARY"
printf '  --screen 3d-maze: Space/Enter=start, arrows=walk/turn, R=restart\n'
printf '  --screen maze: Space=start/next, arrows/WASD=walk, R=restart, C=options\n'
printf '  --screen sokoban3d: Space=start/next, arrows/WASD=walk/turn, U=undo, R=restart, C=options\n'
printf '  --screen cookie-thief: Space=start/next, X/Up=grab, Z/Down=leave, G/Right=golden cookie, C=options\n'
printf '  --screen taskhub: arrows=navigate, Space/Enter=launch implemented native controllers\n'
printf '  --screen sokoban: Space/Enter=start, arrows=move, U=undo, R=restart\n'
printf '  --screen monkey-ladder: Space/Enter=start/commit, arrows=move cursor\n'
printf '  --screen nback3d: Space/Enter=start, A=match, P=pause, R=restart\n'
printf '  --screen tetris: Space/Enter=start/drop, arrows=move/rotate, 1-6=select, R=restart\n'
printf '  --screen mr-time: Space/Enter=start/submit, digits/decimal/backspace=answer\n'
printf '  --screen graph-mapping: Space/Enter=start, Y/S/N/D or arrows=answer\n'
printf '  --screen matrix-reasoning: Space/Enter=start, 1-8=answer\n'
printf '  --screen marble: Space=start/next, arrows=hold tilt, L=level, R=restart\n'
printf '  --screen in-the-dark: Space/Enter=start, 1-5=answer\n'
printf '  --screen fog-of-war: Space/Enter=start, arrows=walk\n'
printf '  --screen removals: Space/Enter=start, 1-5=answer\n'
printf '  --screen chain-of-custody: Space/Enter=start, arrows=claw, Z=grab/drop\n'
printf '  --screen concentration: Space=start, arrows=cursor, Enter=select\n'
printf '  --screen recognition: Space=start, left=seen, right=new\n'
printf '  --screen trivia: Space=start/submit/advance, arrows=choice, 1-8=answer\n'
printf '  --screen reflex: Space/Enter=start, click=target, Esc=menu\n'
printf '  --screen algebra: Space=start/next, type answer, Enter=submit, O=options\n'
printf '    Algebra options: --algebra-level N --algebra-trials N --algebra-no-working --algebra-no-adaptive\n'
printf '  --screen numberology: Space=start, type answer, Enter=submit, O=options\n'
printf '    --numberology-level N --numberology-trials N --numberology-no-adaptive\n'
printf '  --screen jigsaw: Space=start, 0-9=select tile, Enter=advance\n'
printf '    Jigsaw options: --jigsaw-side N --jigsaw-puzzles N --jigsaw-no-adaptive --jigsaw-no-preview --jigsaw-mark-placed\n'
printf '  --screen sudoku: Space=start, arrows=cursor, 1-9/A-G=write, 0/Backspace/Delete=erase, N=pencil\n'
printf '    Sudoku options: --sudoku-level N --sudoku-puzzles N --sudoku-no-clashes --sudoku-no-adaptive\n'
printf '  --screen go: Space=start/answer/next, arrows=cursor, mouse=intersection\n'
printf '  --screen scrabble: Space=start/next, 1-7=lay, arrows=move, Tab=turn, Enter=play, mouse=select/lay\n'
printf '    Scrabble options: --scrabble-level N --scrabble-trials N --scrabble-no-premiums --scrabble-no-adaptive --scrabble-lexicon PATH\n'
printf '  --screen crossword: Space=start/next, letters=write, arrows=move, Tab=turn, mouse=select/turn\n'
printf '    Crossword options: --crossword-level N --crossword-trials N --crossword-no-mistakes --crossword-no-adaptive --crossword-lexicon PATH\n'
printf '  --screen ncup-monte: Space=start/next, mouse=choose cup\n'
printf '  --screen moving-targets: Space=start, mouse=select tracked balls\n'
printf '  --screen lookout: Space=start, F=form, J=colour\n'
printf '  --screen pursuit: Space=start, arrows/mesh=follow the shape\n'
printf '  --screen out-of-sight: Space=start, J=mine, F=not mine\n'
printf '  --screen buzz-wire: Space=start, arrows/W/S=move, I/K/J/L=turn, Shift=brace\n'
printf '  --screen donkey: Space=start, arrows/Space=swerve\n'
printf '  title mode: Space=task hub, arrows=cycle banner, Q/Esc=quit\n'
