#!/usr/bin/env python3
"""Drive the actual SDL event loop with a dummy video driver and scripted keys."""
import ast
import base64
import csv
import io
import json
import datetime
import os
import pickle
import random
import runpy
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from multiprocessing.shared_memory import SharedMemory
import wave
import zlib
from pathlib import Path
from trivia_diff import REF as trivia_reference

root = Path(__file__).resolve().parents[1]
linked, runtime = map(Path, sys.argv[1:3])
mujoco = Path(sys.argv[3]) if len(sys.argv) > 3 else None
windows_gl = Path(sys.argv[4]) if len(sys.argv) > 4 else None
try:
    flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'sdl3'], text=True))
except (OSError, subprocess.CalledProcessError):
    flags = ['-I/opt/homebrew/include', '-L/opt/homebrew/lib', '-lSDL3']
link_flags = ['-Wl,-dead_strip'] if sys.platform == 'darwin' else ['-Wl,--allow-multiple-definition']
if sys.platform.startswith('linux'):
    flags.append('-lm')
source = r'''
#include <SDL3/SDL.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "numberology_results.h"
typedef struct { void *current, *pending; } replay_syllogism_results;
extern void nw_sdl_close_desktop(uintptr_t *, uintptr_t, const uintptr_t *,
                                 replay_syllogism_results *, nw_numberology_results *, uintptr_t, uintptr_t, uintptr_t);
extern int64_t nw_sdl_frame_write(int64_t, int64_t, const int64_t *, const int64_t *, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_you_are_here_info(int64_t, int64_t);
extern int64_t nw_sokoban_info(int64_t, int64_t);
extern int64_t nw_sudoku_create(int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_sudoku_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_sudoku_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_sudoku_destroy(int64_t);
extern int64_t nw_numberology_info(int64_t, int64_t);
extern int64_t nw_nback3d_info(int64_t, int64_t);
extern int64_t nw_scramble_info(int64_t, int64_t);
extern int64_t nw_jigsaw_info(int64_t, int64_t);
extern int64_t nw_sudoku_info(int64_t, int64_t);
extern int64_t nw_salesman_info(int64_t, int64_t);
extern int64_t nw_salesman_city_coordinate(int64_t, int64_t, int64_t);
extern int64_t nw_maze2d_info(int64_t, int64_t);
extern int64_t nw_sokoban3d_info(int64_t, int64_t);
extern int64_t nw_cookie_thief_info(int64_t, int64_t);
extern int64_t nw_ninarow_info(int64_t, int64_t);
extern int64_t nw_hanoi_info(int64_t, int64_t);
extern int64_t nw_go_info(int64_t, int64_t);
extern int64_t nw_crossed_wires_info(int64_t, int64_t);
extern void nw_sdl_dispatch_task_key(int64_t, int64_t, int64_t);
extern int64_t nw_nback3d_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_concentration_info(int64_t, int64_t);
extern int64_t nw_recognition_info(int64_t, int64_t);
extern int64_t nw_jigsaw_create_options(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_jigsaw_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_jigsaw_value(int64_t, int64_t, int64_t);
extern int64_t nw_jigsaw_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_jigsaw_destroy(int64_t);
extern int64_t nw_marble_info(int64_t, int64_t);

static bool large_frame_written;
static float salesman_x[5], salesman_y[5];
static int salesman_clicks;
static bool salesman_settled;
static bool maze2d_restarted;
static int sokoban3d_checked;
static int cookie_phase = -1;
static int64_t sokoban3d_initial_facing;
static int title_hub_frames;
static int hidden_rule_frame, hidden_wiring_frame, triage_frame;
static int at, rendered, exit_sent, quit_sent, puzzle_started, marble_input, picker_frames, jigsaw_hover_frames;
static int env_int(const char *name) { const char *p = getenv(name); return p ? atoi(p) : 0; }
static int delay_frame, hold_it_frame, hold_it_audio_queued, notebook_frame, rooms_frame, nearer_frame, mirror_frame, pov_frame, inside_frame, touching_frame, crossings_frame, time_it_frame, time_it_audio_queued, balance_frame, balance_judged, juggler_frame, juggler_judged, lander_frame, lander_judged, beat_frame, beat_judged, glider_frame, glider_judged, catch_frame, catch_judged, echo_frame, echo_judged, echo_audio_queued;
static int drshape_frame, tuner_frame, tuner_audio_queued, shadow_frame, shadow_audio_queued, captcha_frame, signals_frame, fold_it_frame, who_knows_what_frame;
static int dam_keeper_frame, sonar_frame, gamble_frame, dispatch_frame, dispatch_judged, bluff_frame, bandit_frame, firebreak_frame, crossroads_frame, railyard_frame, airtraffic_frame, escort_frame, sokobanlive_frame, kitchen_frame, crane_frame, ferry_frame, docking_frame, rover_frame, rover_audio_queued, unicycle_frame, unicycle_audio_queued, morning_round_frame, morning_round_audio_queued, heavier_frame, heavier_audio_queued;
static int full_stop_frame, full_stop_audio_queued;
static int missing_word_frame, missing_word_audio_queued;
static int crazy_cog_frame, crazy_cog_audio_queued;
static int cipher_abyss_frame, potter_frame, conductor_frame, tightrope_frame, signpainter_frame, bartender_frame, lockpick_frame, airhockey_frame, semaphore_frame, puppets_frame, watch_frame, kerb_frame, steady_frame, kick_frame, glove_frame, ear_frame, tune_frame, cricket_frame, claw_frame;
static Uint64 airhockey_judged_clock, semaphore_judged_clock, puppets_judged_clock, watch_judged_clock, kerb_judged_clock, steady_judged_clock, kick_judged_clock, glove_judged_clock, ear_judged_clock, tune_judged_clock, cricket_judged_clock, claw_judged_clock;
static bool airhockey_done, semaphore_done, puppets_done, watch_done, kerb_done, steady_done, kick_done, glove_done, ear_done, tune_done, cricket_done, claw_done;
static bool dam_keeper_verdict;
static uint64_t nearer_first_view;
static Uint64 delay_clock;
Uint64 SDL_GetTicks(void) {
    return (env_int("NW_TEST_DELAY_CLOCK") || env_int("NW_TEST_HOLD_IT_CLOCK") || env_int("NW_TEST_NOTEBOOK") || env_int("NW_TEST_ROOMS") || env_int("NW_TEST_NEARER") || env_int("NW_TEST_MIRROR") || env_int("NW_TEST_POV") || env_int("NW_TEST_INSIDE") || env_int("NW_TEST_TOUCHING") || env_int("NW_TEST_CROSSINGS") || env_int("NW_TEST_TIME_IT_CLOCK") || env_int("NW_TEST_BALANCE_CLOCK") || env_int("NW_TEST_JUGGLER_CLOCK") || env_int("NW_TEST_LANDER_CLOCK") || env_int("NW_TEST_BEAT_CLOCK") || env_int("NW_TEST_GLIDER_CLOCK") || env_int("NW_TEST_CATCH_CLOCK") || env_int("NW_TEST_ECHO_CLOCK") || env_int("NW_TEST_DRSHAPE_CLOCK") || env_int("NW_TEST_TUNER_CLOCK") || env_int("NW_TEST_SHADOW_CLOCK") || env_int("NW_TEST_CAPTCHA") || env_int("NW_TEST_SIGNALS") || env_int("NW_TEST_FOLD_IT") || env_int("NW_TEST_WHO_KNOWS_WHAT") || env_int("NW_TEST_DAM_KEEPER") || env_int("NW_TEST_SONAR") || env_int("NW_TEST_GAMBLE") || env_int("NW_TEST_DISPATCH") || env_int("NW_TEST_BLUFF") || env_int("NW_TEST_BANDIT") || env_int("NW_TEST_FIREBREAK") || env_int("NW_TEST_CROSSROADS") || env_int("NW_TEST_RAILYARD") || env_int("NW_TEST_AIRTRAFFIC") || env_int("NW_TEST_ESCORT") || env_int("NW_TEST_SOKOBANLIVE") || env_int("NW_TEST_KITCHEN") || env_int("NW_TEST_CRANE") || env_int("NW_TEST_FERRY") || env_int("NW_TEST_DOCKING") || env_int("NW_TEST_ROVER") || env_int("NW_TEST_UNICYCLE") || env_int("NW_TEST_MORNING_ROUND") || env_int("NW_TEST_HEAVIER") || env_int("NW_TEST_FULL_STOP") || env_int("NW_TEST_MISSING_WORD") || env_int("NW_TEST_PROOFREADER") || env_int("NW_TEST_FIGURES") || env_int("NW_TEST_CRAZY_COG") || env_int("NW_TEST_CIPHER_ABYSS") || env_int("NW_TEST_POTTER") || env_int("NW_TEST_CONDUCTOR") || env_int("NW_TEST_TIGHTROPE") || env_int("NW_TEST_SIGN_PAINTER") || env_int("NW_TEST_BARTENDER") || env_int("NW_TEST_LOCK_PICK") || env_int("NW_TEST_AIR_HOCKEY") || env_int("NW_TEST_SEMAPHORE") || env_int("NW_TEST_SHADOW_PUPPETS") || env_int("NW_TEST_NIGHT_WATCH") || env_int("NW_TEST_KERBSIDE") || env_int("NW_TEST_STEADICAM") || env_int("NW_TEST_FREE_KICK") || env_int("NW_TEST_GLOVE") || env_int("NW_TEST_BY_EAR") || env_int("NW_TEST_PIANO_TUNER") || env_int("NW_TEST_CRICKET_HUNT") || env_int("NW_TEST_CLAW_MACHINE")) ? delay_clock : SDL_GetTicksNS() / 1000000;
}
extern int nw_sdl_window_pointer(SDL_Window *, const uintptr_t *, const uintptr_t *,
                                  int64_t, int64_t, float, float, uint32_t);
static int hover_calls, button_calls, fullscreen_requests;
static int history_frames;
static int applause_frames, applause_clips, applause_queued, applause_gain_updates;
static int recognition_replay, recognition_clips, recognition_queued;
static bool unrelated_close_sent;
int nw_test_pointer(SDL_Window *window, const uintptr_t *rows, const uintptr_t *special,
                     int64_t motion, int64_t button, float x, float y, uint32_t buttons) {
    int accepted = nw_sdl_window_pointer(window, rows, special, motion, button, x, y, buttons);
    if (accepted && env_int("NW_TEST_HOVER")) {
        if (motion != 1 || button != 0 || x != 40 || y != 30) exit(98);
        ++hover_calls;
    }
    if (env_int("NW_TEST_MOUSE_BUTTON")) {
        if (motion != 0 || button != SDL_BUTTON_LEFT || x != 40.5f || y != 30.25f || buttons != 0) exit(98);
        ++button_calls;
    }
    return accepted;
}
void nw_test_shutdown(uintptr_t *state, uintptr_t surface, const uintptr_t *rows,
                      replay_syllogism_results *syllogism,
                      nw_numberology_results *numberology, uintptr_t marble_close,
                      uintptr_t marble_state, uintptr_t physics) {
    if (!quit_sent && exit_sent && env_int("NW_TEST_DIRECT")) {
        if (rendered != 1 || (env_int("NW_TEST_HOVER") && hover_calls != 1)) exit(94);
        puts("SDL event replay: PASS");
    } else if (quit_sent && rendered != 2) {
        exit(95);
    }
    if (env_int("NW_TEST_TITLE_HUB")) {
        if (title_hub_frames != 8 || at != 9) exit(97);
        puts("SDL title and task hub navigation: PASS");
    }
    if (env_int("NW_TEST_TITLE_KEYS") && fullscreen_requests != 2) exit(97);
    if (env_int("NW_TEST_RECOGNITION_SOUND") && (recognition_clips != 2 || recognition_queued != 2)) exit(97);
    if (getenv("NW_TEST_CONCENTRATION_CLIP")) {
        int expected_clips = getenv("NW_TEST_CONCENTRATION_CLIP_TWO") ? 2 : 1;
        if (recognition_clips != expected_clips || recognition_queued != expected_clips) exit(97);
    }
    if (env_int("NW_TEST_APPLAUSE")) {
        int played = env_int("NW_TEST_APPLAUSE") == 1;
        if (applause_clips != played || applause_queued != played) exit(97);
        if (env_int("NW_TEST_REWARD_FADE")) {
            if (applause_gain_updates < 2 || SDL_WasInit(SDL_INIT_AUDIO)) exit(97);
        } else if (applause_gain_updates != played ||
                   SDL_WasInit(SDL_INIT_AUDIO) != (played ? SDL_INIT_AUDIO : 0)) {
            exit(97);
        }
    }
    const char *expected_title = getenv("NW_TEST_WINDOW_TITLE");
    if (expected_title && (!state[0] ||
        strcmp(SDL_GetWindowTitle((SDL_Window *)state[0]), expected_title) != 0)) exit(96);
    const char *expected_summary = getenv("NW_TEST_DEBUG_SUMMARY");
    if (expected_summary) {
        SDL_PropertiesID properties = SDL_GetRendererProperties((SDL_Renderer *)state[1]);
        const char *summary = SDL_GetStringProperty(properties, "nw.debug.summary", "");
        if (strcmp(summary, expected_summary) != 0) {
            fprintf(stderr, "debug summary: expected '%s', got '%s'\n", expected_summary, summary);
            exit(96);
        }
    }
    const char *expected_density = getenv("NW_TEST_CAPTURE_DENSITY");
    if (expected_density) {
        SDL_PropertiesID properties = SDL_GetRendererProperties((SDL_Renderer *)state[1]);
        if (SDL_GetFloatProperty(properties, "nw.capture.density", 0) != (float)atof(expected_density)) exit(96);
    }
    nw_sdl_close_desktop(state, surface, rows, syllogism, numberology, marble_close, marble_state, physics);
    if (physics && *(uintptr_t *)physics) exit(96);
    if (state[0] || state[1] || state[2] || SDL_WasInit(SDL_INIT_VIDEO | SDL_INIT_AUDIO)) exit(96);
}

bool SDL_LoadWAV(const char *path, SDL_AudioSpec *spec, Uint8 **audio, Uint32 *length) {
    if (env_int("NW_TEST_APPLAUSE")) {
        if (!strstr(path, "/res/misc/applause/applause.wav")) exit(97);
        ++applause_clips;
    }
    static char first[4096];
    if (env_int("NW_TEST_RECOGNITION_SOUND")) {
        if (recognition_clips == 0) SDL_strlcpy(first, path, sizeof(first));
        else if (strcmp(first, path)) exit(97);
        ++recognition_clips;
    }
    const char *clip = getenv("NW_TEST_CONCENTRATION_CLIP");
    if (clip) {
        if (recognition_clips == 1) clip = getenv("NW_TEST_CONCENTRATION_CLIP_TWO");
        const char *name = strrchr(path, '/');
        if (!clip || !name || strcmp(name + 1, clip)) exit(97);
        ++recognition_clips;
    }
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(97);
    bool (*load)(const char *, SDL_AudioSpec *, Uint8 **, Uint32 *) =
        (void *)SDL_LoadFunction(library, "SDL_LoadWAV");
    if (!load) exit(97);
    bool result = load(path, spec, audio, length);
    SDL_UnloadObject(library);
    if (env_int("NW_TEST_RECOGNITION_SOUND") && !result) exit(97);
    return result;
}

bool SDL_SetAudioStreamGain(SDL_AudioStream *stream, float gain) {
    if (env_int("NW_TEST_APPLAUSE")) {
        if (applause_gain_updates == 0) {
            if (gain != 0.25f) exit(97);
        } else if (!env_int("NW_TEST_REWARD_FADE") || gain >= 0.25f || gain <= 0.0f) {
            exit(97);
        }
        ++applause_gain_updates;
    }
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(97);
    bool (*set_gain)(SDL_AudioStream *, float) = (void *)SDL_LoadFunction(library, "SDL_SetAudioStreamGain");
    if (!set_gain) exit(97);
    bool result = set_gain(stream, gain);
    SDL_UnloadObject(library);
    return result;
}

bool SDL_PutAudioStreamData(SDL_AudioStream *stream, const void *data, int length) {
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(97);
    bool (*put)(SDL_AudioStream *, const void *, int) =
        (void *)SDL_LoadFunction(library, "SDL_PutAudioStreamData");
    if (!put) exit(97);
    bool result = put(stream, data, length);
    if (env_int("NW_TEST_APPLAUSE") && result && length > 0) ++applause_queued;
    if (env_int("NW_TEST_TIME_IT_CLOCK") && result) {
        if (length < 250000 || length % 4) exit(97);
        const uint8_t *pcm = data;
        bool audible = false;
        for (int i = 100; i < 4000; ++i) if (pcm[i]) audible = true;
        if (!audible) exit(97);
        ++time_it_audio_queued;
    }
    if (env_int("NW_TEST_ECHO_CLOCK") && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(97);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++echo_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_TUNER_CLOCK") && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(97);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++tuner_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_SHADOW_CLOCK") && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(97);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++shadow_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_ROVER") == 2 && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(102);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++rover_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_MORNING_ROUND") && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(104);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++morning_round_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_FULL_STOP") && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(106);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++full_stop_audio_queued;
                break;
            }
        }
    }
    if ((env_int("NW_TEST_MISSING_WORD") || env_int("NW_TEST_PROOFREADER") || env_int("NW_TEST_FIGURES") || env_int("NW_TEST_LINES") || env_int("NW_TEST_SECOND") || env_int("NW_TEST_ARGUE") || env_int("NW_TEST_SENSE") || env_int("NW_TEST_FEEL") || env_int("NW_TEST_STRONG") || env_int("NW_TEST_READ") || env_int("NW_TEST_WHY") || env_int("NW_TEST_TONE") || env_int("NW_TEST_EMO")) && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(107);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++missing_word_audio_queued;
                break;
            }
        }
    }
    if ((env_int("NW_TEST_CRAZY_COG") || env_int("NW_TEST_CIPHER_ABYSS") || env_int("NW_TEST_POTTER") || env_int("NW_TEST_CONDUCTOR") || env_int("NW_TEST_TIGHTROPE") || env_int("NW_TEST_SIGN_PAINTER") || env_int("NW_TEST_BARTENDER") || env_int("NW_TEST_LOCK_PICK") || env_int("NW_TEST_AIR_HOCKEY") || env_int("NW_TEST_SEMAPHORE") || env_int("NW_TEST_SHADOW_PUPPETS") || env_int("NW_TEST_NIGHT_WATCH") || env_int("NW_TEST_KERBSIDE") || env_int("NW_TEST_STEADICAM") || env_int("NW_TEST_FREE_KICK") || env_int("NW_TEST_GLOVE") || env_int("NW_TEST_BY_EAR") || env_int("NW_TEST_PIANO_TUNER") || env_int("NW_TEST_CRICKET_HUNT") || env_int("NW_TEST_CLAW_MACHINE")) && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(109);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++crazy_cog_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_HEAVIER") && result) {
        if (length <= 0 || length > 8820 || length % 4) exit(105);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++heavier_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_UNICYCLE") && result) {
        if (length <= 0 || length > 70560 || length % 4) exit(103);
        const uint8_t *pcm = data;
        for (int i = 0; i < length; ++i) {
            if (pcm[i]) {
                ++unicycle_audio_queued;
                break;
            }
        }
    }
    if (env_int("NW_TEST_HOLD_IT_CLOCK") && result) {
        if (length < 800000 || length % 4) exit(97);
        const uint8_t *pcm = data;
        bool audible = false;
        for (int i = 70600; i < 90000; ++i) if (pcm[i]) audible = true;
        if (!audible) exit(97);
        ++hold_it_audio_queued;
    }
    SDL_UnloadObject(library);
    if ((env_int("NW_TEST_RECOGNITION_SOUND") || getenv("NW_TEST_CONCENTRATION_CLIP")) && result && length > 0) ++recognition_queued;
    return result;
}

bool SDL_SetWindowFullscreen(SDL_Window *window, bool fullscreen) {
    if ((!env_int("NW_TEST_TITLE_KEYS") && !env_int("NW_TEST_FULLSCREEN")) || !window ||
        fullscreen_requests >= 2 || fullscreen != (fullscreen_requests == 0)) exit(97);
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(97);
    bool (*set_fullscreen)(SDL_Window *, bool) =
        (void *)SDL_LoadFunction(library, "SDL_SetWindowFullscreen");
    if (!set_fullscreen || !set_fullscreen(window, fullscreen)) exit(97);
    SDL_UnloadObject(library);
    if (!!(SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN) != fullscreen) exit(97);
    ++fullscreen_requests;
    return true;
}

static int vsync_requests;
bool SDL_SetRenderVSync(SDL_Renderer *renderer, int interval) {
    if (!renderer || interval != 1) exit(97);
    ++vsync_requests;
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(97);
    bool (*set_vsync)(SDL_Renderer *, int) = (void *)SDL_LoadFunction(library, "SDL_SetRenderVSync");
    if (!set_vsync) exit(97);
    bool result = set_vsync(renderer, interval);
    SDL_UnloadObject(library);
    return result;
}

static bool inject_render_failure(const char *operation) {
    const char *fault = getenv("NW_TEST_RENDER_FAILURE");
    return fault && strcmp(fault, operation) == 0;
}

bool SDL_RenderClear(SDL_Renderer *renderer) {
    if (inject_render_failure("clear")) return SDL_SetError("injected clear failure");
    /* SDL supplies the production entry point through its dynamic API. */
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(99);
    bool (*clear)(SDL_Renderer *) = (void *)SDL_LoadFunction(library, "SDL_RenderClear");
    if (!clear) exit(99);
    bool result = clear(renderer);
    SDL_UnloadObject(library);
    return result;
}

static int64_t jigsaw_status_frame, jigsaw_timed_handle;
static int video_jigsaw_first_red = -1;
static bool frame_contains(int64_t dest, int64_t length, const char *text);

bool SDL_RenderPresent(SDL_Renderer *renderer) {
    if (env_int("NW_TEST_HISTORY")) ++history_frames;
    if (env_int("NW_TEST_APPLAUSE") || getenv("NW_TEST_MUSIC_TIER")) ++applause_frames;
    if (inject_render_failure("present")) return SDL_SetError("injected present failure");
    if (env_int("NW_TEST_RECOGNITION_PHOTO")) {
        SDL_Surface *pixels = SDL_RenderReadPixels(renderer, NULL);
        Uint8 red = 0, green = 0, blue = 0, alpha = 0;
        if (!pixels || !SDL_ReadSurfacePixel(pixels, pixels->w / 2, (int)(pixels->h * 0.46),
                                            &red, &green, &blue, &alpha)) exit(97);
        SDL_DestroySurface(pixels);
        if (env_int("NW_TEST_RECOGNITION_PHOTO") == 1 && (red < 190 || green > 55 || blue > 55)) {
            fprintf(stderr, "Recognition JPEG stage pixel was %u,%u,%u\n", red, green, blue);
            exit(97);
        }
        if (env_int("NW_TEST_RECOGNITION_PHOTO") == 2 && (red < 245 || green < 245 || blue < 245)) exit(97);
    }
    const char *jigsaw_note = getenv("NW_TEST_JIGSAW_NOTE");
    if (jigsaw_note && !exit_sent) {
        const Uint8 *header = (const Uint8 *)(intptr_t)jigsaw_status_frame;
        Uint32 count = 0, pool = 0;
        if (!header) exit(97);
        memcpy(&count, header + 8, sizeof(count));
        memcpy(&pool, header + 12, sizeof(pool));
        int64_t length = 16 + (int64_t)count * 40 + pool;
        if (length > 131072 || !frame_contains(jigsaw_status_frame, length, jigsaw_note)) {
            fprintf(stderr, "Jigsaw note missing: %s\n", jigsaw_note);
            exit(97);
        }
    }
    if (jigsaw_timed_handle && !exit_sent) {
        int64_t handle = jigsaw_timed_handle;
        int64_t now = (int64_t)SDL_GetTicks() + 100;
        int64_t tiles = nw_jigsaw_info(handle, 2) * nw_jigsaw_info(handle, 15);
        for (int64_t pos = 0; pos < tiles; ++pos) {
            if (nw_jigsaw_value(handle, 0, pos) == pos) continue;
            int64_t other = pos + 1;
            while (other < tiles && nw_jigsaw_value(handle, 0, other) != pos) ++other;
            if (other == tiles || nw_jigsaw_action(handle, 1, pos, now) != 1 ||
                nw_jigsaw_action(handle, 1, other, now) != 1) exit(97);
        }
        int64_t took = nw_jigsaw_value(handle, 3, 0);
        if (took < 99 || took >= 250) {
            fprintf(stderr, "Jigsaw included the photo-load delay: %lld ms\n", (long long)took);
            exit(97);
        }
        if (env_int("NW_TEST_JIGSAW_ADAPT") &&
            (nw_jigsaw_action(handle, 2, 0, now + 1601) != 1 ||
             nw_jigsaw_info(handle, 2) != 3 || nw_jigsaw_info(handle, 15) != 4)) {
            fprintf(stderr, "Jigsaw did not advance from 9 to 12 pieces\n");
            exit(97);
        }
        jigsaw_timed_handle = 0;
    }
    if (env_int("NW_TEST_VIDEO_JIGSAW") && !exit_sent) {
        SDL_Surface *pixels = SDL_RenderReadPixels(renderer, NULL);
        Uint8 red, green, blue, alpha;
        if (!pixels || !SDL_ReadSurfacePixel(pixels, 210, 205, &red, &green, &blue, &alpha))
            exit(97);
        SDL_DestroySurface(pixels);
        if (green < 160 || blue > 40) {
            fprintf(stderr, "Video Jigsaw tile color: %u %u %u\n", red, green, blue);
            exit(97);
        }
        if (video_jigsaw_first_red < 0) {
            video_jigsaw_first_red = red;
            rendered = 0;
            SDL_Delay(105);
        } else if (red == video_jigsaw_first_red) {
            fprintf(stderr, "Video Jigsaw tile did not advance\n");
            exit(97);
        }
    }
    if (env_int("NW_TEST_JIGSAW_PHOTO") && !exit_sent) {
        SDL_Surface *pixels = SDL_RenderReadPixels(renderer, NULL);
        Uint8 red, green, blue, alpha;
        int board_colors = 0;
        for (int row = 0; row < 2; ++row) {
            for (int column = 0; column < 2; ++column) {
                if (!pixels || !SDL_ReadSurfacePixel(pixels, 200 + 240 * column, 220 + 240 * row,
                                                      &red, &green, &blue, &alpha)) exit(97);
                int color = (red > 230 ? 1 : 0) | (green > 230 ? 2 : 0) | (blue > 230 ? 4 : 0);
                board_colors |= 1 << color;
                if (!SDL_ReadSurfacePixel(pixels, 720 + 110 * column, 140 + 110 * row,
                                         &red, &green, &blue, &alpha)) exit(97);
                int preview = (red > 230 ? 1 : 0) | (green > 230 ? 2 : 0) | (blue > 230 ? 4 : 0);
                int expected[] = {1, 2, 4, 3};
                if (preview != expected[row * 2 + column]) {
                    fprintf(stderr, "Jigsaw preview crop: %d %d %d\n", row, column, preview);
                    exit(97);
                }
            }
        }
        if (board_colors != 30) {
            fprintf(stderr, "Jigsaw tray colors: %d\n", board_colors);
            exit(97);
        }
        SDL_DestroySurface(pixels);
    }
    if (env_int("NW_TEST_CONCENTRATION_PHOTO")) {
        SDL_Surface *pixels = SDL_RenderReadPixels(renderer, NULL);
        Uint8 red = 0, green = 0, blue = 0, alpha = 0;
        if (!pixels || !SDL_ReadSurfacePixel(pixels, 140, 190, &red, &green, &blue, &alpha) ||
            red < 190 || green > 55 || blue > 55) exit(97);
        if (!SDL_ReadSurfacePixel(pixels, 560, 190, &red, &green, &blue, &alpha) ||
            green < 185 || red > 55 || blue > 55) exit(97);
        SDL_DestroySurface(pixels);
    }
    SDL_SharedObject *library = SDL_LoadObject(NW_TEST_SDL_LIBRARY);
    if (!library) exit(99);
    bool (*present)(SDL_Renderer *) = (void *)SDL_LoadFunction(library, "SDL_RenderPresent");
    if (!present) exit(99);
    bool result = present(renderer);
    if (env_int("NW_TEST_PROFILE_PICKER")) ++picker_frames;
    SDL_UnloadObject(library);
    return result;
}

bool nw_test_poll(SDL_Event *event) {
    const char *frame_ack = getenv("NW_TEST_FRAME_ACK");
    if (frame_ack) {
        if (at++ == 0) return false;
        FILE *ready = fopen(getenv("NW_TEST_FRAME_READY"), "wb");
        if (!ready) exit(96);
        fclose(ready);
        SDL_PathInfo info;
        uint64_t deadline = SDL_GetTicks() + 5000;
        while (!SDL_GetPathInfo(frame_ack, &info)) {
            if (SDL_GetTicks() >= deadline) exit(96);
            SDL_Delay(5);
        }
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_QUIT;
        return true;
    }
    if (env_int("NW_TEST_TITLE_HUB")) {
        if (at != title_hub_frames || at >= 9) return false;
        memset(event, 0, sizeof(*event));
        if (at == 2 || at == 3) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            /* Twelve tabs: Reasoning (index 4) spans x 333-387 at 912 wide. */
            event->button.x = at == 2 ? 360 : 665;
            event->button.y = at == 2 ? 128 : 315;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at < 2 || at == 6 ? SDLK_SPACE : SDLK_ESCAPE;
            event->key.repeat = at == 0;
        }
        ++at;
        return true;
    }

    if (env_int("NW_TEST_SUDOKU_MENU") && at < 15) {
        static const SDL_Keycode keys[] = {
            SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN,
            SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_C, SDLK_RIGHT, SDLK_RETURN, SDLK_RETURN
        };
        memset(event, 0, sizeof(*event));
        if (at == 12) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 210.0f;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_GO_PREVIEW") && at < 5) {
        static const SDL_Keycode keys[] = {SDLK_5, SDLK_C, SDLK_LEFT, SDLK_DOWN, SDLK_LEFT};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_GO_MENU") && at < 18) {
        static const SDL_Keycode keys[] = {
            SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN,
            SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_C, SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, SDLK_RETURN, SDLK_RETURN
        };
        memset(event, 0, sizeof(*event));
        if (at == 13) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 210.0f;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_WIRES_MENU") && at < 23) {
        static const SDL_Keycode keys[] = {
            SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN,
            SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_C, SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT,
            SDLK_DOWN, SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, SDLK_RETURN, SDLK_RETURN
        };
        memset(event, 0, sizeof(*event));
        if (at == 14) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 210.0f;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        }
        ++at;
        return true;
    }
    int jigsaw_menu = env_int("NW_TEST_JIGSAW_MENU");
    bool video_menu = jigsaw_menu == 3;
    if (jigsaw_menu && at < 12 + video_menu) {
        static const SDL_Keycode keys[] = {
            SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN,
            SDLK_C, SDLK_RIGHT, SDLK_RETURN, SDLK_RETURN
        };
        memset(event, 0, sizeof(*event));
        if (jigsaw_menu == 2 && at == 9) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 210.0f;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = video_menu && at == 8 ? SDLK_DOWN : keys[at - (video_menu && at > 8)];
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_JIGSAW_HOVER")) {
        if (at > jigsaw_hover_frames) return false;
        memset(event, 0, sizeof(*event));
        if (at == 0) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else if (at <= 3) {
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.x = at == 2 ? 50.0f : 370.0f;
            event->motion.y = 180.0f;
        } else if (at == 4) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_MOUSE_LEAVE;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 5) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 370.0f;
            event->button.y = 180.0f;
        } else {
            puts("SDL Jigsaw hover: PASS");
            fflush(stdout);
            event->type = SDL_EVENT_QUIT;
        }
        ++at;
        return true;
    }
    int picker_mode = env_int("NW_TEST_PROFILE_PICKER");
    if (picker_mode) {
        static const SDL_Keycode existing[] = {SDLK_U, SDLK_DOWN, SDLK_DOWN, SDLK_RETURN};
        static const SDL_Keycode create[] = {SDLK_U, SDLK_UP, SDLK_RETURN, SDLK_RETURN,
                                            0, SDLK_LEFT, SDLK_BACKSPACE, SDLK_RETURN};
        int count = picker_mode == 3 ? sizeof(create) / sizeof(*create) : sizeof(existing) / sizeof(*existing);
        if (at > picker_frames) return false;
        if (at < count) {
            memset(event, 0, sizeof(*event));
            SDL_Keycode key = picker_mode == 3 ? create[at] : existing[at];
            if (picker_mode == 2 && at == 3) key = SDLK_ESCAPE;
            if (!key) {
                event->type = SDL_EVENT_TEXT_INPUT;
                event->text.text = "Zoë QX";
            } else {
                event->type = SDL_EVENT_KEY_DOWN;
                event->key.key = key;
            }
            ++at;
            return true;
        }
        if (picker_mode == 4 && at < count + 17) {
            int step = at++ - count;
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = step < 4 ? SDLK_RIGHT : (step < 16 ? SDLK_DOWN : SDLK_RETURN);
            return true;
        }
        if (picker_mode == 4) count += 17;
        if (at == count) {
            int windows_count = 0;
            SDL_Window **windows = SDL_GetWindows(&windows_count);
            if (windows_count != 1) exit(97);
            const char *expected = picker_mode == 3 ? "Neural Workshop 5.0 - Zoë X" :
                (picker_mode == 2 ? "Neural Workshop 5.0" : "Neural Workshop 5.0 - Other User");
            const char *title = SDL_GetWindowTitle(windows[0]);
            if (strcmp(title, expected) != 0) {
                fprintf(stderr, "profile picker title: %s, expected %s\n", title, expected);
                exit(97);
            }
            SDL_free(windows);
            puts("SDL profile picker: PASS");
            fflush(stdout);
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_QUIT;
            ++at;
            return true;
        }
        return false;
    }
    if (env_int("NW_TEST_HISTORY") && history_frames < 6) {
        if (at != history_frames) return false;
        static const SDL_Keycode history_keys[] = {SDLK_G, SDLK_M, SDLK_N, SDLK_N, SDLK_N, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = history_keys[at++];
        return true;
    }
    if (env_int("NW_TEST_REWARD_FADE") && applause_frames >= 2 && applause_frames < 5) {
        if (at == 1) {
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
            ++at;
            return true;
        }
        if (applause_frames == 3) SDL_Delay(55);
        if (applause_frames == 4) SDL_Delay(220);
        return false;
    }
    if (env_int("NW_TEST_APPLAUSE") || getenv("NW_TEST_MUSIC_TIER")) {
        if (at > 0 && applause_frames < 3) return false;
        if (at == 0) {
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
            ++at;
            return true;
        }
    }
    int media_hub = env_int("NW_TEST_MEDIA_HUB");
    if (media_hub) {
        bool recognition = env_int("NW_TEST_MEDIA_RECOGNITION");
        SDL_Keycode keys[] = {SDLK_RIGHT, SDLK_DOWN, SDLK_C, SDLK_RIGHT,
                              media_hub == 1 ? SDLK_RETURN : SDLK_ESCAPE, SDLK_RETURN};
        if (!recognition && at == 1) ++at;
        if (at < (int)SDL_arraysize(keys)) {
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at++];
            return true;
        }
    }
    int media_menu = env_int("NW_TEST_MEDIA_MENU");
    if (media_menu && at < 3 && (at < 2 || media_menu != 1 || rendered)) {
        memset(event, 0, sizeof(*event));
        if (media_menu == 4 && at == 1) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 400;
            event->button.y = 210;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_C : at == 1 ? SDLK_RIGHT :
                media_menu == 2 || media_menu == 4 ? SDLK_RETURN : SDLK_ESCAPE;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_RECOGNITION_PHOTO") && at == 0) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = SDLK_SPACE;
        ++at;
        return true;
    }
    int concentration_photo = env_int("NW_TEST_CONCENTRATION_PHOTO");
    if ((concentration_photo || getenv("NW_TEST_CONCENTRATION_CLIP")) &&
        at < ((concentration_photo || getenv("NW_TEST_CONCENTRATION_CLIP_TWO")) ? 3 : 2)) {
        memset(event, 0, sizeof(*event));
        if (at++ == 0) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 2 ? 140 : 560;
            event->button.y = 190;
        }
        return true;
    }
    if (env_int("NW_TEST_RECOGNITION_CLICK") && at < 4) {
        memset(event, 0, sizeof(*event));
        int choice = env_int("NW_TEST_RECOGNITION_CLICK");
        if (at == 0) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else if (at == 1) {
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.x = choice == 1 ? 518 : 482;
            event->motion.y = 499;
        } else {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 2 ? 500 : (choice == 1 ? 482 : 518);
            event->button.y = 499;
        }
        ++at;
        return true;
    }
    int recognition_sound = env_int("NW_TEST_RECOGNITION_SOUND");
    if (recognition_sound) {
        if (at == 0 || ((rendered == 1 || recognition_sound == 2) && recognition_replay == 0)) {
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_R;
            if (at++ != 0) recognition_replay = 1;
            return true;
        }
        if (recognition_replay == 1) {
            recognition_replay = 2;
            return false;
        }
    }
    if (env_int("NW_TEST_TYPED_NUMBER") && at < 2) {
        memset(event, 0, sizeof(*event));
        if (at++ == 0) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            event->type = SDL_EVENT_TEXT_INPUT;
            event->text.text = "57";
        }
        return true;
    }
    if (env_int("NW_TEST_MOUSE_BUTTON") && at == 0) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
        event->button.button = SDL_BUTTON_LEFT;
        event->button.x = 40.5f;
        event->button.y = 30.25f;
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FULLSCREEN") == 2 && at == 0) {
        memset(event, 0, sizeof(*event)); event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = SDLK_F11; ++at; return true;
    }
    if (env_int("NW_TEST_HOVER") && at < 2) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_MOUSE_MOTION;
        event->motion.x = at == 0 ? 20 : 40;
        event->motion.y = 30;
        event->motion.state = at++ == 0 ? SDL_BUTTON_LMASK : 0;
        return true;
    }
    if (env_int("NW_TEST_TITLE_KEYS") && at < 8) {
        static const SDL_Keycode keys[] = {SDLK_LEFT, SDLK_UP, SDLK_RETURN, SDLK_DOWN, SDLK_RIGHT, SDLK_F11, SDLK_F11, SDLK_F11};
        memset(event, 0, sizeof(*event)); event->type = SDL_EVENT_KEY_DOWN;
        event->key.repeat = at == 4 || at == 6;
        event->key.key = keys[at++]; return true;
    }
    if (env_int("NW_TEST_ATTENTION_MOUSE") && at < 2) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
        event->button.button = SDL_BUTTON_LEFT;
        /* Twelve tabs: Attention (index 2) spans x 205-259 at 912 wide. */
        event->button.x = at == 0 ? 232 : (env_int("NW_TEST_ATTENTION_MOUSE") % 3 == 2 ? 665 : (env_int("NW_TEST_ATTENTION_MOUSE") % 3 == 1 ? 456 : 247));
        event->button.y = at == 0 ? 128 : 215 + (env_int("NW_TEST_ATTENTION_MOUSE") / 3) * 46;
        ++at;
        return true;
    }
    if (env_int("NW_TEST_HUB_MOUSE") && at < 3) {
        bool wide = env_int("NW_TEST_WIDTH") == 960;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
        event->button.button = SDL_BUTTON_LEFT;
        /* Twelve tabs: Reasoning (index 4) spans x 333-387 at 912 by 684; 960 by 480 draws a 640-wide hub from x 160, where it spans 395-430. */
        event->button.x = at == 0 ? (wide ? 412 : 360) : (at == 1 ? 0 : (wide ? 627 : 665));
        event->button.y = at == 0 ? (wide ? 90 : 128) : (wide ? 239 : 315);
        ++at;
        return true;
    }
    if (env_int("NW_TEST_HUB_WRAP") && at < 3) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        static const SDL_Keycode keys[] = {SDLK_ESCAPE, SDLK_UP, SDLK_RETURN};
        event->key.key = keys[at++];
        return true;
    }
    int category_steps = env_int("NW_TEST_CATEGORY");
    int row_steps = env_int("NW_TEST_ROW");
    int total = category_steps + row_steps + 1;
    if (env_int("NW_TEST_COOKIE_PREVIEW") && at < 4) {
        if ((at == 2 && !rendered) || at == 3) return false;
        static const SDL_Keycode keys[] = {SDLK_C, SDLK_RIGHT, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_COOKIE_MENU") && at >= total && at < total + 11) {
        int offset = at++ - total;
        static const SDL_Keycode keys[] = {SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, SDLK_DOWN,
            SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, 0, 0, SDLK_KP_ENTER, SDLK_RETURN};
        memset(event, 0, sizeof(*event));
        if (offset == 7 || offset == 8) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 402;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
        }
        return true;
    }
    int cookie_offset = at - (env_int("NW_TEST_DIRECT") ? 0 : total);
    if (env_int("NW_TEST_COOKIE_THIEF") && cookie_offset >= 0) {
        if (((cookie_offset == 1 || cookie_offset == 2) && cookie_phase != 2) ||
            (cookie_offset == 3 && cookie_phase != 3) ||
            (cookie_offset == 4 && cookie_phase != 4)) return false;
        if (cookie_offset < 4) {
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_X, SDLK_DOWN, SDLK_SPACE};
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[cookie_offset];
            ++at;
            return true;
        }
    }
    const char *sokoban3d_route = getenv("NW_TEST_SOKOBAN3D_ROUTE");
    int sokoban3d_offset = at - (env_int("NW_TEST_DIRECT") ? 0 : total);
    if (sokoban3d_route && sokoban3d_offset >= 0 && sokoban3d_offset < (int)strlen(sokoban3d_route) + 2) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        int length = (int)strlen(sokoban3d_route);
        event->key.key = sokoban3d_offset == 0 || sokoban3d_offset == length + 1 ?
            SDLK_SPACE : sokoban3d_route[sokoban3d_offset - 1];
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SOKOBAN3D_PREVIEW") && at < 6) {
        if ((at == 4 && !rendered) || at == 5) return false;
        static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_A, SDLK_C, SDLK_RIGHT, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_SOKOBAN3D_MENU") && at >= total && at < total + 11) {
        int offset = at++ - total;
        static const SDL_Keycode keys[] = {SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, SDLK_DOWN,
            SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, 0, 0, SDLK_KP_ENTER, SDLK_RETURN};
        memset(event, 0, sizeof(*event));
        if (offset == 7 || offset == 8) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 402;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
        }
        return true;
    }
    if (env_int("NW_TEST_SOKOBAN3D")) {
        int offset = at - (env_int("NW_TEST_DIRECT") ? 0 : total);
        if (offset >= 1 && offset <= 6 && sokoban3d_checked < offset) return false;
        if (offset >= 0 && offset < 6) {
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_A, SDLK_U, SDLK_D, SDLK_R, SDLK_W};
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
            ++at;
            return true;
        }
    }
    const char *maze_route = getenv("NW_TEST_MAZE2D_ROUTE");
    if (maze_route && at < (int)strlen(maze_route) + 2) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        int length = (int)strlen(maze_route);
        event->key.key = at == 0 || at == length + 1 ? SDLK_SPACE : maze_route[at - 1];
        ++at;
        return true;
    }
    if (env_int("NW_TEST_MAZE2D")) {
        int offset = at - (env_int("NW_TEST_DIRECT") ? 0 : total);
        if ((offset == 5 && !rendered) || (offset == 6 && !maze2d_restarted)) return false;
        if (offset >= 0 && offset < 6) {
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_W, SDLK_D, SDLK_S, SDLK_A, SDLK_R};
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
            ++at;
            return true;
        }
    }
    if (env_int("NW_TEST_MAZE2D_PREVIEW") && at < 4) {
        if ((at == 2 && !rendered) || at == 3) return false;
        static const SDL_Keycode keys[] = {SDLK_C, SDLK_RIGHT, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_MAZE2D_MENU") && at >= total && at < total + 8) {
        int offset = at++ - total;
        static const SDL_Keycode keys[] = {SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT, SDLK_DOWN,
            SDLK_RIGHT, SDLK_RIGHT, SDLK_KP_ENTER, SDLK_RETURN};
        memset(event, 0, sizeof(*event));
        if (offset == 4 || offset == 5) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 354;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
        }
        return true;
    }
    if (env_int("NW_TEST_NINAROW_PREVIEW") && at < 5) {
        if ((at == 3 && !rendered) || at == 4) return false;
        static const SDL_Keycode keys[] = {SDLK_O, SDLK_DOWN, SDLK_RIGHT, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_NINAROW_MENU") && at >= total && at < total + 10) {
        int offset = at++ - total;
        static const SDL_Keycode keys[] = {SDLK_PAGEDOWN, SDLK_RIGHT, SDLK_PAGEUP, SDLK_RIGHT,
            SDLK_DOWN, SDLK_RIGHT, SDLK_RIGHT, SDLK_RIGHT, SDLK_KP_ENTER, SDLK_KP_ENTER};
        memset(event, 0, sizeof(*event));
        if (offset == 6 || offset == 7) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 282;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
        }
        return true;
    }
    if (env_int("NW_TEST_NINAROW")) {
        int offset = at - (env_int("NW_TEST_DIRECT") ? 0 : total);
        static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_SPACE, SDLK_RIGHT, SDLK_KP_ENTER};
        if (offset >= 0 && offset < 4) {
            memset(event, 0, sizeof(*event));
            if (offset == 1 || (offset == 0 && env_int("NW_TEST_DIRECT"))) {
                event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = 310;
                event->button.y = 168;
            } else {
                event->type = SDL_EVENT_KEY_DOWN;
                event->key.key = keys[offset];
            }
            ++at;
            return true;
        }
    }
    if (env_int("NW_TEST_SALESMAN")) {
        int start = env_int("NW_TEST_DIRECT") ? 0 : total;
        if (at == start) {
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
            ++at;
            return true;
        }
        if (at > start && !salesman_settled) {
            if (!rendered || salesman_clicks == 5) return false;
            memset(event, 0, sizeof(*event));
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = salesman_x[salesman_clicks];
            event->button.y = salesman_y[salesman_clicks++];
            return true;
        }
    }
    if (env_int("NW_TEST_SALESMAN_PREVIEW") && at < 6) {
        if ((at == 4 && !rendered) || at == 5) return false;
        static const SDL_Keycode keys[] = {SDLK_C, SDLK_PAGEDOWN, SDLK_PAGEUP, SDLK_RIGHT, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_SALESMAN_MENU") && at >= total && at < total + 10) {
        int offset = at++ - total;
        static const SDL_Keycode keys[] = {SDLK_RIGHT, SDLK_UP, SDLK_DOWN, SDLK_RIGHT,
            SDLK_DOWN, SDLK_RIGHT, SDLK_PAGEDOWN, SDLK_RIGHT, SDLK_KP_ENTER, SDLK_KP_ENTER};
        memset(event, 0, sizeof(*event));
        if (offset == 0) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 210;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
        }
        return true;
    }
    if (env_int("NW_TEST_HANOI_PREVIEW") && at < 4) {
        if ((at == 2 && !rendered) || at == 3) return false;
        static const SDL_Keycode keys[] = {SDLK_C, SDLK_RIGHT, SDLK_ESCAPE};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_HANOI_MENU") && at >= total && at < total + 7) {
        int offset = at++ - total;
        static const SDL_Keycode keys[] = {SDLK_RIGHT, SDLK_DOWN, SDLK_RIGHT,
            SDLK_DOWN, SDLK_RIGHT, SDLK_RETURN, SDLK_RETURN};
        memset(event, 0, sizeof(*event));
        if (offset == 0) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 210;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[offset];
        }
        return true;
    }
    if (env_int("NW_TEST_HANOI")) {
        int offset = at - (env_int("NW_TEST_DIRECT") ? 0 : total);
        static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_1, SDLK_KP_3, SDLK_1, SDLK_2,
            SDLK_3, SDLK_2, SDLK_1, SDLK_3, SDLK_2, SDLK_1, SDLK_2, SDLK_3, SDLK_1, SDLK_3};
        if (offset >= 0 && offset < (int)(sizeof(keys) / sizeof(keys[0]))) {
            memset(event, 0, sizeof(*event));
            if (offset == 1) {
                event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = 188;
                event->button.y = 584;
            } else {
                event->type = SDL_EVENT_KEY_DOWN;
                event->key.key = keys[offset];
            }
            ++at;
            return true;
        }
    }
    if (env_int("NW_TEST_MORNING_ROUND_HUB_POINTER") && at == category_steps) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
        event->button.button = SDL_BUTTON_LEFT;
        event->button.x = 456;
        event->button.y = 290;
        ++at;
        return true;
    }
    if ((env_int("NW_TEST_HEAVIER_HUB_POINTER") || env_int("NW_TEST_FULL_STOP_HUB_POINTER") ||
         env_int("NW_TEST_MISSING_WORD_HUB_POINTER") || env_int("NW_TEST_PROOFREADER_HUB_POINTER") ||
         env_int("NW_TEST_FIGURES_HUB_POINTER") || env_int("NW_TEST_CRAZY_COG_HUB_POINTER")) &&
        at == category_steps) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
        event->button.button = SDL_BUTTON_LEFT;
        event->button.x = (env_int("NW_TEST_MISSING_WORD_HUB_POINTER") || env_int("NW_TEST_CRAZY_COG_HUB_POINTER")) ? 663 :
            (env_int("NW_TEST_FULL_STOP_HUB_POINTER") || env_int("NW_TEST_FIGURES_HUB_POINTER")) ? 456 : 249;
        event->button.y = (env_int("NW_TEST_PROOFREADER_HUB_POINTER") || env_int("NW_TEST_FIGURES_HUB_POINTER") || env_int("NW_TEST_CRAZY_COG_HUB_POINTER")) ? 583 : 537;
        ++at;
        return true;
    }
    if (!env_int("NW_TEST_DIRECT") && at < total) {
        memset(event, 0, sizeof(*event)); event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = at < category_steps ? SDLK_RIGHT : at < category_steps + row_steps ? SDLK_DOWN :
                         env_int("NW_TEST_OPTION") ? SDLK_C : SDLK_RETURN;
        at++; return true;
    }
    if ((env_int("NW_TEST_PUZZLE_SEED") || env_int("NW_TEST_LARGE_FRAME") || env_int("NW_TEST_MARBLE_PHYSICS") || env_int("NW_TEST_JIGSAW_PHOTO") || getenv("NW_TEST_JIGSAW_NOTE")) && !puzzle_started) {
        memset(event, 0, sizeof(*event)); event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = SDLK_SPACE; puzzle_started = 1; return true;
    }
    if (env_int("NW_TEST_JIGSAW_CLOCK") && puzzle_started == 1 && !rendered) {
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = SDLK_RETURN;
        puzzle_started = 2;
        return true;
    }
    if (env_int("NW_TEST_MARBLE_PHYSICS") && marble_input < 5) {
        static const Uint32 types[] = {SDL_EVENT_KEY_DOWN, SDL_EVENT_KEY_DOWN,
            SDL_EVENT_KEY_UP, SDL_EVENT_WINDOW_FOCUS_LOST, SDL_EVENT_KEY_DOWN};
        static const SDL_Keycode keys[] = {SDLK_UP, SDLK_RIGHT, SDLK_RIGHT, 0, SDLK_LEFT};
        memset(event, 0, sizeof(*event));
        event->type = types[marble_input];
        if (event->type == SDL_EVENT_WINDOW_FOCUS_LOST) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->key.key = keys[marble_input];
        }
        if (++marble_input < 5) return true;
        SDL_Delay(10);
        return true;
    }
    if (env_int("NW_TEST_POV") && at < 4) {
        if (pov_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 3) {
            delay_clock += 2500;
            event->type = SDL_EVENT_USER;
        } else if (at == 1 || (at == 2 && env_int("NW_TEST_POV") == 2)) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 1 ? 170 : 800;
            event->button.y = at == 1 ? 314 : 202;
        } else {
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_3;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_INSIDE") && at < 3) {
        if (inside_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 2) {
            delay_clock += 2500;
            event->type = SDL_EVENT_USER;
        } else if (at == 1 && env_int("NW_TEST_INSIDE") == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 320;
            event->button.y = 480;
        } else {
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_I;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_TOUCHING") && at < 3) {
        if (touching_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 2) {
            delay_clock += 2500;
            event->type = SDL_EVENT_USER;
        } else if (at == 1 && env_int("NW_TEST_TOUCHING") == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 95;
            event->button.y = 480;
        } else {
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_O;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CROSSINGS") && at < 3) {
        if (crossings_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 2) {
            delay_clock += 2500;
            event->type = SDL_EVENT_USER;
        } else if (at == 1 && env_int("NW_TEST_CROSSINGS") == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 480;
        } else {
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_2;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_MIRROR") && at < 3) {
        if (mirror_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 2) {
            delay_clock += 2500;
            event->type = SDL_EVENT_USER;
        } else if (at == 1 && env_int("NW_TEST_MIRROR") == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 432;
        } else {
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_S;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_NEARER") && at < 6) {
        if (nearer_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 1 || at == 5) {
            delay_clock += at == 1 ? 600 : 3000;
            event->type = SDL_EVENT_USER;
        } else if (at == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 479;
        } else {
            event->key.key = at == 0 ? SDLK_SPACE : at == 3 ? SDLK_1 : SDLK_3;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_ROOMS") && at < 8) {
        if (rooms_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 7) {
            delay_clock += 3000;
            event->type = SDL_EVENT_USER;
        } else if (at == 6 || at == 1) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 6 ? 436.5344f : 456.0f;
            event->button.y = at == 6 ? 232.1323f : 494.0f;
        } else {
            event->key.key = at == 2 ? SDLK_N : at == 3 ? SDLK_RETURN : SDLK_SPACE;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_NOTEBOOK") && at < 5) {
        if (notebook_frame < at) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        if (at == 0) {
            event->key.key = SDLK_SPACE;
        } else if (at == 1) {
            event->key.key = SDLK_EXCLAIM;
            event->key.scancode = SDL_SCANCODE_1;
            event->key.mod = SDL_KMOD_LSHIFT;
        } else if (at == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 224;
            event->button.y = 359;
        } else if (at == 3) {
            event->key.key = SDLK_2;
        } else {
            delay_clock += 2500;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_BALANCE_CLOCK") && balance_judged < 2) {
        if (balance_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_A : SDLK_LEFT;
        } else if (at == 3) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_A;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            if (at > 100) exit(97);
            delay_clock += balance_judged ? 2500 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_JUGGLER_CLOCK") && juggler_judged < 2) {
        if (juggler_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_A : SDLK_LEFT;
        } else if (at == 3) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_A;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            if (at > 100) exit(97);
            delay_clock += juggler_judged ? 2500 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_LANDER_CLOCK") && lander_judged < 2) {
        if (lander_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_UP : SDLK_LEFT;
        } else if (at == 3) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_UP;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            if (at > 245) exit(97);
            delay_clock += lander_judged ? 2500 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_GLIDER_CLOCK") && glider_judged < 2) {
        if (glider_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_UP : SDLK_W;
        } else if (at == 3) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_SPACE;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            if (at > 120) exit(97);
            delay_clock += glider_judged ? 2500 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CATCH_CLOCK") && catch_judged < 2) {
        if (catch_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_LEFT : SDLK_W;
        } else if (at == 3) {
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.x = 700;
            event->motion.y = 440;
        } else if (at == 6) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            if (at > 500) exit(97);
            delay_clock += catch_judged ? 2500 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if ((env_int("NW_TEST_FIELD_CLICK") || env_int("NW_TEST_DOCK_CLICK") || env_int("NW_TEST_GUN_CLICK")) && at < 5) {
        bool dock = env_int("NW_TEST_DOCK_CLICK") != 0;
        float x = dock ? 515.75f : 425.0f, y = dock ? 367.65f : 301.0f;
        memset(event, 0, sizeof(*event));
        if (at == 0) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            SDL_WindowID id = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
            if (at == 1 || at == 3) {
                event->type = SDL_EVENT_MOUSE_MOTION;
                event->motion.state = at == 3 ? SDL_BUTTON_LMASK : 0;
                event->motion.windowID = id;
                event->motion.x = x;
                event->motion.y = y;
            } else {
                event->type = at == 2 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
                event->button.windowID = id;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = x;
                event->button.y = y;
            }
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_ECHO_CLOCK") && echo_judged < 2) {
        if (echo_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 1 ? SDLK_LEFT : SDLK_SPACE;
        } else if (at == 3) {
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.x = 700;
            event->motion.y = 440;
        } else if (at == 6) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            if (at > 600) exit(97);
            delay_clock += echo_judged ? 2500 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_BEAT_CLOCK") && beat_judged < 2) {
        static unsigned long long last_beat_tap = 0;
        if (beat_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at == 0 || (delay_clock >= 7200 && delay_clock <= 11200 &&
                        (delay_clock - 7200) % 800 == 0 && delay_clock != last_beat_tap)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_F;
            last_beat_tap = delay_clock;
        } else {
            if (at > 260) exit(97);
            delay_clock += beat_judged ? 3000 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_TIME_IT_CLOCK") && at < 96) {
        if (time_it_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at == 0 || at == 94) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            delay_clock += at == 95 ? 3000 : 25;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_HOLD_IT_CLOCK") && at < 104) {
        if (hold_it_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at == 0) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456;
            event->button.y = 342;
        } else if (at == 81) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else if (at == 102) {
            if (env_int("NW_TEST_HOLD_IT_CLOCK") == 2) {
                int count = 0;
                SDL_Window **windows = SDL_GetWindows(&count);
                if (count != 1) exit(97);
                event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
                event->window.windowID = SDL_GetWindowID(windows[0]);
                SDL_free(windows);
            } else {
                event->type = SDL_EVENT_KEY_UP;
                event->key.key = SDLK_SPACE;
            }
        } else {
            delay_clock += at == 103 ? 3000 : 50;
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_DELAY_CLOCK") && at < 9) {
        if (delay_frame < at) return false;
        const Uint64 times[] = {0, 0, 3000, 4000, 4000, 4200, 4700, 60000, 63000};
        delay_clock = times[at];
        memset(event, 0, sizeof(*event));
        if (at <= 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_D;
        } else if (at == 4 || at == 5) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 4 ? 610 : 300;
            event->button.y = 324;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_TRIAGE") && at < 6) {
        if (triage_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at >= 2) {
            static const float xs[] = {390, 525, 640, 525}, ys[] = {391, 391, 184, 391};
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = xs[at - 2];
            event->button.y = ys[at - 2];
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_DRSHAPE_CLOCK") && at < 98) {
        if (drshape_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 72 && env_int("NW_TEST_DRSHAPE_CLOCK") == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 374;
            event->button.y = 324;
        } else if (at == 0 || at == 1 || at == 72) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_1;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FOLD_IT") && at < 57) {
        if (fold_it_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 1) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 789;
            event->button.y = 211;
        } else if (at == 0 || at == 28 || at == 29) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 29 ? SDLK_6 : SDLK_SPACE;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_WHO_KNOWS_WHAT") && at < 57) {
        if (who_knows_what_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 1) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 565;
            event->button.y = 486;
        } else if (at == 0 || at == 28 || at == 29) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 29 ? SDLK_4 : SDLK_SPACE;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_DAM_KEEPER") && at < 351) {
        if (dam_keeper_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 2) {
            // First gate, lower half, at the 912 x 684 reference size.
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 462;
            event->button.y = 275;
        } else if (at == 0 || at == 1 || at == 350) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 1 ? SDLK_Q : SDLK_SPACE;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CROSSROADS") && at < 7) {
        if (crossroads_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 6) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_RIGHT;
            event->button.x = 551.7f;
            event->button.y = 382.3f;
        } else if (at <= 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FERRY") && at < 7) {
        if (ferry_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 4) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_A;
        } else if (at == 6) {
            event->type = SDL_EVENT_USER;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_W : at == 2 ? SDLK_A : SDLK_LEFT;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_DOCKING") && at < 7) {
        if (docking_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 4) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_A;
        } else if (at == 6) {
            event->type = SDL_EVENT_USER;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_R : at == 2 ? SDLK_A : SDLK_Q;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FULL_STOP") && at < 15) {
        if (full_stop_frame < at) return false;
        delay_clock = at == 14 ? 5500 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 3 || at == 4) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 3 ? SDLK_R : SDLK_RETURN;
        } else if (at == 1 || at == 2) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(106);
            event->type = at == 1 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 203;
            event->button.y = 189;
            SDL_free(windows);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_LOCK_PICK") && at < 32) {
        if (lockpick_frame < at) return false;
        delay_clock = at == 31 ? 8000 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 6 || at == 7) {
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_SPACE, SDLK_T, SDLK_SPACE, SDLK_T, SDLK_SPACE};
            event->type = at == 3 || at == 4 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = at == 7 ? SDLK_SPACE : keys[at];
        } else if (at == 6) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(116);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_AIR_HOCKEY") && !airhockey_done && at < 2000) {
        if (airhockey_frame < at) return false;
        delay_clock = airhockey_judged_clock ? airhockey_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 6) {
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_LEFT, SDLK_A, SDLK_LEFT, SDLK_A, SDLK_D};
            event->type = at == 3 || at == 4 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        } else if (at == 6) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(117);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SEMAPHORE") && !semaphore_done && at < 2000) {
        if (semaphore_frame < at) return false;
        delay_clock = semaphore_judged_clock ? semaphore_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 2) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(118);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            /* Enter starts; then C and Q in turn, typed with the flags at rest:
               nothing before a signal is up, a mismatch strike on each signal
               after. C is a letter here, never the options key. */
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_RETURN : (at % 2 ? SDLK_C : SDLK_Q);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CLAW_MACHINE") && !claw_done && at < 2000) {
        if (claw_frame < at) return false;
        delay_clock = claw_judged_clock ? claw_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 10 && at != 5) {
            /* Space starts; Left and A are held and let go each on its own;
               the focus is lost; W is held, repeated and let go; then Enter
               drops the claw, and Space after it does nothing. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_LEFT, SDLK_A, SDLK_LEFT, SDLK_A, 0,
                SDLK_W, SDLK_W, SDLK_W, SDLK_RETURN};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(121);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 11) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CRICKET_HUNT") && !cricket_done && at < 2000) {
        if (cricket_frame < at) return false;
        delay_clock = cricket_judged_clock ? cricket_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 10 && at != 5) {
            /* Space starts; W and Up are held and let go each on its own;
               the focus is lost; Q (the shell's quit elsewhere) is held,
               repeated and let go, and E held and let go. Then three grabs
               at nothing end the try. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_W, SDLK_UP, SDLK_W, SDLK_UP, 0,
                SDLK_Q, SDLK_Q, SDLK_Q, SDLK_E};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(121);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 10) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_E;
        } else if (at == 12 || at == 13 || at == 14) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_PIANO_TUNER") && !tune_done && at < 2000) {
        if (tune_frame < at) return false;
        delay_clock = tune_judged_clock ? tune_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 11 && at != 5) {
            /* Space starts; Up and W are held and let go each on its own;
               the focus is lost; Shift and Down are held, Down repeated and
               let go, Shift let go; then Enter says it is in tune -- it is
               sharp, for it started sharp and was only turned up. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_UP, SDLK_W, SDLK_UP, SDLK_W, 0,
                SDLK_LSHIFT, SDLK_DOWN, SDLK_DOWN, SDLK_DOWN, SDLK_LSHIFT};
            event->type = at == 3 || at == 4 || at == 9 || at == 10 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 8;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(121);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 12) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_RETURN;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_BY_EAR") && !ear_done && at < 2000) {
        if (ear_frame < at) return false;
        delay_clock = ear_judged_clock ? ear_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 0 || at == 5 || at == 6 || at == 32 || at == 33) {
            /* Space starts; G pressed while the tune plays does nothing, nor
               does Space in play; then G and E, as the tune went, after it
               has played (2.9 s). */
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 || at == 6 ? SDLK_SPACE : (at == 33 ? SDLK_D : SDLK_G);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_GLOVE") && !glove_done && at < 2000) {
        if (glove_frame < at) return false;
        delay_clock = glove_judged_clock ? glove_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 9 && at != 5) {
            /* Space starts and then does nothing; Up and W are held and let
               go each on its own, A is held, repeated and let go after the
               focus comes back. Then nobody is at the glove, and the pitches
               go by. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_UP, SDLK_W, SDLK_UP, SDLK_W, 0, SDLK_A, SDLK_A, SDLK_A};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(121);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 9) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FREE_KICK") && !kick_done && at < 2000) {
        if (kick_frame < at) return false;
        delay_clock = kick_judged_clock ? kick_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 10 && at != 5) {
            /* Space starts; Left and W are held and let go each on its own,
               A is held, repeated and let go after the focus comes back, and
               Space kicks. The kick lands in the goal, off the ring. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_LEFT, SDLK_W, SDLK_LEFT, SDLK_W, 0, SDLK_A, SDLK_A, SDLK_A, SDLK_SPACE};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(121);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_STEADICAM") && !steady_done && at < 2000) {
        if (steady_frame < at) return false;
        delay_clock = steady_judged_clock ? steady_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        int count = 0;
        SDL_Window **windows = SDL_GetWindows(&count);
        if (count != 1) exit(120);
        SDL_WindowID window = SDL_GetWindowID(windows[0]);
        SDL_free(windows);
        if (at < 9 && at != 5) {
            /* Space starts; Left and A are held and let go each on its own,
               and Q -- a shell shortcut elsewhere -- zooms out, held,
               repeated and let go after the focus comes back. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_LEFT, SDLK_A, SDLK_LEFT, SDLK_A, 0, SDLK_Q, SDLK_Q, SDLK_Q};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = window;
        } else if (at == 9 || at == 11) {
            /* A drag with the primary button, then the wheel one notch up.
               Then nobody follows the walker, who is lost. */
            event->type = at == 9 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = window;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 9 ? 456.0f : 500.0f;
            event->button.y = at == 9 ? 342.0f : 300.0f;
        } else if (at == 10) {
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.windowID = window;
            event->motion.state = SDL_BUTTON_LMASK;
            event->motion.x = 500.0f;
            event->motion.y = 300.0f;
        } else if (at == 12) {
            event->type = SDL_EVENT_MOUSE_WHEEL;
            event->wheel.windowID = window;
            event->wheel.y = 1.0f;
            event->wheel.direction = SDL_MOUSEWHEEL_NORMAL;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_KERBSIDE") && !kerb_done && at < 2000) {
        if (kerb_frame < at) return false;
        delay_clock = kerb_judged_clock ? kerb_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 9 && at != 5) {
            /* Space starts; Up and W are held and let go each on its own, and
               S is held, repeated and let go after the focus comes back.
               Then nobody walks, and the time runs out on the kerb. */
            static const SDL_Keycode keys[] = {SDLK_SPACE, SDLK_UP, SDLK_W, SDLK_UP, SDLK_W, 0, SDLK_S, SDLK_S, SDLK_S};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(119);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_NIGHT_WATCH") && !watch_done && at < 2000) {
        if (watch_frame < at) return false;
        delay_clock = watch_judged_clock ? watch_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 9 && at != 5) {
            /* Enter starts; Left and A are held and let go each on its own,
               and D is held, repeated and let go after the focus comes
               back. Then nobody keeps watch. */
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_LEFT, SDLK_A, SDLK_LEFT, SDLK_A, 0, SDLK_D, SDLK_D, SDLK_D};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(119);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SHADOW_PUPPETS") && !puppets_done && at < 2000) {
        if (puppets_frame < at) return false;
        delay_clock = puppets_judged_clock ? puppets_judged_clock + 2600 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 9 && at != 5) {
            /* Enter starts; Q and E are held and let go each on its own, and
               Q is taken again after the focus comes back: in play it rolls
               the figure, never the shell's quit. */
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_Q, SDLK_E, SDLK_Q, SDLK_E, 0, SDLK_Q, SDLK_Q, SDLK_Q};
            event->type = at == 3 || at == 4 || at == 8 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.repeat = at == 7;
        } else if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(119);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_BARTENDER") && at < 30) {
        if (bartender_frame < at) return false;
        delay_clock = at == 29 ? 5700 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 3) {
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_SPACE, SDLK_I};
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        } else if (at == 3 || at == 4 || (at >= 17 && at <= 21)) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(115);
            float x = at == 3 ? 208.68494f : at == 19 ? 185.61858f : 237.18821f;
            float y = at == 3 ? 375.26633f : at == 19 ? 302.46625f : 304.17217f;
            float px = 456.0f + (x - 500.0f) * (389.0f / 640.0f);
            float py = 505.0f - y * (389.0f / 640.0f);
            if (at == 4 || at == 19 || at == 20) {
                event->type = SDL_EVENT_MOUSE_MOTION;
                event->motion.windowID = SDL_GetWindowID(windows[0]);
                event->motion.state = SDL_BUTTON_LMASK;
                event->motion.x = px;
                event->motion.y = py;
            } else {
                event->type = at == 3 || at == 18 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
                event->button.windowID = SDL_GetWindowID(windows[0]);
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = px;
                event->button.y = py;
            }
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SIGN_PAINTER") && at < 10) {
        if (signpainter_frame < at) return false;
        delay_clock = at == 9 ? 3400 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 4) {
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_3, SDLK_SPACE, SDLK_R};
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        } else if (at < 9) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(114);
            event->type = at % 2 == 0 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 329.0f;
            SDL_free(windows);
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_TIGHTROPE") && at < 36) {
        if (tightrope_frame < at) return false;
        delay_clock = at == 35 ? 6500 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 7) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(113);
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.windowID = SDL_GetWindowID(windows[0]);
            event->motion.x = 700.0f;
            event->motion.y = 260.0f;
            SDL_free(windows);
        } else if (at == 0 || at == 1 || at == 2 || at == 5) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_RETURN : at == 1 ? SDLK_W : at == 2 ? SDLK_SPACE : SDLK_UP;
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CONDUCTOR") && at < 26) {
        if (conductor_frame < at) return false;
        delay_clock = at == 25 ? 5200 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 3 || at == 4) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(112);
            event->type = at == 3 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 350.3f;
            SDL_free(windows);
        } else if (at < 3) {
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_W, SDLK_S};
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_POTTER") && at < 26) {
        if (potter_frame < at) return false;
        delay_clock = at == 25 ? 5200 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at >= 4 && at <= 6) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(111);
            event->type = at == 5 ? SDL_EVENT_MOUSE_BUTTON_UP : SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 456.0f;
            event->button.y = 421.4f;
            SDL_free(windows);
        } else if (at < 4 || at == 7) {
            static const SDL_Keycode keys[] = {SDLK_RETURN, SDLK_W, SDLK_S, SDLK_SPACE};
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 7 ? SDLK_UP : keys[at];
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CIPHER_ABYSS") && at < 16) {
        if (cipher_abyss_frame < at) return false;
        static const SDL_Keycode keys[] = {
            SDLK_SPACE, SDLK_2, SDLK_1, SDLK_2, SDLK_RETURN, SDLK_X, SDLK_T,
            SDLK_1, SDLK_1, SDLK_2, SDLK_RETURN, SDLK_1, SDLK_1, SDLK_1, SDLK_RETURN
        };
        delay_clock = at == 15 ? 11000 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at < 15) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        } else {
            event->type = SDL_EVENT_USER;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CRAZY_COG") && at < 10) {
        if (crazy_cog_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at >= 3 && at <= 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(109);
            SDL_WindowID window = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
            if (at == 4) {
                event->type = SDL_EVENT_MOUSE_MOTION;
                event->motion.windowID = window;
                event->motion.state = SDL_BUTTON_LMASK;
                event->motion.x = 249.35f;
                event->motion.y = 252.61f;
            } else {
                event->type = at == 3 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
                event->button.windowID = window;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = at == 3 ? 198.90f : 249.35f;
                event->button.y = at == 3 ? 467.32f : 252.61f;
            }
        } else {
            static const SDL_Keycode keys[] = {
                SDLK_SPACE, SDLK_TAB, SDLK_TAB, 0, 0, 0, SDLK_R, SDLK_KP_3, SDLK_G, SDLK_F
            };
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
            event->key.mod = at == 2 ? SDL_KMOD_LSHIFT : SDL_KMOD_NONE;
            SDL_SetModState(event->key.mod);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FEEL") && at < 7) {
        /* Space starts; keypad 1 answers the first comment. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_STRONG") && at < 7) {
        /* Space starts; keypad 1 answers the first dialogue. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_READ") && at < 7) {
        /* Space starts; keypad 1 answers the first story. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_WHY") && at < 7) {
        /* Space starts; keypad 1 answers the first story. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_TONE") && at < 7) {
        /* Space starts; keypad 1 answers the first voice. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_EMO") && at < 7) {
        /* Space starts; keypad 1 answers the first face. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SENSE") && at < 7) {
        /* Space starts; keypad 1 answers the first question. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_ARGUE") && at < 7) {
        /* Space starts; keypad 1 answers the first question. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SECOND") && at < 7) {
        /* Space starts; keypad 1 answers the first question. */
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_LINES") && at < 7) {
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || (at == 1 && env_int("NW_TEST_LINES") == 2)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        } else if ((at == 1 || at == 2) && env_int("NW_TEST_LINES") == 1) {
            /* The first of two answers in a row, as quiz.option_rect puts it. */
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(108);
            event->type = at == 1 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 385;
            event->button.y = 454;
            SDL_free(windows);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FIGURES") && at < 7) {
        if (missing_word_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || (at == 1 && env_int("NW_TEST_FIGURES") == 2)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_KP_1;
        } else if ((at == 1 || at == 2) && env_int("NW_TEST_FIGURES") == 1) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(108);
            event->type = at == 1 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 245;
            event->button.y = 454;
            SDL_free(windows);
        }
        ++at;
        return true;
    }
    if ((env_int("NW_TEST_MISSING_WORD") || env_int("NW_TEST_PROOFREADER")) && at < 15) {
        if (missing_word_frame < at) return false;
        delay_clock = at == 14 ? 5500 : (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 3 || at == 4) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 3 ? SDLK_R : SDLK_RETURN;
        } else if (at == 1 || at == 2) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(107);
            event->type = at == 1 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = env_int("NW_TEST_PROOFREADER") ? 282 : 243;
            event->button.y = env_int("NW_TEST_PROOFREADER") ? 177 : 195;
            SDL_free(windows);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_HEAVIER") && at < 12) {
        if (heavier_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = SDLK_SPACE;
        } else if (at == 1 || at == 3 || at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(105);
            event->type = at == 3 ? SDL_EVENT_MOUSE_BUTTON_UP : SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.windowID = SDL_GetWindowID(windows[0]);
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 5 ? 820 : 160;
            event->button.y = at == 5 ? 425 : at == 3 ? 344 : 224;
            SDL_free(windows);
        } else if (at == 2) {
            event->type = SDL_EVENT_MOUSE_MOTION;
            event->motion.state = SDL_BUTTON_LMASK;
            event->motion.x = 160;
            event->motion.y = 344;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_MORNING_ROUND") && at < 38) {
        if (morning_round_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 22 || at == 25 || at == 28) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 22 ? SDLK_A : at == 25 ? SDLK_Z : SDLK_X;
            event->key.repeat = at == 28;
        } else if (at == 24) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(104);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_UNICYCLE") && at < 12) {
        if (unicycle_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = at <= 2 ? SDL_EVENT_KEY_DOWN : SDL_EVENT_USER;
        event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_UP : SDLK_LEFT;
        ++at;
        return true;
    }
    if (env_int("NW_TEST_ROVER") == 2 && at < 36) {
        if (rover_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = at <= 1 ? SDL_EVENT_KEY_DOWN : SDL_EVENT_USER;
        event->key.key = at == 0 ? SDLK_SPACE : SDLK_UP;
        ++at;
        return true;
    }
    if (env_int("NW_TEST_ROVER") == 1 && at < 7) {
        if (rover_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 4) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_UP;
        } else if (at == 6) {
            event->type = SDL_EVENT_USER;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_UP : at == 2 ? SDLK_W : SDLK_D;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CRANE") && at < 6) {
        if (crane_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        if (at == 4) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->type = SDL_EVENT_WINDOW_FOCUS_LOST;
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
        } else if (at == 3) {
            event->type = SDL_EVENT_KEY_UP;
            event->key.key = SDLK_W;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_W : at == 2 ? SDLK_UP : SDLK_RETURN;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_KITCHEN") && at < 220) {
        if (kitchen_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 21) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_RIGHT;
            event->button.x = 314.0f;
            event->button.y = 227.0f;
        } else if (at == 0 || at == 1 || at == 41 || at == 51 || at == 181 || at == 201) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : at == 1 ? SDLK_1 :
                at == 41 ? SDLK_Q : at == 201 ? SDLK_F : SDLK_E;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SOKOBANLIVE") && at < 31) {
        if (sokobanlive_frame < at) return false;
        static const int route[] = {1, 1, 1, 2, 1, 3, 3, 3, 3, 1, 3, 0, 0, 0, 0};
        static const SDL_Keycode keys[] = {SDLK_UP, SDLK_S, SDLK_LEFT, SDLK_D};
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || (at % 2 == 1 && at <= 29)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : keys[route[(at - 1) / 2]];
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_ESCORT") && at < 7) {
        if (escort_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 6) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_RIGHT;
            event->button.x = 456.0f;
            event->button.y = 157.5f;
        } else if (at <= 1) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : SDLK_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_AIRTRAFFIC") && at < 38) {
        if (airtraffic_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 37) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_RIGHT;
            event->button.x = 473.505f;
            event->button.y = 280.18f;
        } else if (at == 0 || (at >= 33 && at <= 36)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : (at == 33 ? SDLK_1 :
                (at == 34 ? SDLK_H : (at == 35 ? SDLK_A : SDLK_RIGHT)));
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_RAILYARD") && at < 8) {
        if (railyard_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 6) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_RIGHT;
            event->button.x = 195.0f;
            event->button.y = 245.5f;
        } else if (at <= 2 || at == 7) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : (at == 1 ? SDLK_1 : (at == 2 ? SDLK_Q : SDLK_W));
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_FIREBREAK") && at < 7) {
        if (firebreak_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        SDL_SetModState(at == 1 ? SDL_KMOD_LSHIFT : SDL_KMOD_NONE);
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 6) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_RIGHT;
            event->button.x = 465.52f;
            event->button.y = 324.115f;
        } else if (at <= 2) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : (at == 1 ? SDLK_RIGHT : SDLK_RETURN);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_BANDIT") && at < 64) {
        if (bandit_frame < at) return false;
        delay_clock = at <= 60 ? (Uint64)at : (Uint64)(2998 + at);
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 92.0f;
            event->button.y = 350.0f;
        } else if (at <= 60 || at == 63) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 || at == 63 ? SDLK_SPACE : SDLK_1;
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_BLUFF") && at < 26) {
        if (bluff_frame < at) return false;
        delay_clock = at <= 22 ? (Uint64)at : (Uint64)(2998 + at);
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 356.0f;
            event->button.y = 476.0f;
        } else if (at <= 22 || at == 25) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 || at == 25 ? SDLK_SPACE : (at % 2 ? SDLK_K : SDLK_C);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_DISPATCH") && (!dispatch_judged || at <= dispatch_judged + 2)) {
        if (dispatch_frame < at) return false;
        if (at > 600) exit(97);
        delay_clock += dispatch_judged ? (at == dispatch_judged ? 2199 : 1) : (at == 0 ? 0 : 250);
        SDL_SetModState(at == 2 ? SDL_KMOD_LSHIFT : SDL_KMOD_NONE);
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 3 || at == 4) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 3 ? 564.92f : 456.0f;
            event->button.y = at == 3 ? 388.3f : 201.58f;
        } else if (at == 0 || at == 1 || at == 2 || at == 16 || at == 17 ||
                   (dispatch_judged && at == dispatch_judged + 2)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 1 ? SDLK_1 : (at == 2 ? SDLK_J :
                             (at == 16 ? SDLK_2 : (at == 17 ? SDLK_A : SDLK_SPACE)));
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_GAMBLE") && at < 7) {
        if (gamble_frame < at) return false;
        static const Uint64 times[] = {0, 1, 2, 3, 3002, 3003, 3004};
        delay_clock = times[at];
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 2) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 100;
            event->button.y = 342;
        } else if (at < 4 || at == 6) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 1 ? SDLK_1 : (at == 3 ? SDLK_S : SDLK_SPACE);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SONAR") == 2 && at == 0) {
        if (!sonar_frame) return false;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = SDLK_SPACE;
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SONAR") == 1 && at < 8) {
        if (sonar_frame < at) return false;
        static const Uint64 times[] = {0, 1, 2, 3, 4, 1803, 1804, 1805};
        delay_clock = times[at];
        SDL_SetModState(at == 4 ? SDL_KMOD_LSHIFT : SDL_KMOD_NONE);
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 3 || at == 4) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = at == 3 ? SDL_BUTTON_RIGHT : SDL_BUTTON_LEFT;
            event->button.x = at == 3 ? 456.0f : 598.8f;
            event->button.y = at == 3 ? 314.0f : 381.9f;
        } else if (at < 3 || at == 7) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 1 ? SDLK_UP : (at == 2 ? SDLK_P : SDLK_SPACE);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SIGNALS") && at < 55) {
        if (signals_frame < at) return false;
        static const SDL_Keycode keys[] = {
            0, 0, 0, SDLK_I, SDLK_1, SDLK_W, SDLK_E, SDLK_2,
            SDLK_R, SDLK_I, SDLK_1, SDLK_W, SDLK_U, SDLK_4, SDLK_T, SDLK_I,
            SDLK_4, SDLK_T, SDLK_U, SDLK_4, SDLK_T, SDLK_E, SDLK_4, SDLK_W, SDLK_Q
        };
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at < 3) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 1 ? 120 : 300;
            event->button.y = at == 1 ? 334 : 464;
        } else if (at < (int)SDL_arraysize(keys)) {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at];
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_CAPTCHA") && at < 39) {
        if (captcha_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = 420;
            event->button.y = 342;
        } else if (at <= 11) {
            static const SDL_Keycode keys[] = {
                SDLK_C, SDLK_DELETE, SDLK_N, SDLK_U, SDLK_J, SDLK_W, SDLK_H, SDLK_T,
                SDLK_KP_7, SDLK_N, SDLK_RETURN
            };
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = keys[at - 1];
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_SHADOW_CLOCK") && at < 39) {
        if (shadow_frame < at) return false;
        delay_clock = (Uint64)at * 100;
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_USER;
        if (at == 0 || at == 1 || at == 2) {
            event->type = at == 2 ? SDL_EVENT_KEY_UP : SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_RETURN : SDLK_A;
        } else if (at >= 3 && at <= 5) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            SDL_WindowID id = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
            if (at == 4) {
                event->type = SDL_EVENT_MOUSE_MOTION;
                event->motion.windowID = id;
                event->motion.state = SDL_BUTTON_LMASK;
                event->motion.x = 379;
                event->motion.y = 342;
            } else {
                event->type = at == 3 ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
                event->button.windowID = id;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = at == 3 ? 500 : 379;
                event->button.y = 342;
            }
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_TUNER_CLOCK")) {
        bool recorded = env_int("NW_TEST_TUNER_CLOCK") == 2;
        int tune_at = recorded ? 43 : 27;
        if (at < tune_at + 41) {
            if (tuner_frame < at) return false;
            delay_clock = (Uint64)at * 100;
            memset(event, 0, sizeof(*event));
            SDL_WindowID id = 0;
            if (at >= tune_at && at <= tune_at + 2) {
                int count = 0;
                SDL_Window **windows = SDL_GetWindows(&count);
                if (count != 1) exit(97);
                id = SDL_GetWindowID(windows[0]);
                SDL_free(windows);
            }
            if (at == tune_at) {
                event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
                event->button.windowID = id;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = recorded ? 673 : 285;
                event->button.y = 256;
            } else if (at == tune_at + 1) {
                event->type = SDL_EVENT_MOUSE_MOTION;
                event->motion.windowID = id;
                event->motion.state = SDL_BUTTON_LMASK;
                event->motion.x = recorded ? 633 : 245;
                event->motion.y = 256;
            } else if (at == tune_at + 2) {
                event->type = SDL_EVENT_MOUSE_BUTTON_UP;
                event->button.windowID = id;
                event->button.button = SDL_BUTTON_LEFT;
                event->button.x = recorded ? 633 : 245;
                event->button.y = 256;
            } else if (at == 0 || at == tune_at + 3 || at == tune_at + 4) {
                event->type = SDL_EVENT_KEY_DOWN;
                event->key.key = at == tune_at + 3 ? SDLK_R : SDLK_SPACE;
            } else if (at == 1 || at == 4) {
                event->type = at == 1 ? SDL_EVENT_KEY_DOWN : SDL_EVENT_KEY_UP;
                event->key.key = SDLK_RIGHT;
                event->key.mod = at == 1 ? SDL_KMOD_LSHIFT : SDL_KMOD_NONE;
            } else {
                event->type = SDL_EVENT_USER;
            }
            ++at;
            return true;
        }
    }
    if (env_int("NW_TEST_WIRING_OPTIONS") && at < 7) {
        static const SDL_Keycode keys[] = {SDLK_C, SDLK_RIGHT, SDLK_DOWN, SDLK_LEFT, SDLK_DOWN, SDLK_RIGHT, SDLK_RETURN};
        memset(event, 0, sizeof(*event));
        event->type = SDL_EVENT_KEY_DOWN;
        event->key.key = keys[at++];
        return true;
    }
    if (env_int("NW_TEST_HIDDEN_WIRING") && at < 6) {
        if (hidden_wiring_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at == 0 || at == 1 || at == 5) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 5 ? 246 : 196;
            event->button.y = at == 5 ? 468 : 337;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 2 ? SDLK_L : (at == 3 ? SDLK_E : SDLK_RETURN);
        }
        ++at;
        return true;
    }
    if (env_int("NW_TEST_HIDDEN_RULE") && at < 10) {
        if (hidden_rule_frame < at) return false;
        memset(event, 0, sizeof(*event));
        if (at == 1 || at == 4) {
            event->type = SDL_EVENT_MOUSE_BUTTON_DOWN;
            event->button.button = SDL_BUTTON_LEFT;
            event->button.x = at == 1 ? 205 : 138;
            event->button.y = at == 1 ? 165 : 447;
        } else {
            event->type = SDL_EVENT_KEY_DOWN;
            event->key.key = at == 0 ? SDLK_SPACE : (at == 2 ? SDLK_T : (at == 3 ? SDLK_E : SDLK_Y));
        }
        ++at;
        return true;
    }
    if (rendered == 1 && !exit_sent) {
        memset(event, 0, sizeof(*event)); event->type = SDL_EVENT_KEY_DOWN;
        if (env_int("NW_TEST_CLOSE_WINDOW")) {
            event->type = SDL_EVENT_WINDOW_CLOSE_REQUESTED;
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            if (count != 1) exit(97);
            event->window.windowID = SDL_GetWindowID(windows[0]);
            SDL_free(windows);
            if (!unrelated_close_sent) {
                unrelated_close_sent = true;
                event->window.windowID = 0;
                return true;
            }
        } else {
            event->key.key = SDLK_ESCAPE;
        }
        exit_sent = 1; return true;
    }
    if (rendered == 2 && !quit_sent && !env_int("NW_TEST_DIRECT")) { memset(event, 0, sizeof(*event)); event->type = SDL_EVENT_QUIT; quit_sent = 1; return true; }
    if (quit_sent || (exit_sent && env_int("NW_TEST_DIRECT"))) exit(96);
    return false;
}
static bool frame_contains(int64_t dest, int64_t length, const char *text) {
    size_t size = strlen(text);
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    for (int64_t i = 0; i + (int64_t)size <= length; ++i)
        if (memcmp(frame + i, text, size) == 0) return true;
    return false;
}
static int frame_circle_count(int64_t dest, int64_t length, uint32_t rgba) {
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    if (length < 16) return 0;
    uint32_t count;
    memcpy(&count, frame + 8, sizeof(count));
    if ((int64_t)count * 40 + 16 > length) return 0;
    int hits = 0;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *command = frame + 16 + i * 40;
        if (command[0] != 4) continue;
        uint32_t colour;
        memcpy(&colour, command + 4, sizeof(colour));
        if (colour == rgba) ++hits;
    }
    return hits;
}
static int frame_rect_count(int64_t dest, int64_t length, uint32_t rgba) {
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    if (length < 16) return 0;
    uint32_t count;
    memcpy(&count, frame + 8, sizeof(count));
    if ((int64_t)count * 40 + 16 > length) return 0;
    int hits = 0;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *command = frame + 16 + i * 40;
        if (command[0] != 1) continue;
        uint32_t colour;
        memcpy(&colour, command + 4, sizeof(colour));
        if (colour == rgba) ++hits;
    }
    return hits;
}
static float frame_push_y(int64_t dest, int64_t length) {
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    if (length < 16) return -1.0f;
    uint32_t count;
    memcpy(&count, frame + 8, sizeof(count));
    if ((int64_t)count * 40 + 16 > length) return -1.0f;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *command = frame + 16 + i * 40;
        if (command[0] != 7) continue;
        uint32_t colour;
        memcpy(&colour, command + 4, sizeof(colour));
        if (colour == 0xfadc5aff) {
            float y;
            memcpy(&y, command + 12, sizeof(y));
            return y;
        }
    }
    return -1.0f;
}
static float crane_cable_length(int64_t dest, int64_t length) {
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    if (length < 16) return -1.0f;
    uint32_t count;
    memcpy(&count, frame + 8, sizeof(count));
    if ((int64_t)count * 40 + 16 > length) return -1.0f;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *cmd = frame + 16 + i * 40;
        uint32_t colour;
        memcpy(&colour, cmd + 4, sizeof(colour));
        if (cmd[0] == 6 && colour == 0x32323cff) {
            float top, bottom;
            memcpy(&top, cmd + 12, sizeof(top));
            memcpy(&bottom, cmd + 20, sizeof(bottom));
            return top - bottom;
        }
    }
    return -1.0f;
}
static float docking_fuel_height(int64_t dest, int64_t length) {
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    if (length < 16) return -1.0f;
    uint32_t count;
    memcpy(&count, frame + 8, sizeof(count));
    if ((int64_t)count * 40 + 16 > length) return -1.0f;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *cmd = frame + 16 + i * 40;
        uint32_t colour;
        memcpy(&colour, cmd + 4, sizeof(colour));
        if (colour == 0x6ec88cff) {
            float height;
            memcpy(&height, cmd + 20, sizeof(height));
            return height;
        }
    }
    return -1.0f;
}
static float ferry_heading_x(int64_t dest, int64_t length) {
    const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
    if (length < 16) return 1000.0f;
    uint32_t count;
    memcpy(&count, frame + 8, sizeof(count));
    if ((int64_t)count * 40 + 16 > length) return 1000.0f;
    for (uint32_t i = 0; i < count; ++i) {
        const uint8_t *cmd = frame + 16 + i * 40;
        uint32_t colour;
        memcpy(&colour, cmd + 4, sizeof(colour));
        if (cmd[0] == 6 && colour == 0xdc403cff) {
            float aft, bow;
            memcpy(&aft, cmd + 8, sizeof(aft));
            memcpy(&bow, cmd + 16, sizeof(bow));
            return bow - aft;
        }
    }
    return 1000.0f;
}
int64_t nw_test_frame(int64_t dest, int64_t cap, const int64_t *handles, const int64_t *options,
                      int64_t width, int64_t height, int64_t hub, int64_t category, int64_t selected, int64_t trial) {
    if (getenv("NW_TEST_FRAME_ACK"))
        return nw_sdl_frame_write(dest, cap, handles, options, width, height, hub, category, selected, trial);
    if (env_int("NW_TEST_TITLE_HUB")) {
        static const bool hubs[] = {false, true, true, true, true, false, true, false};
        static const int choices[] = {0, 0, 0, 8, 8, 0, 0, 0};
        int frame = title_hub_frames++;
        int slot = env_int("NW_TEST_SLOT");
        if (frame >= 8 || hub != hubs[frame] || category != (frame < 2 ? 0 : 4) ||
            selected != choices[frame] || (handles[slot] != 0) != (frame == 3)) {
            fprintf(stderr, "Title hub frame %d has incorrect navigation state\n", frame);
            exit(97);
        }
        if (frame == 3 && (nw_go_info(handles[slot], 1) != 6 || nw_go_info(handles[slot], 3) != 3))
            exit(97);
        int64_t length = nw_sdl_frame_write(dest, cap, handles, options, width, height, hub, category, selected, trial);
        const char *title = frame == 3 ? "Find the Winning Move" : (hub ? "Choose a task" : "Press SPACE to enter the Workshop");
        if (!frame_contains(dest, length, title)) exit(97);
        return length;
    }
    if (getenv("NW_TEST_JIGSAW_NOTE")) jigsaw_status_frame = dest;
    if ((env_int("NW_TEST_JIGSAW_CLOCK") || env_int("NW_TEST_JIGSAW_ADAPT")) && !rendered) {
        jigsaw_timed_handle = handles[env_int("NW_TEST_SLOT")];
        if (env_int("NW_TEST_JIGSAW_CLOCK")) SDL_Delay(400);
    }
    if (!rendered) {
        int slot = env_int("NW_TEST_SLOT"), option_slot = env_int("NW_TEST_OPTION_SLOT");
        int good = hub == !env_int("NW_TEST_DIRECT") && slot >= -1 && slot < 142 && (slot < 0 || handles[slot] != 0) &&
                   (option_slot < 0 || options[option_slot] == env_int("NW_TEST_OPTION"));
        if (good && getenv("NW_TEST_SOKOBAN3D_ROUTE")) {
            int64_t handle = handles[slot];
            int64_t steps = strlen(getenv("NW_TEST_SOKOBAN3D_ROUTE"));
            int64_t par = env_int("NW_TEST_SOKOBAN3D_PAR");
            good = nw_sokoban3d_info(handle, 0) == 4 &&
                   nw_sokoban3d_info(handle, 1) == env_int("NW_TEST_SOKOBAN3D_NEXT_RUNG") &&
                   nw_sokoban3d_info(handle, 6) == steps && nw_sokoban3d_info(handle, 11) == par &&
                   nw_sokoban3d_info(handle, 12) == par && nw_sokoban3d_info(handle, 15) == 1 &&
                   nw_sokoban3d_info(handle, 21) == steps && nw_sokoban3d_info(handle, 22) == par &&
                   nw_sokoban3d_info(handle, 23) == 2;
        }
        if (good && env_int("NW_TEST_COOKIE_MENU")) {
            int64_t handle = handles[slot];
            good = nw_cookie_thief_info(handle, 0) == 0 && nw_cookie_thief_info(handle, 1) == 2 &&
                   nw_cookie_thief_info(handle, 3) == 2 && nw_cookie_thief_info(handle, 4) == 120 &&
                   nw_cookie_thief_info(handle, 5) == 400 && nw_cookie_thief_info(handle, 6) == 1;
        }
        if (good && env_int("NW_TEST_SOKOBAN3D_MENU")) {
            int64_t handle = handles[slot];
            good = nw_sokoban3d_info(handle, 0) == 0 && nw_sokoban3d_info(handle, 1) == 4 &&
                   nw_sokoban3d_info(handle, 3) == 3 && nw_sokoban3d_info(handle, 18) == 1 &&
                   nw_sokoban3d_info(handle, 19) == 0 && nw_sokoban3d_info(handle, 20) == 1;
        }
        if (good && env_int("NW_TEST_SOKOBAN3D")) {
            int64_t handle = handles[slot];
            good = nw_sokoban3d_info(handle, 0) == 1 && nw_sokoban3d_info(handle, 1) == 3 &&
                   nw_sokoban3d_info(handle, 3) == 2 && nw_sokoban3d_info(handle, 17) == 1 &&
                   nw_sokoban3d_info(handle, 18) == 0 && nw_sokoban3d_info(handle, 19) == 1 &&
                   nw_sokoban3d_info(handle, 20) == 0;
        }
        if (good && getenv("NW_TEST_MAZE2D_ROUTE")) {
            int64_t handle = handles[slot];
            int64_t moves = strlen(getenv("NW_TEST_MAZE2D_ROUTE"));
            good = nw_maze2d_info(handle, 0) == 3 && nw_maze2d_info(handle, 5) == moves &&
                   nw_maze2d_info(handle, 13) == moves && nw_maze2d_info(handle, 17) == 1 &&
                   nw_maze2d_info(handle, 20) == 3 && nw_maze2d_info(handle, 23) == 1;
        }
        if (good && env_int("NW_TEST_MAZE2D")) {
            int64_t handle = handles[slot];
            good = nw_maze2d_info(handle, 0) == 1 && nw_maze2d_info(handle, 1) == 3 &&
                   nw_maze2d_info(handle, 3) == 2 && nw_maze2d_info(handle, 5) > 0 &&
                   nw_maze2d_info(handle, 16) == 0;
        }
        if (good && env_int("NW_TEST_MAZE2D_MENU")) {
            int64_t handle = handles[slot];
            good = nw_maze2d_info(handle, 0) == 0 && nw_maze2d_info(handle, 1) == 4 &&
                   nw_maze2d_info(handle, 3) == 3 && nw_maze2d_info(handle, 15) == 0 &&
                   nw_maze2d_info(handle, 16) == 0;
        }
        if (good && env_int("NW_TEST_NINAROW_MENU")) {
            int64_t handle = handles[slot];
            good = nw_ninarow_info(handle, 0) == 0 && nw_ninarow_info(handle, 1) == 2 &&
                   nw_ninarow_info(handle, 3) == 3 && nw_ninarow_info(handle, 11) == 0 &&
                   nw_ninarow_info(handle, 16) == 6;
        }
        if (good && env_int("NW_TEST_NINAROW")) {
            int64_t handle = handles[slot];
            good = nw_ninarow_info(handle, 0) == 2 && nw_ninarow_info(handle, 3) == 2 &&
                   nw_ninarow_info(handle, 4) == 5 && nw_ninarow_info(handle, 5) == 1 &&
                   nw_ninarow_info(handle, 10) == 0 && nw_ninarow_info(handle, 13) == 1;
        }
        if (good && env_int("NW_TEST_SALESMAN")) {
            int64_t handle = handles[slot];
            good = nw_salesman_info(handle, 0) == 1 && nw_salesman_info(handle, 3) == 5 &&
                   nw_salesman_info(handle, 5) == 3 && nw_salesman_info(handle, 10) == 0;
            for (int i = 0; i < 5; ++i) {
                salesman_x[i] = (float)(54.72 + nw_salesman_city_coordinate(handle, 0, i) * 802.56 / 1000000.0);
                salesman_y[i] = (float)(628.0 - nw_salesman_city_coordinate(handle, 1, i) * 528.0 / 1000000.0);
            }
        }
        if (good && env_int("NW_TEST_SALESMAN_MENU")) {
            int64_t handle = handles[slot];
            good = nw_salesman_info(handle, 0) == 0 && nw_salesman_info(handle, 1) == 6 &&
                   nw_salesman_info(handle, 5) == 5 && nw_salesman_info(handle, 9) == 0 && nw_salesman_info(handle, 10) == 1;
        }
        if (good && env_int("NW_TEST_HANOI_MENU")) {
            int64_t handle = handles[slot];
            good = nw_hanoi_info(handle, 0) == 0 && nw_hanoi_info(handle, 1) == 4 &&
                   nw_hanoi_info(handle, 4) == 3 && nw_hanoi_info(handle, 9) == 0;
        }
        if (good && env_int("NW_TEST_HANOI")) {
            int64_t handle = handles[slot];
            good = nw_hanoi_info(handle, 0) == 2 && nw_hanoi_info(handle, 2) == 3 &&
                   nw_hanoi_info(handle, 4) == 2 && nw_hanoi_info(handle, 5) == 7;
        }
        if (good && env_int("NW_TEST_ATTENTION_MOUSE"))
            good = category == 2 && selected == env_int("NW_TEST_ATTENTION_MOUSE");
        if (good && env_int("NW_TEST_HUB_MOUSE"))
            good = category == 4 && selected == 8 && nw_go_info(handles[slot], 0) == 0;
        if (good && env_int("NW_TEST_SUDOKU_MENU")) {
            int64_t handle = handles[slot];
            good = nw_sudoku_info(handle, 0) == 0 && nw_sudoku_info(handle, 1) == 5;
        }
        if (good && env_int("NW_TEST_GO_MENU")) {
            int64_t handle = handles[slot];
            good = nw_go_info(handle, 0) == 0 && nw_go_info(handle, 1) == 5 && nw_go_info(handle, 3) == 8;
        }
        if (good && env_int("NW_TEST_WIRES_MENU")) {
            int64_t handle = handles[slot];
            good = nw_crossed_wires_info(handle, 0) == 0 && nw_crossed_wires_info(handle, 1) == 7 &&
                   nw_crossed_wires_info(handle, 3) == 8 && nw_crossed_wires_info(handle, 20) == 0 &&
                   nw_crossed_wires_info(handle, 21) == 0;
        }
        if (good && env_int("NW_TEST_JIGSAW_MENU")) {
            bool video_menu = env_int("NW_TEST_JIGSAW_MENU") == 3;
            int64_t handle = handles[slot];
            good = nw_jigsaw_info(handle, 0) == 0 &&
                   nw_jigsaw_info(handle, 19) == video_menu &&
                   nw_jigsaw_info(handle, 15) == (video_menu ? 3 : 4);
        }
        if (good && env_int("NW_TEST_NBACK_BINDING")) {
            int64_t handle = handles[slot];
            nw_nback3d_action(handle, 0, 0, 0);
            nw_nback3d_action(handle, 2, 0, nw_nback3d_info(handle, 13));
            nw_sdl_dispatch_task_key(11, handle, SDLK_A);
            good = nw_nback3d_info(handle, 8) == 0;
            nw_sdl_dispatch_task_key(11, handle, env_int("NW_TEST_NBACK_BINDING"));
            good = good && nw_nback3d_info(handle, 8) == 1;
        }
        if (good && (env_int("NW_TEST_APPLAUSE") || getenv("NW_TEST_MUSIC_TIER"))) {
            int64_t handle = handles[slot];
            for (int i = 0; i < 110 && nw_nback3d_info(handle, 0) != 4; ++i) {
                int64_t deadline = nw_nback3d_info(handle, 13);
                if (env_int("NW_TEST_NBACK_RESPONSE") && nw_nback3d_info(handle, 0) == 1 &&
                    nw_nback3d_info(handle, 2) == 1)
                    nw_nback3d_action(handle, 1, 0, deadline - 375);
                nw_nback3d_action(handle, 2, 0, deadline);
            }
            good = nw_nback3d_info(handle, 0) == 4;
        }
        if (env_int("NW_TEST_WIDTH") && (width != env_int("NW_TEST_WIDTH") || height != env_int("NW_TEST_HEIGHT"))) good = 0;
        if (env_int("NW_TEST_TRIAL") && trial != env_int("NW_TEST_TRIAL")) good = 0;
        if (env_int("NW_TEST_FULLSCREEN") && fullscreen_requests != env_int("NW_TEST_FULLSCREEN")) good = 0;
        if (env_int("NW_TEST_MOUSE_BUTTON") && button_calls != 1) good = 0;
        if (good && env_int("NW_TEST_MEDIA_HUB")) {
            bool recognition = env_int("NW_TEST_MEDIA_RECOGNITION");
            bool applied = env_int("NW_TEST_MEDIA_HUB") == 1;
            int64_t (*info)(int64_t, int64_t) = recognition ? nw_recognition_info : nw_concentration_info;
            int64_t configured = info(handles[slot], 1);
            int64_t expected = recognition ? (applied ? 60 : 40) : (applied ? 10 : 8);
            if (configured != expected || info(handles[slot], 0) != 0 || category != 1 || selected != recognition) {
                fprintf(stderr, "Hub media options returned %lld, expected %lld in a new ready session\n",
                    (long long)configured, (long long)expected);
                good = 0;
            }
        }
        if (env_int("NW_TEST_RECOGNITION_SOUND") &&
            recognition_clips != env_int("NW_TEST_RECOGNITION_SOUND")) good = 0;
        if (env_int("NW_TEST_RECOGNITION_CLICK")) {
            int score = env_int("NW_TEST_RECOGNITION_CLICK") == 1 ? 15 : 16;
            if (slot < 0 || nw_recognition_info(handles[slot], 17) != 1 ||
                nw_recognition_info(handles[slot], score) != 1) {
                fprintf(stderr, "Recognition click failed at %lldx%lld for score field %d\n",
                    (long long)width, (long long)height, score);
                good = 0;
            }
        }
        if (env_int("NW_TEST_TYPED_NUMBER") && (slot < 0 || nw_numberology_info(handles[slot], 6) != 57)) good = 0;
        if (getenv("NW_TEST_VSYNC") && vsync_requests != env_int("NW_TEST_VSYNC")) good = 0;
        if (env_int("NW_TEST_HEADLESS")) {
            int count = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            good = good && count == 1 &&
                (SDL_GetWindowFlags(windows[0]) & (SDL_WINDOW_HIDDEN | SDL_WINDOW_FULLSCREEN)) == SDL_WINDOW_HIDDEN;
            SDL_free(windows);
        }
        const char *video_driver = getenv("NW_TEST_VIDEO_DRIVER");
        if (video_driver && strcmp(SDL_GetCurrentVideoDriver(), video_driver) != 0) good = 0;
        const char *caption = getenv("NW_TEST_WINDOW_CAPTION");
        if (caption) {
            int count = 0, minimum_width = 0, minimum_height = 0;
            SDL_Window **windows = SDL_GetWindows(&count);
            good = good && count == 1 &&
                strcmp(SDL_GetWindowTitle(windows[0]), caption) == 0 &&
                SDL_GetWindowMinimumSize(windows[0], &minimum_width, &minimum_height) &&
                minimum_width == 640 && minimum_height == 480;
            if (!good && count == 1)
                fprintf(stderr, "caption '%s', minimum %dx%d\n",
                        SDL_GetWindowTitle(windows[0]), minimum_width, minimum_height);
            SDL_free(windows);
        }
        if (good && env_int("NW_TEST_MAZE")) {
            int64_t (*info)(int64_t, int64_t) = env_int("NW_TEST_MAZE") == 1 ? nw_you_are_here_info : nw_sokoban_info;
            good = info(handles[slot], 3) == 5;
        }
        if (good && env_int("NW_TEST_MARBLE")) {
            good = nw_marble_info(handles[slot], 1) == 3 && nw_marble_info(handles[slot], 3) == 5;
            if (env_int("NW_TEST_MARBLE_READY"))
                good = good && nw_marble_info(handles[slot], 0) == 0;
            if (env_int("NW_TEST_MARBLE_PHYSICS"))
                good = good && nw_marble_info(handles[slot], 0) == 1 && nw_marble_info(handles[slot], 6) > 0 &&
                       nw_marble_info(handles[slot], 11) == 8;
        }
        int seed = env_int("NW_TEST_PUZZLE_SEED");
        if (good && seed) {
            uint8_t expected[65536];
            bool jigsaw = env_int("NW_TEST_JIGSAW");
            int64_t reference = jigsaw ? nw_jigsaw_create_options(3, 3, 1, 1, 0, seed) : nw_sudoku_create(3, 3, 1, 1, seed);
            if (!reference) exit(92);
            if (jigsaw) nw_jigsaw_action(reference, 0, 0, 0);
            else nw_sudoku_action(reference, 0, 0, 0);
            int64_t n = (jigsaw ? nw_jigsaw_frame_write : nw_sudoku_frame_write)((intptr_t)expected, sizeof(expected), reference, 0, width, height);
            int64_t actual = nw_sdl_frame_write(dest, cap, handles, options, width, height, hub, category, selected, trial);
            if (jigsaw) nw_jigsaw_destroy(reference);
            else nw_sudoku_destroy(reference);
            good = n > 0 && actual == n && memcmp(expected, (void *)(intptr_t)dest, n) == 0;
        }
        if (!good) {
            fprintf(stderr, "event replay selected wrong task or options (hub=%lld category=%lld card=%lld slot=%d)\n",
                    (long long)hub, (long long)category, (long long)selected, slot);
            exit(90);
        }
        rendered = 1;
    } else if (rendered == 1 && exit_sent) {
        int good = env_int("NW_TEST_DIRECT") ? !hub : hub;
        if (!env_int("NW_TEST_DIRECT"))
            for (int i = 0; i < 48; i++) if (handles[i] != 0) good = 0;
        if (!good) { fprintf(stderr, "event replay exit state was incorrect\n"); exit(91); }
        rendered = 2; puts("SDL event replay: PASS"); fflush(stdout);
    }
    int64_t length = nw_sdl_frame_write(dest, cap, handles, options, width, height, hub, category, selected, trial);
    if (env_int("NW_TEST_HIDDEN_WIRING") && handles[45] != 0) {
        const char *phase = at < 4 ? "Learn the wiring" :
            (at < 6 ? "Set the switches for the pattern" : "A = ");
        if (!frame_contains(dest, length, phase) ||
            (at == 3 && !frame_contains(dest, length, "looks 1 (12 left)")) ||
            (at == 5 && !frame_contains(dest, length, "question 2 of 2"))) {
            fprintf(stderr, "Hidden Wiring frame %d did not show %s and its controls\n", at, phase);
            exit(97);
        }
        hidden_wiring_frame = at;
    }
    if (env_int("NW_TEST_DELAY_CLOCK") && handles[47] != 0) {
        const char *labels[] = {"Press Space", "Wait 3.0 s", "Give up", "8 coins", "Wait 3.0 s",
            "Give up", "next offer ...", "Wait 3.0 s", "8 coins (par 90)", "0 of 1 passed"};
        if (!frame_contains(dest, length, labels[at])) {
            fprintf(stderr, "Delay frame %d did not show %s\n", at, labels[at]);
            exit(97);
        }
        if (at < 9) rendered = 0;
        delay_frame = at;
    }
    if (env_int("NW_TEST_SLOT") == 54 && handles[54] != 0) {
        if (!frame_contains(dest, length, "Point of View")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Tables per run")) exit(97);
        if (env_int("NW_TEST_POV")) {
            const char *playing = env_int("NW_TEST_POV") == 2 ? "camera height 4.8" : "Which picture";
            const char *labels[] = {"Press Space", playing, playing, "Right: 3", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Point of View frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 4) rendered = 0;
            pov_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 55 && handles[55] != 0) {
        if (!frame_contains(dest, length, "Inside or Out?")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Puzzles per run")) exit(97);
        if (env_int("NW_TEST_INSIDE")) {
            bool pair = env_int("NW_TEST_INSIDE") == 2;
            const char *labels[] = {"Press Space", pair ? "Can the two dots meet" : "Is the dot inside",
                                    pair ? "Right: Yes" : "Right: Inside", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Inside or Out? frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 3) rendered = 0;
            inside_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 56 && handles[56] != 0) {
        if (!frame_contains(dest, length, "Touching?")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Puzzles per run")) exit(97);
        if (env_int("NW_TEST_TOUCHING")) {
            bool pair = env_int("NW_TEST_TOUCHING") == 2;
            const char *labels[] = {"Press Space", pair ? "How many pairs" : "Do the two shapes touch",
                                    pair ? "Right: 0" : "Right: Overlapping", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Touching? frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 3) rendered = 0;
            touching_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 57 && handles[57] != 0) {
        if (!frame_contains(dest, length, "Crossings")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Puzzles per run")) exit(97);
        if (env_int("NW_TEST_CROSSINGS")) {
            const char *labels[] = {"Press Space", "How many times does the red line cross",
                                    "Right: 2", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Crossings frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 3) rendered = 0;
            crossings_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 53 && handles[53] != 0) {
        if (!frame_contains(dest, length, "Same or Mirror?")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Figures per run")) exit(97);
        if (env_int("NW_TEST_MIRROR")) {
            bool row = env_int("NW_TEST_MIRROR") == 2;
            const char *labels[] = {"Press Space", row ? "Which of the row" : "1  Same",
                                    row ? "Right: 3" : "31 degrees apart", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Same or Mirror? frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 3) rendered = 0;
            mirror_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 52 && handles[52] != 0) {
        if (!frame_contains(dest, length, "Which Is Nearer?")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Scenes per run")) exit(97);
        if (env_int("NW_TEST_NEARER")) {
            const char *labels[] = {"Press Space", "Click them in order", "Click them in order",
                                    "2 (1)", "1 (2)", "Right: all 3 in order", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Which Is Nearer? frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at == 1 || at == 2) {
                uint64_t hash = 14695981039346656037ULL;
                const unsigned char *bytes = (const unsigned char *)(intptr_t)dest;
                for (int64_t index = 0; index < length; ++index)
                    hash = (hash ^ bytes[index]) * 1099511628211ULL;
                if (at == 1) nearer_first_view = hash;
                else if (hash == nearer_first_view) exit(97);
            }
            if (at < 6) rendered = 0;
            nearer_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 51 && handles[51] != 0) {
        if (!frame_contains(dest, length, "Where Was It?")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Visits per run")) exit(97);
        if (env_int("NW_TEST_ROOMS")) {
            const char *labels[] = {"Press Space", "Room 1 of 5", "Room 2 of 5", "Room 3 of 5",
                                    "Room 4 of 5", "Room 5 of 5", "Something in the bedroom has gone",
                                    "Right: that is where the missing thing stood", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Where Was It? frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 8) rendered = 0;
            rooms_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 50 && handles[50] != 0) {
        if (!frame_contains(dest, length, "Notebook")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Rounds per run")) exit(97);
        if (env_int("NW_TEST_NOTEBOOK")) {
            const char *labels[] = {"Press Space", "Door Holly: 112", "Door Holly 112", "Door Holly?",
                                     "1 of 1 answered right", "1 of 1 passed"};
            if (!frame_contains(dest, length, labels[at])) {
                fprintf(stderr, "Notebook frame %d did not show %s\n", at, labels[at]);
                exit(97);
            }
            if (at < 5) rendered = 0;
            notebook_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 59 && handles[59] != 0) {
        if (!frame_contains(dest, length, "Balance")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Courses per run")) exit(97);
        if (env_int("NW_TEST_BALANCE_CLOCK")) {
            if (frame_contains(dest, length, "0 of 1 passed")) balance_judged = 2;
            else if (frame_contains(dest, length, "The pole fell")) balance_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Keep the pole up")) exit(97);
            if (balance_judged < 2) rendered = 0;
            balance_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 60 && handles[60] != 0) {
        if (!frame_contains(dest, length, "Juggler")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Acts per run")) exit(97);
        if (env_int("NW_TEST_JUGGLER_CLOCK")) {
            if (frame_contains(dest, length, "0 of 1 passed")) juggler_judged = 2;
            else if (frame_contains(dest, length, "A ball hit the floor")) juggler_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Keep every ball")) exit(97);
            if (juggler_judged < 2) rendered = 0;
            juggler_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 61 && handles[61] != 0) {
        if (!frame_contains(dest, length, "Lander")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Landings per run")) exit(97);
        if (env_int("NW_TEST_LANDER_CLOCK")) {
            if (frame_contains(dest, length, "0 of 1 passed")) lander_judged = 2;
            else if (frame_contains(dest, length, "Too fast down")) lander_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Land on the pad")) exit(97);
            if (lander_judged < 2) rendered = 0;
            lander_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 63 && handles[63] != 0) {
        if (!frame_contains(dest, length, "Glider")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Flights per run")) exit(97);
        if (env_int("NW_TEST_GLIDER_CLOCK")) {
            if (frame_contains(dest, length, "0 of 1 passed")) glider_judged = 2;
            else if (frame_contains(dest, length, "Hit the canyon floor")) glider_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Thread every gap")) exit(97);
            if (glider_judged < 2) rendered = 0;
            glider_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 64 && handles[64] != 0) {
        if (!frame_contains(dest, length, "Catch")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Rounds per run")) exit(97);
        if (env_int("NW_TEST_CATCH_CLOCK")) {
            if (frame_contains(dest, length, "0 of 1 passed")) catch_judged = 2;
            else if (frame_contains(dest, length, "2 balls dropped")) catch_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Red basket on the keys")) exit(97);
            if (catch_judged < 2) rendered = 0;
            catch_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 69 && handles[69] != 0) {
        if (!frame_contains(dest, length, "Stagehand")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Shows per run")) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 70 && handles[70] != 0) {
        if (!frame_contains(dest, length, "Loading Dock")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Docks per run")) exit(97);
        if (env_int("NW_TEST_DOCK_CLICK")) {
            if (at >= 5 && !frame_contains(dest, length, "OSLO was sent without its order")) exit(97);
            if (at < 5) rendered = 0;
        }
    }
    if (env_int("NW_TEST_SLOT") == 73 && handles[73] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Will It Fall? options" : "Will It Fall?")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Scenes per run") ||
            !frame_contains(dest, length, "Rung 4: towers that stand or fall, planks on a pivot."))) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 80 && handles[80] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Fold It options" : "Fold It")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Nets per run") ||
            !frame_contains(dest, length, "Rung 4: which of 3 cubes."))) exit(97);
        if (env_int("NW_TEST_FOLD_IT")) {
            if (at == 1 && !frame_contains(dest, length, "Which cube does the net fold into?")) exit(97);
            if (at == 2 && !frame_contains(dest, length, "Right: 3")) exit(97);
            if (at == 28 && !frame_contains(dest, length, "1 of 1 passed")) exit(97);
            if (at == 30 && !frame_contains(dest, length, "No: 1")) exit(97);
            if (at == 57 && !frame_contains(dest, length, "0 of 1 passed")) exit(97);
            if (at < 57) rendered = 0;
            fold_it_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 81 && handles[81] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Who Knows What? options" : "Who Knows What?")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Stories per run") ||
            !frame_contains(dest, length, "Rung 3: 2 people, 3 containers"))) exit(97);
        if (env_int("NW_TEST_WHO_KNOWS_WHAT")) {
            if (at == 1 && !frame_contains(dest, length, "Where does Esme think Dev will look for the apple?")) exit(97);
            if (at == 2 && !frame_contains(dest, length, "Right: the drawer")) exit(97);
            if (at == 28 && !frame_contains(dest, length, "1 of 1 passed")) exit(97);
            if (at == 30 && !frame_contains(dest, length, "No: the basket")) exit(97);
            if (at == 57 && !frame_contains(dest, length, "0 of 1 passed")) exit(97);
            if (at < 57) rendered = 0;
            who_knows_what_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 82 && handles[82] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Dam Keeper options" : "Dam Keeper")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Valleys per run") ||
            !frame_contains(dest, length, "Rung 4: 3 dams, 2 storm(s)."))) exit(97);
        if (env_int("NW_TEST_DAM_KEEPER")) {
            const char *playing = "Make room before the rain; never flood the town";
            const char *open_notch = "\xff\xff\xdc\x5a";
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(97);
            if (at == 1 && (!frame_contains(dest, length, playing) || frame_contains(dest, length, open_notch))) exit(97);
            if (at == 2 && !frame_contains(dest, length, open_notch)) exit(97);
            if (at == 3 && frame_contains(dest, length, open_notch)) exit(97);
            if (frame_contains(dest, length, "Dam 1 overtopped")) dam_keeper_verdict = true;
            if (at == 350 && (!dam_keeper_verdict || !frame_contains(dest, length, "0 of 1 passed"))) exit(97);
            if (at == 351 && !frame_contains(dest, length, playing)) exit(97);
            if (at < 351) rendered = 0;
            dam_keeper_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 89 && handles[89] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Crossroads options" : "Crossroads")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Shifts per run") ||
            !frame_contains(dest, length, "Rung 4: 1 junction(s), 70 s."))) exit(97);
        if (env_int("NW_TEST_CROSSROADS")) {
            const char *expected = at == 0 ? "Press Space or click to start" : "Switch the lights; keep the town moving";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Crossroads frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at < 7) rendered = 0;
            crossroads_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 102 && handles[102] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Full Stop options" : "Full Stop")) exit(106);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Runs per run") ||
            !frame_contains(dest, length, "Rung 4: 3 sentences run together."))) exit(106);
        if (env_int("NW_TEST_FULL_STOP")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 1 ? "Ada" : at == 2 || at == 3 ? "Built" : at == 4 ? "built" :
                at >= 6 && at < 15 ? "missing" : at == 15 ? "0 of 1 passed" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "Full Stop frame %d lacked %s\n", at, expected);
                exit(106);
            }
            if (at == 15 && !full_stop_audio_queued) {
                fprintf(stderr, "Full Stop played no audible PCM\n");
                exit(106);
            }
            if (at < 15) rendered = 0;
            full_stop_frame = at;
        }
    }
    int passage_slot = env_int("NW_TEST_SLOT");
    if ((passage_slot == 103 || passage_slot == 104) && handles[passage_slot] != 0) {
        bool proofreader = passage_slot == 104;
        const char *title = proofreader ?
            (env_int("NW_TEST_OPTION") ? "The Proofreader options" : "The Proofreader") :
            (env_int("NW_TEST_OPTION") ? "The Missing Word options" : "The Missing Word");
        if (!frame_contains(dest, length, title)) exit(107);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Passages per run") ||
            !frame_contains(dest, length, "Rung 4: 2 sentence(s), 2 mistake(s) to mend."))) exit(107);
        if ((env_int("NW_TEST_MISSING_WORD") || env_int("NW_TEST_PROOFREADER"))) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 1 ? (proofreader ? "Clara" : "Ada") :
                at == 2 || at == 3 ? (proofreader ? (at == 3 ? "Its forms:" : NULL) : "Put in:") : at == 4 ? "Mend the passage" :
                at >= 6 && at < 15 ? "Not as it was written" : at == 15 ? "0 of 1 passed" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "%s frame %d lacked %s\n", title, at, expected);
                exit(107);
            }
            if (at == 15 && !missing_word_audio_queued) {
                fprintf(stderr, "%s played no audible PCM\n", title);
                exit(107);
            }
            if (at < 15) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 114 && handles[114] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Air Hockey options" : "Air Hockey";
        if (!frame_contains(dest, length, title)) exit(117);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Games per run") ||
            !frame_contains(dest, length, "Rung 4: first to 2; 3 against loses."))) exit(117);
        if (env_int("NW_TEST_AIR_HOCKEY")) {
            bool judged = frame_contains(dest, length, "You lose") || frame_contains(dest, length, "Time: no winner");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Score in the far goal" : "Score in the far goal; keep the puck out of yours"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "You win")) {
                fprintf(stderr, "Air Hockey frame %d lacked %s\n", at, expected);
                exit(117);
            }
            if (judged && !airhockey_judged_clock) airhockey_judged_clock = delay_clock;
            if (done) {
                if (!airhockey_judged_clock || !crazy_cog_audio_queued) exit(117);
                airhockey_done = true;
            } else {
                rendered = 0;
            }
            airhockey_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 115 && handles[115] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Semaphore options" : "Semaphore";
        if (!frame_contains(dest, length, title)) exit(118);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Messages per run") ||
            !frame_contains(dest, length, "Rung 4: 4 letters, 9.0 seconds each."))) exit(118);
        if (env_int("NW_TEST_SEMAPHORE")) {
            bool judged = frame_contains(dest, length, "Your flags do not match");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Your flags do not match" :
                 "Copy each signal with your flags and type its letter"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "Semaphore options") ||
                frame_contains(dest, length, "of 4 read")) {
                fprintf(stderr, "Semaphore frame %d lacked %s\n", at, expected);
                exit(118);
            }
            if (judged && !semaphore_judged_clock) semaphore_judged_clock = delay_clock;
            if (done) {
                if (!semaphore_judged_clock || !crazy_cog_audio_queued) exit(118);
                semaphore_done = true;
            } else {
                rendered = 0;
            }
            semaphore_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 125 && handles[125] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Claw Machine options" : "Claw Machine";
        if (!frame_contains(dest, length, title)) exit(121);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Drops per run") ||
            !frame_contains(dest, length, "Rung 4: 7 prizes."))) exit(121);
        if (env_int("NW_TEST_CLAW_MACHINE")) {
            bool judged = frame_contains(dest, length, "Missed: ") || frame_contains(dest, length, "That is not the gold one");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Missed: " : "Drop the claw over the gold prize"));
            if (judged) expected = frame_contains(dest, length, "Missed: ") ? "Missed: " : "That is not the gold one";
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "Got it") ||
                (!done && at > 0 && !frame_contains(dest, length, "side view"))) {
                fprintf(stderr, "Claw Machine frame %d lacked %s\n", at, expected);
                exit(121);
            }
            if (judged && at < 20) {
                fprintf(stderr, "Claw Machine judged before the claw came down, at frame %d\n", at);
                exit(121);
            }
            if (judged && !claw_judged_clock) claw_judged_clock = delay_clock;
            if (done) {
                if (!claw_judged_clock) exit(121);
                claw_done = true;
            } else {
                rendered = 0;
            }
            claw_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 124 && handles[124] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Cricket Hunt options" : "Cricket Hunt";
        if (!frame_contains(dest, length, title)) exit(121);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Hunts per run") ||
            !frame_contains(dest, length, "Rung 4: 2 cricket(s)."))) exit(121);
        if (env_int("NW_TEST_CRICKET_HUNT")) {
            bool judged = frame_contains(dest, length, "Three grabs at nothing");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Three grabs at nothing" : "Find the crickets by their chirping"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, " caught in ") ||
                (!done && at > 0 && at <= 12 && !frame_contains(dest, length, "rung 1  1/1   caught 0 of 1   grabs left 3"))) {
                fprintf(stderr, "Cricket Hunt frame %d lacked %s\n", at, expected);
                exit(121);
            }
            if (judged && at < 15) {
                fprintf(stderr, "Cricket Hunt judged before the third grab, at frame %d\n", at);
                exit(121);
            }
            if (judged && !cricket_judged_clock) cricket_judged_clock = delay_clock;
            if (done) {
                if (!cricket_judged_clock) exit(121);
                cricket_done = true;
            } else {
                rendered = 0;
            }
            cricket_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 123 && handles[123] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Piano Tuner options" : "Piano Tuner";
        if (!frame_contains(dest, length, title)) exit(121);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Strings per run") ||
            !frame_contains(dest, length, "Rung 4: octave, within 10.0 cents."))) exit(121);
        if (env_int("NW_TEST_PIANO_TUNER")) {
            bool judged = frame_contains(dest, length, " cents sharp");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? " cents sharp" : "String 1 of 1: tune it in unison"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "In tune") ||
                frame_contains(dest, length, "cents flat") ||
                (!done && at > 0 && !frame_contains(dest, length, "rung 1  1/1   within 20.0 cents"))) {
                fprintf(stderr, "Piano Tuner frame %d lacked %s\n", at, expected);
                exit(121);
            }
            if (judged && at < 12) {
                fprintf(stderr, "Piano Tuner judged before Enter, at frame %d\n", at);
                exit(121);
            }
            if (judged && !tune_judged_clock) tune_judged_clock = delay_clock;
            if (done) {
                if (!tune_judged_clock) exit(121);
                tune_done = true;
            } else {
                rendered = 0;
            }
            tune_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 122 && handles[122] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "By Ear options" : "By Ear";
        if (!frame_contains(dest, length, title)) exit(121);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Melodies per run") ||
            !frame_contains(dest, length, "Rung 4: 4 notes."))) exit(121);
        if (env_int("NW_TEST_BY_EAR")) {
            bool judged = frame_contains(dest, length, "All 2 played back");
            bool done = frame_contains(dest, length, "1 of 1 passed   highest rung passed 1");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "1 of 1 passed" : (judged ? "All 2 played back" : (at < 31 ? "Listen..." : "Play it back: ")));
            /* The tune ends 2.9 s in, on the clock's 100 ms frame edge; the
               caption follows a frame behind, so frames 30 and 31 may show
               either. Frame 32, where G is pressed, is past it. */
            if ((at == 30 || at == 31) && !judged && !done)
                expected = frame_contains(dest, length, "Listen...") ? "Listen..." : "Play it back: ";
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "A wrong note") ||
                frame_contains(dest, length, "Too slow") ||
                /* A pass climbs a rung at once, so the verdict shows rung 2. */
                (!done && at > 0 && !frame_contains(dest, length, judged ? "rung 2  1/1" : "rung 1  1/1   2 notes"))) {
                fprintf(stderr, "By Ear frame %d lacked %s\n", at, expected);
                exit(121);
            }
            if (judged && !ear_judged_clock) ear_judged_clock = delay_clock;
            if (done) {
                if (!ear_judged_clock) exit(121);
                ear_done = true;
            } else {
                rendered = 0;
            }
            ear_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 121 && handles[121] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Glove options" : "Glove";
        if (!frame_contains(dest, length, title)) exit(121);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Innings per run") ||
            !frame_contains(dest, length, "Rung 4: 5 pitches at 19 m/s.  A cut about every 1.2 s."))) exit(121);
        if (env_int("NW_TEST_GLOVE")) {
            bool judged = frame_contains(dest, length, "Missed 2");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Missed 2" : "Catch the pitches"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "Caught ") ||
                (!done && at > 0 && !frame_contains(dest, length, "rung 1  1/1   pitch "))) {
                fprintf(stderr, "Glove frame %d lacked %s\n", at, expected);
                exit(121);
            }
            if (judged && !glove_judged_clock) glove_judged_clock = delay_clock;
            if (done) {
                if (!glove_judged_clock) exit(121);
                glove_done = true;
            } else {
                rendered = 0;
            }
            glove_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 120 && handles[120] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Free Kick options" : "Free Kick";
        if (!frame_contains(dest, length, title)) exit(121);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Kicks per run") ||
            !frame_contains(dest, length, "Rung 4: a ring of 0.85 m.  A wall and a keeper."))) exit(121);
        if (env_int("NW_TEST_FREE_KICK")) {
            bool judged = frame_contains(dest, length, "In the goal, but ");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? " m from the ring" : "Kick it into the lit ring"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "In the ring") ||
                (!done && at > 0 && !frame_contains(dest, length, "rung 1  1/1"))) {
                fprintf(stderr, "Free Kick frame %d lacked %s\n", at, expected);
                exit(121);
            }
            if (judged && !kick_judged_clock) kick_judged_clock = delay_clock;
            if (done) {
                if (!kick_judged_clock) exit(121);
                kick_done = true;
            } else {
                rendered = 0;
            }
            kick_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 119 && handles[119] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Steadicam options" : "Steadicam";
        if (!frame_contains(dest, length, title)) exit(120);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Takes per run") ||
            !frame_contains(dest, length, "Rung 4: 30 s, 82% framed."))) exit(120);
        if (env_int("NW_TEST_STEADICAM")) {
            bool judged = frame_contains(dest, length, "Lost them for 3 seconds");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Lost them for 3 seconds" : "Keep the walker in the box"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "% of the time") ||
                (!done && at > 0 && !frame_contains(dest, length, "rung 1  1/1   framed "))) {
                fprintf(stderr, "Steadicam frame %d lacked %s\n", at, expected);
                exit(120);
            }
            if (judged && !steady_judged_clock) steady_judged_clock = delay_clock;
            if (done) {
                if (!steady_judged_clock) exit(120);
                steady_done = true;
            } else {
                rendered = 0;
            }
            steady_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 118 && handles[118] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Kerbside options" : "Kerbside";
        if (!frame_contains(dest, length, title)) exit(119);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Crossings per run") ||
            !frame_contains(dest, length, "Rung 4: 3 lane(s)."))) exit(119);
        if (env_int("NW_TEST_KERBSIDE")) {
            bool judged = frame_contains(dest, length, "Still on the street");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Still on the street" : "Cross when the way is clear -- by ear"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "Hit in lane") ||
                (!done && at > 0 && !frame_contains(dest, length, "rung 1  1/1   1 lanes"))) {
                fprintf(stderr, "Kerbside frame %d lacked %s\n", at, expected);
                exit(119);
            }
            if (judged && !kerb_judged_clock) kerb_judged_clock = delay_clock;
            if (done) {
                if (!kerb_judged_clock || !crazy_cog_audio_queued) exit(119);
                kerb_done = true;
            } else {
                rendered = 0;
            }
            kerb_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 117 && handles[117] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Night Watch options" : "Night Watch";
        if (!frame_contains(dest, length, title)) exit(119);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Nights per run") ||
            !frame_contains(dest, length, "Rung 4: 3 thieves, 2 others."))) exit(119);
        if (env_int("NW_TEST_NIGHT_WATCH")) {
            bool judged = frame_contains(dest, length, "The safe is robbed");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "The safe is robbed" : "Tonight the thieves wear "));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "Every thief caught") ||
                (!done && at > 0 && !frame_contains(dest, length, "caught 0 / 2"))) {
                fprintf(stderr, "Night Watch frame %d lacked %s\n", at, expected);
                exit(119);
            }
            if (judged && !watch_judged_clock) watch_judged_clock = delay_clock;
            if (done) {
                if (!watch_judged_clock || !crazy_cog_audio_queued) exit(119);
                watch_done = true;
            } else {
                rendered = 0;
            }
            watch_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 116 && handles[116] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Shadow Puppets options" : "Shadow Puppets";
        if (!frame_contains(dest, length, title)) exit(119);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Figures per run") ||
            !frame_contains(dest, length, "Rung 4: 1 shadows, within 16 degrees."))) exit(119);
        if (env_int("NW_TEST_SHADOW_PUPPETS")) {
            bool judged = frame_contains(dest, length, "Time: 0 of 1 cast");
            bool done = frame_contains(dest, length, "0 of 1 passed   highest rung passed 0");
            const char *expected = at == 0 ? "Press Space or click to start" :
                (done ? "0 of 1 passed" : (judged ? "Time: 0 of 1 cast" : "Cast the shadow shown"));
            if (!frame_contains(dest, length, expected) || frame_contains(dest, length, "Every shadow cast") ||
                (!done && at > 0 && !frame_contains(dest, length, "shadow 1 of 1"))) {
                fprintf(stderr, "Shadow Puppets frame %d lacked %s\n", at, expected);
                exit(119);
            }
            if (judged && !puppets_judged_clock) puppets_judged_clock = delay_clock;
            if (done) {
                if (!puppets_judged_clock || !crazy_cog_audio_queued) exit(119);
                puppets_done = true;
            } else {
                rendered = 0;
            }
            puppets_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 113 && handles[113] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Lock Pick options" : "Lock Pick";
        if (!frame_contains(dest, length, title)) exit(116);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Locks per run") ||
            !frame_contains(dest, length, "Rung 4: 4 pins."))) exit(116);
        if (env_int("NW_TEST_LOCK_PICK")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 31 ? "The wrench slipped once too often" :
                at == 32 ? "0 of 1 passed   highest rung passed 0" : "0 of 3 set";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Lock Pick frame %d lacked %s\n", at, expected);
                exit(116);
            }
            if (at == 32 && !crazy_cog_audio_queued) exit(116);
            if (at < 32) rendered = 0;
            lockpick_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 112 && handles[112] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Bartender options" : "Bartender";
        if (!frame_contains(dest, length, title)) exit(115);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Nights per run") ||
            !frame_contains(dest, length, "Rung 4: 2 customers, 3 bottles."))) exit(115);
        if (env_int("NW_TEST_BARTENDER")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 15 ? "Seat 1: a green." :
                at == 29 ? "Last orders: a good night" :
                at == 30 ? "1 of 1 passed   highest rung passed 1" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "Bartender frame %d lacked %s\n", at, expected);
                exit(115);
            }
            if (at == 30 && !crazy_cog_audio_queued) exit(115);
            if (at < 30) rendered = 0;
            bartender_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 111 && handles[111] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Sign Painter options" : "Sign Painter";
        if (!frame_contains(dest, length, title)) exit(114);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Signs per run") ||
            !frame_contains(dest, length, "Rung 4.  In the colour asked for."))) exit(114);
        if (env_int("NW_TEST_SIGN_PAINTER")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at < 9 ? "Paint IT in blue." :
                at == 9 ? "That was the wrong colour" : "0 of 1 passed   highest rung passed 0";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Sign Painter frame %d lacked %s\n", at, expected);
                exit(114);
            }
            if (at == 10 && !crazy_cog_audio_queued) exit(114);
            if (at < 10) rendered = 0;
            signpainter_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 110 && handles[110] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Tightrope options" : "Tightrope";
        if (!frame_contains(dest, length, title)) exit(113);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Crossings per run") ||
            !frame_contains(dest, length, "Rung 4: 7 steps."))) exit(113);
        if (env_int("NW_TEST_TIGHTROPE")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 1 ? "0 of 5 steps" : at >= 2 && at < 6 ? "1 of 5 steps" :
                at >= 6 && at <= 8 ? "2 of 5 steps" :
                at == 35 ? "You fell" : at == 36 ? "0 of 1 passed   highest rung passed 0" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "Tightrope frame %d lacked %s\n", at, expected);
                exit(113);
            }
            if (at == 36 && !crazy_cog_audio_queued) exit(113);
            if (at < 36) rendered = 0;
            tightrope_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 109 && handles[109] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Conductor options" : "Conductor";
        if (!frame_contains(dest, length, title)) exit(112);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Pieces per run") ||
            !frame_contains(dest, length, "Rung 4: 12 beats, 2 cues."))) exit(112);
        if (env_int("NW_TEST_CONDUCTOR")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 2 ? "slips left: 2" : at == 3 ? "slips left: 1" : at == 4 ? "slips left: 0" :
                at == 25 ? "The orchestra fell apart" : at == 26 ? "0 of 1 passed   highest rung passed 0" :
                "Beat 5: bring in the woodwind.";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Conductor frame %d lacked %s\n", at, expected);
                exit(112);
            }
            if (at == 26 && !crazy_cog_audio_queued) exit(112);
            if (at < 26) rendered = 0;
            conductor_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 108 && handles[108] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Potter's Wheel options" : "Potter's Wheel";
        if (!frame_contains(dest, length, title)) exit(111);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Pots per run") ||
            !frame_contains(dest, length, "Rung 4: 6 bands.  The clay dries."))) exit(111);
        if (env_int("NW_TEST_POTTER")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 25 ? "The pot collapsed" : at == 26 ? "0 of 1 passed   highest rung passed 0" :
                "Shape the clay to the pot shown, then let go";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Potter's Wheel frame %d lacked %s\n", at, expected);
                exit(111);
            }
            if (at == 2 && frame_circle_count(dest, length, 0xffc846ff) != 2) exit(111);
            if (at == 3 && frame_circle_count(dest, length, 0xffc846ff) != 1) exit(111);
            if ((at == 5 || at == 6) &&
                frame_circle_count(dest, length, 0xecc8aae6) != (at == 5 ? 1 : 0)) exit(111);
            if (at == 26 && !crazy_cog_audio_queued) exit(111);
            if (at < 26) rendered = 0;
            potter_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 107 && handles[107] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "The Cipher Abyss options" : "The Cipher Abyss";
        if (!frame_contains(dest, length, title)) exit(110);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Machines per run") ||
            !frame_contains(dest, length, "Rung 4 (transformations): 3 symbols, rows of 4, 8 experiments."))) exit(110);
        if (env_int("NW_TEST_CIPHER_ABYSS")) {
            const char *expected = at == 0 ? "Press Space or click to start" : at == 6 ? "Notebook saved" :
                at >= 7 && at <= 10 ? "TEST 1 of 2: what does it give for" :
                at >= 11 && at <= 14 ? "TEST 2 of 2: what does it give for" :
                at == 15 ? "CRACKED" : at == 16 ? "1 of 1 cracked" : "CIPHER MACHINE";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Cipher Abyss frame %d lacked %s\n", at, expected);
                exit(110);
            }
            if (at == 1 && !frame_contains(dest, length, "1. click symbols to build an input")) exit(110);
            if (at == 16 && !crazy_cog_audio_queued) exit(110);
            if (at < 16) rendered = 0;
            cipher_abyss_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 106 && handles[106] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Crazy Cog options" : "Crazy Cog";
        if (!frame_contains(dest, length, title)) exit(109);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Machines per run") ||
            !frame_contains(dest, length, "Rung 4: a load of 0.3.  Chains."))) exit(109);
        if (env_int("NW_TEST_CRAZY_COG")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 2 || at == 9 ? "plane 2 of 3" :
                at == 8 || at == 10 ? "plane 3 of 3" : "plane 1 of 3";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Crazy Cog frame %d lacked %s\n", at, expected);
                exit(109);
            }
            int ghosts = frame_circle_count(dest, length, 0x5adc6e6e) + frame_circle_count(dest, length, 0xe6463c6e);
            if ((at == 5) != (ghosts >= 2)) exit(109);
            if (at == 10 && !crazy_cog_audio_queued) exit(109);
            if (at < 10) rendered = 0;
            crazy_cog_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 135 && handles[135] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Emotion options" : "Emotion";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: 7 emotions to tell apart."))) exit(108);
        if (env_int("NW_TEST_EMO")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "Which emotion is this face showing?") ||
                !frame_contains(dest, length, "Which emotion is this?"))) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Emotion frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 134 && handles[134] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Tone of Voice options" : "Tone of Voice";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: 4 emotions to choose from."))) exit(108);
        if (env_int("NW_TEST_TONE")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "How does the speaker feel?") ||
                !frame_contains(dest, length, "(a hum)") || !frame_contains(dest, length, "the same words, said one way"))) {
                fprintf(stderr, "Tone of Voice frame 1 lacks the question, the hum or its note (%d %d %d, start %d, verdict %d %d)\n",
                    frame_contains(dest, length, "How does the speaker feel?"), frame_contains(dest, length, "(a hum)"),
                    frame_contains(dest, length, "the same words, said one way"), frame_contains(dest, length, "Press Space or click to start"),
                    frame_contains(dest, length, "Right: "), frame_contains(dest, length, "No: "));
                exit(108);
            }
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Tone of Voice frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) {
                fprintf(stderr, "Tone of Voice queued no audio by frame 7\n");
                exit(108);
            }
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 133 && handles[133] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Why They Feel options" : "Why They Feel";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: 3 answers to choose from."))) exit(108);
        if (env_int("NW_TEST_WHY")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "What would anyone feel, in their place?") ||
                !frame_contains(dest, length, "feel?"))) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Why They Feel frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 132 && handles[132] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Reading People options" : "Reading People";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: why."))) exit(108);
        if (env_int("NW_TEST_READ")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "Read the story: how do they feel, why, what helps?") ||
                !frame_contains(dest, length, "workshop"))) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Reading People frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 131 && handles[131] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "How Strongly options" : "How Strongly";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: within 8 points of the reference."))) exit(108);
        if (env_int("NW_TEST_STRONG")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "How strongly does the character feel each emotion?") ||
                !frame_contains(dest, length, "workshop"))) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "How Strongly frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 130 && handles[130] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Which Feeling options" : "Which Feeling";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: 3 answers to choose from."))) exit(108);
        if (env_int("NW_TEST_FEEL")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "What does the writer of this comment feel?") ||
                !frame_contains(dest, length, "workshop"))) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Which Feeling frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 129 && handles[129] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Social Sense options" : "Social Sense";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: feel, describe, want, need."))) exit(108);
        if (env_int("NW_TEST_SENSE")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && (!frame_contains(dest, length, "Why do people do it, and what comes of it?") ||
                !frame_contains(dest, length, "workshop"))) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Social Sense frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 128 && handles[128] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Bad Argument options" : "Bad Argument";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: world."))) exit(108);
        if (env_int("NW_TEST_ARGUE")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && !frame_contains(dest, length, "Does the conclusion follow from what is given?")) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Bad Argument frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 127 && handles[127] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Second Thoughts options" : "Second Thoughts";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: race, pond, coin, counts, bakers, price, description."))) exit(108);
        if (env_int("NW_TEST_SECOND")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(108);
            if (at == 1 && !frame_contains(dest, length, "The first answer that comes to mind is not always right")) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: ") && !frame_contains(dest, length, "No: ")) {
                fprintf(stderr, "Second Thoughts frame %d showed no answer\n", at);
                exit(108);
            }
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 126 && handles[126] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Between the Lines options" : "Between the Lines";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: implicature, sarcasm; 20 items."))) exit(108);
        if (env_int("NW_TEST_LINES")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 1 ? "workshop question." : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "%s frame %d lacked %s\n", title, at, expected);
                exit(108);
            }
            if (at == 1 && !frame_contains(dest, length, "What do they really mean?")) exit(108);
            if (at >= 2 && !frame_contains(dest, length, "Right: a") && !frame_contains(dest, length, "No: a"))
                exit(108);
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 105 && handles[105] != 0) {
        const char *title = env_int("NW_TEST_OPTION") ? "Figures of Speech options" : "Figures of Speech";
        if (!frame_contains(dest, length, title)) exit(108);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: metaphor, figure."))) exit(108);
        if (env_int("NW_TEST_FIGURES")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 1 ? "Imported workshop question." : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "%s frame %d lacked %s\n", title, at, expected);
                exit(108);
            }
            if (at >= 2 && !frame_contains(dest, length, "Right: a") && !frame_contains(dest, length, "No: a"))
                exit(108);
            if (at == 7 && !missing_word_audio_queued) exit(108);
            if (at < 7) rendered = 0;
            missing_word_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 101 && handles[101] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Heavier options" : "Heavier")) exit(105);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: 3 crates, 5 boards.  Each floor grips differently."))) exit(105);
        if (env_int("NW_TEST_HEAVIER")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(105);
            if (at > 0 && !frame_contains(dest, length, "rung 1  1/1")) exit(105);
            float push_y = frame_push_y(dest, length);
            if ((at == 2 && push_y <= 400.0f) ||
                (at == 3 && (push_y <= 250.0f || push_y >= 400.0f)) ||
                (at != 2 && at != 3 && push_y >= 0.0f)) exit(105);
            if (at >= 7 && !frame_contains(dest, length, "was the heaviest")) exit(105);
            if (at >= 10 && !heavier_audio_queued) exit(105);
            if (at < 12) rendered = 0;
            heavier_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 100 && handles[100] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Morning Round options" : "Morning Round")) exit(104);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 4: 1 rule(s), 1 block(s), 1 mistake(s) allowed."))) exit(104);
        if (env_int("NW_TEST_MORNING_ROUND")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(104);
            if (at > 0 && (!frame_contains(dest, length, "RULEBOOK") ||
                !frame_contains(dest, length, "rung 1  1/1"))) exit(104);
            if (at >= 35 && !morning_round_audio_queued) exit(104);
            if (at < 38) rendered = 0;
            morning_round_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 99 && handles[99] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Unicycle options" : "Unicycle")) exit(103);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rides per run") ||
            !frame_contains(dest, length, "Rung 4: 40 m.  Hills."))) exit(103);
        if (env_int("NW_TEST_UNICYCLE")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(103);
            if (at >= 8 && (!frame_contains(dest, length, "Head over heels") || !unicycle_audio_queued)) exit(103);
            if (at < 12) rendered = 0;
            unicycle_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 98 && handles[98] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Rover options" : "Rover")) exit(102);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Drives per run") ||
            !frame_contains(dest, length, "Rung 4: 1.0 s delay, 3 flag(s).  8 rocks."))) exit(102);
        if (env_int("NW_TEST_ROVER") == 2) {
            if (at >= 29 && !frame_contains(dest, length, "Hit a rock")) exit(102);
            if (at >= 34 && !rover_audio_queued) exit(102);
            if (at < 36) rendered = 0;
            rover_frame = at;
        } else if (env_int("NW_TEST_ROVER") == 1) {
            int commands = frame_rect_count(dest, length, 0x6edc8cff);
            if ((at == 0 && !frame_contains(dest, length, "Press Space or click to start")) ||
                (at > 0 && !frame_contains(dest, length, "delay 0.2 s")) ||
                (at >= 2 && at <= 5 && commands == 0) || (at >= 7 && commands != 0)) {
                fprintf(stderr, "Rover frame %d had %d drive commands\n", at, commands);
                exit(102);
            }
            if (at < 7) rendered = 0;
            rover_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 97 && handles[97] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Docking options" : "Docking")) exit(101);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Dockings per run") ||
            !frame_contains(dest, length, "Rung 4: within 0.25 m, under 0.35 m/s."))) exit(101);
        if (env_int("NW_TEST_DOCKING")) {
            static float previous;
            static float burn;
            if (at == 0) {
                if (!frame_contains(dest, length, "Press Space or click to start")) exit(101);
            } else {
                float fuel = docking_fuel_height(dest, length);
                float delta = previous - fuel;
                if (at == 2) burn = delta;
                if (fuel <= 0.0f || (at == 2 && burn <= 0.0f) ||
                    (at > 2 && at <= 5 && (delta < burn - 0.001f || delta > burn + 0.001f)) ||
                    (at > 5 && (delta < -0.001f || delta > 0.001f))) {
                    fprintf(stderr, "Docking frame %d fuel height %.5f after %.5f (burn %.5f)\n", at, fuel, previous, burn);
                    exit(101);
                }
                previous = fuel;
            }
            if (at < 7) rendered = 0;
            docking_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 96 && handles[96] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Ferry options" : "Ferry")) exit(100);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rivers per run") ||
            !frame_contains(dest, length, "Rung 4: 2 crossings, a 1.4 m/s river, 1 lane(s)."))) exit(100);
        if (env_int("NW_TEST_FERRY")) {
            static float previous_heading;
            if (at == 0) {
                if (!frame_contains(dest, length, "Press Space or click to start")) exit(100);
            } else {
                float heading = ferry_heading_x(dest, length);
                if (heading > 100.0f || (at >= 3 && at <= 5 && !(heading < previous_heading - 0.8f)) ||
                    (at > 5 && !(heading >= previous_heading - 0.001f && heading <= previous_heading + 0.001f))) {
                    fprintf(stderr, "Ferry frame %d heading %.5f after %.5f\n", at, heading, previous_heading);
                    exit(100);
                }
                previous_heading = heading;
            }
            if (at < 7) rendered = 0;
            ferry_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 95 && handles[95] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Crane options" : "Crane")) exit(99);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Yards per run") ||
            !frame_contains(dest, length, "Rung 4: 3 containers, 180 s."))) exit(99);
        if (env_int("NW_TEST_CRANE")) {
            static float previous_cable;
            if (at == 0) {
                if (!frame_contains(dest, length, "Press Space or click to start")) exit(99);
            } else {
                float cable = crane_cable_length(dest, length);
                if (!(cable > 0.0f) || (at > 1 && at <= 4 && !(cable < previous_cable - 1.0f)) ||
                    (at > 4 && !(cable >= previous_cable - 0.001f && cable <= previous_cable + 0.001f))) {
                    fprintf(stderr, "Crane frame %d cable %.5f after %.5f\n", at, cable, previous_cable);
                    exit(99);
                }
                previous_cable = cable;
            }
            if (at < 6) rendered = 0;
            crane_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 94 && handles[94] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Kitchen options" : "Kitchen")) exit(98);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Shifts per run") ||
            !frame_contains(dest, length, "Rung 4: 4 tickets of up to 1 part(s), 2 stove(s)."))) exit(98);
        if (env_int("NW_TEST_KITCHEN")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 220 ? "binned" : "Cook and plate every ticket before it lapses";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Kitchen frame %d lacked %s\n", at, expected);
                exit(98);
            }
            if (at < 220) rendered = 0;
            kitchen_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 93 && handles[93] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Sokoban Live options" : "Sokoban Live")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Warehouses per run") ||
            !frame_contains(dest, length, "Rung 4: 2 crate(s), 1 guard(s) stepping every 0.65 s."))) exit(97);
        if (env_int("NW_TEST_SOKOBANLIVE")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at < 30 ? "Push every crate onto a pad; keep clear of guards" : "Every pad covered in 3 s";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Sokoban Live frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at < 31) rendered = 0;
            sokobanlive_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 92 && handles[92] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Escort options" : "Escort")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Temples per run") ||
            !frame_contains(dest, length, "Rung 4: 1 walker(s), 2 lever(s)."))) exit(97);
        if (env_int("NW_TEST_ESCORT")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                "Work the levers; bring every walker through";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Escort frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at < 7) rendered = 0;
            escort_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 91 && handles[91] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Air Traffic options" : "Air Traffic")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Skies per run") ||
            !frame_contains(dest, length, "Rung 4: 5 planes, two runways."))) exit(97);
        if (env_int("NW_TEST_AIRTRAFFIC")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at < 34 ? "Land every plane on the runway of its colour" :
                at == 34 ? "plane 1 picked" : at == 35 ? "1 H" :
                at <= 37 ? "1 >" : "1 L";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Air Traffic frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at < 38) rendered = 0;
            airtraffic_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 90 && handles[90] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Rail Yard options" : "Rail Yard")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Yards per run") ||
            !frame_contains(dest, length, "Rung 4: 4 stations, 7 trains, one tunnel."))) exit(97);
        if (env_int("NW_TEST_RAILYARD")) {
            const char *expected = at == 0 ? "Press Space or click to start" : "Every train to the station of its colour";
            if (!frame_contains(dest, length, expected)) {
                fprintf(stderr, "Rail Yard frame %d lacked %s\n", at, expected);
                exit(97);
            }
            int red_signals = frame_circle_count(dest, length, 0xec4038ff);
            if ((at == 2 && frame_circle_count(dest, length, 0xff8028ff) != 1) ||
                (at == 3 && red_signals != 1) || (at == 7 && red_signals != 0) ||
                (at == 8 && red_signals != 1)) {
                fprintf(stderr, "Rail Yard frame %d showed incorrect points or signals\n", at);
                exit(97);
            }
            if (at < 8) rendered = 0;
            railyard_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 88 && handles[88] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Firebreak options" : "Firebreak")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Fires per run") ||
            !frame_contains(dest, length, "Rung 4: one fire, a break takes 0.50 s to dig."))) exit(97);
        if (env_int("NW_TEST_FIREBREAK")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 2 ? "shovels 50" : at == 3 ? "shovels 49" : at == 7 ? "shovels 48" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "Firebreak frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at < 7) rendered = 0;
            firebreak_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 87 && handles[87] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Explore or Exploit options" : "Explore or Exploit")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Runs") ||
            !frame_contains(dest, length, "Rung 4: 3 machines, 40 pulls."))) exit(97);
        if (env_int("NW_TEST_BANDIT")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 3 ? "0 coins     58 pulls left" : at == 6 ? "17 coins     55 pulls left" :
                (at == 61 || at == 62) ? "204 coins (par 311)" :
                at == 63 ? "0 of 1 passed" : at == 64 ? "0 coins     60 pulls left" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "Explore or Exploit frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at == 3 && !frame_contains(dest, length, "?")) exit(97);
            if (at == 62 && frame_contains(dest, length, "highest rung passed")) exit(97);
            if (at < 64) rendered = 0;
            bandit_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 86 && handles[86] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Bluff options" : "Bluff")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 3: 23 hands, cards 1 to 3."))) exit(97);
        if (env_int("NW_TEST_BLUFF")) {
            const char *expected = at == 0 ? "Press Space or click to start" :
                at == 2 ? "hand 2 of 21" : at == 3 ? "chips +3" :
                (at == 23 || at == 24) ? "Your play was worth 8 against a par of 15 (chips +10) -- they were: station" :
                at == 25 ? "0 of 1 at par or better" : at == 26 ? "hand 1 of 21" : NULL;
            if (expected && !frame_contains(dest, length, expected)) {
                fprintf(stderr, "Bluff frame %d lacked %s\n", at, expected);
                exit(97);
            }
            if (at == 24 && frame_contains(dest, length, "highest rung passed")) exit(97);
            if (at < 26) rendered = 0;
            bluff_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 85 && handles[85] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Dispatch options" : "Dispatch")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 2: 2 crews, bursts of up to 1."))) exit(97);
        if (env_int("NW_TEST_DISPATCH")) {
            const char *verdict = "Damage 224 against a par of 64: 1 saved, 5 lost";
            if (at == 0 && !frame_contains(dest, length, "Press Space to start")) exit(97);
            if (at == 52 && !frame_contains(dest, length, "refits 1/3")) exit(97);
            if (!dispatch_judged && frame_contains(dest, length, verdict)) dispatch_judged = at;
            if (dispatch_judged && at == dispatch_judged + 1 && !frame_contains(dest, length, verdict)) exit(97);
            if (dispatch_judged && at == dispatch_judged + 2 &&
                !frame_contains(dest, length, "0 of 1 rounds under par")) exit(97);
            if (dispatch_judged && at == dispatch_judged + 3 &&
                !frame_contains(dest, length, "0s  damage 0")) exit(97);
            if (!dispatch_judged || at < dispatch_judged + 3) rendered = 0;
            dispatch_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 84 && handles[84] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Gamble options" : "Gamble")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 3: 2 machines, 26 pulls."))) exit(97);
        if (env_int("NW_TEST_GAMBLE")) {
            const char *expected[] = {"Press Space or click to start", "pulls left 59",
                "pulls left 58", "pulls left 57", "Your pulls were worth",
                "Your pulls were worth", "highest rung passed", "pulls left 59"};
            if (at > 7 || !frame_contains(dest, length, expected[at])) {
                fprintf(stderr, "Gamble frame %d lacked the expected label\n", at);
                exit(97);
            }
            if (at == 5 && frame_contains(dest, length, "highest rung passed")) exit(97);
            if (at < 7) rendered = 0;
            gamble_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 83 && handles[83] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Sonar options" : "Sonar")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Rounds per run") ||
            !frame_contains(dest, length, "Rung 2: a 6x6 grid, a wrong dig costs 4 pings."))) exit(97);
        if (env_int("NW_TEST_SONAR") == 2) {
            if (at == 0) {
                if (!frame_contains(dest, length, "Press Space to start")) exit(97);
                sonar_frame = 1;
                rendered = 0;
            } else if (length < 500000 || !frame_contains(dest, length, "Find it for 129.5 or less")) {
                exit(97);
            }
        }
        if (env_int("NW_TEST_SONAR") == 1) {
            const char *expected[] = {"Press Space to start", "Find it for 6 or less", "spent 0",
                "spent 1", "spent 4", "Found for 4; par was 6", "Found for 4; par was 6",
                "1 of 1 under par   highest rung passed 1", "spent 0"};
            if (at > 8 || !frame_contains(dest, length, expected[at])) {
                fprintf(stderr, "Sonar frame %d lacked the expected label\n", at);
                exit(97);
            }
            if (at == 6 && frame_contains(dest, length, "under par   highest rung passed")) exit(97);
            if (at < 8) rendered = 0;
            sonar_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 79 && handles[79] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Signals options" : "Signals")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Games per run") ||
            !frame_contains(dest, length, "Rung 4:"))) exit(97);
        if (env_int("NW_TEST_SIGNALS")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(97);
            if (at == 1 && !frame_contains(dest, length, "Partner says")) exit(97);
            if (at == 3 && !frame_contains(dest, length, "You say")) exit(97);
            if (at == 25 && !frame_contains(dest, length, "16 of 16 exchanges understood (par 11.1)")) exit(97);
            if (at == 55 && !frame_contains(dest, length, "1 of 1 passed")) exit(97);
            if (at < 55) rendered = 0;
            signals_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 78 && handles[78] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Captcha options" : "Captcha")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Trials per run") ||
            !frame_contains(dest, length, "Rung 4:"))) exit(97);
        if (env_int("NW_TEST_CAPTCHA")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or click to start")) exit(97);
            if (at == 4 && !frame_contains(dest, length,
                "Type only the black characters, but not the small ones")) exit(97);
            if (at == 18 && !frame_contains(dest, length, "Right: NUJWHT7N")) exit(97);
            if (at == 39 && !frame_contains(dest, length, "1 of 1 passed")) exit(97);
            if (at < 39) rendered = 0;
            captcha_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 77 && handles[77] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Shadow Play options" : "Shadow Play")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Trials per run") ||
            !frame_contains(dest, length, "Rung 4:"))) exit(97);
        if (env_int("NW_TEST_SHADOW_CLOCK")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space or Enter to start")) exit(97);
            if (at == 4 && !frame_contains(dest, length, "Turn it left and right")) exit(97);
            if (at == 18 && (!frame_contains(dest, length, "The shadow fits") || !shadow_audio_queued)) exit(97);
            if (at == 39 && !frame_contains(dest, length, "1 of 1 passed")) exit(97);
            if (at < 39) rendered = 0;
            shadow_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 76 && handles[76] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Tuner options" : "Tuner")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Trials per run") ||
            !frame_contains(dest, length, "Rung 4: 4 stations."))) exit(97);
        if (env_int("NW_TEST_TUNER_CLOCK")) {
            bool recorded = env_int("NW_TEST_TUNER_CLOCK") == 2;
            int tune_at = recorded ? 43 : 27;
            if (at == 0 && !frame_contains(dest, length, "Press Space or Enter to start")) exit(97);
            if (at == 15 && (!frame_contains(dest, length, "Listen to the sound") || !tuner_audio_queued)) exit(97);
            if (at == tune_at && (!frame_contains(dest, length, "Find the station playing it") ||
                !frame_contains(dest, length, recorded ? " stations   recordings" : "tunes (fetch esc50 for recordings)"))) exit(97);
            if (at == tune_at + 17 && !frame_contains(dest, length, "Locked on to the sound")) exit(97);
            if (at == tune_at + 41 && !frame_contains(dest, length, "Run complete")) exit(97);
            if (at < tune_at + 41) rendered = 0;
            tuner_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 75 && handles[75] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Dr Shape options" : "Dr Shape")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Shapes per run") ||
            !frame_contains(dest, length, "Rung 4: 4 candidates."))) exit(97);
        if (env_int("NW_TEST_DRSHAPE_CLOCK")) {
            if (at == 0 && !frame_contains(dest, length, "Press Space to start")) exit(97);
            if (at > 0 && at < 69 && !frame_contains(dest, length, "the turtle draws a shape")) exit(97);
            if (at == 72 && !frame_contains(dest, length, "Which is the same shape?")) exit(97);
            if (at == 73 && !frame_contains(dest, length, "Card 1 -- that is the one")) exit(97);
            if (at == 98 && !frame_contains(dest, length, "1 of 1 passed")) exit(97);
            if (at < 98) rendered = 0;
            drshape_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 74 && handles[74] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Shape from Motion options" : "Shape from Motion")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Clouds per run") ||
            !frame_contains(dest, length, "Rung 4: 300 dots, 4 choices."))) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 72 && handles[72] != 0) {
        if (!frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "What Happens Next options" : "What Happens Next")) exit(97);
        if (env_int("NW_TEST_OPTION") && (!frame_contains(dest, length, "Clips per run") ||
            !frame_contains(dest, length, "Rung 4:"))) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 71 && handles[71] != 0) {
        if (!frame_contains(dest, length, "Gunslinger")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Duels per run")) exit(97);
        if (env_int("NW_TEST_GUN_CLICK")) {
            if (at >= 5 && !frame_contains(dest, length, "You fired first")) exit(97);
            if (at < 5) rendered = 0;
        }
    }
    if (env_int("NW_TEST_SLOT") == 68 && handles[68] != 0) {
        if (!frame_contains(dest, length, "Safecracker")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Safes per run")) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 67 && handles[67] != 0) {
        if (!frame_contains(dest, length, "Field Manual")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Machines per run")) exit(97);
        if (env_int("NW_TEST_FIELD_CLICK")) {
            if (at >= 5 && !frame_contains(dest, length, "Every order carried out")) exit(97);
            if (at < 5) rendered = 0;
        }
    }
    if (env_int("NW_TEST_SLOT") == 66 && handles[66] != 0) {
        if (!frame_contains(dest, length, "Drone Hoops")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Flights per run")) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 65 && handles[65] != 0) {
        if (!frame_contains(dest, length, "Echo Cave")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Flights per run")) exit(97);
        if (env_int("NW_TEST_ECHO_CLOCK")) {
            if (frame_contains(dest, length, "0 of 1 passed")) {
                if (!echo_audio_queued) exit(97);
                echo_judged = 2;
            }
            else if (frame_contains(dest, length, "Hit the rock")) echo_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Dark: Space clicks")) exit(97);
            if (echo_judged < 2) rendered = 0;
            echo_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 62 && handles[62] != 0) {
        if (!frame_contains(dest, length, "Keep the Beat")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Songs per run")) exit(97);
        if (env_int("NW_TEST_BEAT_CLOCK")) {
            if (frame_contains(dest, length, "1 of 1 passed")) beat_judged = 2;
            else if (frame_contains(dest, length, "6 of 6 beats kept")) beat_judged = 1;
            else if (!frame_contains(dest, length, at == 0 ? "Press Space" : "Tap along")) exit(97);
            if (beat_judged < 2) rendered = 0;
            beat_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 58 && handles[58] != 0) {
        if (!frame_contains(dest, length, "Time It")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Shots per run")) exit(97);
        if (env_int("NW_TEST_TIME_IT_CLOCK")) {
            const char *label = at == 0 ? "Press Space" : at < 95 ? "Press as it passes" :
                at == 95 ? "On the mark" : "1 of 1 passed";
            if (!frame_contains(dest, length, label)) {
                fprintf(stderr, "Time It frame %d did not show %s\n", at, label);
                exit(97);
            }
            if (at == 1 && (time_it_audio_queued != 1 || !SDL_WasInit(SDL_INIT_AUDIO))) exit(97);
            if (at == 95 && SDL_WasInit(SDL_INIT_AUDIO)) exit(97);
            if (at < 96) rendered = 0;
            time_it_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 49 && handles[49] != 0) {
        if (!frame_contains(dest, length, "Hold It")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Holds per run")) exit(97);
        if (env_int("NW_TEST_HOLD_IT_CLOCK")) {
            const char *label = at == 0 ? "Press Space" : at == 81 ? "Hold now" :
                at == 82 ? "holding..." : at == 103 ? "held 1.00 s" : at == 104 ? "highest rung passed" : NULL;
            if (label && !frame_contains(dest, length, label)) {
                fprintf(stderr, "Hold It frame %d did not show %s\n", at, label);
                exit(97);
            }
            if (at < 103 && frame_contains(dest, length, "asked ")) exit(97);
            if (at == 82 && (hold_it_audio_queued != 1 || !SDL_WasInit(SDL_INIT_AUDIO))) exit(97);
            if (at == 103 && SDL_WasInit(SDL_INIT_AUDIO)) exit(97);
            if (at < 104) rendered = 0;
            hold_it_frame = at;
        }
    }
    if (env_int("NW_TEST_SLOT") == 48 && handles[48] != 0) {
        if (!frame_contains(dest, length, "Stop & Switch")) exit(97);
        if (env_int("NW_TEST_OPTION") && !frame_contains(dest, length, "Blocks per run")) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 47 && handles[47] != 0) {
        if (env_int("NW_TEST_OPTION")) {
            if (!frame_contains(dest, length, "Delay options") || !frame_contains(dest, length, "s runs")) exit(97);
        } else if (!frame_contains(dest, length, "Delay")) exit(97);
    }
    if (env_int("NW_TEST_TRIAGE") && handles[46] != 0) {
        if (at > 0 && at < 6 && !frame_contains(dest, length, "Earn 2.5 or more with 4 moves")) exit(97);
        if (at == 6) {
            if (frame_contains(dest, length, "1 of 1 passed   highest rung passed 1")) {
                if (!triage_frame || triage_frame != 6) exit(97);
            } else {
                if (!frame_contains(dest, length, "Earned 5 against a par of 2.5")) exit(97);
                rendered = 0;
            }
        } else {
            rendered = 0;
        }
        triage_frame = at;
    }
    if (env_int("NW_TEST_SLOT") == 46 && handles[46] != 0) {
        if (env_int("NW_TEST_OPTION")) {
            if (!frame_contains(dest, length, "Triage options") ||
                !frame_contains(dest, length, "the moves cover about")) exit(97);
        } else if (!frame_contains(dest, length, "Triage")) exit(97);
    }
    if (env_int("NW_TEST_SLOT") == 45 && handles[45] != 0 &&
        !frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Hidden Wiring options" : "Hidden Wiring")) exit(97);
    if (env_int("NW_TEST_SLOT") == 44 && handles[44] != 0 &&
        !frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Hidden Rule options" : "Hidden Rule")) exit(97);
    if (env_int("NW_TEST_HIDDEN_RULE") && handles[44] != 0) {
        const char *phase = at < 4 ? "Learn the rule" : (at < 10 ? "Lit or dark?" : "The rule was:");
        if (!frame_contains(dest, length, phase) ||
            (at == 1 && !frame_contains(dest, length, "Test (T)")) ||
            (at == 3 && !frame_contains(dest, length, "tests 1 (cost 1 each, 47 left)")) ||
            (at == 5 && !frame_contains(dest, length, "question 2 of 6"))) {
            fprintf(stderr, "Hidden Rule frame %d did not show %s and its controls\n", at, phase);
            exit(97);
        }
        hidden_rule_frame = at;
    }
    if (env_int("NW_TEST_SLOT") == 43 && handles[43] != 0 &&
        !frame_contains(dest, length, env_int("NW_TEST_OPTION") ? "Video Sequence options" : "Video Sequence")) exit(97);
    if (env_int("NW_TEST_SALESMAN") && salesman_clicks == 5 && !exit_sent) {
        int64_t handle = handles[env_int("NW_TEST_SLOT")];
        if (nw_salesman_info(handle, 0) != 2 || nw_salesman_info(handle, 6) != 5 ||
            nw_salesman_info(handle, 13) != 1) exit(97);
        salesman_settled = true;
    }
    if (env_int("NW_TEST_COOKIE_PREVIEW") && !exit_sent) {
        if (at == 2) {
            if (!frame_contains(dest, length, "Cookie Thief options") ||
                !frame_contains(dest, length, "Take 4 and leave") ||
                !frame_contains(dest, length, "Guessing gets away clean about 6%") ||
                !frame_contains(dest, length, "0.080 s")) exit(97);
        } else if (at == 3) {
            if (frame_contains(dest, length, "Cookie Thief options") ||
                nw_cookie_thief_info(handles[env_int("NW_TEST_SLOT")], 1) != 1) exit(97);
            ++at;
        }
    }
    if (env_int("NW_TEST_COOKIE_THIEF") && !exit_sent) {
        int64_t handle = handles[env_int("NW_TEST_SLOT")];
        int phase = nw_cookie_thief_info(handle, 0);
        if (!frame_contains(dest, length, "Cookie Thief") ||
            nw_cookie_thief_info(handle, 3) != 1 || nw_cookie_thief_info(handle, 4) != 80 ||
            nw_cookie_thief_info(handle, 5) != 0 || nw_cookie_thief_info(handle, 6) != 0) exit(97);
        if (phase >= 3 && (nw_cookie_thief_info(handle, 7) != 1 ||
            nw_cookie_thief_info(handle, 8) != 1 || nw_cookie_thief_info(handle, 9) != 0 ||
            nw_cookie_thief_info(handle, 10) != 1 || nw_cookie_thief_info(handle, 11) != 1 ||
            nw_cookie_thief_info(handle, 12) != 1 ||
            !frame_contains(dest, length, "Away with 1 — +1 points"))) exit(97);
        if (phase == 4 && !frame_contains(dest, length, "1 of 1 clean, 1 points off 1 cookies")) exit(97);
        if (phase == 3 && cookie_phase != 3) SDL_Delay(1010);
        cookie_phase = phase;
    }
    if (getenv("NW_TEST_SOKOBAN3D_ROUTE") && !exit_sent) {
        if (!frame_contains(dest, length, getenv("NW_TEST_SOKOBAN3D_SUMMARY")) ||
            !frame_contains(dest, length, getenv("NW_TEST_SOKOBAN3D_VERDICT"))) exit(97);
    }
    if (env_int("NW_TEST_SOKOBAN3D_PREVIEW") && !exit_sent) {
        int64_t handle = handles[env_int("NW_TEST_SLOT")];
        if (at == 4) {
            if (!frame_contains(dest, length, "3D Sokoban options") ||
                !frame_contains(dest, length, "7 × 7 warehouse with 2 boxes and at least 20% trap floor")) exit(97);
        } else if (at == 5) {
            if (frame_contains(dest, length, "3D Sokoban options") ||
                nw_sokoban3d_info(handle, 0) != 1 || nw_sokoban3d_info(handle, 1) != 3 ||
                nw_sokoban3d_info(handle, 6) != 1) exit(97);
            ++at;
        }
    }
    if (env_int("NW_TEST_SOKOBAN3D") && !exit_sent) {
        int initial = env_int("NW_TEST_DIRECT") ? 0 : env_int("NW_TEST_CATEGORY") + env_int("NW_TEST_ROW") + 1;
        int offset = at - initial;
        int64_t handle = handles[env_int("NW_TEST_SLOT")];
        int64_t facing = nw_sokoban3d_info(handle, 5);
        int64_t steps = nw_sokoban3d_info(handle, 6);
        if (offset == 1) sokoban3d_initial_facing = facing;
        bool turned = offset == 2 || offset == 4;
        bool restored = offset == 3 || offset == 5;
        if ((turned && (facing == sokoban3d_initial_facing || steps != 1)) ||
            (restored && (facing != sokoban3d_initial_facing || steps != 0)) ||
            !frame_contains(dest, length, "3D Sokoban")) {
            fprintf(stderr, "3D Sokoban replay step %d: facing %lld (initial %lld), steps %lld, frame %lld\n",
                    offset, (long long)facing, (long long)sokoban3d_initial_facing, (long long)steps, (long long)length);
            exit(97);
        }
        sokoban3d_checked = offset;
    }
    if (getenv("NW_TEST_MAZE2D_ROUTE") && !exit_sent) {
        if (!frame_contains(dest, length, "1 mazes, 100% step efficiency, highest rung 3") ||
            !frame_contains(dest, length, "Perfect — the minimum ")) exit(97);
    }
    if (env_int("NW_TEST_MAZE2D") && !exit_sent) {
        int initial = env_int("NW_TEST_DIRECT") ? 0 : env_int("NW_TEST_CATEGORY") + env_int("NW_TEST_ROW") + 1;
        if (at == initial + 6) {
            int64_t handle = handles[env_int("NW_TEST_SLOT")];
            if (nw_maze2d_info(handle, 5) != 0 || nw_maze2d_info(handle, 4) != nw_maze2d_info(handle, 9))
                exit(97);
            maze2d_restarted = true;
        }
    }
    if (env_int("NW_TEST_MAZE2D_PREVIEW") && !exit_sent) {
        if (at == 2) {
            if (!frame_contains(dest, length, "Maze options") ||
                !frame_contains(dest, length, "2 locked doors, at least 72 steps")) exit(97);
        } else if (at == 3) {
            if (frame_contains(dest, length, "Maze options") ||
                nw_maze2d_info(handles[env_int("NW_TEST_SLOT")], 1) != 3) exit(97);
            ++at;
        }
    }
    if (env_int("NW_TEST_NINAROW_PREVIEW") && !exit_sent) {
        if (at == 3) {
            if (!frame_contains(dest, length, "N-in-a-row options") ||
                !frame_contains(dest, length, "board with about")) exit(97);
        } else if (at == 4) {
            if (frame_contains(dest, length, "N-in-a-row options") ||
                nw_ninarow_info(handles[env_int("NW_TEST_SLOT")], 3) != 2) exit(97);
            ++at;
        }
    }
    if (env_int("NW_TEST_SALESMAN_PREVIEW") && !exit_sent) {
        if (at == 4) {
            if (!frame_contains(dest, length, "6 cities. Your score compares your route")) exit(97);
        } else if (at == 5) {
            if (frame_contains(dest, length, "Traveling Salesman options") ||
                nw_salesman_info(handles[env_int("NW_TEST_SLOT")], 1) != 5) exit(97);
            ++at;
        }
    }
    if (env_int("NW_TEST_HANOI_PREVIEW") && !exit_sent) {
        if (at == 2) {
            if (!frame_contains(dest, length, "A tower of 4 disks takes at least 15 moves.")) exit(97);
        } else if (at == 3) {
            if (frame_contains(dest, length, "Tower of Hanoi options") ||
                nw_hanoi_info(handles[env_int("NW_TEST_SLOT")], 1) != 3) exit(97);
            ++at;
        }
    }
    if (env_int("NW_TEST_GO_PREVIEW") && !exit_sent) {
        if (!frame_contains(dest, length, "White group of 24") ||
            !frame_contains(dest, length, "1 position per run") ||
            !frame_contains(dest, length, "Find the target group on the board.") ||
            !frame_contains(dest, length, "23, 20, 16, 12, 8, 4"))
            exit(97);
    }
    if (env_int("NW_TEST_JIGSAW_HOVER")) {
        int64_t handle = handles[env_int("NW_TEST_SLOT")];
        int64_t hovered = nw_jigsaw_info(handle, 16);
        int64_t picked = nw_jigsaw_info(handle, 7);
        int expected = at == 2 || at == 4 ? 0 : -1;
        if (hovered != expected || picked != (at == 6 ? 0 : -1)) {
            fprintf(stderr, "Jigsaw pointer at %d: hovered %lld picked %lld\n",
                    at, (long long)hovered, (long long)picked);
            exit(97);
        }
        ++jigsaw_hover_frames;
    }
    if (env_int("NW_TEST_PROFILE_PICKER") == 4 && at == 21) {
        int slot = env_int("NW_TEST_PROFILE_TASK_SLOT");
        int64_t level = nw_scramble_info(handles[slot], 1);
        int64_t trials = nw_scramble_info(handles[slot], 3);
        if (level != 4 || trials != 5) {
            fprintf(stderr, "profile task options: %lld %lld\n", (long long)level, (long long)trials);
            exit(97);
        }
    }
    if (env_int("NW_TEST_HISTORY") && !exit_sent) {
        const char *titles[] = {"Position N-Back history", "Position N-Back history", "Sound N-Back history",
                                "Dual N-Back history", "Position N-Back history"};
        const char *title = history_frames < 5 ? titles[history_frames] : "3D N-Back";
        bool empty = env_int("NW_TEST_HISTORY") == 2;
        if (empty && history_frames < 5) title = "Position N-Back history";
        if (!frame_contains(dest, length, title)) exit(97);
        if (history_frames < 5) {
            const char *expected = empty ? "Insufficient data: two days needed" :
                (history_frames == 0 ? "Level" : "Accuracy");
            if (!frame_contains(dest, length, expected)) exit(97);
            if (!empty) {
                const char *legend = history_frames == 2 ? "Last 50 rounds: Sound 75%" :
                    history_frames == 3 ? "Last 50 rounds: Position 45%   Sound 60%" :
                    "Last 50 rounds: Position 65%";
                if (!frame_contains(dest, length, "2/28") || !frame_contains(dest, length, legend)) exit(97);
            }
        }
    }
    if (getenv("NW_TEST_MUSIC_TIER") && applause_frames >= 1 && !exit_sent) {
        int64_t tier = nw_nback3d_info(handles[env_int("NW_TEST_SLOT")], 24);
        int expected = env_int("NW_TEST_MUSIC_TIER");
        if (env_int("NW_TEST_REWARD_FADE") && applause_frames >= 4) expected = 0;
        if (tier != expected) {
            fprintf(stderr, "Reward music tier %lld, expected %d\n", (long long)tier, expected);
            exit(97);
        }
    }
    if (env_int("NW_TEST_MEDIA_MENU") && !exit_sent) {
        bool recognition = env_int("NW_TEST_MEDIA_RECOGNITION");
        int mode = env_int("NW_TEST_MEDIA_MENU"), slot = env_int("NW_TEST_SLOT");
        int64_t configured = recognition ? nw_recognition_info(handles[slot], 1) : nw_concentration_info(handles[slot], 1);
        bool applied = mode == 2 || mode == 4;
        int64_t expected = recognition ? (applied ? 60 : 40) : (applied ? 10 : 8);
        if (env_int("NW_TEST_MEDIA_EXPECTED")) expected = env_int("NW_TEST_MEDIA_EXPECTED");
        const char *title = recognition ? "Seen it before? options" : "Concentration options";
        size_t title_length = strlen(title);
        bool shown = false;
        const uint8_t *frame = (const uint8_t *)(intptr_t)dest;
        for (int64_t pos = 0; pos + (int64_t)title_length <= length; ++pos) {
            if (memcmp(frame + pos, title, title_length) == 0) { shown = true; break; }
        }
        if (configured != expected || shown != (mode == 1)) {
            fprintf(stderr, "Media options mode %d returned setting %lld and menu state %d\n",
                mode, (long long)configured, shown);
            exit(97);
        }
    }
    if (env_int("NW_TEST_LARGE_FRAME") && !large_frame_written) {
        if (length <= 40976) exit(93);
        large_frame_written = true;
    }
    return length;
}
'''
# Compare decoded pixels with SDL so PNG compression and metadata cannot affect the result.
logo_check = r"""
#include <SDL3/SDL.h>
int main(int argc, char **argv) {
#if SDL_VERSION_ATLEAST(3, 4, 0)
    if (argc != 3) return 1;
    SDL_Surface *plain = SDL_LoadPNG(argv[1]);
    SDL_Surface *branded = SDL_LoadPNG(argv[2]);
    if (!plain || !branded || plain->w != 480 || plain->h != 360 ||
        branded->w != plain->w || branded->h != plain->h) return 2;
    int changed = 0;
    for (int y = 0; y < plain->h; ++y) {
        for (int x = 0; x < plain->w; ++x) {
            Uint32 a, b;
            if (!SDL_ReadSurfacePixel(plain, x, y, (Uint8 *)&a, (Uint8 *)&a + 1,
                                      (Uint8 *)&a + 2, (Uint8 *)&a + 3) ||
                !SDL_ReadSurfacePixel(branded, x, y, (Uint8 *)&b, (Uint8 *)&b + 1,
                                      (Uint8 *)&b + 2, (Uint8 *)&b + 3)) return 3;
            if (a == b) continue;
            /* Splash room: x=276..636, y=268..584 at 912x684. */
            if (x < 145 || x > 335 || y < 52 || y > 219) return 4;
            ++changed;
        }
    }
    SDL_DestroySurface(plain);
    SDL_DestroySurface(branded);
    return changed > 100 ? 0 : 5;
#else
    return 1;
#endif
}
"""
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    harness = tmp / 'harness.c'
    main_object = tmp / 'main.o'
    exe = tmp / ('replay.exe' if os.name == 'nt' else 'replay')
    sdl_library = ('libSDL3.0.dylib' if sys.platform == 'darwin' else
                   'SDL3.dll' if os.name == 'nt' else 'libSDL3.so.0')
    harness.write_text(f'#define NW_TEST_SDL_LIBRARY "{sdl_library}"\n' + source)
    defines = ['-DNW_MARBLE_MUJOCO'] if mujoco else []
    subprocess.run(['cc', '-O2', '-std=c11', *defines, '-DSDL_PollEvent=nw_test_poll', '-DNW_TEST_FRAME_WRITER=nw_test_frame',
                    '-Dnw_sdl_close_desktop=nw_test_shutdown', '-Dnw_sdl_window_pointer=nw_test_pointer',
                    '-c', str(root / 'shells/sdl3/main.c'), '-o', str(main_object), *flags], check=True, timeout=30)
    extra = []
    if mujoco:
        extra = [str(mujoco)]
        if sys.platform == 'darwin':
            extra += ['-framework', 'OpenGL', '-Wl,-headerpad_max_install_names']
        elif sys.platform.startswith('linux'):
            extra += ['-Wl,-rpath,' + str(mujoco.parent), '-lGL', '-lm']
        elif windows_gl is not None or os.name == 'nt':
            extra.append(str(windows_gl or root / "shells/sdl3/marble_gl_windows.c"))
    subprocess.run(['cc', '-O2', '-std=c11', '-o', str(exe), str(main_object), '-I' + str(root / 'shells/sdl3'), str(harness), str(linked), str(runtime),
                    *extra, *link_flags, *flags], check=True, timeout=30)
    if mujoco and sys.platform == 'darwin':
        install_name = subprocess.check_output(['otool', '-D', str(mujoco)], text=True).splitlines()[1]
        if install_name != str(mujoco):
            subprocess.run(['install_name_tool', '-change', install_name, str(mujoco), str(exe)], check=True)
            subprocess.run(['codesign', '--force', '--sign', '-', str(exe)], check=True)
    env = {key: value for key, value in os.environ.items() if not key.startswith('NW_')}
    env.update(SDL_VIDEODRIVER='dummy', SDL_RENDER_DRIVER='software', HOME=directory,
               APPDATA=directory, USERPROFILE=directory)
    frame_oracle = runpy.run_path(str(root.parent / "original-neural-workshop-enhanced/nwenv/export.py"))
    frame_header = frame_oracle["HEADER"]
    frame_name = "nwfb_" + uuid.uuid4().hex[:16]
    frame_ack = tmp / "frame-read"
    frame_ready = tmp / "frame-ready"
    frame_env = dict(env, NW_SHM=frame_name, NW_TEST_FRAME_ACK=str(frame_ack),
                     NW_TEST_FRAME_READY=str(frame_ready))
    track_options = {"track": False} if sys.version_info >= (3, 13) else {}
    with subprocess.Popen([str(exe), "--screen", "cookie-thief", "--width", "640", "--height", "480"],
                          env=frame_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as child:
        try:
            deadline = time.monotonic() + 4
            while not frame_ready.exists():
                assert time.monotonic() < deadline and child.poll() is None, "SDL did not render a frame"
                time.sleep(0.01)
            shared = SharedMemory(name=frame_name, **track_options)
            if not track_options and os.name == "posix":
                from multiprocessing import resource_tracker
                resource_tracker.unregister("/" + frame_name, "shared_memory")
            try:
                magic, version, sequence, timestamp, width, height, consumed = frame_header.unpack_from(shared.buf)
                assert (magic, version, sequence, width, height, consumed) == (b"NWFB", 1, 1, 640, 480, 0)
                assert timestamp > 0
                rgba = bytes(shared.buf[frame_header.size:frame_header.size + width * height * 4])
                assert len(rgba) == width * height * 4
                assert len(set(rgba[0::4])) > 1, "expected the actual task drawing"
                assert set(rgba[3::4]) == {255}, "expected opaque top-down RGBA"
            finally:
                shared.close()
        except Exception as error:
            frame_ack.touch()
            stdout, stderr = child.communicate(timeout=10)
            raise AssertionError((stdout, stderr)) from error
        frame_ack.touch()
        stdout, stderr = child.communicate(timeout=10)
        assert child.returncode == 0, (stdout, stderr)
    try:
        shared = SharedMemory(name=frame_name, **track_options)
    except FileNotFoundError:
        pass
    else:
        shared.close()
        raise AssertionError("desktop did not release its frame mapping")
    print("SDL frame export: Python reads rendered Cookie Thief pixels and the desktop releases its mapping")
    unavailable_video = dict(env, SDL_VIDEODRIVER='nw-invalid-driver')
    saved = tmp / 'scramble-options'
    saved.write_text('4 5 1 0\n')
    settings_env = dict(unavailable_video, NW_SCRAMBLE_SETTINGS_PATH='~/scramble-options')
    result = subprocess.run([str(exe), '--selftest-scramble-settings-read'],
                            env=settings_env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and result.stdout.strip() == '4 5 1 0', result.stderr
    saved.write_text('+0_4 0_5 1 -0_0\n')
    result = subprocess.run([str(exe), '--selftest-scramble-settings-read'],
                            env=settings_env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and result.stdout.strip() == '4 5 1 0', result.stderr
    saved.write_text('4 5 1 0_\n')
    result = subprocess.run([str(exe), '--selftest-scramble-settings-read'],
                            env=settings_env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and result.stdout.strip() == '3 5 1 1', result.stderr
    nested_settings = dict(unavailable_video, NW_SCRAMBLE_SETTINGS_PATH='~/nested/options/scramble')
    subprocess.run([str(exe), '--selftest-scramble-settings-write'],
                   env=nested_settings, check=True, capture_output=True, timeout=20)
    assert (tmp / 'nested/options/scramble').read_text() == '12 15 0 1\n'
    data_settings = tmp / 'alternate profile' / 'data'
    data_env = dict(unavailable_video, NW_DATA_DIRECTORY=str(data_settings))
    subprocess.run([str(exe), '--selftest-scramble-settings-write'],
                   env=data_env, check=True, capture_output=True, timeout=20)
    assert (data_settings / 'scramble-options').read_text() == '12 15 0 1\n'
    subprocess.run([str(exe), '--selftest-numberology-result-lifecycle'],
                   env=data_env, check=True, capture_output=True, timeout=20)
    assert len(list((data_settings / 'results' / 'numberology').glob('*.json'))) == 1
    data_args = [str(exe), '--screen', 'scramble', '--dump', '--seed', '42']
    selected_settings = subprocess.run(
        [*data_args, '--datadir', str(data_settings)], env=unavailable_video,
        check=True, capture_output=True, timeout=20,
    )
    explicit_settings = subprocess.run(
        data_args, env=dict(unavailable_video, NW_SCRAMBLE_SETTINGS_PATH=str(data_settings / 'scramble-options')),
        check=True, capture_output=True, timeout=20,
    )
    assert selected_settings.stdout == explicit_settings.stdout
    named_options = data_settings / 'Other User-config.ini.scramble-options'
    named_env = dict(data_env, NW_SELECTED_USER='Other User')
    subprocess.run([str(exe), '--selftest-scramble-settings-write'],
                   env=named_env, check=True, capture_output=True, timeout=20)
    assert named_options.read_text() == '12 15 0 1\n'
    named_options.write_text('4 5 1 0\n', encoding='ascii')
    named = subprocess.run([*data_args, '--datadir', str(data_settings), '--user', 'Other User'],
                           env=unavailable_video, check=True, capture_output=True, timeout=20)
    explicit_named = subprocess.run(
        data_args, env=dict(unavailable_video, NW_SCRAMBLE_SETTINGS_PATH=str(named_options)),
        check=True, capture_output=True, timeout=20,
    )
    assert named.stdout == explicit_named.stdout and named.stdout != selected_settings.stdout
    assert (data_settings / 'scramble-options').read_text() == '12 15 0 1\n'
    python_profile = tmp / 'python task INI'
    python_profile.mkdir()
    legacy_ini = python_profile / 'Legacy User-config.ini'
    task_ini = {
        'crossword': ('SHOW_MISTAKES', 'no-mistakes', 'ADAPTIVE'),
        'scrabble': ('SHOW_PREMIUMS', 'no-premiums', 'ADAPTIVE'),
        'algebra': ('SHOW_WORKING', 'no-working', 'ADAPTIVE'),
        'scramble': ('SHOW_COUNT', 'no-count', 'ADAPTIVE'),
        'numberology': (None, None, 'ADVANCE'),
        'syllogism': ('SHOW_WORKING', 'no-working', 'ADAPTIVE'),
    }
    ini_lines = ['[DEFAULT]', 'SYLLOGISM_REAL_WORDS = False']
    for screen, (display_key, _, adaptive_key) in task_ini.items():
        key = screen.upper()
        ini_lines.extend((f'{key}_LEVEL = 4', f'{key}_TRIALS = 8', f'{key}_{adaptive_key} = False'))
        if display_key:
            ini_lines.append(f'{key}_{display_key} = False')
    legacy_ini.write_text('\n'.join(ini_lines) + '\n', encoding='utf-8')

    def task_ini_dump(screen, *options):
        return subprocess.run(
            [str(exe), '--screen', screen, '--datadir', str(python_profile), '--seed', '42',
             '--dump', *options], env=unavailable_video, capture_output=True, check=True, timeout=20,
        ).stdout

    for screen, (_, display_flag, _) in task_ini.items():
        task_flags = [f'--{screen}-level', '4', f'--{screen}-trials', '8', f'--{screen}-no-adaptive']
        if display_flag:
            task_flags.append(f'--{screen}-{display_flag}')
        if screen == 'syllogism':
            task_flags.append('--syllogism-invented-words')
        configured = task_ini_dump(screen, '--user', 'Legacy User')
        assert configured == task_ini_dump(screen, *task_flags), screen
        assert configured != task_ini_dump(screen), screen
    (python_profile / 'Legacy User-config.ini.scramble-options').write_text('7 5 0 0\n', encoding='ascii')
    assert task_ini_dump('scramble', '--user', 'Legacy User', '--scramble-level', '9') == task_ini_dump(
        'scramble', '--scramble-level', '9', '--scramble-trials', '5',
        '--scramble-no-count', '--scramble-no-adaptive',
    )
    with legacy_ini.open('a', encoding='utf-8') as profile:
        profile.write(
            'SUDOKU_LEVEL = 4\nSUDOKU_TRIALS = 5\nSUDOKU_SHOW_CLASHES = False\nSUDOKU_ADAPTIVE = False\n'
            'JIGSAW_PIECES = 16\nJIGSAW_PUZZLES = 5\nJIGSAW_ADAPTIVE = False\n'
            'JIGSAW_PREVIEW = False\nJIGSAW_MARK_PLACED = True\n'
            'GO_LEVEL = 4\nGO_TRIALS = 5\n'
            'WIRES_LEVEL = 4\nWIRES_ROUNDS = 8\nWIRES_ADAPTIVE = False\nWIRES_GRID = False\n'
        )
    puzzle_flags = {
        'sudoku': ['--sudoku-level', '4', '--sudoku-puzzles', '5',
                   '--sudoku-no-clashes', '--sudoku-no-adaptive'],
        'jigsaw': ['--jigsaw-side', '4', '--jigsaw-puzzles', '5',
                   '--jigsaw-no-adaptive', '--jigsaw-no-preview', '--jigsaw-mark-placed'],
        'go': ['--go-level', '4', '--go-trials', '5'],
        'crossed-wires': ['--crossed-wires-level', '4', '--crossed-wires-rounds', '8',
                          '--crossed-wires-no-adaptive', '--crossed-wires-no-grid'],
    }
    for screen, task_flags in puzzle_flags.items():
        configured = task_ini_dump(screen, '--user', 'Legacy User')
        assert configured == task_ini_dump(screen, *task_flags), screen
        assert configured != task_ini_dump(screen), screen
    assert task_ini_dump('jigsaw', '--user', 'Legacy User', '--jigsaw-side', '5') == task_ini_dump(
        'jigsaw', '--jigsaw-side', '5', *puzzle_flags['jigsaw'][2:],
    )
    video_ini = python_profile / 'Large Video-config.ini'
    for pieces, dimensions in ((2500, (58, 44)), (4000, (73, 55)), (1000000, (320, 240))):
        video_ini.write_text(f'[DEFAULT]\nVIDEO_JIGSAW_PIECES = {pieces}\n', encoding='utf-8')
        output = task_ini_dump('video-jigsaw', '--user', 'Large Video', '--trials', '2').decode()
        video_states = [ast.literal_eval(line[len('# state='):].split(' bytes=')[0])
                        for line in output.splitlines() if line.startswith('# state=')]
        assert len(video_states) == 2 and all((state[2], state[15]) == dimensions for state in video_states)
    jigsaw_ini = python_profile / 'Rectangle-config.ini'
    for pieces, columns, rows in ((2, 1, 2), (5, 2, 3), (12, 3, 4), (81, 9, 9), (1000, 32, 32), (1600, 40, 40), (2500, 50, 50), (4000, 63, 64), (1000000, 277, 277)):
        jigsaw_ini.write_text(f'[DEFAULT]\nJIGSAW_PIECES = {pieces}\n', encoding='utf-8')
        output = task_ini_dump('jigsaw', '--user', 'Rectangle', '--trials', '2').decode()
        started = [line for line in output.splitlines() if line.startswith('# state=')][1]
        state = ast.literal_eval(started.split('=', 1)[1].split(' bytes=')[0])
        assert (state[2], state[15]) == (columns, rows), state
        assert f'tiles {columns}x{rows}' in output
    theme_data = tmp / 'theme profile'
    theme_data.mkdir()
    theme_config = theme_data / 'config.ini'
    theme_args = [str(exe), '--screen', 'title', '--dump', '--datadir', str(theme_data)]

    def theme_dump(*flags):
        return subprocess.run([*theme_args, *flags], env=unavailable_video,
                              check=True, capture_output=True, timeout=20).stdout

    light = theme_dump()
    dark = theme_dump('--black-background')
    assert light != dark
    theme_config.write_bytes(b'[DEFAULT]\r\n; black_background = False\r\n'
                             b'BLACK_background : True\r\n'
                             b'[unrelated]\r\nBLACK_BACKGROUND = False\r\n')
    assert theme_dump() == dark
    theme_config.write_text('[DEFAULT]\nBLACK_BACKGROUND = False\n', encoding='utf-8')
    assert theme_dump() == light and theme_dump('--black-background') == dark
    theme_config.write_text('[DEFAULT]\nBLACK_BACKGROUND = True\nblack_background = False\n',
                            encoding='utf-8')
    assert theme_dump() == light
    theme_config.write_text('[DEFAULT]\nBLACK_BACKGROUND = False\n', encoding='utf-8')
    named_config = theme_data / 'François-config.ini'
    named_config.write_text('[DEFAULT]\nBLACK_BACKGROUND = True\n', encoding='utf-8')
    saved_profile = theme_data / 'defaults.ini'
    for protocol in (4, 5):
        saved_profile.write_bytes(pickle.dumps({'USER': 'François'}, protocol=protocol))
        assert theme_dump() == dark
    for user in ('DEFAULT', '../outside', 'A' * 256):
        saved_profile.write_bytes(pickle.dumps({'USER': user}))
        assert theme_dump() == light
    saved_profile.write_bytes(pickle.dumps({'USER': 'François'})[:-1])
    assert theme_dump() == light
    custom_config = theme_data / 'custom theme.ini'
    custom_config.write_text('[DEFAULT]\nBLACK_BACKGROUND = True\n', encoding='utf-8')
    assert theme_dump('--configfile', custom_config.name) == dark
    assert theme_dump(f'--configfile={custom_config}') == dark
    assert theme_dump('--configfile', 'config.ini', '--configfile', custom_config.name) == light
    saved_profile.write_bytes(pickle.dumps({'USER': 'François'}))
    assert theme_dump('--configfile', 'config.ini') == dark
    another_profile = theme_data / 'Other User-config.ini'
    another_profile.write_text('[DEFAULT]\nBLACK_BACKGROUND = False\n', encoding='utf-8')
    assert theme_dump('--user', 'Other User') == light
    assert theme_dump('--user=DEFAULT') == light
    assert theme_dump('--user', 'François') == dark
    assert pickle.loads(saved_profile.read_bytes()) == {'USER': 'François'}
    for invalid_user in ('', '../outside', 'nested\\name', 'bad:name', 'A' * 256):
        rejected = subprocess.run([*theme_args, f'--user={invalid_user}'], env=unavailable_video,
                                  capture_output=True, timeout=20)
        assert rejected.returncode == 2 and b'Invalid --user name' in rejected.stderr
    (theme_data / 'François-stats.txt').touch()
    for screen, mode, expected in (('title', '2', 'François'), ('taskhub', '1', 'Other User')):
        picker = subprocess.run(
            [str(exe), '--screen', screen, '--user', 'default', '--datadir', str(theme_data)],
            env=dict(env, NW_TEST_PROFILE_PICKER=mode, NW_TEST_SLOT='-1', NW_TEST_OPTION_SLOT='-1',
                     NW_TEST_DIRECT='1' if screen == 'title' else '0'),
            capture_output=True, text=True, timeout=20,
        )
        assert picker.returncode == 0 and 'SDL profile picker: PASS' in picker.stdout, (
            screen, picker.returncode, picker.stdout, picker.stderr,
        )
        assert pickle.loads(saved_profile.read_bytes()) == {'USER': expected}
    assert theme_dump() == light
    picker = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--user', 'default', '--datadir', str(theme_data)],
        env=dict(env, NW_TEST_PROFILE_PICKER='3', NW_TEST_SLOT='-1', NW_TEST_OPTION_SLOT='-1'),
        capture_output=True, text=True, timeout=20,
    )
    assert picker.returncode == 0 and 'SDL profile picker: PASS' in picker.stdout, picker.stderr
    assert pickle.loads(saved_profile.read_bytes()) == {'USER': 'Zoë X'}
    assert (theme_data / 'Zoë X-stats.txt').read_bytes() == b''
    (theme_data / 'Zoë X-config.ini').write_text('[DEFAULT]\nBLACK_BACKGROUND = True\n', encoding='utf-8')
    assert theme_dump() == dark
    saved_profile.write_bytes(pickle.dumps({'USER': 'François'}))
    named_config.write_text('[DEFAULT]\nSKIP_TITLE_SCREEN = True\n', encoding='utf-8')
    skip_args = [str(exe), '--dump', '--datadir', str(theme_data)]
    default_route = subprocess.run(skip_args, env=unavailable_video, check=True,
                                   capture_output=True, timeout=20)
    hub_route = subprocess.run([*skip_args, '--screen', 'taskhub'], env=unavailable_video,
                               check=True, capture_output=True, timeout=20)
    assert default_route.stdout == hub_route.stdout
    assert theme_dump() == light and theme_dump() != hub_route.stdout
    named_config.write_text('[DEFAULT]\nWINDOW_WIDTH = 802\nWINDOW_HEIGHT = 530\n',
                            encoding='utf-8')
    window_args = [str(exe), '--screen', 'title', '--datadir', str(theme_data)]
    window_env = dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT='-1', NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_WINDOW_CAPTION='Neural Workshop 5.0 - François')
    for overrides, width in (([], '802'), (['--width', '720'], '720')):
        resized = subprocess.run(
            [*window_args, *overrides], env=dict(window_env, NW_TEST_WIDTH=width, NW_TEST_HEIGHT='530'),
            capture_output=True, timeout=20,
        )
        assert resized.returncode == 0 and b'SDL event replay: PASS' in resized.stdout, resized.stderr
    named_config.write_text('[DEFAULT]\nWINDOW_WIDTH = 12\nWINDOW_HEIGHT = invalid\n',
                            encoding='utf-8')
    clamped = subprocess.run(
        window_args, env=dict(window_env, NW_TEST_WIDTH='640', NW_TEST_HEIGHT='684'),
        check=True, capture_output=True, timeout=20,
    )
    assert b'SDL event replay: PASS' in clamped.stdout
    for vsync_args, requests in (([], str(int(sys.platform == 'darwin'))), (['--vsync'], '1')):
        synced = subprocess.run(
            [*window_args, *vsync_args], env=dict(window_env, NW_TEST_VSYNC=requests),
            check=True, capture_output=True, timeout=20,
        )
        assert b'SDL event replay: PASS' in synced.stdout
    named_config.write_text('[DEFAULT]\nWINDOW_FULLSCREEN = True\n', encoding='utf-8')
    for screen, requests in (('title', '1'), ('sudoku', '2')):
        fullscreen_replay = subprocess.run(
            [str(exe), '--screen', screen, '--datadir', str(theme_data)],
            env=dict(window_env, NW_TEST_FULLSCREEN=requests),
            check=True, capture_output=True, timeout=20,
        )
        assert b'SDL event replay: PASS' in fullscreen_replay.stdout
    hidden_env = dict(window_env, NW_TEST_HEADLESS='1', NW_TEST_VSYNC='0')
    hidden = subprocess.run([*window_args, '--headless'], env=hidden_env,
                            check=True, capture_output=True, timeout=20)
    assert b'SDL event replay: PASS' in hidden.stdout
    hidden = subprocess.run(window_args, env=dict(hidden_env, NW_HEADLESS='YeS'),
                            check=True, capture_output=True, timeout=20)
    assert b'SDL event replay: PASS' in hidden.stdout
    named_config.write_text('[DEFAULT]\nHEADLESS = True\nWINDOW_FULLSCREEN = True\n',
                            encoding='utf-8')
    hidden = subprocess.run(window_args, env=hidden_env, check=True, capture_output=True, timeout=20)
    assert b'SDL event replay: PASS' in hidden.stdout
    no_display = dict(hidden_env, NW_TEST_VIDEO_DRIVER='dummy')
    for key in ('SDL_VIDEO_DRIVER', 'SDL_VIDEODRIVER', 'DISPLAY', 'WAYLAND_DISPLAY'):
        no_display.pop(key, None)
    hidden = subprocess.run(window_args, env=no_display, check=True, capture_output=True, timeout=20)
    assert b'SDL event replay: PASS' in hidden.stdout
    rejected_driver = subprocess.run(
        window_args, env=dict(no_display, SDL_VIDEO_DRIVER='nw-invalid-driver'),
        capture_output=True, text=True, timeout=20,
    )
    assert rejected_driver.returncode == 1 and 'SDL_Init failed' in rejected_driver.stderr
    for flag in ('--help', '-h'):
        result = subprocess.run([str(exe), '--screen', 'marble', flag], env=unavailable_video,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'Usage:' in result.stdout
        assert '--marble-start-rung VALUE' in result.stdout and '--black-background' in result.stdout
        assert '  you-are-here\n' in result.stdout and '  3d-maze (alias for you-are-here)' in result.stdout
        assert '  taskhub\n' in result.stdout and '  overrun\n' in result.stdout
    for option in ('--trials', '--marble-start-rung'):
        rejected = subprocess.run([str(exe), '--screen', 'title', option, 'bad'],
                                  env=unavailable_video, capture_output=True, text=True, timeout=20)
        assert rejected.returncode == 2 and f'Invalid {option} value' in rejected.stderr, rejected.stderr
    for invalid in (['--unknown'], ['unexpected-positional'], ['--seed'],
                    ['--scramble-index', '--black-background']):
        result = subprocess.run([str(exe), '--dump', *invalid], env=unavailable_video,
                                capture_output=True, timeout=20)
        assert result.returncode == 2 and not result.stdout, (invalid, result.stderr)
    for screen in ('you-are-here', 'sokoban'):
        for seed, expected in (('invalid', 2), ('-42', 1)):
            result = subprocess.run([str(exe), '--screen', screen, '--seed', seed],
                                    env=unavailable_video, capture_output=True, text=True, timeout=20)
            assert result.returncode == expected, (screen, seed, result.returncode, result.stderr)
    dump_screens = (
        ('you-are-here', 3), ('sokoban', 3), ('marble', 13), ('tetris', 9), ('jigsaw', 16), ('video-jigsaw', 16),
        ('sudoku', 21), ('go', 13), ('crossed-wires', 27),
        ('count', 16), ('mr-time', 20), ('graph-mapping', 22), ('matrix-reasoning', 22),
    )
    for screen, fields in dump_screens:
        args = [str(exe), '--screen', screen, '--dump', '--trials', '2', '--seed', '42']
        result = subprocess.run(args, env=unavailable_video, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, (screen, result.stderr)
        states = [ast.literal_eval(line[len('# state='):].split(' bytes=')[0])
                  for line in result.stdout.splitlines() if line.startswith('# state=')]
        assert len(states) == 2 and all(len(state) == fields for state in states), (screen, states)
        assert states[0][0] == 0 and states[1][0] == 1, (screen, states)
        if screen == 'count':
            assert all(state[4] == 5 for state in states), states
        if screen == 'mr-time':
            assert all(state[5] == 15 and state[7] == 0 for state in states), states
    trivia_profile = tmp / 'trivia-profile'
    if os.name == 'nt':
        trivia_folder = 'Brain Workshop/data/trivia'
        trivia_env = dict(unavailable_video, APPDATA=str(trivia_profile))
    else:
        trivia_folder = ('Library/Application Support/Brain Workshop/data/trivia'
                         if sys.platform == 'darwin' else '.brainworkshop/data/trivia')
        trivia_env = dict(unavailable_video, HOME=str(trivia_profile))
    trivia_index = trivia_profile / trivia_folder / 'questions.tsv'
    trivia_index.parent.mkdir(parents=True)
    questions = [
        ('Which fictional mascot leads this exercise?', 'Aardvark', ('aardvark', 'barrow pig')),
        ('Which fictional mascot guards the workshop?', 'Bison',
         tuple([f'alias {number:02}' for number in range(11)] + ['bison', 'chinchilla'])),
        ('Which fictional mascot visits the museum?', 'Chinchilla', ('chinchilla', 'rodent')),
    ]
    trivia_rows = ''.join(
        f'{question}\t{answer}\tword\t{"|".join(aliases)}\n'
        for question, answer, aliases in questions
    )
    trivia_index.write_text('malformed\n' + trivia_rows, encoding='utf-8')
    trivia_args = [str(exe), '--screen', 'trivia', '--dump', '--seed', '42', '--trials', '2']
    indexed = subprocess.run(trivia_args, env=trivia_env, capture_output=True, text=True,
                             check=True, timeout=20).stdout
    trivia_states = [ast.literal_eval(line[len('# state='):].split(' bytes=')[0])
                     for line in indexed.splitlines() if line.startswith('# state=')]
    started = trivia_states[1]
    assert started[0] == 1 and started[12] == len(questions), trivia_states
    bank = trivia_reference['Bank']([
        trivia_reference['Question'](question, answer, 'word', frozenset(aliases))
        for question, answer, aliases in questions
    ])
    expected = trivia_reference['generate'](1, started[16], bank)
    assert expected is not None and started[8] == expected.answer, started
    assert expected.question.answer == 'Bison' and 'Chinchilla' not in expected.options
    assert f'text={expected.question.asked} x=' in indexed, indexed
    for position, option in enumerate(expected.options, 1):
        assert f'text={position}. {option} x=' in indexed, indexed
    trivia_index.write_text('malformed\n', encoding='utf-8')
    fallback = subprocess.run(trivia_args, env=trivia_env, capture_output=True, text=True,
                              check=True, timeout=20).stdout
    assert '120 questions in the pool' in fallback and 'fictional mascot' not in fallback
    alternate_data = tmp / 'alternate trivia data'
    alternate_index = alternate_data / 'trivia' / 'questions.tsv'
    alternate_index.parent.mkdir(parents=True)
    alternate_index.write_text(trivia_rows, encoding='utf-8')
    for override in (['--datadir', str(alternate_data)], [f'--datadir={alternate_data}'],
                     ['--datadir', str(alternate_data), '--datadir', str(trivia_profile)]):
        redirected = subprocess.run([*trivia_args, *override], env=trivia_env, capture_output=True,
                                    text=True, check=True, timeout=20)
        assert redirected.stdout == indexed, redirected.stdout

    args = [str(exe), '--screen', 'marble', '--dump', '--trials', '2', '--seed']
    def dump_seed(value):
        return subprocess.run([*args, value], env=unavailable_video, capture_output=True, timeout=20)
    plain_seed = dump_seed('-42')
    assert plain_seed.returncode == 0
    attached = subprocess.run([str(exe), '--screen=marble', '--dump', '--trials=2', '--seed=-42'],
                              env=unavailable_video, capture_output=True, timeout=20)
    assert attached.returncode == 0 and attached.stdout == plain_seed.stdout, attached.stderr
    corpus = tmp / 'sentences.txt'
    corpus.write_text('they go to the farm that he had bought\n')
    corpus_args = [str(exe), '--screen=scramble', '--dump', '--trials=2']
    absolute = subprocess.run([*corpus_args, f'--scramble-sentences={corpus}'],
                              env=unavailable_video, capture_output=True, timeout=20)
    assert absolute.returncode == 0, absolute.stderr
    for relative in (['--scramble-sentences', '~/sentences.txt'], ['--scramble-sentences=~/sentences.txt']):
        expanded = subprocess.run([*corpus_args, *relative], env=unavailable_video,
                                  capture_output=True, timeout=20)
        assert expanded.returncode == 0 and expanded.stdout == absolute.stdout, expanded.stderr
    path_env = dict(unavailable_video, NW_TEST_DIRECT='1', NW_TEST_SLOT='-1',
                    NW_TEST_OPTION_SLOT='-1')
    path = subprocess.run([str(exe), '--screenshot=--dump'], cwd=tmp, env=path_env,
                          capture_output=True, text=True, timeout=20)
    if 'PNG screenshots require SDL' not in path.stderr:
        assert path.returncode == 0, path.stderr
        assert (tmp / '--dump').read_bytes().startswith(b'\x89PNG')
    first_path, last_path = tmp / 'first.png', tmp / 'last.png'
    repeated = subprocess.run([str(exe), '--screenshot', str(first_path), '--screenshot', str(last_path)],
                              env=path_env, capture_output=True, text=True, timeout=20)
    if 'PNG screenshots require SDL' not in repeated.stderr:
        assert repeated.returncode == 0, repeated.stderr
        assert last_path.read_bytes().startswith(b'\x89PNG')
        assert not first_path.exists()
    dump_with_path = subprocess.run([str(exe), '--screenshot', str(first_path), '--dump'],
                                    env=unavailable_video, capture_output=True, timeout=20)
    assert dump_with_path.returncode == 0 and dump_with_path.stdout
    assert not first_path.exists()
    abbreviated = subprocess.run([str(exe), '--dum', '--heig=684', '--see', '42', '--'],
                                 env=unavailable_video, capture_output=True, timeout=20)
    assert abbreviated.returncode == 0 and abbreviated.stdout == dump_with_path.stdout
    for tail in ('--help', '-h', '--dum', 'title'):
        rejected = subprocess.run([str(exe), '--dump', '--', tail], env=unavailable_video,
                                  capture_output=True, timeout=20)
        assert rejected.returncode == 2 and not rejected.stdout, tail
    for flag in ('--help', '-h', '-output.png'):
        rejected = subprocess.run([str(exe), '--dump', '--screenshot', flag],
                                  env=unavailable_video, capture_output=True, timeout=20)
        assert rejected.returncode == 2 and not rejected.stdout, flag
    for path_option in ('--screenshot=-h', '--screenshot=-output.png'):
        accepted = subprocess.run([str(exe), '--dump', path_option],
                                  env=unavailable_video, capture_output=True, timeout=20)
        assert accepted.returncode == 0 and accepted.stdout == dump_with_path.stdout
    for bad_option in ('--seed=', '--dump=yes', '--unknown=3', '--scr=title', '--tria=2'):
        rejected = subprocess.run([str(exe), '--dump', bad_option], env=unavailable_video,
                                  capture_output=True, timeout=20)
        assert rejected.returncode == 2 and not rejected.stdout, bad_option
    assert dump_seed(' -4_2\t').stdout == plain_seed.stdout
    for bad_seed in ('_42', '4__2', '42_', '4 2', '-9_223_372_036_854_775_809'):
        assert dump_seed(bad_seed).returncode == 2, bad_seed
    for screen in ('go', 'syllogism', 'algebra', 'scramble', 'scrabble', 'crossword', 'numberology'):
        args = [str(exe), '--screen', screen, '--dump', f'--{screen}-level']
        def dump_level(level):
            return subprocess.run([*args, level], env=unavailable_video, capture_output=True, timeout=20)

        plain_level = dump_level('4')
        formatted_level = dump_level(' +0_4\t')
        assert plain_level.returncode == formatted_level.returncode == 0, screen
        assert plain_level.stdout == formatted_level.stdout, screen
        for bad_level in ('_4', '4_', '0__4', '0 4'):
            assert dump_level(bad_level).returncode == 2, (screen, bad_level)
        if screen != 'numberology':
            assert dump_level('99').returncode == 2, screen

    def literal(file, name):
        tree = ast.parse((root / 'test' / file).read_text())
        return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
    cases = literal('sdl_hub_defaults_native_test.py', 'cases')
    frames = literal('sdl_frame_dispatch_native_test.py', 'names') + ('syllogism', 'scramble', 'scrabble', 'hanoi', 'salesman', 'ninarow', 'maze', 'sokoban3d', 'cookie_thief', 'video_sequence', 'hidden_rule', 'hidden_wiring', 'triage', 'delay', 'stop_and_switch', 'hold_it', 'notebook', 'where_was_it', 'which_is_nearer', 'same_or_mirror', 'point_of_view')
    (theme_data / 'Other User-config.ini.scramble-options').write_text('4 5 1 0\n', encoding='ascii')
    picker = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--user', 'default', '--datadir', str(theme_data)],
        env=dict(env, NW_TEST_PROFILE_PICKER='4', NW_TEST_SLOT='-1', NW_TEST_OPTION_SLOT='-1',
                 NW_TEST_PROFILE_TASK_SLOT=str(frames.index('scramble'))),
        capture_output=True, text=True, timeout=20,
    )
    assert picker.returncode == 0 and 'SDL profile picker: PASS' in picker.stdout, picker.stderr
    saved_profile.write_bytes(pickle.dumps({'USER': 'François'}))
    routes = [(category, selected, name) for category, selected, name, _ in cases]
    routes += [(4, 2, 'hidden_rule'), (4, 3, 'hidden_wiring'), (4, 4, 'jigsaw'),
               (4, 6, 'video_sequence'), (4, 7, 'sudoku'), (4, 8, 'go'), (4, 9, 'crossed_wires'),
               (4, 10, 'crossword'), (4, 11, 'scrabble'), (4, 12, 'scramble'),
               (4, 13, 'algebra'), (4, 14, 'numberology'), (4, 15, 'syllogism'), (7, 7, 'triage'), (6, 1, 'stop_and_switch'), (6, 2, 'delay'), (6, 3, 'hold_it'), (1, 3, 'notebook'), (1, 4, 'where_was_it'), (3, 4, 'same_or_mirror'), (3, 5, 'which_is_nearer'), (3, 7, 'point_of_view')]
    option_slots = {'numberology': 7, 'algebra': 14, 'scramble': 21, 'scrabble': 28, 'syllogism': 0, 'video_sequence': -1, 'hidden_rule': -1, 'hidden_wiring': -1, 'triage': -1, 'delay': -1, 'stop_and_switch': -1, 'hold_it': -1, 'notebook': -1, 'where_was_it': -1, 'which_is_nearer': -1, 'same_or_mirror': -1, 'point_of_view': -1}
    assert len(routes) == 49
    hidden_rule = subprocess.run(
        [str(exe), '--screen', 'hidden-rule', '--width', '912', '--height', '684'],
        env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('hidden_rule')),
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_HIDDEN_RULE='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hidden_rule.returncode == 0 and 'SDL event replay: PASS' in hidden_rule.stdout, hidden_rule.stderr
    hidden_wiring = subprocess.run(
        [str(exe), '--screen', 'hidden-wiring', '--width', '912', '--height', '684'],
        env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('hidden_wiring')),
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_HIDDEN_WIRING='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hidden_wiring.returncode == 0 and 'SDL event replay: PASS' in hidden_wiring.stdout, hidden_wiring.stderr
    triage_profile = tmp / 'triage-config.ini'
    triage_profile.write_text('[DEFAULT]\nTRIAGE_RUNG = 5\nTRIAGE_TRIALS = 5\nTRIAGE_ADAPTIVE = True\n')
    triage_env = dict(env, NW_MEDIA_CONFIGFILE=str(triage_profile), NW_TEST_DIRECT='1',
                      NW_TEST_SLOT=str(frames.index('triage')), NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1')
    triage = subprocess.run([str(exe), '--screen', 'triage'], env=triage_env,
                            capture_output=True, text=True, timeout=20)
    assert triage.returncode == 0 and 'SDL event replay: PASS' in triage.stdout, triage.stderr
    assert triage_profile.with_name(triage_profile.name + '.triage-options').read_text() == (
        '[DEFAULT]\nTRIAGE_RUNG = 8\nTRIAGE_TRIALS = 3\nTRIAGE_ADAPTIVE = False\n')
    triage_dump = subprocess.run([str(exe), '--screen', 'triage', '--dump'],
                                  env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(triage_profile)),
                                  check=True, capture_output=True, text=True, timeout=20)
    state = next(line for line in triage_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 8, 0, 3)
    triage_round_profile = tmp / 'triage-round-config.ini'
    triage_round_profile.write_text('[DEFAULT]\nTRIAGE_RUNG = 1\nTRIAGE_TRIALS = 1\n')
    triage_round = subprocess.run(
        [str(exe), '--screen', 'triage', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(triage_round_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='46',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_TRIAGE='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert triage_round.returncode == 0 and 'SDL event replay: PASS' in triage_round.stdout, triage_round.stderr
    notebook_profile = tmp / 'notebook-config.ini'
    notebook_profile.write_text('[DEFAULT]\nNOTEBOOK_RUNG = 3\nNOTEBOOK_TRIALS = 3\nNOTEBOOK_ADAPTIVE = True\n')
    notebook_options = subprocess.run(
        [str(exe), '--screen', 'notebook'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(notebook_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='50',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert notebook_options.returncode == 0 and 'SDL event replay: PASS' in notebook_options.stdout, notebook_options.stderr
    assert notebook_profile.with_name(notebook_profile.name + '.notebook-options').read_text() == (
        '[DEFAULT]\nNOTEBOOK_RUNG = 6\nNOTEBOOK_TRIALS = 1\nNOTEBOOK_ADAPTIVE = False\n')
    notebook_dump = subprocess.run(
        [str(exe), '--screen', 'notebook', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(notebook_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in notebook_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 6, 0, 1)
    notebook_round = tmp / 'notebook-round.ini'
    notebook_round.write_text('[DEFAULT]\nNOTEBOOK_RUNG = 1\nNOTEBOOK_TRIALS = 1\n')
    played = subprocess.run(
        [str(exe), '--screen', 'notebook', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(notebook_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='50',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_NOTEBOOK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    rooms_profile = tmp / 'where-was-it-config.ini'
    rooms_profile.write_text('[DEFAULT]\nWHERE_WAS_IT_RUNG = 16\nWHERE_WAS_IT_TRIALS = 4\nWHERE_WAS_IT_ADAPTIVE = False\n')
    rooms_options = subprocess.run(
        [str(exe), '--screen', 'where-was-it'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(rooms_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='51',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert rooms_options.returncode == 0 and 'SDL event replay: PASS' in rooms_options.stdout, rooms_options.stderr
    assert rooms_profile.with_name(rooms_profile.name + '.where-was-it-options').read_text() == (
        '[DEFAULT]\nWHERE_WAS_IT_RUNG = 20\nWHERE_WAS_IT_TRIALS = 1\nWHERE_WAS_IT_ADAPTIVE = True\n')
    rooms_dump = subprocess.run(
        [str(exe), '--screen', 'where_was_it', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(rooms_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in rooms_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 20, 0, 1)
    played = subprocess.run(
        [str(exe), '--screen', 'where-was-it', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(rooms_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='51',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_ROOMS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    nearer_profile = tmp / 'which-is-nearer-config.ini'
    nearer_profile.write_text('[DEFAULT]\nWHICH_IS_NEARER_RUNG = 16\nWHICH_IS_NEARER_TRIALS = 6\nWHICH_IS_NEARER_ADAPTIVE = False\n')
    nearer_options = subprocess.run(
        [str(exe), '--screen', 'which-is-nearer'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(nearer_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='52',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert nearer_options.returncode == 0 and 'SDL event replay: PASS' in nearer_options.stdout, nearer_options.stderr
    assert nearer_profile.with_name(nearer_profile.name + '.which-is-nearer-options').read_text() == (
        '[DEFAULT]\nWHICH_IS_NEARER_RUNG = 20\nWHICH_IS_NEARER_TRIALS = 1\nWHICH_IS_NEARER_ADAPTIVE = True\n')
    nearer_dump = subprocess.run(
        [str(exe), '--screen', 'which_is_nearer', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(nearer_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in nearer_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 20, 0, 1)
    played = subprocess.run(
        [str(exe), '--screen', 'which-is-nearer', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(nearer_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='52',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_NEARER='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    mirror_profile = tmp / 'same-or-mirror-config.ini'
    mirror_profile.write_text('[DEFAULT]\nSAME_OR_MIRROR_RUNG = 21\nSAME_OR_MIRROR_TRIALS = 6\nSAME_OR_MIRROR_ADAPTIVE = False\n')
    mirror_options = subprocess.run(
        [str(exe), '--screen', 'same-or-mirror'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(mirror_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='53',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert mirror_options.returncode == 0 and 'SDL event replay: PASS' in mirror_options.stdout, mirror_options.stderr
    assert mirror_profile.with_name(mirror_profile.name + '.same-or-mirror-options').read_text() == (
        '[DEFAULT]\nSAME_OR_MIRROR_RUNG = 25\nSAME_OR_MIRROR_TRIALS = 1\nSAME_OR_MIRROR_ADAPTIVE = True\n')
    mirror_dump = subprocess.run(
        [str(exe), '--screen', 'same_or_mirror', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(mirror_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in mirror_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 25, 0, 1)
    mirror_pair = tmp / 'same-or-mirror-pair.ini'
    mirror_pair.write_text('[DEFAULT]\nSAME_OR_MIRROR_RUNG = 1\nSAME_OR_MIRROR_TRIALS = 1\n')
    for mode, profile in ((1, mirror_pair), (2, mirror_profile)):
        played = subprocess.run(
            [str(exe), '--screen', 'same-or-mirror', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='53',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_MIRROR=str(mode), NW_TEST_CLOSE_WINDOW='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    pov_profile = tmp / 'point-of-view-config.ini'
    pov_profile.write_text('[DEFAULT]\nPOINT_OF_VIEW_RUNG = 16\nPOINT_OF_VIEW_TRIALS = 5\nPOINT_OF_VIEW_ADAPTIVE = False\n')
    pov_options = subprocess.run(
        [str(exe), '--screen', 'point-of-view'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(pov_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='54',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pov_options.returncode == 0 and 'SDL event replay: PASS' in pov_options.stdout, pov_options.stderr
    assert pov_profile.with_name(pov_profile.name + '.point-of-view-options').read_text() == (
        '[DEFAULT]\nPOINT_OF_VIEW_RUNG = 20\nPOINT_OF_VIEW_TRIALS = 1\nPOINT_OF_VIEW_ADAPTIVE = True\n')
    pov_dump = subprocess.run(
        [str(exe), '--screen', 'point_of_view', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(pov_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in pov_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 20, 0, 1)
    pov_pair = tmp / 'point-of-view-pair.ini'
    pov_pair.write_text('[DEFAULT]\nPOINT_OF_VIEW_RUNG = 1\nPOINT_OF_VIEW_TRIALS = 1\n')
    for mode, profile in ((1, pov_pair), (2, pov_profile)):
        played = subprocess.run(
            [str(exe), '--screen', 'point-of-view', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='54',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_POV=str(mode), NW_TEST_CLOSE_WINDOW='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    inside_profile = tmp / 'inside-or-out.ini'
    inside_profile.write_text('[DEFAULT]\nINSIDE_RUNG = 20\nINSIDE_TRIALS = 5\nINSIDE_ADAPTIVE = False\n')
    inside_options = subprocess.run(
        [str(exe), '--screen', 'inside-or-out'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(inside_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='55',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert inside_options.returncode == 0 and 'SDL event replay: PASS' in inside_options.stdout, inside_options.stderr
    assert inside_profile.with_name(inside_profile.name + '.inside-or-out-options').read_text() == (
        '[DEFAULT]\nINSIDE_RUNG = 25\nINSIDE_TRIALS = 3\nINSIDE_ADAPTIVE = True\n')
    inside_dump = subprocess.run(
        [str(exe), '--screen', 'inside_or_out', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(inside_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in inside_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 25, 0, 3)
    for mode, rung in ((1, 1), (2, 25)):
        profile = tmp / f'inside-{rung}.ini'
        profile.write_text(f'[DEFAULT]\nINSIDE_RUNG = {rung}\nINSIDE_TRIALS = 1\n')
        played = subprocess.run(
            [str(exe), '--screen', 'inside-or-out', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='55',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_INSIDE=str(mode), NW_TEST_CLOSE_WINDOW='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    touching_profile = tmp / 'touching.ini'
    touching_profile.write_text('[DEFAULT]\nTOUCHING_RUNG = 20\nTOUCHING_TRIALS = 5\nTOUCHING_ADAPTIVE = False\n')
    touching_options = subprocess.run(
        [str(exe), '--screen', 'touching'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(touching_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='56',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert touching_options.returncode == 0 and 'SDL event replay: PASS' in touching_options.stdout, touching_options.stderr
    assert touching_profile.with_name(touching_profile.name + '.touching-options').read_text() == (
        '[DEFAULT]\nTOUCHING_RUNG = 25\nTOUCHING_TRIALS = 3\nTOUCHING_ADAPTIVE = True\n')
    touching_dump = subprocess.run(
        [str(exe), '--screen', 'touching', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(touching_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in touching_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 25, 0, 3)
    for mode, rung in ((1, 1), (2, 10)):
        profile = tmp / f'touching-{rung}.ini'
        profile.write_text(f'[DEFAULT]\nTOUCHING_RUNG = {rung}\nTOUCHING_TRIALS = 1\n')
        played = subprocess.run(
            [str(exe), '--screen', 'touching', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='56',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_TOUCHING=str(mode), NW_TEST_CLOSE_WINDOW='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    crossings_profile = tmp / 'crossings.ini'
    crossings_profile.write_text('[DEFAULT]\nCROSSINGS_RUNG = 20\nCROSSINGS_TRIALS = 5\nCROSSINGS_ADAPTIVE = False\n')
    crossings_options = subprocess.run(
        [str(exe), '--screen', 'crossings'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(crossings_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='57',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert crossings_options.returncode == 0 and 'SDL event replay: PASS' in crossings_options.stdout, crossings_options.stderr
    assert crossings_profile.with_name(crossings_profile.name + '.crossings-options').read_text() == (
        '[DEFAULT]\nCROSSINGS_RUNG = 25\nCROSSINGS_TRIALS = 3\nCROSSINGS_ADAPTIVE = True\n')
    crossings_dump = subprocess.run(
        [str(exe), '--screen', 'crossings', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(crossings_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in crossings_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 25, 0, 3)
    for mode, rung in ((1, 1), (2, 10)):
        profile = tmp / f'crossings-{rung}.ini'
        profile.write_text(f'[DEFAULT]\nCROSSINGS_RUNG = {rung}\nCROSSINGS_TRIALS = 1\n')
        played = subprocess.run(
            [str(exe), '--screen', 'crossings', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='57',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_CROSSINGS=str(mode), NW_TEST_CLOSE_WINDOW='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    hold_profile = tmp / 'hold-it-config.ini'
    hold_profile.write_text('[DEFAULT]\nHOLDIT_RUNG = 4\nHOLDIT_TRIALS = 5\nHOLDIT_ADAPTIVE = True\n')
    hold_options = subprocess.run(
        [str(exe), '--screen', 'hold-it'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(hold_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='49',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hold_options.returncode == 0 and 'SDL event replay: PASS' in hold_options.stdout, hold_options.stderr
    assert hold_profile.with_name(hold_profile.name + '.hold-it-options').read_text() == (
        '[DEFAULT]\nHOLDIT_RUNG = 7\nHOLDIT_TRIALS = 3\nHOLDIT_ADAPTIVE = False\n')
    hold_dump = subprocess.run(
        [str(exe), '--screen', 'hold-it', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(hold_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    state = next(line for line in hold_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 7, 0, 3)
    hold_round = tmp / 'hold-it-round.ini'
    hold_round.write_text('[DEFAULT]\nHOLDIT_RUNG = 1\nHOLDIT_TRIALS = 1\n')
    for release in (1, 2):
        held = subprocess.run(
            [str(exe), '--screen', 'hold-it', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(hold_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='49',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_HOLD_IT_CLOCK=str(release), NW_TEST_CLOSE_WINDOW='1',
                     SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert held.returncode == 0 and 'SDL event replay: PASS' in held.stdout, held.stderr

    time_it_profile = tmp / 'time-it-config.ini'
    time_it_profile.write_text('[DEFAULT]\nTIMEIT_RUNG = 4\nTIMEIT_TRIALS = 5\nTIMEIT_ADAPTIVE = True\n')
    options = subprocess.run(
        [str(exe), '--screen', 'time-it'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(time_it_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='58',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, options.stderr
    assert time_it_profile.with_name(time_it_profile.name + '.time-it-options').read_text() == (
        '[DEFAULT]\nTIMEIT_RUNG = 7\nTIMEIT_TRIALS = 3\nTIMEIT_ADAPTIVE = False\n')
    time_it_round = tmp / 'time-it-round.ini'
    time_it_round.write_text('[DEFAULT]\nTIMEIT_RUNG = 1\nTIMEIT_TRIALS = 1\n')
    timed = subprocess.run(
        [str(exe), '--screen', 'time_it', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(time_it_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='58',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_TIME_IT_CLOCK='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert timed.returncode == 0 and 'SDL event replay: PASS' in timed.stdout, timed.stderr

    balance_profile = tmp / 'balance-config.ini'
    balance_profile.write_text('[DEFAULT]\nBALANCE_RUNG = 4\nBALANCE_TRIALS = 5\nBALANCE_ADAPTIVE = True\n')
    balance_options = subprocess.run(
        [str(exe), '--screen', 'balance'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(balance_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='59',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert balance_options.returncode == 0 and 'SDL event replay: PASS' in balance_options.stdout, balance_options.stderr
    assert balance_profile.with_name(balance_profile.name + '.balance-options').read_text() == (
        '[DEFAULT]\nBALANCE_RUNG = 7\nBALANCE_TRIALS = 3\nBALANCE_ADAPTIVE = False\n')
    balance_round = tmp / 'balance-round.ini'
    balance_round.write_text('[DEFAULT]\nBALANCE_RUNG = 1\nBALANCE_TRIALS = 1\n')
    balance = subprocess.run(
        [str(exe), '--screen', 'balance', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(balance_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='59',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_BALANCE_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert balance.returncode == 0 and 'SDL event replay: PASS' in balance.stdout, balance.stderr

    juggler_profile = tmp / 'juggler-config.ini'
    juggler_profile.write_text('[DEFAULT]\nJUGGLER_RUNG = 4\nJUGGLER_TRIALS = 5\nJUGGLER_ADAPTIVE = True\n')
    juggler_options = subprocess.run(
        [str(exe), '--screen', 'juggler'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(juggler_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='60',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert juggler_options.returncode == 0 and 'SDL event replay: PASS' in juggler_options.stdout, juggler_options.stderr
    assert juggler_profile.with_name(juggler_profile.name + '.juggler-options').read_text() == (
        '[DEFAULT]\nJUGGLER_RUNG = 7\nJUGGLER_TRIALS = 3\nJUGGLER_ADAPTIVE = False\n')
    juggler_round = tmp / 'juggler-round.ini'
    juggler_round.write_text('[DEFAULT]\nJUGGLER_RUNG = 1\nJUGGLER_TRIALS = 1\n')
    juggler = subprocess.run(
        [str(exe), '--screen', 'juggler', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(juggler_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='60',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_JUGGLER_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert juggler.returncode == 0 and 'SDL event replay: PASS' in juggler.stdout, juggler.stderr

    lander_profile = tmp / 'lander-config.ini'
    lander_profile.write_text('[DEFAULT]\nLANDER_RUNG = 4\nLANDER_TRIALS = 5\nLANDER_ADAPTIVE = True\n')
    lander_options = subprocess.run(
        [str(exe), '--screen', 'lander'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(lander_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='61',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert lander_options.returncode == 0 and 'SDL event replay: PASS' in lander_options.stdout, lander_options.stderr
    assert lander_profile.with_name(lander_profile.name + '.lander-options').read_text() == (
        '[DEFAULT]\nLANDER_RUNG = 7\nLANDER_TRIALS = 3\nLANDER_ADAPTIVE = False\n')
    lander_round = tmp / 'lander-round.ini'
    lander_round.write_text('[DEFAULT]\nLANDER_RUNG = 1\nLANDER_TRIALS = 1\n')
    lander = subprocess.run(
        [str(exe), '--screen', 'lander', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(lander_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='61',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_LANDER_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert lander.returncode == 0 and 'SDL event replay: PASS' in lander.stdout, lander.stderr

    glider_profile = tmp / 'glider-config.ini'
    glider_profile.write_text('[DEFAULT]\nGLIDER_RUNG = 4\nGLIDER_TRIALS = 5\nGLIDER_ADAPTIVE = True\n')
    glider_options = subprocess.run(
        [str(exe), '--screen', 'glider'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(glider_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='63',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert glider_options.returncode == 0 and 'SDL event replay: PASS' in glider_options.stdout, glider_options.stderr
    assert glider_profile.with_name(glider_profile.name + '.glider-options').read_text() == (
        '[DEFAULT]\nGLIDER_RUNG = 7\nGLIDER_TRIALS = 3\nGLIDER_ADAPTIVE = False\n')
    glider_round = tmp / 'glider-round.ini'
    glider_round.write_text('[DEFAULT]\nGLIDER_RUNG = 1\nGLIDER_TRIALS = 1\n')
    glider = subprocess.run(
        [str(exe), '--screen', 'glider', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(glider_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='63',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_GLIDER_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert glider.returncode == 0 and 'SDL event replay: PASS' in glider.stdout, glider.stderr

    catch_profile = tmp / 'catch-config.ini'
    catch_profile.write_text('[DEFAULT]\nCATCH_RUNG = 4\nCATCH_TRIALS = 5\nCATCH_ADAPTIVE = True\n')
    catch_options = subprocess.run(
        [str(exe), '--screen', 'catch'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(catch_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='64',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert catch_options.returncode == 0 and 'SDL event replay: PASS' in catch_options.stdout, catch_options.stderr
    assert catch_profile.with_name(catch_profile.name + '.catch-options').read_text() == (
        '[DEFAULT]\nCATCH_RUNG = 7\nCATCH_TRIALS = 3\nCATCH_ADAPTIVE = False\n')
    catch_round = tmp / 'catch-round.ini'
    catch_round.write_text('[DEFAULT]\nCATCH_RUNG = 20\nCATCH_TRIALS = 1\n')
    catch = subprocess.run(
        [str(exe), '--screen', 'catch', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(catch_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='64',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_CATCH_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert catch.returncode == 0 and 'SDL event replay: PASS' in catch.stdout, catch.stderr

    safe_profile = tmp / 'safe-config.ini'
    safe_profile.write_text('[DEFAULT]\nSAFE_RUNG = 4\nSAFE_TRIALS = 5\nSAFE_ADAPTIVE = True\n')
    safe_options = subprocess.run(
        [str(exe), '--screen', 'safecracker'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(safe_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='68',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert safe_options.returncode == 0 and 'SDL event replay: PASS' in safe_options.stdout, safe_options.stderr
    assert safe_profile.with_name(safe_profile.name + '.safecracker-options').read_text() == (
        '[DEFAULT]\nSAFE_RUNG = 7\nSAFE_TRIALS = 3\nSAFE_ADAPTIVE = False\n')

    stage_profile = tmp / 'stage-config.ini'
    stage_profile.write_text('[DEFAULT]\nSTAGE_RUNG = 4\nSTAGE_TRIALS = 5\nSTAGE_ADAPTIVE = True\n')
    stage_options = subprocess.run(
        [str(exe), '--screen', 'stagehand'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(stage_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='69',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert stage_options.returncode == 0 and 'SDL event replay: PASS' in stage_options.stdout, stage_options.stderr
    assert stage_profile.with_name(stage_profile.name + '.stagehand-options').read_text() == (
        '[DEFAULT]\nSTAGE_RUNG = 7\nSTAGE_TRIALS = 3\nSTAGE_ADAPTIVE = False\n')

    dock_profile = tmp / 'dock-config.ini'
    dock_profile.write_text('[DEFAULT]\nDOCK_RUNG = 4\nDOCK_TRIALS = 5\nDOCK_ADAPTIVE = True\n')
    dock_options = subprocess.run(
        [str(exe), '--screen', 'loading_dock'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(dock_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='70',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dock_options.returncode == 0 and 'SDL event replay: PASS' in dock_options.stdout, dock_options.stderr
    assert dock_profile.with_name(dock_profile.name + '.loading_dock-options').read_text() == (
        '[DEFAULT]\nDOCK_RUNG = 7\nDOCK_TRIALS = 3\nDOCK_ADAPTIVE = False\n')

    dock_round = tmp / 'dock-round.ini'
    dock_round.write_text('[DEFAULT]\nDOCK_RUNG = 1\nDOCK_TRIALS = 1\n')
    dock = subprocess.run(
        [str(exe), '--screen', 'loading_dock', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(dock_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='70',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_DOCK_CLICK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dock.returncode == 0 and 'SDL event replay: PASS' in dock.stdout, dock.stderr

    next_profile = tmp / 'what-next-config.ini'
    next_profile.write_text('[DEFAULT]\nWHAT_NEXT_RUNG = 1\nWHAT_NEXT_TRIALS = 10\nWHAT_NEXT_ADAPTIVE = True\n')
    next_env = dict(env, NW_MEDIA_CONFIGFILE=str(next_profile), NW_TEST_SLOT='72',
                    NW_TEST_OPTION_SLOT='-1')
    next_options = subprocess.run(
        [str(exe), '--screen', 'what-next'],
        env=dict(next_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert next_options.returncode == 0 and 'SDL event replay: PASS' in next_options.stdout, next_options.stderr
    assert next_profile.with_name(next_profile.name + '.what-next-options').read_text() == (
        '[DEFAULT]\nWHAT_NEXT_RUNG = 4\nWHAT_NEXT_TRIALS = 5\nWHAT_NEXT_ADAPTIVE = False\n')
    next_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(next_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='2', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert next_hub.returncode == 0 and 'SDL event replay: PASS' in next_hub.stdout, next_hub.stderr

    falls_profile = tmp / 'will-it-fall-config.ini'
    falls_profile.write_text('[DEFAULT]\nWILL_IT_FALL_RUNG = 1\nWILL_IT_FALL_TRIALS = 10\nWILL_IT_FALL_ADAPTIVE = True\n')
    falls_env = dict(env, NW_MEDIA_CONFIGFILE=str(falls_profile), NW_TEST_SLOT='73',
                     NW_TEST_OPTION_SLOT='-1')
    falls_options = subprocess.run(
        [str(exe), '--screen', 'will-it-fall'],
        env=dict(falls_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert falls_options.returncode == 0 and 'SDL event replay: PASS' in falls_options.stdout, falls_options.stderr
    assert falls_profile.with_name(falls_profile.name + '.will-it-fall-options').read_text() == (
        '[DEFAULT]\nWILL_IT_FALL_RUNG = 4\nWILL_IT_FALL_TRIALS = 5\nWILL_IT_FALL_ADAPTIVE = False\n')
    falls_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(falls_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='3', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert falls_hub.returncode == 0 and 'SDL event replay: PASS' in falls_hub.stdout, falls_hub.stderr
    falls_dump = subprocess.run(
        [str(exe), '--screen', 'will-it-fall', '--seed', '17', '--trials', '2', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(falls_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    falls_states = [ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
                    for line in falls_dump.stdout.splitlines() if line.startswith('# state=')]
    assert falls_states == [(0, 4, 0, 5, 0, 0, 0), (1, 4, 1, 5, 0, 0, 0)], falls_states

    sfm_profile = tmp / 'shape-from-motion-config.ini'
    sfm_profile.write_text('[DEFAULT]\nSHAPE_FROM_MOTION_RUNG = 1\nSHAPE_FROM_MOTION_TRIALS = 12\nSHAPE_FROM_MOTION_ADAPTIVE = True\n')
    sfm_env = dict(env, NW_MEDIA_CONFIGFILE=str(sfm_profile), NW_TEST_SLOT='74',
                     NW_TEST_OPTION_SLOT='-1')
    sfm_options = subprocess.run(
        [str(exe), '--screen', 'shape-from-motion'],
        env=dict(sfm_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sfm_options.returncode == 0 and 'SDL event replay: PASS' in sfm_options.stdout, sfm_options.stderr
    assert sfm_profile.with_name(sfm_profile.name + '.shape-from-motion-options').read_text() == (
        '[DEFAULT]\nSHAPE_FROM_MOTION_RUNG = 4\nSHAPE_FROM_MOTION_TRIALS = 6\nSHAPE_FROM_MOTION_ADAPTIVE = False\n')
    sfm_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(sfm_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='6', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sfm_hub.returncode == 0 and 'SDL event replay: PASS' in sfm_hub.stdout, sfm_hub.stderr
    sfm_dump = subprocess.run(
        [str(exe), '--screen', 'shape-from-motion', '--seed', '17', '--trials', '2', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(sfm_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    sfm_states = [ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
                    for line in sfm_dump.stdout.splitlines() if line.startswith('# state=')]
    assert sfm_states == [(0, 4, 0, 6, 0, 0, 0), (1, 4, 1, 6, 0, 0, 0)], sfm_states

    drshape_profile = tmp / 'dr-shape-config.ini'
    drshape_profile.write_text('[DEFAULT]\nDRSHAPE_RUNG = 1\nDRSHAPE_TRIALS = 5\nDRSHAPE_ADAPTIVE = True\n')
    drshape_env = dict(env, NW_MEDIA_CONFIGFILE=str(drshape_profile), NW_TEST_SLOT='75',
                     NW_TEST_OPTION_SLOT='-1')
    drshape_options = subprocess.run(
        [str(exe), '--screen', 'dr-shape'],
        env=dict(drshape_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert drshape_options.returncode == 0 and 'SDL event replay: PASS' in drshape_options.stdout, drshape_options.stderr
    assert drshape_profile.with_name(drshape_profile.name + '.dr-shape-options').read_text() == (
        '[DEFAULT]\nDRSHAPE_RUNG = 4\nDRSHAPE_TRIALS = 3\nDRSHAPE_ADAPTIVE = False\n')
    drshape_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(drshape_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='8', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert drshape_hub.returncode == 0 and 'SDL event replay: PASS' in drshape_hub.stdout, drshape_hub.stderr
    drshape_dump = subprocess.run(
        [str(exe), '--screen', 'dr-shape', '--seed', '17', '--trials', '2', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(drshape_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    drshape_states = [ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
                    for line in drshape_dump.stdout.splitlines() if line.startswith('# state=')]
    assert drshape_states == [
        (0, 4, 0, 3, -1, -1, -1, -1, 0, 0, -1, -1, -1, 0),
        (1, 4, 1, 3, 0, 3, 4, -1, 0, 0, -1, -1, -1, 0),
    ], drshape_states

    drshape_round = tmp / 'dr-shape-round.ini'
    drshape_round.write_text('[DEFAULT]\nDRSHAPE_RUNG = 1\nDRSHAPE_TRIALS = 1\n')
    for control in ('1', '2'):
        played = subprocess.run(
            [str(exe), '--screen', 'dr-shape', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(env, NW_MEDIA_CONFIGFILE=str(drshape_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='75',
                     NW_TEST_DRSHAPE_CLOCK=control, NW_TEST_CLOSE_WINDOW='1', NW_TEST_OPTION_SLOT='-1'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, played.stderr

    fold_it_profile = tmp / 'fold-it-config.ini'
    fold_it_profile.write_text('[DEFAULT]\nFOLD_IT_RUNG = 1\nFOLD_IT_TRIALS = 10\nFOLD_IT_ADAPTIVE = True\n')
    fold_it_env = dict(env, NW_MEDIA_CONFIGFILE=str(fold_it_profile), NW_TEST_SLOT='80', NW_TEST_OPTION_SLOT='-1')
    fold_it_options = subprocess.run(
        [str(exe), '--screen', 'fold-it'],
        env=dict(fold_it_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert fold_it_options.returncode == 0 and 'SDL event replay: PASS' in fold_it_options.stdout, fold_it_options.stderr
    assert fold_it_profile.with_name(fold_it_profile.name + '.fold-it-options').read_text() == (
        '[DEFAULT]\nFOLD_IT_RUNG = 4\nFOLD_IT_TRIALS = 5\nFOLD_IT_ADAPTIVE = False\n')
    fold_it_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(fold_it_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='19', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert fold_it_hub.returncode == 0 and 'SDL event replay: PASS' in fold_it_hub.stdout, fold_it_hub.stderr
    fold_it_round = tmp / 'fold-it-round.ini'
    fold_it_round.write_text('[DEFAULT]\nFOLD_IT_RUNG = 25\nFOLD_IT_TRIALS = 1\n')
    fold_it_played = subprocess.run(
        [str(exe), '--screen', 'fold-it', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(fold_it_env, NW_MEDIA_CONFIGFILE=str(fold_it_round), NW_TEST_DIRECT='1',
                 NW_TEST_FOLD_IT='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert fold_it_played.returncode == 0 and 'SDL event replay: PASS' in fold_it_played.stdout, (
        fold_it_played.returncode, fold_it_played.stderr)
    print('SDL Fold It: saved options, hub launch, mouse and keyboard verdicts, and restart pass')

    who_knows_what_profile = tmp / 'who-knows-what-config.ini'
    who_knows_what_profile.write_text('[DEFAULT]\nWHO_KNOWS_WHAT_RUNG = 1\nWHO_KNOWS_WHAT_TRIALS = 10\nWHO_KNOWS_WHAT_ADAPTIVE = True\n')
    who_knows_what_env = dict(env, NW_MEDIA_CONFIGFILE=str(who_knows_what_profile), NW_TEST_SLOT='81', NW_TEST_OPTION_SLOT='-1')
    who_knows_what_options = subprocess.run(
        [str(exe), '--screen', 'who-knows-what'],
        env=dict(who_knows_what_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert who_knows_what_options.returncode == 0 and 'SDL event replay: PASS' in who_knows_what_options.stdout, who_knows_what_options.stderr
    assert who_knows_what_profile.with_name(who_knows_what_profile.name + '.who-knows-what-options').read_text() == (
        '[DEFAULT]\nWHO_KNOWS_WHAT_RUNG = 3\nWHO_KNOWS_WHAT_TRIALS = 5\nWHO_KNOWS_WHAT_ADAPTIVE = False\n')
    who_knows_what_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(who_knows_what_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='20', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert who_knows_what_hub.returncode == 0 and 'SDL event replay: PASS' in who_knows_what_hub.stdout, who_knows_what_hub.stderr
    who_knows_what_round = tmp / 'who-knows-what-round.ini'
    who_knows_what_round.write_text('[DEFAULT]\nWHO_KNOWS_WHAT_RUNG = 25\nWHO_KNOWS_WHAT_TRIALS = 1\n')
    who_knows_what_played = subprocess.run(
        [str(exe), '--screen', 'who-knows-what', '--seed', '222', '--width', '912', '--height', '684'],
        env=dict(who_knows_what_env, NW_MEDIA_CONFIGFILE=str(who_knows_what_round), NW_TEST_DIRECT='1',
                 NW_TEST_WHO_KNOWS_WHAT='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert who_knows_what_played.returncode == 0 and 'SDL event replay: PASS' in who_knows_what_played.stdout, (
        who_knows_what_played.returncode, who_knows_what_played.stderr)
    print('SDL Who Knows What?: saved options, hub launch, dense story, mouse and keyboard verdicts, and restart pass')

    dam_keeper_profile = tmp / 'dam-keeper-config.ini'
    dam_keeper_profile.write_text('[DEFAULT]\nDAMKEEPER_RUNG = 1\nDAMKEEPER_TRIALS = 5\nDAMKEEPER_ADAPTIVE = True\n')
    dam_keeper_env = dict(env, NW_MEDIA_CONFIGFILE=str(dam_keeper_profile), NW_TEST_SLOT='82', NW_TEST_OPTION_SLOT='-1')
    dam_options = subprocess.run(
        [str(exe), '--screen', 'dam-keeper'],
        env=dict(dam_keeper_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dam_options.returncode == 0 and 'SDL event replay: PASS' in dam_options.stdout, dam_options.stderr
    assert dam_keeper_profile.with_name(dam_keeper_profile.name + '.dam-keeper-options').read_text() == (
        '[DEFAULT]\nDAMKEEPER_RUNG = 4\nDAMKEEPER_TRIALS = 3\nDAMKEEPER_ADAPTIVE = False\n')
    dam_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(dam_keeper_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='8', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dam_hub.returncode == 0 and 'SDL event replay: PASS' in dam_hub.stdout, dam_hub.stderr

    dam_round = tmp / 'dam-keeper-round.ini'
    dam_round.write_text('[DEFAULT]\nDAMKEEPER_RUNG = 1\nDAMKEEPER_TRIALS = 1\n')
    dam_played = subprocess.run(
        [str(exe), '--screen', 'dam-keeper', '--seed', '222', '--width', '912', '--height', '684'],
        env=dict(dam_keeper_env, NW_MEDIA_CONFIGFILE=str(dam_round), NW_TEST_DIRECT='1',
                 NW_TEST_DAM_KEEPER='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dam_played.returncode == 0 and 'SDL event replay: PASS' in dam_played.stdout, (
        dam_played.returncode, dam_played.stderr)
    print('SDL Dam Keeper: saved options, Decisions hub, Q and click gate input, timed feedback, and restart pass')

    sonar_profile = tmp / 'sonar-config.ini'
    sonar_profile.write_text('[DEFAULT]\nSONAR_RUNG = 1\nSONAR_TRIALS = 8\nSONAR_ADAPTIVE = True\n')
    sonar_env = dict(env, NW_MEDIA_CONFIGFILE=str(sonar_profile), NW_TEST_SLOT='83', NW_TEST_OPTION_SLOT='-1')
    sonar_options = subprocess.run(
        [str(exe), '--screen', 'sonar'],
        env=dict(sonar_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sonar_options.returncode == 0 and 'SDL event replay: PASS' in sonar_options.stdout, sonar_options.stderr
    assert sonar_profile.with_name(sonar_profile.name + '.sonar-options').read_text() == (
        '[DEFAULT]\nSONAR_RUNG = 2\nSONAR_TRIALS = 5\nSONAR_ADAPTIVE = False\n')
    sonar_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(sonar_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='0', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sonar_hub.returncode == 0 and 'SDL event replay: PASS' in sonar_hub.stdout, sonar_hub.stderr

    sonar_round = tmp / 'sonar-round.ini'
    sonar_round.write_text('[DEFAULT]\nSONAR_RUNG = 1\nSONAR_TRIALS = 1\n')
    sonar_played = subprocess.run(
        [str(exe), '--screen', 'sonar', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(sonar_env, NW_MEDIA_CONFIGFILE=str(sonar_round), NW_TEST_DIRECT='1',
                 NW_TEST_SONAR='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sonar_played.returncode == 0 and 'SDL event replay: PASS' in sonar_played.stdout, (
        sonar_played.returncode, sonar_played.stderr)
    sonar_large = tmp / 'sonar-large.ini'
    sonar_large.write_text('[DEFAULT]\nSONAR_RUNG = 25\nSONAR_TRIALS = 3\nSONAR_ADAPTIVE = False\n')
    sonar_dump = subprocess.run(
        [str(exe), '--screen', 'sonar', '--seed', '17', '--trials', '2', '--dump'],
        env=dict(sonar_env, NW_MEDIA_CONFIGFILE=str(sonar_large)),
        capture_output=True, text=True, timeout=20,
    )
    assert sonar_dump.returncode == 0, sonar_dump.stderr
    assert 'state=(1, 25, 1, 3, 24, 300, 0, 0, 259,' in sonar_dump.stdout
    assert 'Find it for 129.5 or less' in sonar_dump.stdout
    sonar_large_frame = subprocess.run(
        [str(exe), '--screen', 'sonar', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(sonar_env, NW_MEDIA_CONFIGFILE=str(sonar_large), NW_TEST_DIRECT='1',
                 NW_TEST_SONAR='2', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sonar_large_frame.returncode == 0 and 'SDL event replay: PASS' in sonar_large_frame.stdout, (
        sonar_large_frame.returncode, sonar_large_frame.stderr)
    print('SDL Sonar: saved options, Decisions hub, keyboard ping, right-click and Shift-click digs, verdict, restart, and largest board pass')

    gamble_profile = tmp / 'gamble-config.ini'
    gamble_profile.write_text('[DEFAULT]\nGAMBLE_RUNG = 1\nGAMBLE_TRIALS = 5\nGAMBLE_ADAPTIVE = True\n')
    gamble_env = dict(env, NW_MEDIA_CONFIGFILE=str(gamble_profile), NW_TEST_SLOT='84', NW_TEST_OPTION_SLOT='-1')
    gamble_options = subprocess.run(
        [str(exe), '--screen', 'gamble'],
        env=dict(gamble_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert gamble_options.returncode == 0 and 'SDL event replay: PASS' in gamble_options.stdout, gamble_options.stderr
    assert gamble_profile.with_name(gamble_profile.name + '.gamble-options').read_text() == (
        '[DEFAULT]\nGAMBLE_RUNG = 3\nGAMBLE_TRIALS = 3\nGAMBLE_ADAPTIVE = False\n')
    gamble_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(gamble_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='2', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert gamble_hub.returncode == 0 and 'SDL event replay: PASS' in gamble_hub.stdout, gamble_hub.stderr
    gamble_round = tmp / 'gamble-round.ini'
    gamble_round.write_text('[DEFAULT]\nGAMBLE_RUNG = 18\nGAMBLE_TRIALS = 1\nGAMBLE_ADAPTIVE = False\n')
    gamble_played = subprocess.run(
        [str(exe), '--screen', 'gamble', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(gamble_env, NW_MEDIA_CONFIGFILE=str(gamble_round), NW_TEST_DIRECT='1',
                 NW_TEST_GAMBLE='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert gamble_played.returncode == 0 and 'SDL event replay: PASS' in gamble_played.stdout, (
        gamble_played.returncode, gamble_played.stderr)
    print('SDL Gamble: saved options, Decisions hub, keyboard and pointer pulls, stopping, timed verdict, and restart pass')

    dispatch_profile = tmp / 'dispatch-config.ini'
    dispatch_profile.write_text('[DEFAULT]\nDISPATCH_RUNG = 1\nDISPATCH_TRIALS = 3\nDISPATCH_ADAPTIVE = True\n')
    dispatch_env = dict(env, NW_MEDIA_CONFIGFILE=str(dispatch_profile), NW_TEST_SLOT='85', NW_TEST_OPTION_SLOT='-1')
    dispatch_options = subprocess.run(
        [str(exe), '--screen', 'dispatch'],
        env=dict(dispatch_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dispatch_options.returncode == 0 and 'SDL event replay: PASS' in dispatch_options.stdout, dispatch_options.stderr
    assert dispatch_profile.with_name(dispatch_profile.name + '.dispatch-options').read_text() == (
        '[DEFAULT]\nDISPATCH_RUNG = 2\nDISPATCH_TRIALS = 2\nDISPATCH_ADAPTIVE = False\n')
    dispatch_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(dispatch_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='1', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dispatch_hub.returncode == 0 and 'SDL event replay: PASS' in dispatch_hub.stdout, dispatch_hub.stderr
    dispatch_round = tmp / 'dispatch-round.ini'
    dispatch_round.write_text('[DEFAULT]\nDISPATCH_RUNG = 8\nDISPATCH_TRIALS = 1\nDISPATCH_ADAPTIVE = False\n')
    dispatch_played = subprocess.run(
        [str(exe), '--screen', 'dispatch', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(dispatch_env, NW_MEDIA_CONFIGFILE=str(dispatch_round), NW_TEST_DIRECT='1',
                 NW_TEST_DISPATCH='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert dispatch_played.returncode == 0 and 'SDL event replay: PASS' in dispatch_played.stdout, (
        dispatch_played.returncode, dispatch_played.stderr)
    print('SDL Dispatch: saved options, Decisions hub, shifted refit, keyboard and mouse orders, timed verdict, and restart pass')

    bluff_profile = tmp / 'bluff-config.ini'
    bluff_profile.write_text('[DEFAULT]\nBLUFF_RUNG = 1\nBLUFF_TRIALS = 5\nBLUFF_ADAPTIVE = True\n')
    bluff_env = dict(env, NW_MEDIA_CONFIGFILE=str(bluff_profile), NW_TEST_SLOT='86', NW_TEST_OPTION_SLOT='-1')
    bluff_options = subprocess.run(
        [str(exe), '--screen', 'bluff'],
        env=dict(bluff_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert bluff_options.returncode == 0 and 'SDL event replay: PASS' in bluff_options.stdout, bluff_options.stderr
    assert bluff_profile.with_name(bluff_profile.name + '.bluff-options').read_text() == (
        '[DEFAULT]\nBLUFF_RUNG = 3\nBLUFF_TRIALS = 3\nBLUFF_ADAPTIVE = False\n')
    bluff_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(bluff_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='3', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert bluff_hub.returncode == 0 and 'SDL event replay: PASS' in bluff_hub.stdout, bluff_hub.stderr
    bluff_round = tmp / 'bluff-round.ini'
    bluff_round.write_text('[DEFAULT]\nBLUFF_RUNG = 1\nBLUFF_TRIALS = 1\nBLUFF_ADAPTIVE = False\n')
    bluff_played = subprocess.run(
        [str(exe), '--screen', 'bluff', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(bluff_env, NW_MEDIA_CONFIGFILE=str(bluff_round), NW_TEST_DIRECT='1',
                 NW_TEST_BLUFF='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert bluff_played.returncode == 0 and 'SDL event replay: PASS' in bluff_played.stdout, (
        bluff_played.returncode, bluff_played.stderr)
    print('SDL Bluff: saved options, Decisions hub, keyboard and mouse choices, timed verdict, and restart pass')

    bandit_profile = tmp / 'bandit-config.ini'
    bandit_profile.write_text('[DEFAULT]\nEXPLORE_EXPLOIT_RUNG = 1\nEXPLORE_EXPLOIT_TRIALS = 3\nEXPLORE_EXPLOIT_ADAPTIVE = True\n')
    bandit_env = dict(env, NW_MEDIA_CONFIGFILE=str(bandit_profile), NW_TEST_SLOT='87', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'explore-exploit'],
        env=dict(bandit_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, options.stderr
    assert bandit_profile.with_name(bandit_profile.name + '.explore-exploit-options').read_text() == (
        '[DEFAULT]\nEXPLORE_EXPLOIT_RUNG = 4\nEXPLORE_EXPLOIT_TRIALS = 1\nEXPLORE_EXPLOIT_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(bandit_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='4', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    bandit_round = tmp / 'bandit-round.ini'
    bandit_round.write_text('[DEFAULT]\nEXPLORE_EXPLOIT_RUNG = 16\nEXPLORE_EXPLOIT_TRIALS = 1\nEXPLORE_EXPLOIT_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'explore-exploit', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(bandit_env, NW_MEDIA_CONFIGFILE=str(bandit_round), NW_TEST_DIRECT='1',
                 NW_TEST_BANDIT='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Explore or Exploit: options, Decisions hub, batched payouts, keyboard, click, feedback, and restart pass')

    firebreak_profile = tmp / 'firebreak-config.ini'
    firebreak_profile.write_text('[DEFAULT]\nFIREBREAK_RUNG = 1\nFIREBREAK_TRIALS = 5\nFIREBREAK_ADAPTIVE = True\n')
    firebreak_env = dict(env, NW_MEDIA_CONFIGFILE=str(firebreak_profile), NW_TEST_SLOT='88', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'firebreak'],
        env=dict(firebreak_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, options.stderr
    assert firebreak_profile.with_name(firebreak_profile.name + '.firebreak-options').read_text() == (
        '[DEFAULT]\nFIREBREAK_RUNG = 4\nFIREBREAK_TRIALS = 3\nFIREBREAK_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(firebreak_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='5', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    firebreak_round = tmp / 'firebreak-round.ini'
    firebreak_round.write_text('[DEFAULT]\nFIREBREAK_RUNG = 16\nFIREBREAK_TRIALS = 1\nFIREBREAK_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'firebreak', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(firebreak_env, NW_MEDIA_CONFIGFILE=str(firebreak_round), NW_TEST_DIRECT='1',
                 NW_TEST_FIREBREAK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Firebreak: profile options, Decisions hub, shifted movement, Enter, and pointer digging pass')

    crossroads_profile = tmp / 'crossroads-config.ini'
    crossroads_profile.write_text('[DEFAULT]\nCROSSROADS_RUNG = 1\nCROSSROADS_TRIALS = 5\nCROSSROADS_ADAPTIVE = True\n')
    crossroads_env = dict(env, NW_MEDIA_CONFIGFILE=str(crossroads_profile), NW_TEST_SLOT='89', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'crossroads'],
        env=dict(crossroads_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, options.stderr
    assert crossroads_profile.with_name(crossroads_profile.name + '.crossroads-options').read_text() == (
        '[DEFAULT]\nCROSSROADS_RUNG = 4\nCROSSROADS_TRIALS = 3\nCROSSROADS_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(crossroads_env, NW_TEST_CATEGORY='7', NW_TEST_ROW='6', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    crossroads_round = tmp / 'crossroads-round.ini'
    crossroads_round.write_text('[DEFAULT]\nCROSSROADS_RUNG = 16\nCROSSROADS_TRIALS = 1\nCROSSROADS_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'crossroads', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(crossroads_env, NW_MEDIA_CONFIGFILE=str(crossroads_round), NW_TEST_DIRECT='1',
                 NW_TEST_CROSSROADS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Crossroads: profile options, Decisions hub, start and signal controls pass')

    railyard_profile = tmp / 'railyard-config.ini'
    railyard_profile.write_text('[DEFAULT]\nRAILYARD_RUNG = 1\nRAILYARD_TRIALS = 5\nRAILYARD_ADAPTIVE = True\n')
    railyard_env = dict(env, NW_MEDIA_CONFIGFILE=str(railyard_profile), NW_TEST_SLOT='90', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'rail-yard'],
        env=dict(railyard_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert railyard_profile.with_name(railyard_profile.name + '.railyard-options').read_text() == (
        '[DEFAULT]\nRAILYARD_RUNG = 4\nRAILYARD_TRIALS = 3\nRAILYARD_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(railyard_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='8', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    railyard_round = tmp / 'railyard-round.ini'
    railyard_round.write_text('[DEFAULT]\nRAILYARD_RUNG = 16\nRAILYARD_TRIALS = 1\nRAILYARD_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'rail-yard', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(railyard_env, NW_MEDIA_CONFIGFILE=str(railyard_round), NW_TEST_DIRECT='1',
                 NW_TEST_RAILYARD='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Rail Yard: profile options, Planning hub, start and signal controls pass')

    airtraffic_profile = tmp / 'airtraffic-config.ini'
    airtraffic_profile.write_text('[DEFAULT]\nAIRTRAFFIC_RUNG = 1\nAIRTRAFFIC_TRIALS = 5\nAIRTRAFFIC_ADAPTIVE = True\n')
    airtraffic_env = dict(env, NW_MEDIA_CONFIGFILE=str(airtraffic_profile), NW_TEST_SLOT='91', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'air-traffic'],
        env=dict(airtraffic_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert airtraffic_profile.with_name(airtraffic_profile.name + '.airtraffic-options').read_text() == (
        '[DEFAULT]\nAIRTRAFFIC_RUNG = 4\nAIRTRAFFIC_TRIALS = 3\nAIRTRAFFIC_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(airtraffic_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='9', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    airtraffic_round = tmp / 'airtraffic-round.ini'
    airtraffic_round.write_text('[DEFAULT]\nAIRTRAFFIC_RUNG = 16\nAIRTRAFFIC_TRIALS = 1\nAIRTRAFFIC_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'air-traffic', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(airtraffic_env, NW_MEDIA_CONFIGFILE=str(airtraffic_round), NW_TEST_DIRECT='1',
                 NW_TEST_AIRTRAFFIC='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Air Traffic: profile options, Planning hub, plane selection, hold, turn, and runway clicks pass')

    escort_profile = tmp / 'escort-config.ini'
    escort_profile.write_text('[DEFAULT]\nESCORT_RUNG = 1\nESCORT_TRIALS = 5\nESCORT_ADAPTIVE = True\n')
    escort_env = dict(env, NW_MEDIA_CONFIGFILE=str(escort_profile), NW_TEST_SLOT='92', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'escort'],
        env=dict(escort_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert escort_profile.with_name(escort_profile.name + '.escort-options').read_text() == (
        '[DEFAULT]\nESCORT_RUNG = 4\nESCORT_TRIALS = 3\nESCORT_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(escort_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='10', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    escort_round = tmp / 'escort-round.ini'
    escort_round.write_text('[DEFAULT]\nESCORT_RUNG = 16\nESCORT_TRIALS = 1\nESCORT_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'escort', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(escort_env, NW_MEDIA_CONFIGFILE=str(escort_round), NW_TEST_DIRECT='1',
                 NW_TEST_ESCORT='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Escort: profile options, Planning hub, keyboard and pointer levers pass')

    sokobanlive_profile = tmp / 'sokobanlive-config.ini'
    sokobanlive_profile.write_text('[DEFAULT]\nSOKOBANLIVE_RUNG = 1\nSOKOBANLIVE_TRIALS = 5\nSOKOBANLIVE_ADAPTIVE = True\n')
    sokobanlive_env = dict(env, NW_MEDIA_CONFIGFILE=str(sokobanlive_profile), NW_TEST_SLOT='93', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'sokoban-live'],
        env=dict(sokobanlive_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert sokobanlive_profile.with_name(sokobanlive_profile.name + '.sokobanlive-options').read_text() == (
        '[DEFAULT]\nSOKOBANLIVE_RUNG = 4\nSOKOBANLIVE_TRIALS = 3\nSOKOBANLIVE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(sokobanlive_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='11', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    sokobanlive_round = tmp / 'sokobanlive-round.ini'
    sokobanlive_round.write_text('[DEFAULT]\nSOKOBANLIVE_RUNG = 1\nSOKOBANLIVE_TRIALS = 1\nSOKOBANLIVE_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'sokoban-live', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(sokobanlive_env, NW_MEDIA_CONFIGFILE=str(sokobanlive_round), NW_TEST_DIRECT='1',
                 NW_TEST_SOKOBANLIVE='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Sokoban Live: profile options, Planning hub, arrow and WASD solution, timed verdict pass')

    kitchen_profile = tmp / 'kitchen-config.ini'
    kitchen_profile.write_text('[DEFAULT]\nKITCHEN_RUNG = 1\nKITCHEN_TRIALS = 5\nKITCHEN_ADAPTIVE = True\n')
    kitchen_env = dict(env, NW_MEDIA_CONFIGFILE=str(kitchen_profile), NW_TEST_SLOT='94', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'kitchen'],
        env=dict(kitchen_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert kitchen_profile.with_name(kitchen_profile.name + '.kitchen-options').read_text() == (
        '[DEFAULT]\nKITCHEN_RUNG = 4\nKITCHEN_TRIALS = 3\nKITCHEN_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(kitchen_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='12', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    kitchen_round = tmp / 'kitchen-round.ini'
    kitchen_round.write_text('[DEFAULT]\nKITCHEN_RUNG = 1\nKITCHEN_TRIALS = 1\nKITCHEN_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'kitchen', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(kitchen_env, NW_MEDIA_CONFIGFILE=str(kitchen_round), NW_TEST_DIRECT='1',
                 NW_TEST_KITCHEN='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Kitchen: profile options, Planning hub, keyboard and pointer cooking and burn pass')

    crane_profile = tmp / 'crane-config.ini'
    crane_profile.write_text('[DEFAULT]\nCRANE_RUNG = 1\nCRANE_TRIALS = 5\nCRANE_ADAPTIVE = True\n')
    crane_env = dict(env, NW_MEDIA_CONFIGFILE=str(crane_profile), NW_TEST_SLOT='95', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'crane'],
        env=dict(crane_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert crane_profile.with_name(crane_profile.name + '.crane-options').read_text() == (
        '[DEFAULT]\nCRANE_RUNG = 4\nCRANE_TRIALS = 3\nCRANE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(crane_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='13', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    crane_round = tmp / 'crane-round.ini'
    crane_round.write_text('[DEFAULT]\nCRANE_RUNG = 1\nCRANE_TRIALS = 1\nCRANE_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'crane', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(crane_env, NW_MEDIA_CONFIGFILE=str(crane_round), NW_TEST_DIRECT='1',
                 NW_TEST_CRANE='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Crane: profile options, Planning hub, held aliases, hoist, grab, and focus release pass')

    ferry_profile = tmp / 'ferry-config.ini'
    ferry_profile.write_text('[DEFAULT]\nFERRY_RUNG = 1\nFERRY_TRIALS = 5\nFERRY_ADAPTIVE = True\n')
    ferry_env = dict(env, NW_MEDIA_CONFIGFILE=str(ferry_profile), NW_TEST_SLOT='96', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'ferry'],
        env=dict(ferry_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert ferry_profile.with_name(ferry_profile.name + '.ferry-options').read_text() == (
        '[DEFAULT]\nFERRY_RUNG = 4\nFERRY_TRIALS = 3\nFERRY_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(ferry_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='14', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    ferry_round = tmp / 'ferry-round.ini'
    ferry_round.write_text('[DEFAULT]\nFERRY_RUNG = 1\nFERRY_TRIALS = 1\nFERRY_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'ferry', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(ferry_env, NW_MEDIA_CONFIGFILE=str(ferry_round), NW_TEST_DIRECT='1',
                 NW_TEST_FERRY='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Ferry: profile options, Planning hub, combined thrust and turn, alias release, and focus cleanup pass')

    docking_profile = tmp / 'docking-config.ini'
    docking_profile.write_text('[DEFAULT]\nBERTH_RUNG = 1\nBERTH_TRIALS = 5\nBERTH_ADAPTIVE = True\n')
    docking_env = dict(env, NW_MEDIA_CONFIGFILE=str(docking_profile), NW_TEST_SLOT='97', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'docking'],
        env=dict(docking_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert docking_profile.with_name(docking_profile.name + '.docking-options').read_text() == (
        '[DEFAULT]\nBERTH_RUNG = 4\nBERTH_TRIALS = 3\nBERTH_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(docking_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='15', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    docking_round = tmp / 'docking-round.ini'
    docking_round.write_text('[DEFAULT]\nBERTH_RUNG = 1\nBERTH_TRIALS = 1\nBERTH_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'docking', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(docking_env, NW_MEDIA_CONFIGFILE=str(docking_round), NW_TEST_DIRECT='1',
                 NW_TEST_DOCKING='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Docking: profile options, Planning hub, held controls, fuel use, and focus cleanup pass')

    rover_profile = tmp / 'rover-config.ini'
    rover_profile.write_text('[DEFAULT]\nROVER_RUNG = 1\nROVER_TRIALS = 5\nROVER_ADAPTIVE = True\n')
    rover_env = dict(env, NW_MEDIA_CONFIGFILE=str(rover_profile), NW_TEST_SLOT='98', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'rover'],
        env=dict(rover_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert rover_profile.with_name(rover_profile.name + '.rover-options').read_text() == (
        '[DEFAULT]\nROVER_RUNG = 4\nROVER_TRIALS = 3\nROVER_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(rover_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='16', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    rover_round = tmp / 'rover-round.ini'
    rover_round.write_text('[DEFAULT]\nROVER_RUNG = 1\nROVER_TRIALS = 1\nROVER_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'rover', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(rover_env, NW_MEDIA_CONFIGFILE=str(rover_round), NW_TEST_DIRECT='1',
                 NW_TEST_ROVER='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    rover_round.write_text('[DEFAULT]\nROVER_RUNG = 4\nROVER_TRIALS = 1\nROVER_ADAPTIVE = False\n')
    collision = subprocess.run(
        [str(exe), '--screen', 'rover', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(rover_env, NW_MEDIA_CONFIGFILE=str(rover_round), NW_TEST_DIRECT='1',
                 NW_TEST_ROVER='2', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert collision.returncode == 0 and 'SDL event replay: PASS' in collision.stdout, (collision.returncode, collision.stderr)
    print('SDL Rover: profile options, Planning hub, delayed controls, held aliases, focus cleanup, and collision audio pass')

    unicycle_profile = tmp / 'unicycle-config.ini'
    unicycle_profile.write_text('[DEFAULT]\nUNI_RUNG = 1\nUNI_TRIALS = 5\nUNI_ADAPTIVE = True\n')
    unicycle_env = dict(env, NW_MEDIA_CONFIGFILE=str(unicycle_profile), NW_TEST_SLOT='99', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'unicycle'],
        env=dict(unicycle_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert unicycle_profile.with_name(unicycle_profile.name + '.unicycle-options').read_text() == (
        '[DEFAULT]\nUNI_RUNG = 4\nUNI_TRIALS = 3\nUNI_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(unicycle_env, NW_TEST_CATEGORY='5', NW_TEST_ROW='17', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    unicycle_round = tmp / 'unicycle-round.ini'
    unicycle_round.write_text('[DEFAULT]\nUNI_RUNG = 1\nUNI_TRIALS = 1\nUNI_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'unicycle', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(unicycle_env, NW_MEDIA_CONFIGFILE=str(unicycle_round), NW_TEST_DIRECT='1',
                 NW_TEST_UNICYCLE='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Unicycle: profile options, Planning hub, combined keys, fall verdict, and audio pass')

    morning_round_profile = tmp / 'morning-round-config.ini'
    morning_round_profile.write_text('[DEFAULT]\nROUND_RUNG = 1\nROUND_TRIALS = 5\nROUND_ADAPTIVE = True\n')
    morning_round_env = dict(env, NW_MEDIA_CONFIGFILE=str(morning_round_profile), NW_TEST_SLOT='100', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'morning-round'],
        env=dict(morning_round_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert morning_round_profile.with_name(morning_round_profile.name + '.morning-round-options').read_text() == (
        '[DEFAULT]\nROUND_RUNG = 4\nROUND_TRIALS = 3\nROUND_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(morning_round_env, NW_TEST_CATEGORY='6', NW_TEST_ROW='4', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(morning_round_env, NW_TEST_CATEGORY='6', NW_TEST_MORNING_ROUND_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    morning_round_play_profile = tmp / 'morning-round-round.ini'
    morning_round_play_profile.write_text('[DEFAULT]\nROUND_RUNG = 1\nROUND_TRIALS = 1\nROUND_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'morning-round', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(morning_round_env, NW_MEDIA_CONFIGFILE=str(morning_round_play_profile), NW_TEST_DIRECT='1',
                 NW_TEST_MORNING_ROUND='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Morning Round: profile options, Self-control hub, steering, throws, and audio pass')

    heavier_profile = tmp / 'heavier-config.ini'
    heavier_profile.write_text('[DEFAULT]\nHEAVY_RUNG = 1\nHEAVY_TRIALS = 5\nHEAVY_ADAPTIVE = True\n')
    heavier_env = dict(env, NW_MEDIA_CONFIGFILE=str(heavier_profile), NW_TEST_SLOT='101', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'heavier'],
        env=dict(heavier_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert heavier_profile.with_name(heavier_profile.name + '.heavier-options').read_text() == (
        '[DEFAULT]\nHEAVY_RUNG = 4\nHEAVY_TRIALS = 3\nHEAVY_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(heavier_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='21', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, hub.stderr
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(heavier_env, NW_TEST_CATEGORY='4', NW_TEST_HEAVIER_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    heavier_play_profile = tmp / 'heavier-round.ini'
    heavier_play_profile.write_text('[DEFAULT]\nHEAVY_RUNG = 1\nHEAVY_TRIALS = 1\nHEAVY_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'heavier', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(heavier_env, NW_MEDIA_CONFIGFILE=str(heavier_play_profile), NW_TEST_DIRECT='1',
                 NW_TEST_HEAVIER='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Heavier: profile options, Reasoning hub, mouse pushes, answer buttons, and audio pass')

    full_stop_profile = tmp / 'full-stop-config.ini'
    full_stop_profile.write_text('[DEFAULT]\nSTOP_RUNG = 1\nSTOP_TRIALS = 5\nSTOP_ADAPTIVE = True\n')
    full_stop_env = dict(env, NW_MEDIA_CONFIGFILE=str(full_stop_profile), NW_TEST_SLOT='102', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'full-stop'],
        env=dict(full_stop_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert full_stop_profile.with_name(full_stop_profile.name + '.full-stop-options').read_text() == (
        '[DEFAULT]\nSTOP_RUNG = 4\nSTOP_TRIALS = 3\nSTOP_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(full_stop_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='22', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(full_stop_env, NW_TEST_CATEGORY='4', NW_TEST_FULL_STOP_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    full_stop_play_profile = tmp / 'full-stop-round.ini'
    full_stop_play_profile.write_text('[DEFAULT]\nSTOP_RUNG = 1\nSTOP_TRIALS = 1\nSTOP_ADAPTIVE = False\n')
    full_stop_data = tmp / 'full-stop-data'
    (full_stop_data / 'words').mkdir(parents=True)
    (full_stop_data / 'words/passages.txt').write_text(
        'Ada built a wooden boat. Clara painted it bright red.\n' * 100)
    played = subprocess.run(
        [str(exe), '--screen', 'full-stop', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(full_stop_env, NW_MEDIA_CONFIGFILE=str(full_stop_play_profile),
                 NW_DATA_DIRECTORY=str(full_stop_data), NW_TEST_DIRECT='1', NW_TEST_FULL_STOP='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Full Stop: Reasoning hub, profile options, original passage cache, pointer, keyboard, feedback, and audio pass')

    missing_word_profile = tmp / 'missing-word-config.ini'
    missing_word_profile.write_text('[DEFAULT]\nGAPW_RUNG = 1\nGAPW_TRIALS = 5\nGAPW_ADAPTIVE = True\n')
    missing_word_env = dict(env, NW_MEDIA_CONFIGFILE=str(missing_word_profile), NW_TEST_SLOT='103', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'missing-word'],
        env=dict(missing_word_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert missing_word_profile.with_name(missing_word_profile.name + '.missing-word-options').read_text() == (
        '[DEFAULT]\nGAPW_RUNG = 4\nGAPW_TRIALS = 3\nGAPW_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(missing_word_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='23', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(missing_word_env, NW_TEST_CATEGORY='4', NW_TEST_MISSING_WORD_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    missing_word_play_profile = tmp / 'missing-word-round.ini'
    missing_word_play_profile.write_text('[DEFAULT]\nGAPW_RUNG = 4\nGAPW_TRIALS = 1\nGAPW_ADAPTIVE = False\n')
    missing_word_data = tmp / 'missing-word-data'
    (missing_word_data / 'words').mkdir(parents=True)
    (missing_word_data / 'words/passages.txt').write_text(
        'Ada built a wooden boat. Clara painted it bright red.\n' * 100)
    played = subprocess.run(
        [str(exe), '--screen', 'missing-word', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(missing_word_env, NW_MEDIA_CONFIGFILE=str(missing_word_play_profile),
                 NW_DATA_DIRECTORY=str(missing_word_data), NW_TEST_DIRECT='1', NW_TEST_MISSING_WORD='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL The Missing Word: Reasoning hub, profile options, original passage cache, pointer, keyboard, feedback, and audio pass')

    proofreader_profile = tmp / 'proofreader-config.ini'
    proofreader_profile.write_text('[DEFAULT]\nPROOF_RUNG = 1\nPROOF_TRIALS = 5\nPROOF_ADAPTIVE = True\n')
    proofreader_env = dict(env, NW_MEDIA_CONFIGFILE=str(proofreader_profile), NW_TEST_SLOT='104', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'proofreader'],
        env=dict(proofreader_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert proofreader_profile.with_name(proofreader_profile.name + '.proofreader-options').read_text() == (
        '[DEFAULT]\nPROOF_RUNG = 4\nPROOF_TRIALS = 3\nPROOF_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(proofreader_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='24', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(proofreader_env, NW_TEST_CATEGORY='4', NW_TEST_PROOFREADER_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    proofreader_play_profile = tmp / 'proofreader-round.ini'
    proofreader_play_profile.write_text('[DEFAULT]\nPROOF_RUNG = 4\nPROOF_TRIALS = 1\nPROOF_ADAPTIVE = False\n')
    proofreader_data = tmp / 'proofreader-data'
    (proofreader_data / 'words').mkdir(parents=True)
    (proofreader_data / 'words/passages.txt').write_text(
        'Ada built a wooden boat. Clara painted it bright red.\n' * 100)
    played = subprocess.run(
        [str(exe), '--screen', 'proofreader', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(proofreader_env, NW_MEDIA_CONFIGFILE=str(proofreader_play_profile),
                 NW_DATA_DIRECTORY=str(proofreader_data), NW_TEST_DIRECT='1', NW_TEST_PROOFREADER='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL The Proofreader: Reasoning hub, profile options, original passage cache, pointer, keyboard, feedback, and audio pass')

    figures_profile = tmp / 'figures-config.ini'
    figures_profile.write_text('[DEFAULT]\nFIGURE_RUNG = 1\nFIGURE_TRIALS = 5\nFIGURE_ADAPTIVE = True\n')
    figures_env = dict(env, NW_MEDIA_CONFIGFILE=str(figures_profile), NW_TEST_SLOT='105', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'figures-of-speech'],
        env=dict(figures_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert figures_profile.with_name(figures_profile.name + '.figures-of-speech-options').read_text() == (
        '[DEFAULT]\nFIGURE_RUNG = 4\nFIGURE_TRIALS = 3\nFIGURE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(figures_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='25', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(figures_env, NW_TEST_CATEGORY='4', NW_TEST_FIGURES_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    figures_round = tmp / 'figures-round.ini'
    figures_round.write_text('[DEFAULT]\nFIGURE_RUNG = 1\nFIGURE_TRIALS = 1\nFIGURE_ADAPTIVE = False\n')
    figures_data = tmp / 'figures-data'
    (figures_data / 'datasets/social').mkdir(parents=True)
    (figures_data / 'datasets/social/questions.jsonl').write_text(
        '{"kind":"metaphor","prompt":"Imported workshop question.","ask":"What does it mean?",'
        '"options":["a","b","c","d"],"answer":0}\n')
    for policy in ('1', '2'):
        played = subprocess.run(
            [str(exe), '--screen', 'figures-of-speech', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(figures_env, NW_MEDIA_CONFIGFILE=str(figures_round), NW_DATA_DIRECTORY=str(figures_data),
                     NW_TEST_DIRECT='1', NW_TEST_FIGURES=policy, NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Figures of Speech: hub, options, original question cache, keyboard, pointer, and audio pass')

    lines_profile = tmp / 'lines-config.ini'
    lines_profile.write_text('[DEFAULT]\nLINES_RUNG = 1\nLINES_TRIALS = 5\nLINES_ADAPTIVE = True\n')
    lines_env = dict(env, NW_MEDIA_CONFIGFILE=str(lines_profile), NW_TEST_SLOT='126', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'between-the-lines'],
        env=dict(lines_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert lines_profile.with_name(lines_profile.name + '.between-the-lines-options').read_text() == (
        '[DEFAULT]\nLINES_RUNG = 4\nLINES_TRIALS = 3\nLINES_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(lines_env, NW_TEST_CATEGORY='10', NW_TEST_ROW='0', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    lines_round = tmp / 'lines-round.ini'
    lines_round.write_text('[DEFAULT]\nLINES_RUNG = 1\nLINES_TRIALS = 1\nLINES_ADAPTIVE = False\n')
    lines_data = tmp / 'lines-data'
    (lines_data / 'datasets/social').mkdir(parents=True)
    # The right answer is "a" in both, first in one and second in the other.
    (lines_data / 'datasets/social/questions.jsonl').write_text(
        '{"kind":"implicature","prompt":"Imported workshop question.","ask":"Does B mean yes or no?",'
        '"options":["a","b"],"answer":0}\n'
        '{"kind":"implicature","prompt":"Second workshop question.","ask":"Does B mean yes or no?",'
        '"options":["b","a"],"answer":1}\n')
    for policy in ('1', '2'):
        played = subprocess.run(
            [str(exe), '--screen', 'between-the-lines', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(lines_env, NW_MEDIA_CONFIGFILE=str(lines_round), NW_DATA_DIRECTORY=str(lines_data),
                     NW_TEST_DIRECT='1', NW_TEST_LINES=policy, NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Between the Lines: Social hub, profile options, original question cache, keyboard, pointer, and audio pass')

    second_profile = tmp / 'second-config.ini'
    second_profile.write_text('[DEFAULT]\nSECOND_RUNG = 1\nSECOND_TRIALS = 5\nSECOND_ADAPTIVE = True\n')
    second_env = dict(env, NW_MEDIA_CONFIGFILE=str(second_profile), NW_TEST_SLOT='127', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'second-thoughts'],
        env=dict(second_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert second_profile.with_name(second_profile.name + '.second-thoughts-options').read_text() == (
        '[DEFAULT]\nSECOND_RUNG = 4\nSECOND_TRIALS = 3\nSECOND_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(second_env, NW_TEST_CATEGORY='11', NW_TEST_ROW='1', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    second_round = tmp / 'second-round.ini'
    second_round.write_text('[DEFAULT]\nSECOND_RUNG = 1\nSECOND_TRIALS = 1\nSECOND_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'second-thoughts', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(second_env, NW_MEDIA_CONFIGFILE=str(second_round), NW_TEST_DIRECT='1', NW_TEST_SECOND='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Second Thoughts: Rationality hub, profile options, keyboard answer, and audio pass')

    argue_profile = tmp / 'argue-config.ini'
    argue_profile.write_text('[DEFAULT]\nARGUE_RUNG = 1\nARGUE_TRIALS = 5\nARGUE_ADAPTIVE = True\n')
    argue_env = dict(env, NW_MEDIA_CONFIGFILE=str(argue_profile), NW_TEST_SLOT='128', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'bad-argument'],
        env=dict(argue_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert argue_profile.with_name(argue_profile.name + '.bad-argument-options').read_text() == (
        '[DEFAULT]\nARGUE_RUNG = 4\nARGUE_TRIALS = 3\nARGUE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(argue_env, NW_TEST_CATEGORY='11', NW_TEST_ROW='0', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    argue_data = tmp / 'argue-data'
    (argue_data / 'datasets/social').mkdir(parents=True)
    (argue_data / 'datasets/social/questions.jsonl').write_text(
        '{"kind":"fallacy","prompt":"Imported workshop argument.","ask":"Valid?","options":["a","b"],"answer":1}\n'
        '{"kind":"formal","prompt":"Imported formal argument.","ask":"Valid?","options":["a","b"],"answer":0}\n')
    for rung in (1, 7, 13):
        argue_round = tmp / f'argue-round-{rung}.ini'
        argue_round.write_text(f'[DEFAULT]\nARGUE_RUNG = {rung}\nARGUE_TRIALS = 1\nARGUE_ADAPTIVE = False\n')
        played = subprocess.run(
            [str(exe), '--screen', 'bad-argument', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(argue_env, NW_MEDIA_CONFIGFILE=str(argue_round), NW_DATA_DIRECTORY=str(argue_data),
                     NW_TEST_DIRECT='1', NW_TEST_ARGUE='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (rung, played.returncode, played.stderr)
    print('SDL Bad Argument: Rationality hub, profile options, question cache, keyboard answer, and audio pass')

    sense_profile = tmp / 'sense-config.ini'
    sense_profile.write_text('[DEFAULT]\nSENSE_RUNG = 1\nSENSE_TRIALS = 5\nSENSE_ADAPTIVE = True\n')
    sense_env = dict(env, NW_MEDIA_CONFIGFILE=str(sense_profile), NW_TEST_SLOT='129', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'social-sense'],
        env=dict(sense_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert sense_profile.with_name(sense_profile.name + '.social-sense-options').read_text() == (
        '[DEFAULT]\nSENSE_RUNG = 4\nSENSE_TRIALS = 3\nSENSE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(sense_env, NW_TEST_CATEGORY='10', NW_TEST_ROW='1', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    sense_data = tmp / 'sense-data'
    (sense_data / 'datasets/social').mkdir(parents=True)
    # Both kinds of the lowest rungs, and a situation asked two things.
    (sense_data / 'datasets/social/questions.jsonl').write_text(
        '{"kind":"social:feel","prompt":"A workshop situation.","ask":"How would they feel?","options":["a","b","c"],"answer":0}\n'
        '{"kind":"social:describe","prompt":"A workshop situation.","ask":"How would you describe them?","options":["a","b","c"],"answer":1}\n')
    for rung in (1,):
        sense_round = tmp / f'sense-round-{rung}.ini'
        sense_round.write_text(f'[DEFAULT]\nSENSE_RUNG = {rung}\nSENSE_TRIALS = 1\nSENSE_ADAPTIVE = False\n')
        played = subprocess.run(
            [str(exe), '--screen', 'social-sense', '--seed', '17', '--width', '912', '--height', '684'],
            env=dict(sense_env, NW_MEDIA_CONFIGFILE=str(sense_round), NW_DATA_DIRECTORY=str(sense_data),
                     NW_TEST_DIRECT='1', NW_TEST_SENSE='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (rung, played.returncode, played.stderr)
    print('SDL Social Sense: Social hub, profile options, question cache, keyboard answer, and audio pass')

    feel_profile = tmp / 'feel-config.ini'
    feel_profile.write_text('[DEFAULT]\nFEEL_RUNG = 1\nFEEL_TRIALS = 5\nFEEL_ADAPTIVE = True\n')
    feel_env = dict(env, NW_MEDIA_CONFIGFILE=str(feel_profile), NW_TEST_SLOT='130', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'which-feeling'],
        env=dict(feel_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert feel_profile.with_name(feel_profile.name + '.which-feeling-options').read_text() == (
        '[DEFAULT]\nFEEL_RUNG = 4\nFEEL_TRIALS = 3\nFEEL_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(feel_env, NW_TEST_CATEGORY='9', NW_TEST_ROW='1', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    feel_data = tmp / 'feel-data'
    (feel_data / 'datasets/emotion').mkdir(parents=True)
    (feel_data / 'datasets/emotion/goemotions.tsv').write_text(
        'joy\tA workshop comment.\nanger\tAnother workshop comment.\n')
    feel_round = tmp / 'feel-round.ini'
    feel_round.write_text('[DEFAULT]\nFEEL_RUNG = 1\nFEEL_TRIALS = 1\nFEEL_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'which-feeling', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(feel_env, NW_MEDIA_CONFIGFILE=str(feel_round), NW_DATA_DIRECTORY=str(feel_data),
                 NW_TEST_DIRECT='1', NW_TEST_FEEL='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Which Feeling: Emotion hub, profile options, comment cache, keyboard answer, and audio pass')

    strong_profile = tmp / 'strong-config.ini'
    strong_profile.write_text('[DEFAULT]\nSTRONG_RUNG = 1\nSTRONG_TRIALS = 5\nSTRONG_ADAPTIVE = True\n')
    strong_env = dict(env, NW_MEDIA_CONFIGFILE=str(strong_profile), NW_TEST_SLOT='131', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'how-strongly'],
        env=dict(strong_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert strong_profile.with_name(strong_profile.name + '.how-strongly-options').read_text() == (
        '[DEFAULT]\nSTRONG_RUNG = 4\nSTRONG_TRIALS = 3\nSTRONG_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(strong_env, NW_TEST_CATEGORY='9', NW_TEST_ROW='2', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    strong_data = tmp / 'strong-data'
    (strong_data / 'datasets/emotion').mkdir(parents=True)
    (strong_data / 'datasets/emotion/eqbench.jsonl').write_text(
        ''.join(json.dumps({'text': f'{who}: A workshop dialogue.', 'who': who, 'emotions': ['Happy', 'Sad', 'Angry', 'Afraid'],
                            'scores': scores}) + '\n' for who, scores in (('Ana', [9, 1, 0, 2]), ('Ben', [0, 3, 9, 1]))))
    strong_round = tmp / 'strong-round.ini'
    strong_round.write_text('[DEFAULT]\nSTRONG_RUNG = 1\nSTRONG_TRIALS = 1\nSTRONG_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'how-strongly', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(strong_env, NW_MEDIA_CONFIGFILE=str(strong_round), NW_DATA_DIRECTORY=str(strong_data),
                 NW_TEST_DIRECT='1', NW_TEST_STRONG='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL How Strongly: Emotion hub, profile options, dialogue cache, keyboard answer, and audio pass')

    read_profile = tmp / 'read-config.ini'
    read_profile.write_text('[DEFAULT]\nREAD_RUNG = 1\nREAD_TRIALS = 5\nREAD_ADAPTIVE = True\n')
    read_env = dict(env, NW_MEDIA_CONFIGFILE=str(read_profile), NW_TEST_SLOT='132', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'reading-people'],
        env=dict(read_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert read_profile.with_name(read_profile.name + '.reading-people-options').read_text() == (
        '[DEFAULT]\nREAD_RUNG = 4\nREAD_TRIALS = 3\nREAD_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(read_env, NW_TEST_CATEGORY='9', NW_TEST_ROW='3', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    read_data = tmp / 'read-data'
    (read_data / 'datasets/emotion').mkdir(parents=True)
    (read_data / 'datasets/emotion/emobench.jsonl').write_text(
        ''.join(json.dumps({'kind': 'understand', 'scenario': f'{who} won a prize at the workshop.', 'subject': who,
                            'choices': ['Glad', 'Sad', 'Bored'], 'answer': 'Glad', 'causes': ['The prize', 'The rain'],
                            'cause': 'The prize'}) + '\n' for who in ('Ana', 'Ben')))
    read_round = tmp / 'read-round.ini'
    read_round.write_text('[DEFAULT]\nREAD_RUNG = 1\nREAD_TRIALS = 1\nREAD_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'reading-people', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(read_env, NW_MEDIA_CONFIGFILE=str(read_round), NW_DATA_DIRECTORY=str(read_data),
                 NW_TEST_DIRECT='1', NW_TEST_READ='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Reading People: Emotion hub, profile options, story cache, keyboard answer, and audio pass')

    why_profile = tmp / 'why-config.ini'
    why_profile.write_text('[DEFAULT]\nWHY_RUNG = 1\nWHY_TRIALS = 5\nWHY_ADAPTIVE = True\n')
    why_env = dict(env, NW_MEDIA_CONFIGFILE=str(why_profile), NW_TEST_SLOT='133', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'why-they-feel'],
        env=dict(why_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert why_profile.with_name(why_profile.name + '.why-they-feel-options').read_text() == (
        '[DEFAULT]\nWHY_RUNG = 4\nWHY_TRIALS = 3\nWHY_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(why_env, NW_TEST_CATEGORY='9', NW_TEST_ROW='4', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    why_round = tmp / 'why-round.ini'
    why_round.write_text('[DEFAULT]\nWHY_RUNG = 1\nWHY_TRIALS = 1\nWHY_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'why-they-feel', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(why_env, NW_MEDIA_CONFIGFILE=str(why_round),
                 NW_TEST_DIRECT='1', NW_TEST_WHY='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Why They Feel: Emotion hub, profile options, keyboard answer, and audio pass')

    tone_profile = tmp / 'tone-config.ini'
    tone_profile.write_text('[DEFAULT]\nVOICE_RUNG = 1\nVOICE_TRIALS = 5\nVOICE_ADAPTIVE = True\n')
    tone_env = dict(env, NW_MEDIA_CONFIGFILE=str(tone_profile), NW_TEST_SLOT='134', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'tone-of-voice'],
        env=dict(tone_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert tone_profile.with_name(tone_profile.name + '.tone-of-voice-options').read_text() == (
        '[DEFAULT]\nVOICE_RUNG = 4\nVOICE_TRIALS = 3\nVOICE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(tone_env, NW_TEST_CATEGORY='9', NW_TEST_ROW='5', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    tone_round = tmp / 'tone-round.ini'
    tone_round.write_text('[DEFAULT]\nVOICE_RUNG = 1\nVOICE_TRIALS = 1\nVOICE_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'tone-of-voice', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(tone_env, NW_MEDIA_CONFIGFILE=str(tone_round),
                 NW_TEST_DIRECT='1', NW_TEST_TONE='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Tone of Voice: Emotion hub, profile options, keyboard answer, and audio pass')

    emo_profile = tmp / 'emo-config.ini'
    emo_profile.write_text('[DEFAULT]\nEMO_RUNG = 1\nEMO_TRIALS = 5\nEMO_ADAPTIVE = True\n')
    emo_env = dict(env, NW_MEDIA_CONFIGFILE=str(emo_profile), NW_TEST_SLOT='135', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'emotion'],
        env=dict(emo_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert emo_profile.with_name(emo_profile.name + '.emotion-options').read_text() == (
        '[DEFAULT]\nEMO_RUNG = 4\nEMO_TRIALS = 3\nEMO_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(emo_env, NW_TEST_CATEGORY='9', NW_TEST_ROW='0', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    emo_round = tmp / 'emo-round.ini'
    emo_round.write_text('[DEFAULT]\nEMO_RUNG = 1\nEMO_TRIALS = 1\nEMO_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'emotion', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(emo_env, NW_MEDIA_CONFIGFILE=str(emo_round),
                 NW_TEST_DIRECT='1', NW_TEST_EMO='1', NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Emotion: Emotion hub, profile options, keyboard answer, and audio pass')

    cog_profile = tmp / 'crazy-cog-config.ini'
    cog_profile.write_text('[DEFAULT]\nCOG_RUNG = 1\nCOG_TRIALS = 5\nCOG_ADAPTIVE = True\n')
    cog_env = dict(env, NW_MEDIA_CONFIGFILE=str(cog_profile), NW_TEST_SLOT='106', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'crazy-cog'],
        env=dict(cog_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert cog_profile.with_name(cog_profile.name + '.crazy-cog-options').read_text() == (
        '[DEFAULT]\nCOG_RUNG = 4\nCOG_TRIALS = 3\nCOG_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(cog_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='26', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    pointer_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
        env=dict(cog_env, NW_TEST_CATEGORY='4', NW_TEST_CRAZY_COG_HUB_POINTER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert pointer_hub.returncode == 0 and 'SDL event replay: PASS' in pointer_hub.stdout, (
        pointer_hub.returncode, pointer_hub.stderr)
    cog_round = tmp / 'crazy-cog-round.ini'
    cog_round.write_text('[DEFAULT]\nCOG_RUNG = 20\nCOG_TRIALS = 1\nCOG_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'crazy-cog', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(cog_env, NW_MEDIA_CONFIGFILE=str(cog_round), NW_TEST_DIRECT='1', NW_TEST_CRAZY_COG='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print('SDL Crazy Cog: hub, profile settings, plane shortcuts, drag, and PCM playback pass')

    cipher_profile = tmp / 'cipher-abyss-config.ini'
    cipher_profile.write_text('[DEFAULT]\nCIPHER_RUNG = 1\nCIPHER_TRIALS = 5\nCIPHER_ADAPTIVE = True\n')
    cipher_data = tmp / 'cipher-abyss-data'
    cipher_data.mkdir()
    cipher_env = dict(env, NW_MEDIA_CONFIGFILE=str(cipher_profile), NW_DATA_DIRECTORY=str(cipher_data),
                      NW_TEST_SLOT='107', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'cipher-abyss'],
        env=dict(cipher_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert cipher_profile.with_name(cipher_profile.name + '.cipher-abyss-options').read_text() == (
        '[DEFAULT]\nCIPHER_RUNG = 4\nCIPHER_TRIALS = 3\nCIPHER_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(cipher_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='27', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    cipher_library = cipher_data / 'cipher_abyss_library.json'
    cipher_library.write_text(json.dumps({'version': 1, 'operators': {'rev': 2, 'shift': 7}}))
    cipher_round = tmp / 'cipher-abyss-round.ini'
    cipher_round.write_text('[DEFAULT]\nCIPHER_RUNG = 1\nCIPHER_TRIALS = 1\nCIPHER_ADAPTIVE = False\n')
    played = subprocess.run(
        [str(exe), '--screen', 'cipher-abyss', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(cipher_env, NW_MEDIA_CONFIGFILE=str(cipher_round), NW_TEST_DIRECT='1', NW_TEST_CIPHER_ABYSS='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    assert (cipher_data / 'cipher_abyss_notebook.txt').read_text().endswith(' 1  1 0 1 -> 1 1 0\n')
    assert (cipher_data / 'cipher_abyss_tutorial_seen').read_text() == '1\n'
    metrics = json.loads((cipher_data / 'cipher_abyss_rounds.jsonl').read_text())
    assert (metrics['won'], metrics['questions'], metrics['bits']) == (True, 2, [2.874]), metrics
    assert json.loads(cipher_library.read_text()) == {
        'version': 1, 'operators': {'rev': 2, 'rot': 1, 'shift': 1},
    }
    print('SDL Cipher Abyss: hub, original options, full seeded round, audio, notebook, tutorial, metrics, and operator library pass')

    potter_profile = tmp / 'potters-wheel-config.ini'
    potter_profile.write_text('[DEFAULT]\nPOTTER_RUNG = 1\nPOTTER_TRIALS = 5\nPOTTER_ADAPTIVE = True\n')
    potter_env = dict(env, NW_MEDIA_CONFIGFILE=str(potter_profile), NW_TEST_SLOT='108', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'potters-wheel'],
        env=dict(potter_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert potter_profile.with_name(potter_profile.name + '.potters-wheel-options').read_text() == (
        '[DEFAULT]\nPOTTER_RUNG = 4\nPOTTER_TRIALS = 3\nPOTTER_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(potter_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='25', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    potter_round = tmp / 'potters-wheel-round.ini'
    potter_round.write_text('[DEFAULT]\nPOTTER_RUNG = 4\nPOTTER_TRIALS = 1\nPOTTER_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'potters-wheel', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(potter_env, NW_MEDIA_CONFIGFILE=str(potter_round), NW_TEST_DIRECT='1', NW_TEST_POTTER='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Potter's Wheel: Attention hub, profile options, wheel keys, mouse shaping, feedback, and PCM pass")

    conductor_profile = tmp / 'conductor-config.ini'
    conductor_profile.write_text('[DEFAULT]\nCONDUCT_RUNG = 1\nCONDUCT_TRIALS = 5\nCONDUCT_ADAPTIVE = True\n')
    conductor_env = dict(env, NW_MEDIA_CONFIGFILE=str(conductor_profile), NW_TEST_SLOT='109', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'conductor'],
        env=dict(conductor_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert conductor_profile.with_name(conductor_profile.name + '.conductor-options').read_text() == (
        '[DEFAULT]\nCONDUCT_RUNG = 4\nCONDUCT_TRIALS = 3\nCONDUCT_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(conductor_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='26', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    conductor_round = tmp / 'conductor-round.ini'
    conductor_round.write_text('[DEFAULT]\nCONDUCT_RUNG = 1\nCONDUCT_TRIALS = 1\nCONDUCT_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'conductor', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(conductor_env, NW_MEDIA_CONFIGFILE=str(conductor_round), NW_TEST_DIRECT='1', NW_TEST_CONDUCTOR='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Conductor: Attention hub, profile options, volume keys, section clicks, feedback, and PCM pass")

    tightrope_profile = tmp / 'tightrope-config.ini'
    tightrope_profile.write_text('[DEFAULT]\nROPE_RUNG = 1\nROPE_TRIALS = 5\nROPE_ADAPTIVE = True\n')
    tightrope_env = dict(env, NW_MEDIA_CONFIGFILE=str(tightrope_profile), NW_TEST_SLOT='110', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'tightrope'],
        env=dict(tightrope_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert tightrope_profile.with_name(tightrope_profile.name + '.tightrope-options').read_text() == (
        '[DEFAULT]\nROPE_RUNG = 4\nROPE_TRIALS = 3\nROPE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(tightrope_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='27', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    tightrope_round = tmp / 'tightrope-round.ini'
    tightrope_round.write_text('[DEFAULT]\nROPE_RUNG = 1\nROPE_TRIALS = 1\nROPE_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'tightrope', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(tightrope_env, NW_MEDIA_CONFIGFILE=str(tightrope_round), NW_TEST_DIRECT='1', NW_TEST_TIGHTROPE='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Tightrope: Attention hub, profile options, step keys, pole movement, feedback, and PCM pass")

    signpainter_profile = tmp / 'signpainter-config.ini'
    signpainter_profile.write_text('[DEFAULT]\nSIGN_RUNG = 1\nSIGN_TRIALS = 5\nSIGN_ADAPTIVE = True\n')
    signpainter_env = dict(env, NW_MEDIA_CONFIGFILE=str(signpainter_profile), NW_TEST_SLOT='111', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'sign-painter'],
        env=dict(signpainter_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert signpainter_profile.with_name(signpainter_profile.name + '.sign-painter-options').read_text() == (
        '[DEFAULT]\nSIGN_RUNG = 4\nSIGN_TRIALS = 3\nSIGN_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(signpainter_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='28', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    signpainter_round = tmp / 'signpainter-round.ini'
    signpainter_round.write_text('[DEFAULT]\nSIGN_RUNG = 4\nSIGN_TRIALS = 1\nSIGN_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'sign-painter', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(signpainter_env, NW_MEDIA_CONFIGFILE=str(signpainter_round), NW_TEST_DIRECT='1', NW_TEST_SIGN_PAINTER='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Sign Painter: Attention hub, profile options, palette keys, brush clicks, feedback, and PCM pass")

    bartender_profile = tmp / 'bartender-config.ini'
    bartender_profile.write_text('[DEFAULT]\nBAR_RUNG = 1\nBAR_TRIALS = 5\nBAR_ADAPTIVE = True\n')
    bartender_env = dict(env, NW_MEDIA_CONFIGFILE=str(bartender_profile), NW_TEST_SLOT='112', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'bartender'],
        env=dict(bartender_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert bartender_profile.with_name(bartender_profile.name + '.bartender-options').read_text() == (
        '[DEFAULT]\nBAR_RUNG = 4\nBAR_TRIALS = 3\nBAR_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(bartender_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='29', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    bartender_round = tmp / 'bartender-round.ini'
    bartender_round.write_text('[DEFAULT]\nBAR_RUNG = 1\nBAR_TRIALS = 1\nBAR_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'bartender', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(bartender_env, NW_MEDIA_CONFIGFILE=str(bartender_round), NW_TEST_DIRECT='1', NW_TEST_BARTENDER='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Bartender: Attention hub, profile options, ice keys, pouring, sliding, feedback, and PCM pass")

    lockpick_profile = tmp / 'lockpick-config.ini'
    lockpick_profile.write_text('[DEFAULT]\nPICK_RUNG = 1\nPICK_TRIALS = 5\nPICK_ADAPTIVE = True\n')
    lockpick_env = dict(env, NW_MEDIA_CONFIGFILE=str(lockpick_profile), NW_TEST_SLOT='113', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'lock-pick'],
        env=dict(lockpick_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert lockpick_profile.with_name(lockpick_profile.name + '.lock-pick-options').read_text() == (
        '[DEFAULT]\nPICK_RUNG = 4\nPICK_TRIALS = 3\nPICK_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(lockpick_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='30', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    lockpick_round = tmp / 'lockpick-round.ini'
    lockpick_round.write_text('[DEFAULT]\nPICK_RUNG = 1\nPICK_TRIALS = 1\nPICK_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'lock-pick', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(lockpick_env, NW_MEDIA_CONFIGFILE=str(lockpick_round), NW_TEST_DIRECT='1', NW_TEST_LOCK_PICK='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Lock Pick: Attention hub, profile options, tension aliases, key releases, focus loss, feedback, and PCM pass")

    airhockey_profile = tmp / 'airhockey-config.ini'
    airhockey_profile.write_text('[DEFAULT]\nHOCKEY_RUNG = 1\nHOCKEY_TRIALS = 5\nHOCKEY_ADAPTIVE = True\n')
    airhockey_env = dict(env, NW_MEDIA_CONFIGFILE=str(airhockey_profile), NW_TEST_SLOT='114', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'air-hockey'],
        env=dict(airhockey_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert airhockey_profile.with_name(airhockey_profile.name + '.air-hockey-options').read_text() == (
        '[DEFAULT]\nHOCKEY_RUNG = 4\nHOCKEY_TRIALS = 3\nHOCKEY_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(airhockey_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='31', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    airhockey_round = tmp / 'airhockey-round.ini'
    airhockey_round.write_text('[DEFAULT]\nHOCKEY_RUNG = 1\nHOCKEY_TRIALS = 1\nHOCKEY_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'air-hockey', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(airhockey_env, NW_MEDIA_CONFIGFILE=str(airhockey_round), NW_TEST_DIRECT='1', NW_TEST_AIR_HOCKEY='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=120,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Air Hockey: Attention hub, profile options, four held bar keys, focus loss, an unattended game's verdict, hold, and PCM pass")

    semaphore_profile = tmp / 'semaphore-config.ini'
    semaphore_profile.write_text('[DEFAULT]\nSEMA_RUNG = 1\nSEMA_TRIALS = 5\nSEMA_ADAPTIVE = True\n')
    semaphore_env = dict(env, NW_MEDIA_CONFIGFILE=str(semaphore_profile), NW_TEST_SLOT='115', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'semaphore'],
        env=dict(semaphore_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert semaphore_profile.with_name(semaphore_profile.name + '.semaphore-options').read_text() == (
        '[DEFAULT]\nSEMA_RUNG = 4\nSEMA_TRIALS = 3\nSEMA_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(semaphore_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='32', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    semaphore_round = tmp / 'semaphore-round.ini'
    semaphore_round.write_text('[DEFAULT]\nSEMA_RUNG = 1\nSEMA_TRIALS = 1\nSEMA_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'semaphore', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(semaphore_env, NW_MEDIA_CONFIGFILE=str(semaphore_round), NW_TEST_DIRECT='1', NW_TEST_SEMAPHORE='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=120,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Semaphore: Attention hub, profile options, letter keys (C a letter in play), focus loss, a struck message's verdict, hold, and PCM pass")

    puppets_profile = tmp / 'puppets-config.ini'
    puppets_profile.write_text('[DEFAULT]\nPUPPET_RUNG = 1\nPUPPET_TRIALS = 5\nPUPPET_ADAPTIVE = True\n')
    puppets_env = dict(env, NW_MEDIA_CONFIGFILE=str(puppets_profile), NW_TEST_SLOT='116', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'shadow-puppets'],
        env=dict(puppets_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert puppets_profile.with_name(puppets_profile.name + '.shadow-puppets-options').read_text() == (
        '[DEFAULT]\nPUPPET_RUNG = 4\nPUPPET_TRIALS = 3\nPUPPET_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(puppets_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='33', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    puppets_round = tmp / 'puppets-round.ini'
    puppets_round.write_text('[DEFAULT]\nPUPPET_RUNG = 1\nPUPPET_TRIALS = 1\nPUPPET_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'shadow-puppets', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(puppets_env, NW_MEDIA_CONFIGFILE=str(puppets_round), NW_TEST_DIRECT='1', NW_TEST_SHADOW_PUPPETS='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Shadow Puppets: Attention hub, profile options, Q and E held in play (Q never the shell's quit), focus loss, "
          "an unturned figure's verdict, hold, and PCM pass")

    watch_profile = tmp / 'watch-config.ini'
    watch_profile.write_text('[DEFAULT]\nWATCH_RUNG = 1\nWATCH_TRIALS = 5\nWATCH_ADAPTIVE = True\n')
    watch_env = dict(env, NW_MEDIA_CONFIGFILE=str(watch_profile), NW_TEST_SLOT='117', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'night-watch'],
        env=dict(watch_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert watch_profile.with_name(watch_profile.name + '.night-watch-options').read_text() == (
        '[DEFAULT]\nWATCH_RUNG = 4\nWATCH_TRIALS = 3\nWATCH_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(watch_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='34', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    watch_round = tmp / 'watch-round.ini'
    watch_round.write_text('[DEFAULT]\nWATCH_RUNG = 1\nWATCH_TRIALS = 1\nWATCH_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'night-watch', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(watch_env, NW_MEDIA_CONFIGFILE=str(watch_round), NW_TEST_DIRECT='1', NW_TEST_NIGHT_WATCH='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Night Watch: Attention hub, profile options, Left/A/D held in play, focus loss, "
          "a robbed safe's verdict, hold, and PCM pass")

    kerb_profile = tmp / 'kerb-config.ini'
    kerb_profile.write_text('[DEFAULT]\nKERB_RUNG = 1\nKERB_TRIALS = 5\nKERB_ADAPTIVE = True\n')
    kerb_env = dict(env, NW_MEDIA_CONFIGFILE=str(kerb_profile), NW_TEST_SLOT='118', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'kerbside'],
        env=dict(kerb_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert kerb_profile.with_name(kerb_profile.name + '.kerbside-options').read_text() == (
        '[DEFAULT]\nKERB_RUNG = 4\nKERB_TRIALS = 3\nKERB_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(kerb_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='35', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    kerb_round = tmp / 'kerb-round.ini'
    kerb_round.write_text('[DEFAULT]\nKERB_RUNG = 1\nKERB_TRIALS = 1\nKERB_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'kerbside', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(kerb_env, NW_MEDIA_CONFIGFILE=str(kerb_round), NW_TEST_DIRECT='1', NW_TEST_KERBSIDE='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Kerbside: Attention hub, profile options, Up/W/S held in play, focus loss, "
          "a walker left on the kerb, hold, and PCM pass")

    steady_profile = tmp / 'steady-config.ini'
    steady_profile.write_text('[DEFAULT]\nSTEADY_RUNG = 1\nSTEADY_TRIALS = 5\nSTEADY_ADAPTIVE = True\n')
    steady_env = dict(env, NW_MEDIA_CONFIGFILE=str(steady_profile), NW_TEST_SLOT='119', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'steadicam'],
        env=dict(steady_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert steady_profile.with_name(steady_profile.name + '.steadicam-options').read_text() == (
        '[DEFAULT]\nSTEADY_RUNG = 4\nSTEADY_TRIALS = 3\nSTEADY_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(steady_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='36', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    steady_round = tmp / 'steady-round.ini'
    steady_round.write_text('[DEFAULT]\nSTEADY_RUNG = 1\nSTEADY_TRIALS = 1\nSTEADY_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'steadicam', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(steady_env, NW_MEDIA_CONFIGFILE=str(steady_round), NW_TEST_DIRECT='1', NW_TEST_STEADICAM='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Steadicam: Attention hub, profile options, Left/A/Q held in play, focus loss, drag, wheel, "
          "a lost walker, and hold pass")

    kick_profile = tmp / 'kick-config.ini'
    kick_profile.write_text('[DEFAULT]\nKICK_RUNG = 1\nKICK_TRIALS = 5\nKICK_ADAPTIVE = True\n')
    kick_env = dict(env, NW_MEDIA_CONFIGFILE=str(kick_profile), NW_TEST_SLOT='120', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'free-kick'],
        env=dict(kick_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert kick_profile.with_name(kick_profile.name + '.free-kick-options').read_text() == (
        '[DEFAULT]\nKICK_RUNG = 4\nKICK_TRIALS = 3\nKICK_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(kick_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='37', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    kick_round = tmp / 'kick-round.ini'
    kick_round.write_text('[DEFAULT]\nKICK_RUNG = 1\nKICK_TRIALS = 1\nKICK_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'free-kick', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(kick_env, NW_MEDIA_CONFIGFILE=str(kick_round), NW_TEST_DIRECT='1', NW_TEST_FREE_KICK='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Free Kick: Attention hub, profile options, Left/W/A held in play, focus loss, Space's kick off the ring, "
          "and hold pass")

    glove_profile = tmp / 'glove-config.ini'
    glove_profile.write_text('[DEFAULT]\nGLOVE_RUNG = 1\nGLOVE_TRIALS = 5\nGLOVE_ADAPTIVE = True\n')
    glove_env = dict(env, NW_MEDIA_CONFIGFILE=str(glove_profile), NW_TEST_SLOT='121', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'glove'],
        env=dict(glove_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert glove_profile.with_name(glove_profile.name + '.glove-options').read_text() == (
        '[DEFAULT]\nGLOVE_RUNG = 4\nGLOVE_TRIALS = 3\nGLOVE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(glove_env, NW_TEST_CATEGORY='2', NW_TEST_ROW='38', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    glove_inning = tmp / 'glove-inning.ini'
    glove_inning.write_text('[DEFAULT]\nGLOVE_RUNG = 1\nGLOVE_TRIALS = 1\nGLOVE_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'glove', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(glove_env, NW_MEDIA_CONFIGFILE=str(glove_inning), NW_TEST_DIRECT='1', NW_TEST_GLOVE='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Glove: Attention hub, profile options, Up/W/A held in play, focus loss, Space ignored in play, "
          "two pitches let by, and hold pass")

    ear_profile = tmp / 'ear-config.ini'
    ear_profile.write_text('[DEFAULT]\nEAR_RUNG = 1\nEAR_TRIALS = 5\nEAR_ADAPTIVE = True\n')
    ear_env = dict(env, NW_MEDIA_CONFIGFILE=str(ear_profile), NW_TEST_SLOT='122', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'by-ear'],
        env=dict(ear_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert ear_profile.with_name(ear_profile.name + '.by-ear-options').read_text() == (
        '[DEFAULT]\nEAR_RUNG = 4\nEAR_TRIALS = 3\nEAR_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(ear_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='15', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    ear_try = tmp / 'ear-try.ini'
    ear_try.write_text('[DEFAULT]\nEAR_RUNG = 1\nEAR_TRIALS = 1\nEAR_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'by-ear', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(ear_env, NW_MEDIA_CONFIGFILE=str(ear_try), NW_TEST_DIRECT='1', NW_TEST_BY_EAR='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL By Ear: Perception hub, profile options, a key ignored while the tune plays, Space ignored in play, "
          "the tune played back on G and E, and hold pass")

    tune_profile = tmp / 'tune-config.ini'
    tune_profile.write_text('[DEFAULT]\nTUNE_RUNG = 1\nTUNE_TRIALS = 5\nTUNE_ADAPTIVE = True\n')
    tune_env = dict(env, NW_MEDIA_CONFIGFILE=str(tune_profile), NW_TEST_SLOT='123', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'piano-tuner'],
        env=dict(tune_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert tune_profile.with_name(tune_profile.name + '.piano-tuner-options').read_text() == (
        '[DEFAULT]\nTUNE_RUNG = 4\nTUNE_TRIALS = 3\nTUNE_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(tune_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='16', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    tune_try = tmp / 'tune-try.ini'
    tune_try.write_text('[DEFAULT]\nTUNE_RUNG = 1\nTUNE_TRIALS = 1\nTUNE_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'piano-tuner', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(tune_env, NW_MEDIA_CONFIGFILE=str(tune_try), NW_TEST_DIRECT='1', NW_TEST_PIANO_TUNER='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Piano Tuner: Perception hub, profile options, Up/W held in play, focus loss, Shift and Down, "
          "Enter judged sharp, and hold pass")

    cricket_profile = tmp / 'cricket-config.ini'
    cricket_profile.write_text('[DEFAULT]\nCRICKET_RUNG = 1\nCRICKET_TRIALS = 5\nCRICKET_ADAPTIVE = True\n')
    cricket_env = dict(env, NW_MEDIA_CONFIGFILE=str(cricket_profile), NW_TEST_SLOT='124', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'cricket-hunt'],
        env=dict(cricket_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert cricket_profile.with_name(cricket_profile.name + '.cricket-hunt-options').read_text() == (
        '[DEFAULT]\nCRICKET_RUNG = 4\nCRICKET_TRIALS = 3\nCRICKET_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(cricket_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='17', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    cricket_try = tmp / 'cricket-try.ini'
    cricket_try.write_text('[DEFAULT]\nCRICKET_RUNG = 1\nCRICKET_TRIALS = 1\nCRICKET_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'cricket-hunt', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(cricket_env, NW_MEDIA_CONFIGFILE=str(cricket_try), NW_TEST_DIRECT='1', NW_TEST_CRICKET_HUNT='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Cricket Hunt: Perception hub, profile options, W/Up held in play, focus loss, Q held in play, "
          "three grabs at nothing, and hold pass")

    claw_profile = tmp / 'claw-config.ini'
    claw_profile.write_text('[DEFAULT]\nCLAW_RUNG = 1\nCLAW_TRIALS = 5\nCLAW_ADAPTIVE = True\n')
    claw_env = dict(env, NW_MEDIA_CONFIGFILE=str(claw_profile), NW_TEST_SLOT='125', NW_TEST_OPTION_SLOT='-1')
    options = subprocess.run(
        [str(exe), '--screen', 'claw-machine'],
        env=dict(claw_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert options.returncode == 0 and 'SDL event replay: PASS' in options.stdout, (options.returncode, options.stderr)
    assert claw_profile.with_name(claw_profile.name + '.claw-machine-options').read_text() == (
        '[DEFAULT]\nCLAW_RUNG = 4\nCLAW_TRIALS = 3\nCLAW_ADAPTIVE = False\n')
    hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(claw_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='18', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub.returncode == 0 and 'SDL event replay: PASS' in hub.stdout, (hub.returncode, hub.stderr)
    claw_try = tmp / 'claw-try.ini'
    claw_try.write_text('[DEFAULT]\nCLAW_RUNG = 1\nCLAW_TRIALS = 1\nCLAW_ADAPTIVE = True\n')
    played = subprocess.run(
        [str(exe), '--screen', 'claw-machine', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(claw_env, NW_MEDIA_CONFIGFILE=str(claw_try), NW_TEST_DIRECT='1', NW_TEST_CLAW_MACHINE='1',
                 NW_TEST_CLOSE_WINDOW='1', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=180,
    )
    assert played.returncode == 0 and 'SDL event replay: PASS' in played.stdout, (played.returncode, played.stderr)
    print("SDL Claw Machine: Perception hub, profile options, Left/A held in play, focus loss, W held in play, "
          "Enter's drop missed, Space after it ignored, and hold pass")

    signals_profile = tmp / 'signals-config.ini'
    signals_profile.write_text('[DEFAULT]\nSIGNALS_RUNG = 1\nSIGNALS_TRIALS = 5\nSIGNALS_ADAPTIVE = True\n')
    signals_env = dict(env, NW_MEDIA_CONFIGFILE=str(signals_profile), NW_TEST_SLOT='79', NW_TEST_OPTION_SLOT='-1')
    signals_options = subprocess.run(
        [str(exe), '--screen', 'signals'],
        env=dict(signals_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert signals_options.returncode == 0 and 'SDL event replay: PASS' in signals_options.stdout, signals_options.stderr
    assert signals_profile.with_name(signals_profile.name + '.signals-options').read_text() == (
        '[DEFAULT]\nSIGNALS_RUNG = 4\nSIGNALS_TRIALS = 3\nSIGNALS_ADAPTIVE = False\n')
    signals_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(signals_env, NW_TEST_CATEGORY='4', NW_TEST_ROW='18', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert signals_hub.returncode == 0 and 'SDL event replay: PASS' in signals_hub.stdout, signals_hub.stderr
    signals_round = tmp / 'signals-round.ini'
    signals_round.write_text('[DEFAULT]\nSIGNALS_RUNG = 12\nSIGNALS_TRIALS = 1\n')
    signals_played = subprocess.run(
        [str(exe), '--screen', 'signals', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(signals_env, NW_MEDIA_CONFIGFILE=str(signals_round), NW_TEST_DIRECT='1',
                 NW_TEST_SIGNALS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert signals_played.returncode == 0 and 'SDL event replay: PASS' in signals_played.stdout, (
        signals_played.returncode, signals_played.stderr)
    print('SDL Signals: profile settings, hub route, pointer and key play, and perfect-game verdict pass')

    captcha_profile = tmp / 'captcha-config.ini'
    captcha_profile.write_text('[DEFAULT]\nCAPTCHA_RUNG = 1\nCAPTCHA_TRIALS = 5\nCAPTCHA_ADAPTIVE = True\n')
    captcha_env = dict(env, NW_MEDIA_CONFIGFILE=str(captcha_profile), NW_TEST_SLOT='78', NW_TEST_OPTION_SLOT='-1')
    captcha_options = subprocess.run(
        [str(exe), '--screen', 'captcha'],
        env=dict(captcha_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert captcha_options.returncode == 0 and 'SDL event replay: PASS' in captcha_options.stdout, captcha_options.stderr
    assert captcha_profile.with_name(captcha_profile.name + '.captcha-options').read_text() == (
        '[DEFAULT]\nCAPTCHA_RUNG = 4\nCAPTCHA_TRIALS = 3\nCAPTCHA_ADAPTIVE = False\n')
    captcha_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(captcha_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='14', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert captcha_hub.returncode == 0 and 'SDL event replay: PASS' in captcha_hub.stdout, captcha_hub.stderr
    captcha_round = tmp / 'captcha-round.ini'
    captcha_round.write_text('[DEFAULT]\nCAPTCHA_RUNG = 30\nCAPTCHA_TRIALS = 1\n')
    captcha_played = subprocess.run(
        [str(exe), '--screen', 'captcha', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(captcha_env, NW_MEDIA_CONFIGFILE=str(captcha_round), NW_TEST_DIRECT='1',
                 NW_TEST_CAPTCHA='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert captcha_played.returncode == 0 and 'SDL event replay: PASS' in captcha_played.stdout, (
        captcha_played.returncode, captcha_played.stderr)
    print('SDL Captcha: profile settings, hub route, click start, typing, erase, and dense-round verdict pass')

    shadow_profile = tmp / 'shadow-play-config.ini'
    shadow_profile.write_text('[DEFAULT]\nSHADOW_RUNG = 1\nSHADOW_TRIALS = 5\nSHADOW_ADAPTIVE = True\n')
    shadow_env = dict(env, NW_MEDIA_CONFIGFILE=str(shadow_profile), NW_TEST_SLOT='77', NW_TEST_OPTION_SLOT='-1')
    shadow_options = subprocess.run(
        [str(exe), '--screen', 'shadow-play'],
        env=dict(shadow_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert shadow_options.returncode == 0 and 'SDL event replay: PASS' in shadow_options.stdout, shadow_options.stderr
    assert shadow_profile.with_name(shadow_profile.name + '.shadow-play-options').read_text() == (
        '[DEFAULT]\nSHADOW_RUNG = 4\nSHADOW_TRIALS = 3\nSHADOW_ADAPTIVE = False\n')
    shadow_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(shadow_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='13', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert shadow_hub.returncode == 0 and 'SDL event replay: PASS' in shadow_hub.stdout, shadow_hub.stderr
    shadow_round = tmp / 'shadow-play-round.ini'
    shadow_round.write_text('[DEFAULT]\nSHADOW_RUNG = 1\nSHADOW_TRIALS = 1\n')
    shadow_played = subprocess.run(
        [str(exe), '--screen', 'shadow-play', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(shadow_env, NW_MEDIA_CONFIGFILE=str(shadow_round), NW_TEST_DIRECT='1',
                 NW_TEST_SHADOW_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert shadow_played.returncode == 0 and 'SDL event replay: PASS' in shadow_played.stdout, (
        shadow_played.returncode, shadow_played.stderr)
    print('SDL Shadow Play: profile settings, hub route, held and drag controls, PCM and verdict pass')

    tuner_profile = tmp / 'tuner-config.ini'
    tuner_profile.write_text('[DEFAULT]\nTUNER_RUNG = 1\nTUNER_TRIALS = 5\nTUNER_ADAPTIVE = True\n')
    tuner_env = dict(env, NW_MEDIA_CONFIGFILE=str(tuner_profile), NW_TEST_SLOT='76',
                     NW_DATA_DIRECTORY=str(tmp / 'tuner-data'), NW_TEST_OPTION_SLOT='-1')
    tuner_options = subprocess.run(
        [str(exe), '--screen', 'tuner'],
        env=dict(tuner_env, NW_TEST_DIRECT='1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert tuner_options.returncode == 0 and 'SDL event replay: PASS' in tuner_options.stdout, tuner_options.stderr
    assert tuner_profile.with_name(tuner_profile.name + '.tuner-options').read_text() == (
        '[DEFAULT]\nTUNER_RUNG = 4\nTUNER_TRIALS = 3\nTUNER_ADAPTIVE = False\n')
    tuner_hub = subprocess.run(
        [str(exe), '--screen', 'taskhub'],
        env=dict(tuner_env, NW_TEST_CATEGORY='3', NW_TEST_ROW='12', NW_TEST_OPTION='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert tuner_hub.returncode == 0 and 'SDL event replay: PASS' in tuner_hub.stdout, tuner_hub.stderr
    tuner_round = tmp / 'tuner-round.ini'
    tuner_round.write_text('[DEFAULT]\nTUNER_RUNG = 1\nTUNER_TRIALS = 1\n')
    tuner_played = subprocess.run(
        [str(exe), '--screen', 'tuner', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(tuner_env, NW_MEDIA_CONFIGFILE=str(tuner_round), NW_TEST_DIRECT='1',
                 NW_TEST_TUNER_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert tuner_played.returncode == 0 and 'SDL event replay: PASS' in tuner_played.stdout, (
        tuner_played.returncode, tuner_played.stderr)
    tuner_dump = subprocess.run(
        [str(exe), '--screen', 'tuner', '--seed', '17', '--trials', '2', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(tuner_profile),
                 NW_DATA_DIRECTORY=str(tmp / 'tuner-data')),
        check=True, capture_output=True, text=True, timeout=20,
    )
    tuner_states = [ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
                    for line in tuner_dump.stdout.splitlines() if line.startswith('# state=')]
    assert [state[:4] for state in tuner_states] == [(0, 4, 0, 3), (1, 4, 1, 3)], tuner_states

    tuner_index = root / 'res' / 'misc' / 'esc50' / 'index.tsv'
    installed_index = exe.parent / 'res' / 'misc' / 'esc50' / 'index.tsv'
    installed_index.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tuner_index, installed_index)
    tuner_bank = tmp / 'tuner-data' / 'datasets' / 'esc50'
    tuner_bank.mkdir(parents=True)
    valid_rows = []
    for line in tuner_index.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        row, label, start, end, share, db = line.split('\t')
        if int(end) - int(start) >= 1000 and float(share) >= 0.45 and float(db) >= -42.0:
            valid_rows.append(int(row))
    assert len(valid_rows) >= 300
    recording = tmp / 'tuner-sample.wav'
    with wave.open(str(recording), 'wb') as sample:
        sample.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
        sample.writeframes(struct.pack('<hhhh', 9000, 6000, -9000, -6000) * 55125)
    for row in valid_rows[:300]:
        os.link(recording, tuner_bank / f'{row:07}.wav')
    tuner_recorded = subprocess.run(
        [str(exe), '--screen', 'tuner', '--seed', '17', '--trials', '2', '--dump'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(tuner_round),
                 NW_DATA_DIRECTORY=str(tmp / 'tuner-data')),
        check=True, capture_output=True, text=True, timeout=20,
    )
    recorded_states = [ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
                       for line in tuner_recorded.stdout.splitlines() if line.startswith('# state=')]
    assert [state[13] for state in recorded_states] == [0, 1], recorded_states

    tuner_played_recording = subprocess.run(
        [str(exe), '--screen', 'tuner', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(tuner_env, NW_MEDIA_CONFIGFILE=str(tuner_round), NW_TEST_DIRECT='1',
                 NW_TEST_TUNER_CLOCK='2', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert tuner_played_recording.returncode == 0 and 'SDL event replay: PASS' in tuner_played_recording.stdout, (
        tuner_played_recording.returncode, tuner_played_recording.stderr)

    gun_profile = tmp / 'gun-config.ini'
    gun_profile.write_text('[DEFAULT]\nGUN_RUNG = 4\nGUN_TRIALS = 5\nGUN_ADAPTIVE = True\n')
    gun_options = subprocess.run(
        [str(exe), '--screen', 'gunslinger'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(gun_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='71',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert gun_options.returncode == 0 and 'SDL event replay: PASS' in gun_options.stdout, gun_options.stderr
    assert gun_profile.with_name(gun_profile.name + '.gunslinger-options').read_text() == (
        '[DEFAULT]\nGUN_RUNG = 7\nGUN_TRIALS = 3\nGUN_ADAPTIVE = False\n')

    gun_round = tmp / 'gun-round.ini'
    gun_round.write_text('[DEFAULT]\nGUN_RUNG = 1\nGUN_TRIALS = 1\n')
    gun = subprocess.run(
        [str(exe), '--screen', 'gunslinger', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(gun_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='71',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_GUN_CLICK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert gun.returncode == 0 and 'SDL event replay: PASS' in gun.stdout, gun.stderr

    field_profile = tmp / 'field-config.ini'
    field_profile.write_text('[DEFAULT]\nFIELD_RUNG = 4\nFIELD_TRIALS = 5\nFIELD_ADAPTIVE = True\n')
    field_options = subprocess.run(
        [str(exe), '--screen', 'field-manual'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(field_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='67',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert field_options.returncode == 0 and 'SDL event replay: PASS' in field_options.stdout, field_options.stderr
    assert field_profile.with_name(field_profile.name + '.field-manual-options').read_text() == (
        '[DEFAULT]\nFIELD_RUNG = 7\nFIELD_TRIALS = 3\nFIELD_ADAPTIVE = False\n')

    field_round = tmp / 'field-round.ini'
    field_round.write_text('[DEFAULT]\nFIELD_RUNG = 1\nFIELD_TRIALS = 1\n')
    field = subprocess.run(
        [str(exe), '--screen', 'field-manual', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(field_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='67',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_FIELD_CLICK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert field.returncode == 0 and 'SDL event replay: PASS' in field.stdout, field.stderr

    drone_profile = tmp / 'drone-config.ini'
    drone_profile.write_text('[DEFAULT]\nDRONE_RUNG = 4\nDRONE_TRIALS = 5\nDRONE_ADAPTIVE = True\n')
    drone_options = subprocess.run(
        [str(exe), '--screen', 'drone-hoops'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(drone_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='66',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert drone_options.returncode == 0 and 'SDL event replay: PASS' in drone_options.stdout, drone_options.stderr
    assert drone_profile.with_name(drone_profile.name + '.drone-hoops-options').read_text() == (
        '[DEFAULT]\nDRONE_RUNG = 7\nDRONE_TRIALS = 3\nDRONE_ADAPTIVE = False\n')

    echo_profile = tmp / 'echo-config.ini'
    echo_profile.write_text('[DEFAULT]\nECHO_RUNG = 4\nECHO_TRIALS = 5\nECHO_ADAPTIVE = True\n')
    echo_options = subprocess.run(
        [str(exe), '--screen', 'echo-cave'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(echo_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='65',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert echo_options.returncode == 0 and 'SDL event replay: PASS' in echo_options.stdout, echo_options.stderr
    assert echo_profile.with_name(echo_profile.name + '.echo-cave-options').read_text() == (
        '[DEFAULT]\nECHO_RUNG = 7\nECHO_TRIALS = 3\nECHO_ADAPTIVE = False\n')
    echo_round = tmp / 'echo-round.ini'
    echo_round.write_text('[DEFAULT]\nECHO_RUNG = 10\nECHO_TRIALS = 1\n')
    echo = subprocess.run(
        [str(exe), '--screen', 'echo-cave', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(echo_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='65',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_ECHO_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert echo.returncode == 0 and 'SDL event replay: PASS' in echo.stdout, echo.stderr

    beat_profile = tmp / 'beat-config.ini'
    beat_profile.write_text('[DEFAULT]\nBEAT_RUNG = 4\nBEAT_TRIALS = 5\nBEAT_ADAPTIVE = True\n')
    beat_options = subprocess.run(
        [str(exe), '--screen', 'keep-the-beat'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(beat_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='62',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert beat_options.returncode == 0 and 'SDL event replay: PASS' in beat_options.stdout, beat_options.stderr
    assert beat_profile.with_name(beat_profile.name + '.keep-the-beat-options').read_text() == (
        '[DEFAULT]\nBEAT_RUNG = 7\nBEAT_TRIALS = 3\nBEAT_ADAPTIVE = False\n')
    beat_round = tmp / 'beat-round.ini'
    beat_round.write_text('[DEFAULT]\nBEAT_RUNG = 1\nBEAT_TRIALS = 1\n')
    beat_run = subprocess.run(
        [str(exe), '--screen', 'keep-the-beat', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(beat_round), NW_TEST_DIRECT='1', NW_TEST_SLOT='62',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_BEAT_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert beat_run.returncode == 0 and 'SDL event replay: PASS' in beat_run.stdout, beat_run.stderr

    stop_profile = tmp / 'stop-switch-config.ini'
    stop_profile.write_text('[DEFAULT]\nSTOP_AND_SWITCH_RUNG = 4\nSTOP_AND_SWITCH_TRIALS = 6\nSTOP_AND_SWITCH_ADAPTIVE = True\n')
    stop_options = subprocess.run(
        [str(exe), '--screen', 'stop-and-switch'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(stop_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='48',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert stop_options.returncode == 0 and 'SDL event replay: PASS' in stop_options.stdout, stop_options.stderr
    assert stop_profile.with_name(stop_profile.name + '.stop-switch-options').read_text() == (
        '[DEFAULT]\nSTOP_AND_SWITCH_RUNG = 7\nSTOP_AND_SWITCH_TRIALS = 3\nSTOP_AND_SWITCH_ADAPTIVE = False\n')
    stop_dump = subprocess.run(
        [str(exe), '--screen', 'stop-and-switch', '--dump', '--trials', '2'],
        env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(stop_profile)),
        check=True, capture_output=True, text=True, timeout=20,
    )
    stop_states = [ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
                   for line in stop_dump.stdout.splitlines() if line.startswith('# state=')]
    assert [state[:4] for state in stop_states] == [(0, 7, 0, 3), (1, 7, 1, 3)]
    assert stop_states[1][7:13] == (0, 0, 0, -1, -1, -1)
    delay_profile = tmp / 'delay-config.ini'
    delay_profile.write_text('[DEFAULT]\nDELAY_RUNG = 4\nDELAY_TRIALS = 3\nDELAY_ADAPTIVE = True\n')
    delay_env = dict(env, NW_MEDIA_CONFIGFILE=str(delay_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='47',
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1')
    delay_options = subprocess.run([str(exe), '--screen', 'delay'], env=delay_env,
                                   capture_output=True, text=True, timeout=20)
    assert delay_options.returncode == 0 and 'SDL event replay: PASS' in delay_options.stdout, delay_options.stderr
    assert delay_profile.with_name(delay_profile.name + '.delay-options').read_text() == (
        '[DEFAULT]\nDELAY_RUNG = 7\nDELAY_TRIALS = 1\nDELAY_ADAPTIVE = False\n')
    delay_dump = subprocess.run([str(exe), '--screen', 'delay', '--dump'],
                                env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(delay_profile)),
                                check=True, capture_output=True, text=True, timeout=20)
    state = next(line for line in delay_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 7, 0, 1)
    delay_round_profile = tmp / 'delay-round.ini'
    delay_round_profile.write_text('[DEFAULT]\nDELAY_RUNG = 1\nDELAY_TRIALS = 1\n')
    delay_round = subprocess.run(
        [str(exe), '--screen', 'delay', '--seed', '17', '--width', '912', '--height', '684'],
        env=dict(env, NW_MEDIA_CONFIGFILE=str(delay_round_profile), NW_TEST_DIRECT='1', NW_TEST_SLOT='47',
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_DELAY_CLOCK='1', NW_TEST_CLOSE_WINDOW='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert delay_round.returncode == 0 and 'SDL event replay: PASS' in delay_round.stdout, delay_round.stderr

    wiring_profile = tmp / 'hidden-wiring-config.ini'
    wiring_profile.write_text('[DEFAULT]\nWIRING_RUNG = 5\nWIRING_TRIALS = 5\nWIRING_ADAPTIVE = True\n')
    wiring_env = dict(env, NW_MEDIA_CONFIGFILE=str(wiring_profile), NW_TEST_DIRECT='1',
                      NW_TEST_SLOT=str(frames.index('hidden_wiring')), NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1')
    wiring_options = subprocess.run([str(exe), '--screen', 'hidden-wiring'], env=wiring_env,
                                     capture_output=True, text=True, timeout=20)
    assert wiring_options.returncode == 0 and 'SDL event replay: PASS' in wiring_options.stdout, wiring_options.stderr
    assert wiring_profile.with_name(wiring_profile.name + '.hidden-wiring-options').read_text() == (
        '[DEFAULT]\nWIRING_RUNG = 7\nWIRING_TRIALS = 3\nWIRING_ADAPTIVE = False\n')
    wiring_dump = subprocess.run([str(exe), '--screen', 'hidden-wiring', '--dump'],
                                  env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(wiring_profile)),
                                  check=True, capture_output=True, text=True, timeout=20)
    state = next(line for line in wiring_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 7, 0, 3)

    hidden_profile = tmp / 'hidden-rule-config.ini'
    hidden_profile.write_text('[DEFAULT]\nHIDDEN_RULE_RUNG = 4\nHIDDEN_RULE_TRIALS = 5\nHIDDEN_RULE_ADAPTIVE = True\n')
    hidden_env = dict(env, NW_MEDIA_CONFIGFILE=str(hidden_profile), NW_TEST_DIRECT='1',
                      NW_TEST_SLOT=str(frames.index('hidden_rule')), NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_WIRING_OPTIONS='1', NW_TEST_CLOSE_WINDOW='1')
    hidden_menu = subprocess.run([str(exe), '--screen', 'hidden-rule'], env=hidden_env,
                                 capture_output=True, text=True, timeout=20)
    assert hidden_menu.returncode == 0 and 'SDL event replay: PASS' in hidden_menu.stdout, hidden_menu.stderr
    saved_hidden = hidden_profile.with_name(hidden_profile.name + '.hidden-rule-options')
    assert saved_hidden.read_text() == ('[DEFAULT]\nHIDDEN_RULE_RUNG = 6\n'
                                        'HIDDEN_RULE_TRIALS = 3\nHIDDEN_RULE_ADAPTIVE = False\n')
    hidden_dump = subprocess.run([str(exe), '--screen', 'hidden-rule', '--dump'],
                                 env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(hidden_profile)),
                                 check=True, capture_output=True, text=True, timeout=20)
    state = next(line for line in hidden_dump.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(state.split('=', 1)[1].split(' bytes=')[0])[:4] == (0, 6, 0, 3)

    capture = dict(unavailable_video, NW_TEST_DIRECT='1', NW_TEST_SLOT='-1', NW_TEST_OPTION_SLOT='-1',
                   NW_TEST_WIDTH='480', NW_TEST_HEIGHT='360')
    for screen in ('title', 'sudoku', 'numberology', 'mr-time', 'matrix-reasoning', 'video-sequence'):
        png = tmp / f'{screen}.png'
        capture['NW_TEST_SLOT'] = '-1' if screen == 'title' else str(frames.index(screen.replace('-', '_')))
        args = [str(exe), '--screen', screen, '--width', '480', '--height', '360', '--screenshot']
        result = subprocess.run([*args, str(png)], env=capture, capture_output=True, text=True, timeout=20)
        if result.returncode == 1 and 'PNG screenshots require SDL 3.4 or newer' in result.stderr:
            assert not png.exists()
            break
        assert result.returncode == 0, (screen, result.stderr)
        data = png.read_bytes()
        assert data[:16] == bytes.fromhex('89504e470d0a1a0a0000000d49484452')
        assert struct.unpack('>II', data[16:24]) == (480, 360)
        failure = subprocess.run([*args, str(tmp / 'missing-directory' / 'out.png')],
                                 env=capture, capture_output=True, text=True, timeout=20)
        assert failure.returncode == 1 and 'Could not save screenshot' in failure.stderr, failure.stderr
    cocoa_density = os.environ.get('NW_TEST_COCOA_DPR')
    if sys.platform == 'darwin' and cocoa_density:
        density = float(cocoa_density)
        png = tmp / 'cocoa-hud.png'
        cocoa = dict(capture, SDL_VIDEODRIVER='cocoa', NW_TEST_SLOT='-1', NW_NATIVE_DEBUG_HUD='1',
                     NW_TEST_CAPTURE_DENSITY=cocoa_density, NW_TEST_WIDTH=str(round(480 * density)),
                     NW_TEST_HEIGHT=str(round(360 * density)))
        result = subprocess.run([str(exe), '--screen', 'title', '--width', '480', '--height', '360',
                                 '--screenshot', str(png)], env=cocoa, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert struct.unpack('>II', png.read_bytes()[16:24]) == (round(480 * density), round(360 * density))
    if (tmp / 'title.png').exists():
        hud_png = tmp / 'title-hud.png'
        hud_env = dict(capture, NW_TEST_SLOT='-1', NW_NATIVE_DEBUG_HUD='1',
                       NW_TEST_DEBUG_SUMMARY='title banner 0 - ', NW_TEST_CAPTURE_DENSITY='1')
        result = subprocess.run([str(exe), '--screen', 'title', '--width', '480', '--height', '360',
                                 '--screenshot', str(hud_png)], env=hud_env, capture_output=True, timeout=20)
        assert result.returncode == 0 and hud_png.read_bytes() != (tmp / 'title.png').read_bytes(), result.stderr
    if (tmp / 'title.png').exists():
        hud_env = dict(capture, NW_TEST_SLOT=str(frames.index('algebra')), NW_NATIVE_DEBUG_HUD='1',
                       NW_TEST_DEBUG_SUMMARY='Algebra ready - trial 0/1 - right 0 - typed 0 - ')
        result = subprocess.run([str(exe), '--screen', 'algebra', '--algebra-trials', '1',
                                 '--width', '480', '--height', '360', '--screenshot', str(tmp / 'algebra-hud.png')],
                                env=hud_env, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
    if (tmp / 'title.png').exists():
        hud_env = dict(capture, NW_TEST_SLOT=str(frames.index('matrix_reasoning')), NW_NATIVE_DEBUG_HUD='1',
                       NW_TEST_DEBUG_SUMMARY='Matrix Reasoning ready - trial 0/5 - right 0 - ')
        result = subprocess.run([str(exe), '--screen', 'matrix-reasoning',
                                 '--width', '480', '--height', '360', '--screenshot', str(tmp / 'matrix-hud.png')],
                                env=hud_env, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
    if (tmp / 'title.png').exists():
        hud_env = dict(capture, NW_TEST_DIRECT='0', NW_TEST_SLOT='-1', NW_NATIVE_DEBUG_HUD='1',
                       NW_TEST_DEBUG_SUMMARY='task menu - Working memory - 3D N-Back - ')
        result = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '480', '--height', '360',
                                 '--screenshot', str(tmp / 'hub-hud.png')],
                                env=hud_env, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
    if (tmp / 'title.png').exists():
        hud_env = dict(capture, NW_TEST_SLOT=str(frames.index('sokoban')), NW_NATIVE_DEBUG_HUD='1',
                       NW_TEST_DEBUG_SUMMARY='Sokoban - phase 0 - pushes 0 - moves 0 - ')
        result = subprocess.run([str(exe), '--screen', 'sokoban', '--width', '480', '--height', '360',
                                 '--screenshot', str(tmp / 'sokoban-hud.png')],
                                env=hud_env, capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
    if (tmp / 'title.png').exists():
        for operation in ('clear', 'present'):
            failed_png = tmp / f'failed-{operation}.png'
            failure_env = dict(capture, NW_TEST_SLOT='-1', NW_TEST_RENDER_FAILURE=operation)
            result = subprocess.run([str(exe), '--screen', 'title', '--width', '480', '--height', '360', '--screenshot', str(failed_png)],
                                    env=failure_env, capture_output=True, text=True, timeout=20)
            assert result.returncode == 1 and not failed_png.exists(), (operation, result.stderr)
            assert f'injected {operation} failure' in result.stderr, result.stderr
            assert 'Could not render screenshot frame' in result.stderr, result.stderr
    for operation in ('clear', 'present'):
        failure_env = dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT='-1', NW_TEST_OPTION_SLOT='-1',
                           NW_TEST_RENDER_FAILURE=operation)
        result = subprocess.run([str(exe), '--screen', 'title'], env=failure_env,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 1, (operation, result.stderr)
        assert f'injected {operation} failure' in result.stderr, result.stderr
    sudoku_settings = tmp / 'sudoku settings'
    sudoku_settings.mkdir()
    sudoku_profile = sudoku_settings / 'Sudoku User-config.ini'
    sudoku_profile.write_text('[DEFAULT]\nSUDOKU_LEVEL = 4\nSUDOKU_TRIALS = 2\n', encoding='utf-8')
    sudoku_args = ['--datadir', str(sudoku_settings), '--user', 'Sudoku User']
    sudoku_menu = subprocess.run(
        [str(exe), '--screen', 'taskhub', *sudoku_args],
        env=dict(env, NW_TEST_SLOT=str(frames.index('sudoku')), NW_TEST_OPTION_SLOT='-1',
                 NW_TEST_SUDOKU_MENU='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert sudoku_menu.returncode == 0 and 'SDL event replay: PASS' in sudoku_menu.stdout, sudoku_menu.stderr
    assert (sudoku_settings / 'Sudoku User-config.ini.sudoku-options').read_text() == '5 2 1 1\n'
    for options, level in (([], 5), (['--sudoku-level', '6'], 6)):
        result = subprocess.run([str(exe), '--screen', 'sudoku', '--dump', *sudoku_args, *options],
                                env=unavailable_video, check=True, capture_output=True, text=True, timeout=20)
        line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        assert ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])[1] == level
    go_settings = tmp / 'go settings'
    go_settings.mkdir()
    go_profile = go_settings / 'Go User-config.ini'
    go_profile.write_text('[DEFAULT]\nGO_LEVEL = 4\nGO_TRIALS = 5\n', encoding='utf-8')
    go_args = ['--datadir', str(go_settings), '--user', 'Go User']
    go_menu = subprocess.run(
        [str(exe), '--screen', 'taskhub', *go_args],
        env=dict(env, NW_TEST_SLOT=str(frames.index('go')), NW_TEST_OPTION_SLOT='-1',
                 NW_TEST_GO_MENU='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert go_menu.returncode == 0 and 'SDL event replay: PASS' in go_menu.stdout, go_menu.stderr
    assert (go_settings / 'Go User-config.ini.go-options').read_text() == '5 8\n'
    for options, expected in (([], (5, 8)), (['--go-level', '6'], (6, 8))):
        result = subprocess.run([str(exe), '--screen', 'go', '--dump', *go_args, *options],
                                env=unavailable_video, check=True, capture_output=True, text=True, timeout=20)
        line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
        assert (state[1], state[3]) == expected
    assert go_profile.read_text(encoding='utf-8') == '[DEFAULT]\nGO_LEVEL = 4\nGO_TRIALS = 5\n'
    go_sidecar = go_settings / 'Go User-config.ini.go-options'
    go_sidecar.write_text('5 8 invalid\n', encoding='utf-8')
    result = subprocess.run([str(exe), '--screen', 'go', '--dump', *go_args],
                            env=unavailable_video, check=True, capture_output=True, text=True, timeout=20)
    line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
    state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
    assert (state[1], state[3]) == (4, 5)
    go_preview = subprocess.run(
        [str(exe), '--screen', 'go', '--go-level', '1', '--go-trials', '3'],
        env=dict(env, NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1', NW_TEST_GO_PREVIEW='1',
                 NW_TEST_SLOT=str(frames.index('go')), NW_TEST_OPTION_SLOT='-1'),
        capture_output=True, text=True, timeout=20,
    )
    assert go_preview.returncode == 0 and 'SDL event replay: PASS' in go_preview.stdout, go_preview.stderr
    wires_settings = tmp / 'wires settings'
    wires_settings.mkdir()
    wires_profile = wires_settings / 'Wires User-config.ini'
    wires_profile.write_text('[DEFAULT]\nWIRES_LEVEL = 6\nWIRES_ROUNDS = 5\n', encoding='utf-8')
    wires_args = ['--datadir', str(wires_settings), '--user', 'Wires User']
    wires_menu = subprocess.run(
        [str(exe), '--screen', 'taskhub', *wires_args],
        env=dict(env, NW_TEST_SLOT=str(frames.index('crossed_wires')), NW_TEST_OPTION_SLOT='-1',
                 NW_TEST_WIRES_MENU='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert wires_menu.returncode == 0 and 'SDL event replay: PASS' in wires_menu.stdout, wires_menu.stderr
    assert (wires_settings / 'Wires User-config.ini.wires-options').read_text() == '7 8 0 0\n'
    for options, level in (([], 7), (['--crossed-wires-level', '5'], 5)):
        result = subprocess.run([str(exe), '--screen', 'crossed-wires', '--dump', *wires_args, *options],
                                env=unavailable_video, check=True, capture_output=True, text=True, timeout=20)
        line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
        assert (state[1], state[3], state[20], state[21]) == (level, 8, 0, 0)
    # Python advances a clean 9-piece solve to 12 pieces, even when the
    # starting request happens to describe a square board.
    jigsaw_ini.write_text('[DEFAULT]\nJIGSAW_PIECES = 9\nJIGSAW_PUZZLES = 2\n', encoding='utf-8')
    for profile_flags in ([], ['--user', 'Rectangle']):
        adaptive_jigsaw = subprocess.run(
            [str(exe), '--screen', 'jigsaw', '--datadir', str(python_profile), *profile_flags],
            env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('jigsaw')),
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_JIGSAW_NOTE='tiles 3x3',
                     NW_TEST_JIGSAW_ADAPT='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert adaptive_jigsaw.returncode == 0 and 'SDL event replay: PASS' in adaptive_jigsaw.stdout, (
            adaptive_jigsaw.returncode, adaptive_jigsaw.stdout, adaptive_jigsaw.stderr
        )
    jigsaw_settings_dir = tmp / 'jigsaw settings'
    jigsaw_settings_dir.mkdir()
    jigsaw_profile = jigsaw_settings_dir / 'Jigsaw User-config.ini'
    profile_bytes = b'[DEFAULT]\nJIGSAW_PIECES = 9\nJIGSAW_PUZZLES = 2\n'
    jigsaw_profile.write_bytes(profile_bytes)
    profile_args = ['--datadir', str(jigsaw_settings_dir), '--user', 'Jigsaw User']
    jigsaw_sidecar = jigsaw_settings_dir / 'Jigsaw User-config.ini.jigsaw-options'
    for interaction in ('1', '2'):
        jigsaw_sidecar.unlink(missing_ok=True)
        jigsaw_menu = subprocess.run(
            [str(exe), '--screen', 'taskhub', *profile_args],
            env=dict(env, NW_TEST_SLOT=str(frames.index('jigsaw')), NW_TEST_OPTION_SLOT='-1',
                     NW_TEST_JIGSAW_MENU=interaction),
            capture_output=True, text=True, timeout=20,
        )
        assert jigsaw_menu.returncode == 0 and 'SDL event replay: PASS' in jigsaw_menu.stdout, jigsaw_menu.stderr
        assert jigsaw_sidecar.read_text() == '12 2 1 1 0\n'
    assert jigsaw_profile.read_bytes() == profile_bytes
    video_menu = subprocess.run(
        [str(exe), '--screen', 'taskhub', *profile_args],
        env=dict(env, NW_TEST_SLOT=str(frames.index('jigsaw')), NW_TEST_OPTION_SLOT='-1',
                 NW_TEST_JIGSAW_MENU='3'),
        capture_output=True, text=True, timeout=20,
    )
    assert video_menu.returncode == 0 and 'SDL event replay: PASS' in video_menu.stdout, video_menu.stderr
    assert (jigsaw_settings_dir / 'Jigsaw User-config.ini.video-jigsaw-options').read_text() == '9 3 1 0 0\n'
    assert jigsaw_sidecar.read_text() == '12 2 1 1 0\n'

    def jigsaw_saved_grid(*args):
        output = subprocess.run(
            [str(exe), '--screen', 'jigsaw', '--dump', '--datadir', str(jigsaw_settings_dir), *args],
            env=unavailable_video, check=True, capture_output=True, text=True, timeout=20,
        ).stdout
        line = next(line for line in output.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
        return state[2], state[15], state[4]

    assert jigsaw_saved_grid('--user', 'Jigsaw User') == (3, 4, 2)
    assert jigsaw_saved_grid('--user', 'Jigsaw User', '--jigsaw-side', '4') == (4, 4, 2)
    assert jigsaw_saved_grid('--user', 'default') == (3, 3, 3)
    jigsaw_sidecar.write_text('12 2 1 1 9\n', encoding='ascii')
    assert jigsaw_saved_grid('--user', 'Jigsaw User') == (3, 3, 2)
    jigsaw_hover = subprocess.run(
        [str(exe), '--screen', 'jigsaw', '--width', '1200', '--height', '684'],
        env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('jigsaw')),
                 NW_TEST_OPTION_SLOT='-1', NW_TEST_JIGSAW_HOVER='1'),
        capture_output=True, text=True, timeout=20,
    )
    assert jigsaw_hover.returncode == 0 and 'SDL Jigsaw hover: PASS' in jigsaw_hover.stdout, (
        jigsaw_hover.returncode, jigsaw_hover.stderr,
    )
    video_data = tmp / 'video jigsaw clips'
    ucf101 = video_data / 'datasets' / 'ucf101'
    ucf101.mkdir(parents=True)
    video_env = dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('jigsaw')),
                     NW_TEST_OPTION_SLOT='-1')
    video_args = [str(exe), '--screen', 'video-jigsaw', '--datadir', str(video_data),
                  '--width', '912', '--height', '684']
    no_video = subprocess.run(video_args, env=dict(video_env, NW_TEST_JIGSAW_NOTE='No video library yet'),
                              capture_output=True, text=True, timeout=20)
    assert no_video.returncode == 0 and 'SDL event replay: PASS' in no_video.stdout, no_video.stderr
    hub_video = subprocess.run(
        [str(exe), '--screen', 'taskhub', *video_args[3:]],
        env=dict(video_env, NW_TEST_DIRECT='0', NW_TEST_CATEGORY='4', NW_TEST_ROW='5',
                 NW_TEST_JIGSAW_NOTE='No video library yet'),
        capture_output=True, text=True, timeout=20,
    )
    assert hub_video.returncode == 0 and 'SDL event replay: PASS' in hub_video.stdout, (
        hub_video.returncode, hub_video.stderr,
    )
    if ffmpeg := shutil.which('ffmpeg'):
        clip = ucf101 / 'motion sample.avi'
        frames_rgb = b''.join(bytes((index * 8, 200, 20)) * (120 * 82) for index in range(30))
        subprocess.run(
            [ffmpeg, '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
             '-video_size', '120x80', '-framerate', '15', '-i', 'pipe:0', '-pix_fmt', 'bgr24',
             '-c:v', 'rawvideo', str(clip)],
            input=frames_rgb, check=True, timeout=20,
        )
        rotation = ucf101 / 'seen_jigsaw.txt'
        rotation.write_text('already.avi\n', encoding='utf-8')
        video = subprocess.run(
            video_args, env=dict(video_env, NW_TEST_VIDEO_JIGSAW='1',
                                 NW_TEST_JIGSAW_NOTE='tiles 3x2'),
            capture_output=True, text=True, timeout=20,
        )
        assert video.returncode == 0 and 'SDL event replay: PASS' in video.stdout, (
            video.returncode, video.stderr,
        )
        assert rotation.read_text(encoding='utf-8').splitlines() == ['already.avi', clip.name]
        clip.write_bytes(b'not a video')
        corrupt = subprocess.run(video_args, env=dict(
            video_env, NW_TEST_JIGSAW_NOTE='None of the downloaded clips would decode'),
            capture_output=True, text=True, timeout=20,
        )
        assert corrupt.returncode == 0 and 'SDL event replay: PASS' in corrupt.stdout, corrupt.stderr
    if (tmp / 'title.png').exists():
        jigsaw_data = tmp / 'jigsaw photographs'
        div2k = jigsaw_data / 'datasets' / 'div2k'
        div2k.mkdir(parents=True)

        def png_chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

        # Magenta margins sit outside the central crop. Each tile has a
        # distinct central color so the tray and preview can be checked.
        colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
        scanlines = bytearray()
        for y in range(65):
            scanlines.append(0)
            for x in range(130):
                scanlines.extend(colors[((y - 1) // 32) * 2 + (x - 32) // 32]
                                 if y > 0 and 32 <= x < 96 else (255, 0, 255))
        (div2k / 'fixture.png').write_bytes(
            b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 130, 65, 8, 2, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress(scanlines)) + png_chunk(b'IEND', b''),
        )
        shutil.copyfile(div2k / 'fixture.png', div2k / 'second.png')
        rotation = div2k / 'seen.txt'
        rotation.write_text('fixture.png\n', encoding='utf-8')
        for expected_count in (2, 1):
            jigsaw = subprocess.run(
                [str(exe), '--screen', 'jigsaw', '--jigsaw-side', '2', '--datadir', str(jigsaw_data)],
                env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('jigsaw')),
                         NW_TEST_OPTION_SLOT='-1', NW_TEST_JIGSAW_PHOTO='1',
                         NW_TEST_JIGSAW_NOTE='Only 2 photographs downloaded'),
                capture_output=True, text=True, timeout=20,
            )
            assert jigsaw.returncode == 0 and 'SDL event replay: PASS' in jigsaw.stdout, jigsaw.stderr
            shown = rotation.read_text(encoding='utf-8').splitlines()
            assert len(shown) == expected_count, shown
            if expected_count == 2:
                assert shown == ['fixture.png', 'second.png'], shown
            else:
                assert shown[0] in ('fixture.png', 'second.png'), shown
        tiny_data = tmp / 'jigsaw tiny photo'
        tiny_library = tiny_data / 'datasets' / 'div2k'
        tiny_library.mkdir(parents=True)
        (tiny_library / 'tiny.png').write_bytes(
            b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress(bytes((0, *colors[0], *colors[1],
                                                     0, *colors[2], *colors[3]))))
            + png_chunk(b'IEND', b''),
        )
        tiny = subprocess.run(
            [str(exe), '--screen', 'jigsaw', '--jigsaw-side', '3', '--datadir', str(tiny_data)],
            env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('jigsaw')),
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_JIGSAW_NOTE='tiles 2x2', NW_TEST_JIGSAW_CLOCK='1'),
            capture_output=True, text=True, timeout=20,
        )
        assert tiny.returncode == 0 and 'SDL event replay: PASS' in tiny.stdout, tiny.stderr
        for corrupt, note in (
            (False, 'No photographs in the DIV2K library. Using colored tiles.'),
            (True, 'Could not load the photograph. Using colored tiles.'),
        ):
            fallback_data = tmp / ('jigsaw corrupt' if corrupt else 'jigsaw missing')
            fallback_data.mkdir()
            if corrupt:
                library = fallback_data / 'datasets' / 'div2k'
                library.mkdir(parents=True)
                (library / 'broken.png').write_bytes(b'Not a PNG')
            fallback = subprocess.run(
                [str(exe), '--screen', 'jigsaw', '--datadir', str(fallback_data)],
                env=dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('jigsaw')),
                         NW_TEST_OPTION_SLOT='-1', NW_TEST_JIGSAW_NOTE=note),
                capture_output=True, text=True, timeout=20,
            )
            assert fallback.returncode == 0 and 'SDL event replay: PASS' in fallback.stdout, fallback.stderr
    if (tmp / 'title.png').exists():
        marble_capture = dict(capture, NW_TEST_SLOT=str(frames.index('marble')),
                              NW_TEST_MARBLE='1', NW_TEST_MARBLE_READY='1', NW_NATIVE_DEBUG_HUD='1',
                              NW_TEST_DEBUG_SUMMARY='Marble Maze ready - rung 3 - tray 0/5 - 2D fallback - ')
        marble_png = tmp / 'marble-ready.png'
        result = subprocess.run([str(exe), '--screen', 'marble', '--marble-start-rung', '3',
                                 '--trials', '5', '--width', '480', '--height', '360',
                                 '--screenshot', str(marble_png)], env=marble_capture,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert struct.unpack('>II', marble_png.read_bytes()[16:24]) == (480, 360)
    if (tmp / 'title.png').exists():
        # An odd, wide framebuffer exercises letterboxing and the hub layout.
        hub_png = tmp / 'wide-hub.png'
        hub_capture = dict(capture, NW_TEST_DIRECT='0', NW_TEST_SLOT='-1',
                           NW_TEST_WIDTH='641', NW_TEST_HEIGHT='397')
        result = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '641',
                                 '--height', '397', '--screenshot', str(hub_png)],
                                env=hub_capture, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert struct.unpack('>II', hub_png.read_bytes()[16:24]) == (641, 397)
    # Run from a different directory to exercise executable-relative asset lookup.
    if (tmp / 'title.png').exists():
        checker_source, checker = tmp / 'logo_check.c', tmp / 'logo_check'
        checker_source.write_text(logo_check)
        subprocess.run(['cc', '-o', str(checker), str(checker_source), *flags], check=True, timeout=20)
        logos = tmp / 'res' / 'Logo'
        logos.mkdir(parents=True)
        work = tmp / 'working-directory'
        work.mkdir()
        for theme, filename in (([], 'logo.png'), (['--black-background'], 'logo-dark.png')):
            asset = logos / filename
            plain, branded = tmp / 'plain.png', tmp / 'branded.png'
            args = [str(exe), '--screen', 'title', '--width', '480', '--height', '360', *theme, '--screenshot']
            title = dict(capture, NW_TEST_SLOT='-1')
            subprocess.run([*args, str(plain)], cwd=work, env=title, check=True, capture_output=True, timeout=20)
            shutil.copyfile(root / 'res' / 'Logo' / filename, asset)
            subprocess.run([*args, str(branded)], cwd=work, env=title, check=True, capture_output=True, timeout=20)
            subprocess.run([str(checker), str(plain), str(branded)], check=True, timeout=20)
            asset.unlink()
    for position, slot in ((15, '62'), (18, '65'), (19, '66'), (20, '67'), (21, '68'), (22, '69'), (23, '70'), (24, '71')):
        attention_mouse = dict(env, NW_TEST_ATTENTION_MOUSE=str(position), NW_TEST_SLOT=slot,
                               NW_TEST_OPTION_SLOT='-1', NW_TEST_WIDTH='912', NW_TEST_HEIGHT='684')
        result = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                                env=attention_mouse, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    wrap = dict(env, NW_TEST_HUB_WRAP='1', NW_TEST_SLOT=str(frames.index('custody')),
                NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1')
    result = subprocess.run([str(exe), '--screen', 'taskhub'], env=wrap,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    for width, height in (('912', '684'), ('960', '480')):
        mouse = dict(env, NW_TEST_HUB_MOUSE='1', NW_TEST_SLOT=str(frames.index('go')),
                     NW_TEST_OPTION_SLOT='-1', NW_TEST_WIDTH=width, NW_TEST_HEIGHT=height)
        result = subprocess.run([str(exe), '--screen', 'taskhub', '--width', width, '--height', height],
                                env=mouse, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    cookie_profile = tmp / 'cookie-profile.ini'
    cookie_profile.write_text('[DEFAULT]\nCOOKIE_LEVEL = 1\nCOOKIE_TRIALS = 1\n'
                              'COOKIE_BEAT_SECONDS = 0.08\nCOOKIE_SET_SECONDS = 0.0\nCOOKIE_ADAPTIVE = False\n')
    for direct, screen in ((0, 'taskhub'), (1, 'cookie-thief')):
        cookie = dict(env, NW_TEST_COOKIE_THIEF='1', NW_MEDIA_CONFIGFILE=str(cookie_profile),
                      NW_TEST_SLOT=str(frames.index('cookie_thief')), NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='6', NW_TEST_ROW='0')
        result = subprocess.run([str(exe), '--screen', screen, '--seed', '42'],
                                env=cookie, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            screen, result.returncode, result.stdout, result.stderr,
        )
    cookie_base = dict(env, NW_MEDIA_CONFIGFILE=str(cookie_profile),
                       NW_TEST_SLOT=str(frames.index('cookie_thief')), NW_TEST_OPTION_SLOT='-1')
    cookie_saved = cookie_profile.with_name('cookie-profile.ini.cookie-thief-options')
    preview = subprocess.run([str(exe), '--screen', 'cookie-thief'],
                             env=dict(cookie_base, NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1',
                                      NW_TEST_COOKIE_PREVIEW='1'),
                             capture_output=True, text=True, timeout=20)
    assert preview.returncode == 0 and 'SDL event replay: PASS' in preview.stdout, (
        preview.returncode, preview.stdout, preview.stderr,
    )
    assert not cookie_saved.exists()
    menu = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                          env=dict(cookie_base, NW_TEST_CATEGORY='6', NW_TEST_ROW='0',
                                   NW_TEST_OPTION='1', NW_TEST_COOKIE_MENU='1'),
                          capture_output=True, text=True, timeout=20)
    assert menu.returncode == 0 and 'SDL event replay: PASS' in menu.stdout, menu.stderr
    assert cookie_saved.read_text() == '2 2 120 400 1\n'
    for expected in ((2, 2, 120, 400, 1), (1, 1, 80, 0, 0)):
        result = subprocess.run([str(exe), '--screen', 'cookie-thief', '--dump'],
                                env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(cookie_profile)),
                                check=True, capture_output=True, text=True, timeout=20)
        line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
        assert (state[1], *state[3:7]) == expected
        cookie_saved.write_text('2 2 120 400 1 trailing data\n')
    invalid_cookie_profile = tmp / 'cookie-invalid-durations.ini'
    invalid_cookie_profile.write_text('[DEFAULT]\nCOOKIE_BEAT_SECONDS = 0.9\nCOOKIE_SET_SECONDS = 2.0\n')
    result = subprocess.run([str(exe), '--screen', 'cookie-thief', '--dump'],
                            env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(invalid_cookie_profile)),
                            check=True, capture_output=True, text=True, timeout=20)
    line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
    assert ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])[4:6] == (160, 800)
    sokoban3d_profile = tmp / 'sokoban3d-profile.ini'
    sokoban3d_profile.write_text('[DEFAULT]\nSOKO3D_LEVEL = 3\nSOKO3D_TRIALS = 2\n'
                                 'SOKO3D_ADAPTIVE = False\nSOKO3D_MARKS = False\nSOKO3D_TRAPS = True\n')
    for direct, screen in ((0, 'taskhub'), (1, 'sokoban3d')):
        sokoban3d = dict(env, NW_TEST_SOKOBAN3D='1', NW_MEDIA_CONFIGFILE=str(sokoban3d_profile),
                         NW_TEST_SLOT=str(frames.index('sokoban3d')), NW_TEST_OPTION_SLOT='-1',
                         NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='5', NW_TEST_ROW='5')
        result = subprocess.run([str(exe), '--screen', screen, '--seed', '42'],
                                env=sokoban3d, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            screen, result.returncode, result.stdout, result.stderr,
        )
    # Run the Python solver in isolation and drive its route through the SDL event loop.
    sokoban3d_oracle = subprocess.run(
        [sys.executable, '-c', """
import json, random
from neural_workshop import sokoban, sokoban3d
sokoban._native = None
level = sokoban3d.deal(2, seed=random.Random(23).randrange(1 << 30))
minimum, bound, route = sokoban3d.solve_bounded(level)
assert minimum == bound == len(route)
keys = {'ahead': 'w', 'back': 's', 'left': 'a', 'right': 'd'}
print(json.dumps([minimum, ''.join(keys[action] for action in route)]))
"""], cwd=root.parent / 'original-neural-workshop-enhanced',
        check=True, capture_output=True, text=True, timeout=20,
    )
    par, optimal_route = ast.literal_eval(sokoban3d_oracle.stdout)
    score_profile = tmp / 'sokoban3d-score.ini'
    score_profile.write_text('[DEFAULT]\nSOKO3D_LEVEL = 2\nSOKO3D_TRIALS = 1\n')
    for route, next_rung, verdict in (
        (optimal_route, 3, f'Done — the minimum {par} steps'),
        ('ad' * par + optimal_route, 1, f'Done in {3 * par} steps — the minimum was {par}'),
    ):
        score_env = dict(env, NW_MEDIA_CONFIGFILE=str(score_profile),
                         NW_TEST_SLOT=str(frames.index('sokoban3d')), NW_TEST_OPTION_SLOT='-1',
                         NW_TEST_CATEGORY='5', NW_TEST_ROW='5', NW_TEST_SOKOBAN3D_ROUTE=route,
                         NW_TEST_SOKOBAN3D_PAR=str(par), NW_TEST_SOKOBAN3D_NEXT_RUNG=str(next_rung),
                         NW_TEST_SOKOBAN3D_SUMMARY=f'1 warehouses, {round(100 * par / len(route))}% step efficiency, highest rung 2',
                         NW_TEST_SOKOBAN3D_VERDICT=verdict)
        result = subprocess.run([str(exe), '--screen', 'taskhub', '--seed', '23'],
                                env=score_env, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            result.returncode, result.stdout, result.stderr,
        )
    sokoban3d_base = dict(env, NW_MEDIA_CONFIGFILE=str(sokoban3d_profile),
                          NW_TEST_SLOT=str(frames.index('sokoban3d')), NW_TEST_OPTION_SLOT='-1')
    sokoban3d_saved = sokoban3d_profile.with_name('sokoban3d-profile.ini.sokoban3d-options')
    preview = subprocess.run([str(exe), '--screen', 'sokoban3d', '--seed', '42'],
                             env=dict(sokoban3d_base, NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1',
                                      NW_TEST_SOKOBAN3D_PREVIEW='1'),
                             capture_output=True, text=True, timeout=20)
    assert preview.returncode == 0 and 'SDL event replay: PASS' in preview.stdout, (
        preview.returncode, preview.stdout, preview.stderr,
    )
    assert not sokoban3d_saved.exists()
    menu = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                          env=dict(sokoban3d_base, NW_TEST_CATEGORY='5', NW_TEST_ROW='5',
                                   NW_TEST_OPTION='1', NW_TEST_SOKOBAN3D_MENU='1'),
                          capture_output=True, text=True, timeout=20)
    assert menu.returncode == 0 and 'SDL event replay: PASS' in menu.stdout, menu.stderr
    assert sokoban3d_saved.read_text() == '4 3 1 1 0\n'
    for expected in ((4, 3, 1, 0, 1), (3, 2, 0, 1, 0)):
        result = subprocess.run([str(exe), '--screen', 'sokoban3d', '--seed', '42', '--dump'],
                                env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(sokoban3d_profile)),
                                check=True, capture_output=True, text=True, timeout=20)
        line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
        assert (state[1], state[3], *state[18:21]) == expected
        sokoban3d_saved.write_text('4 3 1 1 0 trailing data\n')
    maze2d_profile = tmp / 'maze2d-profile.ini'
    maze2d_profile.write_text('[DEFAULT]\nMAZE_LEVEL = 3\nMAZE_TRIALS = 2\nMAZE_SHOW_TRAIL = False\n')
    for direct, screen in ((0, 'taskhub'), (1, 'maze')):
        maze2d = dict(env, NW_TEST_MAZE2D='1', NW_MEDIA_CONFIGFILE=str(maze2d_profile),
                      NW_TEST_SLOT=str(frames.index('maze')), NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='5', NW_TEST_ROW='3')
        result = subprocess.run([str(exe), '--screen', screen, '--seed', '42'],
                                env=maze2d, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            screen, result.returncode, result.stdout, result.stderr,
        )
    maze2d_base = dict(env, NW_MEDIA_CONFIGFILE=str(maze2d_profile),
                       NW_TEST_SLOT=str(frames.index('maze')), NW_TEST_OPTION_SLOT='-1')
    maze2d_saved = maze2d_profile.with_name('maze2d-profile.ini.maze-options')
    preview = subprocess.run([str(exe), '--screen', 'maze'],
                             env=dict(maze2d_base, NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1',
                                      NW_TEST_MAZE2D_PREVIEW='1'),
                             capture_output=True, text=True, timeout=20)
    assert preview.returncode == 0 and 'SDL event replay: PASS' in preview.stdout, preview.stderr
    assert not maze2d_saved.exists()
    menu = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                          env=dict(maze2d_base, NW_TEST_CATEGORY='5', NW_TEST_ROW='3',
                                   NW_TEST_OPTION='1', NW_TEST_MAZE2D_MENU='1'),
                          capture_output=True, text=True, timeout=20)
    assert menu.returncode == 0 and 'SDL event replay: PASS' in menu.stdout, menu.stderr
    assert maze2d_saved.read_text() == '4 3 0 0\n'
    for expected in ((4, 3, 0, 0), (3, 2, 1, 0)):
        result = subprocess.run([str(exe), '--screen', 'maze', '--seed', '42', '--dump'],
                                env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(maze2d_profile)),
                                check=True, capture_output=True, text=True, timeout=20)
        line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
        assert (state[1], state[3], state[15], state[16]) == expected
        maze2d_saved.write_text('4 3 0 0 trailing data\n')
    maze_reference = runpy.run_path(str(root.parent / 'original-neural-workshop-enhanced' /
                                        'neural_workshop' / 'maze.py'))
    maze = maze_reference['generate'](3, seed=random.Random(42).randrange(1 << 30))
    walk = maze_reference['route'](maze)
    assert walk[0] == maze.start and walk[-1] == maze.way_out and len(walk) - 1 == maze.minimum
    keys = {-maze.width: 'w', maze.width: 's', -1: 'a', 1: 'd'}
    route = ''.join(keys[right - left] for left, right in zip(walk, walk[1:]))
    solve_profile = tmp / 'maze2d-solve.ini'
    solve_profile.write_text('[DEFAULT]\nMAZE_LEVEL = 3\nMAZE_TRIALS = 1\n')
    result = subprocess.run([str(exe), '--screen', 'maze', '--seed', '42'],
                            env=dict(maze2d_base, NW_TEST_DIRECT='1', NW_TEST_MAZE2D_ROUTE=route,
                                     NW_MEDIA_CONFIGFILE=str(solve_profile)),
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
        result.returncode, result.stdout, result.stderr,
    )
    ninarow_profile = tmp / 'ninarow-profile.ini'
    ninarow_profile.write_text('[DEFAULT]\nNINAROW_GRID = 5\nNINAROW_TRIALS = 2\nNINAROW_SHOW_ANSWER = False\n')
    for direct, screen in ((0, 'taskhub'), (1, 'ninarow')):
        ninarow = dict(env, NW_TEST_NINAROW='1', NW_MEDIA_CONFIGFILE=str(ninarow_profile),
                       NW_TEST_SLOT=str(frames.index('ninarow')), NW_TEST_OPTION_SLOT='-1',
                       NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='5', NW_TEST_ROW='7')
        result = subprocess.run([str(exe), '--screen', screen, '--seed', '42', '--width', '912', '--height', '684'],
                                env=ninarow, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            screen, result.returncode, result.stdout, result.stderr,
        )
    ninarow_base = dict(env, NW_MEDIA_CONFIGFILE=str(ninarow_profile),
                      NW_TEST_SLOT=str(frames.index('ninarow')), NW_TEST_OPTION_SLOT='-1')
    preview = subprocess.run([str(exe), '--screen', 'ninarow'],
                             env=dict(ninarow_base, NW_TEST_NINAROW_PREVIEW='1',
                                      NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1'),
                             capture_output=True, text=True, timeout=20)
    assert preview.returncode == 0 and 'SDL event replay: PASS' in preview.stdout, preview.stderr
    sidecar = ninarow_profile.with_name('ninarow-profile.ini.ninarow-options')
    assert not sidecar.exists()
    menu = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                          env=dict(ninarow_base, NW_TEST_CATEGORY='5', NW_TEST_ROW='7',
                                   NW_TEST_OPTION='1', NW_TEST_NINAROW_MENU='1'),
                          capture_output=True, text=True, timeout=20)
    assert menu.returncode == 0 and 'SDL event replay: PASS' in menu.stdout, menu.stderr
    assert sidecar.read_text() == '2 3 6 0 0 0 0\n'
    result = subprocess.run([str(exe), '--screen', 'ninarow', '--dump'],
                            env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(ninarow_profile)),
                            check=True, capture_output=True, text=True, timeout=20)
    line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
    state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
    assert (state[1], state[3], state[11], state[16]) == (2, 3, 0, 6)
    salesman_profile = tmp / 'salesman-profile.ini'
    salesman_profile.write_text('[DEFAULT]\nTSP_CITIES = 5\nTSP_ROUNDS = 3\nTSP_SHOW_BEST = False\n')
    for direct, screen in ((0, 'taskhub'), (1, 'salesman')):
        salesman = dict(env, NW_TEST_SALESMAN='1', NW_MEDIA_CONFIGFILE=str(salesman_profile),
                        NW_TEST_SLOT=str(frames.index('salesman')), NW_TEST_OPTION_SLOT='-1',
                        NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='5', NW_TEST_ROW='1')
        result = subprocess.run([str(exe), '--screen', screen, '--seed', '42', '--width', '912', '--height', '684'],
                                env=salesman, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            screen, result.returncode, result.stdout, result.stderr,
        )
    salesman_base = dict(env, NW_MEDIA_CONFIGFILE=str(salesman_profile),
                       NW_TEST_SLOT=str(frames.index('salesman')), NW_TEST_OPTION_SLOT='-1')
    preview = subprocess.run([str(exe), '--screen', 'salesman'],
                             env=dict(salesman_base, NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1',
                                      NW_TEST_SALESMAN_PREVIEW='1'),
                             capture_output=True, text=True, timeout=20)
    assert preview.returncode == 0 and 'SDL event replay: PASS' in preview.stdout, preview.stderr
    assert not salesman_profile.with_name('salesman-profile.ini.salesman-options').exists()
    menu = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                          env=dict(salesman_base, NW_TEST_CATEGORY='5', NW_TEST_ROW='1',
                                   NW_TEST_OPTION='1', NW_TEST_SALESMAN_MENU='1'),
                          capture_output=True, text=True, timeout=20)
    assert menu.returncode == 0 and 'SDL event replay: PASS' in menu.stdout, menu.stderr
    assert salesman_profile.with_name('salesman-profile.ini.salesman-options').read_text() == '6 5 0 1\n'
    result = subprocess.run([str(exe), '--screen', 'salesman', '--dump'],
                            env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(salesman_profile)),
                            check=True, capture_output=True, text=True, timeout=20)
    line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
    state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
    assert (state[1], state[5], state[9], state[10]) == (6, 5, 0, 1)
    salesman_profile.with_name('salesman-profile.ini.salesman-options').write_text('6 5 0 1 extra\n')
    result = subprocess.run([str(exe), '--screen', 'salesman', '--dump'],
                            env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(salesman_profile)),
                            check=True, capture_output=True, text=True, timeout=20)
    line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
    state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
    assert (state[1], state[5], state[9], state[10]) == (5, 3, 1, 0)
    hanoi_profile = tmp / 'hanoi-profile.ini'
    hanoi_profile.write_text('[DEFAULT]\nHANOI_DISKS = 3\nHANOI_ROUNDS = 2\n')
    for direct, screen in ((0, 'taskhub'), (1, 'hanoi')):
        hanoi = dict(env, NW_TEST_HANOI='1', NW_MEDIA_CONFIGFILE=str(hanoi_profile),
                     NW_TEST_SLOT=str(frames.index('hanoi')), NW_TEST_OPTION_SLOT='-1',
                     NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='5', NW_TEST_ROW='0')
        result = subprocess.run([str(exe), '--screen', screen, '--width', '912', '--height', '684'],
                                env=hanoi, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            screen, result.returncode, result.stdout, result.stderr,
        )
    hanoi_base = dict(env, NW_MEDIA_CONFIGFILE=str(hanoi_profile),
                       NW_TEST_SLOT=str(frames.index('hanoi')), NW_TEST_OPTION_SLOT='-1')
    preview = subprocess.run([str(exe), '--screen', 'hanoi'],
                             env=dict(hanoi_base, NW_TEST_DIRECT='1', NW_TEST_CLOSE_WINDOW='1',
                                      NW_TEST_HANOI_PREVIEW='1'),
                             capture_output=True, text=True, timeout=20)
    assert preview.returncode == 0 and 'SDL event replay: PASS' in preview.stdout, preview.stderr
    assert not hanoi_profile.with_name('hanoi-profile.ini.hanoi-options').exists()
    menu = subprocess.run([str(exe), '--screen', 'taskhub', '--width', '912', '--height', '684'],
                          env=dict(hanoi_base, NW_TEST_CATEGORY='5', NW_TEST_ROW='0',
                                   NW_TEST_OPTION='1', NW_TEST_HANOI_MENU='1'),
                          capture_output=True, text=True, timeout=20)
    assert menu.returncode == 0 and 'SDL event replay: PASS' in menu.stdout, menu.stderr
    assert hanoi_profile.with_name('hanoi-profile.ini.hanoi-options').read_text() == '4 3 0\n'
    result = subprocess.run([str(exe), '--screen', 'hanoi', '--dump'],
                            env=dict(unavailable_video, NW_MEDIA_CONFIGFILE=str(hanoi_profile)),
                            check=True, capture_output=True, text=True, timeout=20)
    line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
    state = ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
    assert (state[1], state[4], state[9]) == (4, 3, 0)
    for category, selected, name in routes:
        for is_option in ((0, 1) if name in option_slots else (0,)):
            env.update(NW_TEST_CATEGORY=str(category), NW_TEST_ROW=str(selected), NW_TEST_SLOT=str(frames.index(name)),
                       NW_TEST_OPTION=str(is_option), NW_TEST_OPTION_SLOT=str(option_slots.get(name, -1)))
            result = subprocess.run([str(exe), '--screen', 'taskhub'], env=env, capture_output=True, text=True, timeout=20)
            assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (name, is_option, result.returncode, result.stdout, result.stderr)
    for category, selected, name in routes:
        if name not in ('you_are_here', 'sokoban'):
            continue
        custom = dict(env, NW_TEST_CATEGORY=str(category), NW_TEST_ROW=str(selected),
                      NW_TEST_SLOT=str(frames.index(name)), NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1',
                      NW_TEST_MAZE='1' if name == 'you_are_here' else '2')
        result = subprocess.run([str(exe), '--screen', 'taskhub', '--trial', '3', '--trials', '5', '--seed', '-42'],
                                env=custom, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (name, result.stderr)
    for puzzle, row in (('jigsaw', 4), ('sudoku', 7)):
        for direct in (0, 1):
            custom = dict(env, NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY='4', NW_TEST_ROW=str(row),
                          NW_TEST_SLOT=str(frames.index(puzzle)), NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1',
                          NW_TEST_PUZZLE_SEED='42', NW_TEST_JIGSAW=str(int(puzzle == 'jigsaw')))
            result = subprocess.run([str(exe), '--screen', puzzle if direct else 'taskhub', '--seed', '42'],
                                    env=custom, capture_output=True, text=True, timeout=20)
            assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (puzzle, direct, result.stderr)
    matrix = dict(env, NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('matrix_reasoning')),
                  NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1', NW_TEST_LARGE_FRAME='1',
                  NW_TEST_WINDOW_TITLE='Neural Workshop 5.0')
    result = subprocess.run([str(exe), '--screen', 'matrix-reasoning', '--seed', '42'],
                            env=matrix, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (result.returncode, result.stderr)
    marble_category, marble_row, _ = next(route for route in routes if route[2] == 'marble')
    for direct in (0, 1):
        custom = dict(env, NW_TEST_DIRECT=str(direct), NW_TEST_CATEGORY=str(marble_category),
                      NW_TEST_ROW=str(marble_row), NW_TEST_SLOT=str(frames.index('marble')),
                      NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1', NW_TEST_MARBLE='1',
                      NW_TEST_MARBLE_PHYSICS=str(int(mujoco is not None)))
        result = subprocess.run([str(exe), '--screen', 'marble' if direct else 'taskhub',
                                 '--marble-start-rung', '3', '--trials', '5', '--seed', '42'],
                                env=custom, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (direct, result.stderr)
    aliases = {'you_are_here': '3d-maze', 'fog': 'fog-of-war', 'custody': 'chain-of-custody',
               'tracking': 'moving-targets'}
    for name in frames:
        screen = aliases.get(name, name.replace('_', '-'))
        env.update(NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index(name)), NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1')
        result = subprocess.run([str(exe), '--screen', screen], env=env, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (name, result.returncode, result.stdout, result.stderr)
    env.update(NW_TEST_DIRECT='1', NW_TEST_SLOT=str(frames.index('sudoku')), NW_TEST_OPTION='0',
               NW_TEST_OPTION_SLOT='-1', NW_TEST_WIDTH='640', NW_TEST_HEIGHT='480')
    result = subprocess.run([str(exe), '--width', '320', '--width', ' +6_40 ', '--height', '4_80', '--screen', 'sudoku'],
                            env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (result.returncode, result.stdout, result.stderr)
    env.update(NW_TEST_DIRECT='1', NW_TEST_SLOT='-1', NW_TEST_OPTION='0', NW_TEST_OPTION_SLOT='-1',
               NW_TEST_WIDTH='0', NW_TEST_HEIGHT='0')
    for raw, expected in (('1', 1), ('3', 3), ('99', 4), ('-5', 1), (' +0_3 ', 3), ('9' * 40, 4)):
        env['NW_TEST_TRIAL'] = str(expected)
        result = subprocess.run([str(exe), '--screen', 'title', '--trial', raw], env=env,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (raw, result.returncode, result.stdout, result.stderr)
    close = dict(env, NW_TEST_CLOSE_WINDOW='1', NW_TEST_TRIAL='1')
    result = subprocess.run([str(exe), '--screen', 'title'], env=close,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    hover = dict(env, NW_TEST_HOVER='1', NW_TEST_TRIAL='1', NW_TEST_SLOT=str(frames.index('scrabble')))
    result = subprocess.run([str(exe), '--screen', 'scrabble'], env=hover,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    audio_data = tmp / 'audio data'
    audio_library = audio_data / 'datasets' / 'esc50'
    audio_library.mkdir(parents=True)
    for screen in ('concentration', 'recognition'):
        result = subprocess.run(
            [str(exe), '--screen', screen, f'--{screen}-sound', '--datadir', str(audio_data),
             '--dump', '--trials', '2', '--seed', '42'],
            env=env, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, (screen, result.stderr)
        assert result.stdout.count('# state=(0,') == 2, (screen, result.stdout)
        assert 'No sound library yet' in result.stdout, (screen, result.stdout)
    for clip in reversed(range(10)):
        with wave.open(str(audio_library / f'{clip:02}.wav'), 'wb') as wav:
            wav.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            wav.writeframes(struct.pack('<h', clip * 100) * 800)
    small_audio_data = tmp / 'small audio library'
    small_audio_library = small_audio_data / 'datasets' / 'esc50'
    small_audio_library.mkdir(parents=True)
    for clip in ('00.wav', '01.wav'):
        shutil.copyfile(audio_library / clip, small_audio_library / clip)
    sound_env = dict(env, NW_TEST_RECOGNITION_SOUND='1', NW_TEST_SLOT=str(frames.index('recognition')),
                     NW_TEST_TRIAL='1', SDL_AUDIODRIVER='dummy')
    for mode in ('1', '2'):
        sound = subprocess.run([str(exe), '--screen', 'recognition', '--recognition-sound',
                                '--datadir', str(small_audio_data), '--seed', '42'],
                               env=dict(sound_env, NW_TEST_RECOGNITION_SOUND=mode), capture_output=True, text=True, timeout=20)
        assert sound.returncode == 0 and 'SDL event replay: PASS' in sound.stdout, (sound.returncode, sound.stderr)
    (audio_data / 'config.ini').write_text('[DEFAULT]\nCONCENTRATION_PAIRS = 4\n', encoding='utf-8')
    rng = random.Random(42)
    choices = list(range(10))
    rng.shuffle(choices)
    cards = [clip for clip in reversed(choices[-4:]) for _ in range(2)]
    rng.shuffle(cards)
    concentration_env = dict(env, NW_TEST_CONCENTRATION_CLIP=f'{cards[0]:02}.wav',
                             NW_TEST_SLOT=str(frames.index('concentration')),
                             NW_TEST_TRIAL='1', SDL_AUDIODRIVER='dummy')
    sound = subprocess.run([str(exe), '--screen', 'concentration', '--concentration-sound',
                            '--datadir', str(audio_data), '--seed', '42', '--width', '912', '--height', '684'],
                           env=concentration_env, capture_output=True, text=True, timeout=20)
    assert sound.returncode == 0 and 'SDL event replay: PASS' in sound.stdout, (sound.returncode, sound.stderr)
    sound = subprocess.run([str(exe), '--screen', 'concentration', '--concentration-sound',
                            '--datadir', str(audio_data), '--seed', '42', '--width', '912', '--height', '684'],
                           env=dict(concentration_env, NW_TEST_CONCENTRATION_CLIP_TWO=f'{cards[2]:02}.wav'), capture_output=True, text=True, timeout=20)
    assert sound.returncode == 0 and 'SDL event replay: PASS' in sound.stdout, (sound.returncode, sound.stderr)
    for screen in ('concentration', 'recognition'):
        for mode in ('1', '2', '3', '4'):
            menu_env = dict(env, NW_TEST_SLOT=str(frames.index(screen)), NW_TEST_TRIAL='1',
                            NW_TEST_MEDIA_MENU=mode, NW_TEST_MEDIA_RECOGNITION=str(int(screen == 'recognition')))
            menu_data = tmp / f'{screen}-options-{mode}'
            menu_data.mkdir()
            result = subprocess.run([str(exe), '--screen', screen, '--datadir', str(menu_data),
                                     '--width', '912', '--height', '684'], env=menu_env,
                                    capture_output=True, text=True, timeout=20)
            assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
                screen, mode, result.returncode, result.stdout, result.stderr,
            )
    for screen in ('concentration', 'recognition'):
        for mode in ('1', '2'):
            menu_env = dict(env, NW_TEST_DIRECT='0', NW_TEST_SLOT=str(frames.index(screen)),
                            NW_TEST_TRIAL='1', NW_TEST_CATEGORY='0', NW_TEST_ROW='0',
                            NW_TEST_MEDIA_HUB=mode, NW_TEST_MEDIA_RECOGNITION=str(int(screen == 'recognition')))
            menu_data = tmp / f'{screen}-hub-options-{mode}'
            menu_data.mkdir()
            result = subprocess.run([str(exe), '--screen', 'taskhub', '--datadir', str(menu_data)], env=menu_env,
                                    capture_output=True, text=True, timeout=20)
            assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
                screen, mode, result.returncode, result.stdout, result.stderr,
            )
    applause_assets = tmp / 'res' / 'misc' / 'applause'
    applause_assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / 'res' / 'misc' / 'applause' / 'applause.wav', applause_assets / 'applause.wav')
    applause_profile = tmp / 'applause profile'
    applause_profile.mkdir()
    applause_progress = applause_profile / 'config.ini.nback3d-progress'
    for mode, flags in (
        ('1', 'USE_APPLAUSE = True\nTHRESHOLD_ADVANCE = 0\n'),
        ('2', 'USE_APPLAUSE = False\nTHRESHOLD_ADVANCE = 0\n'),
        ('2', 'USE_APPLAUSE = True\nTHRESHOLD_ADVANCE = 101\n'),
        ('2', 'USE_SESSION_FEEDBACK = False\nTHRESHOLD_ADVANCE = 0\n'),
    ):
        applause_progress.unlink(missing_ok=True)
        (applause_profile / 'config.ini').write_text(
            '[DEFAULT]\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\nSFX_VOLUME = 0.25\n' + flags,
            encoding='utf-8',
        )
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--adaptive', '--datadir', str(applause_profile)],
            env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                     NW_TEST_APPLAUSE=mode, SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            flags, result.returncode, result.stdout, result.stderr,
        )
    if os.environ.get('NW_MIXER_LIBRARY'):
        reward_music = tmp / 'reward music'
        fixture = Path(os.environ.get('NW_TEST_REWARD_OGG', applause_assets / 'applause.wav'))
        for album in ('advance', 'great', 'good'):
            folder = reward_music / album
            folder.mkdir(parents=True)
            shutil.copyfile(fixture, folder / fixture.name)
        for tier, advance, fallback, extra in (
            (3, 0, 0, ''),
            (2, 1, 0, ''),
            (1, 100, 0, ''),
            (0, 100, 50, ''),
            (0, 0, 0, 'USE_MUSIC = False\n'),
            (0, 0, 0, 'USE_SESSION_FEEDBACK = False\n'),
            (0, 0, 0, 'MUSIC_VOLUME = 0\n'),
            (3, 0, 0, 'USE_MUSIC_MANUAL = True\n'),
            (0, 0, 0, 'USE_MUSIC_MANUAL = False\n'),
        ):
            applause_progress.unlink(missing_ok=True)
            (applause_profile / 'config.ini').write_text(
                '[DEFAULT]\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\nUSE_APPLAUSE = False\n'
                f'THRESHOLD_ADVANCE = {advance}\nTHRESHOLD_FALLBACK = {fallback}\n' + extra,
                encoding='utf-8',
            )
            args = [str(exe), '--screen', 'nback3d', '--datadir', str(applause_profile)]
            if 'USE_MUSIC_MANUAL' not in extra:
                args.append('--adaptive')
            result = subprocess.run(
                args, env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                               NW_TEST_MUSIC_TIER=str(tier), NW_REWARD_MUSIC_DIR=str(reward_music),
                               NW_MIXER_LIBRARY=os.environ['NW_MIXER_LIBRARY'], SDL_AUDIODRIVER='dummy'),
                capture_output=True, text=True, timeout=20,
            )
            assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
                tier, extra, result.returncode, result.stdout, result.stderr,
            )
        applause_progress.unlink(missing_ok=True)
        (applause_profile / 'config.ini').write_text(
            '[DEFAULT]\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\nTHRESHOLD_ADVANCE = 0\n'
            'SFX_VOLUME = 0.25\nMUSIC_VOLUME = 0.25\n',
            encoding='utf-8',
        )
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--adaptive', '--datadir', str(applause_profile)],
            env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                     NW_TEST_APPLAUSE='1', NW_TEST_REWARD_FADE='1', NW_TEST_MUSIC_TIER='3',
                     NW_REWARD_MUSIC_DIR=str(reward_music), NW_MIXER_LIBRARY=os.environ['NW_MIXER_LIBRARY'],
                     SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            result.returncode, result.stdout, result.stderr,
        )
    applause_progress.unlink(missing_ok=True)
    (applause_profile / 'config.ini').write_text(
        '[DEFAULT]\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\nTHRESHOLD_ADVANCE = 0\n'
        'USE_APPLAUSE = True\nUSE_MUSIC = True\n', encoding='utf-8',
    )
    headless_rewards = dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                            NW_TEST_APPLAUSE='2', NW_TEST_MUSIC_TIER='0', SDL_AUDIODRIVER='dummy')
    if os.environ.get('NW_MIXER_LIBRARY'):
        headless_rewards.update(NW_REWARD_MUSIC_DIR=str(reward_music),
                                NW_MIXER_LIBRARY=os.environ['NW_MIXER_LIBRARY'])
    result = subprocess.run(
        [str(exe), '--screen', 'nback3d', '--adaptive', '--headless', '--datadir', str(applause_profile)],
        env=headless_rewards, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
        result.returncode, result.stdout, result.stderr,
    )
    nback_profile = tmp / 'nback progression'
    nback_profile.mkdir()
    (nback_profile / 'config.ini').write_text(
        '[DEFAULT]\nBACK_DEFAULT = 4\nBACK_10 = 3\nNUM_TRIALS = 10\n'
        'NUM_TRIALS_FACTOR = 3\nNUM_TRIALS_EXPONENT = 1\n',
        encoding='utf-8',
    )
    for adaptive in ([], ['--adaptive']):
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--dump', '--datadir', str(nback_profile), *adaptive],
            env=env, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, result.stderr
        state_line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(state_line.split('=', 1)[1].split(' bytes=')[0])
        assert state[1] == 3 and state[3] == 19, state
    for symbol, sdl_key, label in ((106, 106, 'J'), (65361, 1073741904, 'Left')):
        (nback_profile / 'config.ini').write_text(
            f'[DEFAULT]\nKEY_POSITION1 = {symbol}\n', encoding='utf-8',
        )
        launch = [str(exe), '--screen', 'nback3d', '--datadir', str(nback_profile)]
        result = subprocess.run(
            launch, env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                             NW_TEST_NBACK_BINDING=str(sdl_key)),
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (label, result.stderr)
        dumped = subprocess.run([*launch, '--dump'], env=env, capture_output=True, text=True,
                                timeout=20, check=True)
        assert f'{label}: match' in dumped.stdout, dumped.stdout
    timing_config = nback_profile / 'config.ini'
    timing_config.write_text(
        '[DEFAULT]\nGRID_3D_CUBES = 9\nTICK_DURATION_MS = 20\n'
        'TICKS_DEFAULT = 30\nTICKS_10 = 24\n'
        'STIMULUS_DURATION_MS = 110\nFEEDBACK_DURATION_MS = 50\n',
        encoding='utf-8',
    )
    timing_args = [str(exe), '--screen', 'nback3d', '--dump', '--trials', '2',
                   '--datadir', str(nback_profile)]
    timing_env = dict(env, NW_TRIAL_MS='410', NW_TICK_MS='25', NW_STIM_MS='75')

    def check_timing(args, settings, expected, startup):
        result = subprocess.run(
            [*timing_args, *args], env=settings, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, result.stderr
        states = [
            ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
            for line in result.stdout.splitlines() if line.startswith('# state=')
        ]
        assert len(states) == 2, states
        assert states[0][4] == 6, states
        assert states[0][14:17] == expected, states
        assert states[1][0] == 7 and states[1][13] == startup, states

    check_timing([], env, (480, 110, 50), 200)
    with timing_config.open('a', encoding='utf-8') as config:
        config.write('TRIAL_INTERVAL_MS = 515\n')
    check_timing([], env, (520, 110, 50), 200)
    check_timing([], timing_env, (400, 75, 50), 250)
    check_timing(['--trial-ms=333', '--tick-ms', '10', '--stim-ms=45'],
                 dict(timing_env, NW_TICK_MS='invalid'), (330, 45, 50), 100)
    check_timing(['--trial-ms', '0'], timing_env, (600, 75, 50), 250)
    for args, settings, option in (
        (['--trial-ms=bad'], timing_env, '--trial-ms'),
        (['--stim-ms'], timing_env, '--stim-ms'),
        ([], dict(env, NW_TICK_MS='invalid'), 'NW_TICK_MS'),
    ):
        result = subprocess.run(
            [*timing_args, *args], env=settings, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 2 and option in result.stderr, result.stderr
    timing_config.write_text('[DEFAULT]\nGRID_3D_CUBES = 6\n', encoding='utf-8')
    check_timing(['--headless'], env, (10, 500, 200), 10)
    check_timing([], dict(env, NW_HEADLESS='YeS', NW_TICK_MS='8'), (80, 500, 200), 80)
    check_timing(['--headless', '--trial-ms=450'], env, (400, 500, 200), 1000)
    with timing_config.open('a', encoding='utf-8') as config:
        config.write('HEADLESS = True\nTICK_DURATION_MS = 20\n')
    check_timing([], env, (200, 500, 200), 200)
    progress_profile = tmp / 'saved nback progression'
    progress_profile.mkdir()
    profile_file = progress_profile / 'config.ini'
    progress_file = progress_profile / 'config.ini.nback3d-progress'

    def nback_progress_run(advance, fallback):
        profile_file.write_text(
            '[DEFAULT]\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\nUSE_SESSION_FEEDBACK = False\n'
            f'THRESHOLD_ADVANCE = {advance}\nTHRESHOLD_FALLBACK = {fallback}\n',
            encoding='utf-8',
        )
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--adaptive', '--datadir', str(progress_profile)],
            env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                     NW_TEST_APPLAUSE='2', SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
        version, level, fallback_count, day, hour = map(int, progress_file.read_text().split())
        assert version == 2 and day > 20000101 and 0 <= hour <= 23
        return level, fallback_count

    def nback_saved_level(*flags):
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--dump', '--datadir', str(progress_profile), *flags],
            env=env, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, result.stderr
        state_line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        return ast.literal_eval(state_line.split('=', 1)[1].split(' bytes=')[0])[1]

    assert nback_progress_run(0, 0) == (3, 0)
    assert nback_saved_level('--adaptive') == 3
    assert nback_saved_level() == 2
    assert nback_progress_run(101, 50) == (3, 1)
    assert nback_progress_run(101, 50) == (3, 2)
    assert nback_progress_run(101, 50) == (2, 0)
    progress_file.write_text('1 4 0 20000101\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 4
    with profile_file.open('a', encoding='utf-8') as config:
        config.write('RESET_LEVEL = True\n')
    assert nback_saved_level('--adaptive') == 2
    progress_file.write_text('1 9 0 20000101\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 2
    local = datetime.datetime.now()
    today = local.date()
    yesterday = today - datetime.timedelta(days=1)
    rollover = 23 if local.hour < 23 else 0
    profile_file.write_text(
        f'[DEFAULT]\nRESET_LEVEL = True\nROLLOVER_HOUR = {rollover}\n', encoding='utf-8',
    )
    progress_file.write_text(f'2 4 0 {yesterday:%Y%m%d} 23\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == (4 if local.hour < rollover else 2)
    progress_file.write_text(f'2 6 0 {today:%Y%m%d} {local.hour}\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 6
    progress_file.write_text(f'2 6 0 {today:%Y%m%d} 24\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 2
    profile_file.write_text(
        '[DEFAULT]\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\nUSE_SESSION_FEEDBACK = False\n'
        'RESET_LEVEL = True\nROLLOVER_HOUR = 0\n', encoding='utf-8',
    )
    assert not (progress_profile / 'logfile.dat').exists()
    shared_stats = progress_profile / 'shared stats.txt'
    session_dump = progress_profile / 'default-sessions.dat'
    session_dump.unlink(missing_ok=True)
    prior_row = '2020-02-29 15:30:01,Po2B,82,10,2,30,4,0,19'
    shared_stats.write_text(prior_row, encoding='utf-8')
    for adaptive in (True, False):
        if not adaptive:
            profile_file.write_text(
                profile_file.read_text().replace('NUM_TRIALS = 4', 'NUM_TRIALS = 24'),
                encoding='utf-8',
            )
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--datadir', str(progress_profile),
             '--statsfile', str(shared_stats), '--clinical-log', *(['--adaptive'] if adaptive else [])],
            env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                     NW_TEST_APPLAUSE='2', NW_TEST_NBACK_RESPONSE='1', SDL_AUDIODRIVER='dummy'),
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    contents = shared_stats.read_text(encoding='utf-8')
    original, adaptive, manual = csv.reader(io.StringIO(contents))
    assert ','.join(original) == prior_row
    assert len(adaptive) == len(manual) == 27
    assert adaptive[1:10] == ['Po2B', '0', '10', '2', '30', '4', '0', '20', '0'], adaptive
    assert manual[1:10] == ['Po2B', '0', '10', '2', '30', '24', '1', '21', '0'], manual
    assert float(adaptive[25]) == 12 and float(manual[25]) == 72
    for row in (adaptive, manual):
        datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
        assert row[10:25] == ['0'] * 15 and row[26] == '0'
    with session_dump.open('rb') as stream:
        for row in (adaptive, manual):
            record = pickle.load(stream)
            assert record['summary'] == row and record['timestamp'] == row[0]
            assert record['mode'] == 10 and record['n'] == 2
            assert record['manual'] is (row[7] == '1')
            assert record['trial_duration'] == 3.0 and record['trials'] == int(row[6])
            trials = record['session']
            assert len(trials['position1']) == len(trials['color']) == record['trials']
            assert all(isinstance(item, int) and item > 0 for item in trials['position1'])
            assert trials['position1_input'] == [True] + [False] * (record['trials'] - 1)
            assert trials['position1_rt'] == [0.125] + [0.0] * (record['trials'] - 1)
        assert stream.read() == b''
    with (progress_profile / 'logfile.dat').open('rb') as stream:
        for row in (adaptive, manual):
            offset = stream.tell()
            assert stream.read(2) == b'\x80\x02'
            stream.seek(offset)
            assert pickle.load(stream) == row[:2] + list(map(int, row[2:25]))
        assert stream.read() == b''
    progress_file.unlink(missing_ok=True)
    history = progress_profile / 'stats.txt'
    rows = (
        '# original Python session history\n'
        '2020-02-29 15:30:01,P4B,82,10,4,90,36,0,1\n'
        '2020-02-29 16:30:01,D8B,100,2,8,90,84,0,2\n'
        'bad record\n'
    )
    history.write_text(rows, encoding='utf-8')
    profile_file.write_text('[DEFAULT]\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 5
    progress_file.write_text('1 7 0 20000101\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 7
    progress_file.unlink()
    custom_history = progress_profile / 'custom stats.txt'
    custom_history.write_text(
        '2020-02-29 13:00:00\tP6B\t20\t10\t6\t90\t56\t0\t1\n'
        '2020-02-29 13:10:00\tP6B\t35\t10\t6\t90\t56\t0\t2\n'
        '2020-02-29 13:20:00\tP6B\t40\t10\t6\t90\t56\t0\t3\n',
        encoding='utf-8',
    )
    profile_file.write_text('[DEFAULT]\nSTATSFILE = "custom stats.txt"\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 5
    profile_file.write_text('[DEFAULT]\nTHRESHOLD_FALLBACK_SESSIONS = 4\n', encoding='utf-8')
    assert nback_saved_level('--adaptive', '--statsfile', str(custom_history)) == 6
    profile_file.write_text('[DEFAULT]\nRESET_LEVEL = True\nROLLOVER_HOUR = 0\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 2
    day = datetime.date.today().isoformat()
    history.write_text(rows + f'{day} 00:00:00,P3B,90,10,3,90,29,0,3\n', encoding='utf-8')
    assert nback_saved_level('--adaptive') == 4
    assert history.read_text() == rows + f'{day} 00:00:00,P3B,90,10,3,90,29,0,3\n'
    assert not progress_file.exists()
    (progress_profile / 'defaults.ini').write_bytes(pickle.dumps({'USER': 'History User'}, protocol=4))
    (progress_profile / 'History User-stats.txt').write_text(
        '2020-02-29 15:30:01,P5B,90,10,5,90,45,0,1\n', encoding='utf-8',
    )
    assert nback_saved_level('--adaptive') == 6
    result = subprocess.run(
        [str(exe), '--screen', 'nback3d', '--datadir', str(progress_profile), '--clinical-log'],
        env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                 NW_TEST_APPLAUSE='2', SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    with (progress_profile / 'History User-logfile.dat').open('rb') as stream:
        assert pickle.load(stream)[1:9] == ['Po2B', 0, 10, 2, 30, 24, 1, 2]
        assert stream.read() == b''
    selected_user = 'Second User'
    (progress_profile / f'{selected_user}-config.ini').write_text(
        '[DEFAULT]\nBACK_10 = 3\nNUM_TRIALS = 4\nNUM_TRIALS_FACTOR = 0\n', encoding='utf-8',
    )
    result = subprocess.run(
        [str(exe), '--screen', 'nback3d', '--datadir', str(progress_profile),
         '--user', selected_user, '--clinical-log'],
        env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1',
                 NW_TEST_APPLAUSE='2', NW_TEST_WINDOW_TITLE=f'Neural Workshop 5.0 - {selected_user}',
                 SDL_AUDIODRIVER='dummy'),
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, result.stderr
    assert (progress_profile / f'{selected_user}-stats.txt').is_file()
    with (progress_profile / f'{selected_user}-sessions.dat').open('rb') as stream:
        record = pickle.load(stream)
        assert record['n'] == 3 and record['trials'] == 4
    assert (progress_profile / f'{selected_user}-logfile.dat').is_file()
    assert pickle.loads((progress_profile / 'defaults.ini').read_bytes()) == {'USER': 'History User'}
    history_chart_data = tmp / 'nback history chart'
    history_chart_data.mkdir()
    (history_chart_data / 'stats.txt').write_text(
        '2020-02-29 03:00:00,Po2B,60,10,2,30,24,0,1,60\n'
        '2020-02-29 13:00:00,Po2B,80,10,2,30,24,0,2,80\n'
        '2020-02-29 14:00:00,Po3B,50,10,3,30,29,0,3,55\n'
        '2020-02-29 15:00:00,Po8B,100,10,8,30,84,1,4,100\n'
        '2020-02-28 12:00:00,Au3B,60,11,3,30,29,0,1,0,50\n'
        '2020-02-29 12:00:00,Au3B,90,11,3,30,29,0,2,0,100\n'
        '2020-02-28 12:00:00,D2B,45,2,2,30,24,0,1,40,50\n'
        '2020-02-29 12:00:00,D2B,60,2,2,30,24,0,2,50,70\n',
        encoding='utf-8',
    )
    for mode, override in (('1', []), ('2', ['--statsfile', 'empty stats.txt'])):
        result = subprocess.run(
            [str(exe), '--screen', 'nback3d', '--datadir', str(history_chart_data), *override],
            env=dict(env, NW_TEST_SLOT=str(frames.index('nback3d')), NW_TEST_TRIAL='1', NW_TEST_HISTORY=mode),
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            mode, result.returncode, result.stdout, result.stderr,
        )
    profile_data = tmp / 'media settings'
    profile_data.mkdir()
    media_config = profile_data / 'custom.ini'
    media_config.write_text(
        "[DEFAULT]\n"
        "CONCENTRATION_PAIRS = 8\nCONCENTRATION_PEEK_MS = 1000\n"
        "CONCENTRATION_HIDE_MS = 700\nCONCENTRATION_SHOW_TURNS = False\n"
        "RECOGNITION_TRIALS = 30\nRECOGNITION_MEDIUM = 'sound'\n"
        "RECOGNITION_REPEAT_PERCENT = 20\nRECOGNITION_MIN_LAG = 6\n"
        "RECOGNITION_STUDY_MS = 0\nRECOGNITION_FEEDBACK = False\n",
        encoding='utf-8',
    )

    profile_photos = profile_data / 'datasets' / 'tiny-imagenet'
    profile_photos.mkdir(parents=True)
    for photo in range(10):
        (profile_photos / f'{photo:02}.jpg').write_bytes(b'test catalog entry')

    def media_settings_dump(screen, *flags, trials='2'):
        result = subprocess.run(
            [str(exe), '--screen', screen, '--datadir', str(profile_data), '--configfile',
             media_config.name, '--dump', '--trials', trials, *flags],
            env=env, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, result.stderr
        states = [
            ast.literal_eval(line.split('=', 1)[1].split(' bytes=')[0])
            for line in result.stdout.splitlines() if line.startswith('# state=')
        ]
        return states, result.stdout

    states, _ = media_settings_dump('concentration')
    assert states[0][1] == 8 and states[0][10] == 0
    assert states[1][0] == 1 and states[1][12] == 1000
    states, output = media_settings_dump('recognition')
    assert states[0][1:8] == (30, 0, 1, 20, 6, 0, 0)
    assert 'No sound library yet' in output
    states, output = media_settings_dump('recognition', '--recognition-pictures')
    assert states[0][3] == 0 and states[1][0] == 1
    states, _ = media_settings_dump('recognition', trials='10')
    assert states[0][1] == 10
    original_profile = media_config.read_bytes()
    for screen, expected in (('concentration', 10), ('recognition', 40)):
        menu_env = dict(env, NW_TEST_SLOT=str(frames.index(screen)), NW_TEST_TRIAL='1',
                        NW_TEST_MEDIA_MENU='2', NW_TEST_MEDIA_EXPECTED=str(expected),
                        NW_TEST_MEDIA_RECOGNITION=str(int(screen == 'recognition')))
        applied = subprocess.run(
            [str(exe), '--screen', screen, '--datadir', str(profile_data), '--configfile', media_config.name],
            env=menu_env, capture_output=True, text=True, timeout=20,
        )
        assert applied.returncode == 0 and 'SDL event replay: PASS' in applied.stdout, (
            screen, applied.returncode, applied.stdout, applied.stderr,
        )
        assert media_config.read_bytes() == original_profile
        states, _ = media_settings_dump(screen)
        assert states[0][1] == expected
        saved = profile_data / f'{media_config.name}.{screen}-options'
        assert saved.exists()
        saved.write_text('malformed preferences\n', encoding='utf-8')
        states, _ = media_settings_dump(screen)
        assert states[0][1] == (8 if screen == 'concentration' else 30)
    for screen, expected in (('concentration', (8, 0, 0)), ('recognition', (40, 0, 0))):
        empty = tmp / f'{screen}-fresh-profile'
        empty.mkdir()
        result = subprocess.run(
            [str(exe), '--screen', screen, '--datadir', str(empty), '--dump', '--trials', '2'],
            env=env, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'No picture library yet' in result.stdout, result.stderr
        state_line = next(line for line in result.stdout.splitlines() if line.startswith('# state='))
        state = ast.literal_eval(state_line.split('=', 1)[1].split(' bytes=')[0])
        assert (state[1], state[3], state[11 if screen == 'concentration' else 6]) == expected
    photos = tmp / 'photo data'
    photo_library = photos / 'datasets' / 'tiny-imagenet'
    photo_library.mkdir(parents=True)
    (photos / 'config.ini').write_text('[DEFAULT]\nCONCENTRATION_PAIRS = 4\n', encoding='utf-8')
    photo_args = [str(exe), '--screen', 'recognition', '--datadir', str(photos), '--seed', '42']
    missing = subprocess.run([*photo_args, '--dump', '--trials', '2'],
                             env=env, capture_output=True, text=True, timeout=20)
    assert missing.returncode == 0 and 'No picture library yet' in missing.stdout, missing.stderr
    concentration_photo_args = [
        str(exe), '--screen', 'concentration', '--datadir', str(photos), '--seed', '42',
    ]
    missing = subprocess.run([*concentration_photo_args, '--dump', '--trials', '2'],
                             env=env, capture_output=True, text=True, timeout=20)
    assert missing.returncode == 0 and 'No picture library yet' in missing.stdout, missing.stderr
    if os.environ.get('NW_JPEG_LIBRARY'):
        red_photo = base64.b64decode(
            b"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4R"
            b"DgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU"
            b"FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAALABEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAA"
            b"AAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFgEBAQEAAAAAAAAAAAAAAAAAAAcJ/8QAFBEBAAAAAAAAAAAAAAAA"
            b"AAAAAP/aAAwDAQACEQMRAD8AhQCaNAwAH//Z"
        )
        photo_env = dict(env, NW_JPEG_LIBRARY=os.environ['NW_JPEG_LIBRARY'],
                         NW_TEST_SLOT=str(frames.index('recognition')), NW_TEST_TRIAL='1')
        for mode, image in (('1', red_photo), ('2', b'corrupt JPEG')):
            for filename in ('00.jpg', '01.jpg'):
                (photo_library / filename).write_bytes(image)
            result = subprocess.run(
                [*photo_args, '--width', '912', '--height', '684'],
                env=dict(photo_env, NW_TEST_RECOGNITION_PHOTO=mode),
                capture_output=True, text=True, timeout=20,
            )
            assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
                mode, result.returncode, result.stdout, result.stderr,
            )
        green_photo = base64.b64decode(
            b"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4R"
            b"DgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU"
            b"FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAALABEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAA"
            b"AAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAj/xAAUEQEAAAAAAAAAAAAAAAAA"
            b"AAAA/9oADAMBAAIRAxEAPwC6AmRFgAD/2Q=="
        )
        assert cards[0] != cards[2]
        for clip in reversed(range(10)):
            image = {cards[0]: red_photo, cards[2]: green_photo}.get(clip, b'corrupt JPEG')
            (photo_library / f'{clip:02}.jpg').write_bytes(image)
        concentration_photo = dict(env, NW_JPEG_LIBRARY=os.environ['NW_JPEG_LIBRARY'], NW_TEST_SLOT=str(frames.index('concentration')),
                                   NW_TEST_TRIAL='1', NW_TEST_CONCENTRATION_PHOTO='1')
        result = subprocess.run(
            [*concentration_photo_args, '--width', '912', '--height', '684'],
            env=concentration_photo, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            result.returncode, result.stdout, result.stderr,
        )
    for choice in ('1', '2'):
        recognition_click = dict(env, NW_TEST_RECOGNITION_CLICK=choice,
                                 NW_TEST_SLOT=str(frames.index('recognition')), NW_TEST_TRIAL='1',
                                 NW_TEST_WIDTH='1000', NW_TEST_HEIGHT='600')
        result = subprocess.run(
            [str(exe), '--screen', 'recognition', '--datadir', str(profile_data),
             '--recognition-pictures', '--seed', '42', '--width', '1000', '--height', '600'],
            env=recognition_click, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (
            choice, result.returncode, result.stdout, result.stderr,
        )
    for screen, event_env, slot in (
        ('title', 'NW_TEST_MOUSE_BUTTON', -1),
        ('numberology', 'NW_TEST_TYPED_NUMBER', frames.index('numberology')),
    ):
        scripted = dict(env, NW_TEST_SLOT=str(slot), NW_TEST_TRIAL='1', **{event_env: '1'})
        result = subprocess.run([str(exe), '--screen', screen], env=scripted,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (screen, result.stderr)
    result = subprocess.run([str(exe), '--screen', 'title', '--width', '912', '--height', '684',
                             '--go-level', '6', '--go-trials', '3'],
                            env=dict(env, NW_TEST_TITLE_HUB='1', NW_TEST_SLOT=str(frames.index('go'))),
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL title and task hub navigation: PASS' in result.stdout, (
        result.returncode, result.stdout, result.stderr,
    )
    env.update(NW_TEST_TITLE_KEYS='1', NW_TEST_TRIAL='1', NW_TEST_WINDOW_TITLE='Neural Workshop 5.0')
    result = subprocess.run([str(exe), '--screen', 'title'], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0 and 'SDL event replay: PASS' in result.stdout, (result.returncode, result.stdout, result.stderr)
print('SDL dummy-video event loop: 37 direct and hub launches/exits, plus five option cancellations pass')
