#!/usr/bin/env bash
# Exercise Elisa's model and data lifecycle against an installed MuJoCo library.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
library="$(cd -- "$(dirname -- "${1:?pass the path to the MuJoCo shared library}")" && pwd)/$(basename -- "$1")"
headers="${2:-$(dirname -- "$library")/include}"
runtime_root="${ELISA_SDL_RUNTIME_ROOT:-$ELISA_STAGE1_ROOT}"
compiler="${ELISA_SDL_COMPILER:-$ELISA_STAGE1_BIN}"
runtime="${ELISA_SDL_RUNTIME_OBJ:-$ELISA_RUNTIME_OBJ}"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
host_system="$(uname -s)"
test_binary="$work/test"
case "$host_system" in
    Linux) export ELISA_HOST_LINUX=1 ;;
    MINGW*|MSYS*|UCRT*|CYGWIN*)
        export ELISA_HOST_WINDOWS=1
        export PATH="${NW_MUJOCO_DLL_DIR:-$(dirname -- "$library")}:$PATH"
        test_binary="$work/test.exe"
        ;;
esac
if [[ "$(uname -m)" == x86_64 ]]; then
    export ELISA_HOST_X86_64=1
fi

python3 "$ROOT/scripts/prepare_runtime_sources.py" "$ROOT" "$work/source" "$runtime_root"
bash "$ROOT/scripts/prepare_mujoco_layout.sh" "$headers" "$work/source/src/native/marble_mujoco_layout.elisa"
"$compiler" -emit obj -O2 -o "$work/test.o" "$work/source/test/marble_mujoco_ffi.elisa"
python3 "$ROOT/scripts/prepare_native_object.py" "$work/test.o" "$work/link.o"

cat > "$work/main.c" <<'C'
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL3/SDL.h>
#include "marble_present.h"
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

extern bool nw_marble_prepare_gl(void);
extern void nw_marble_set_png_loader(uintptr_t);
extern int nw_sdl_marble_assets_selftest(void);

extern void nw_sdl_bind_rows(int64_t *, unsigned char *, uintptr_t *);
extern int nw_sdl_marble_finish_frame(MarblePresentation *, SDL_Renderer *, uintptr_t, uintptr_t,
                                      const uint8_t *, int64_t, int, int, int64_t, int64_t);
extern int nw_sdl_desktop_frame(const uintptr_t *, const int *, const uintptr_t *, const uintptr_t *,
    uint64_t *, int64_t, int64_t, int64_t, int64_t, int64_t, uintptr_t,
    int64_t, unsigned char *, Uint64 *, int64_t *, uintptr_t, uintptr_t, uintptr_t,
    uintptr_t, uintptr_t, uintptr_t, uintptr_t, uintptr_t);

extern int nw_marble_mujoco_selftest(void);
extern int64_t nw_marble_test_desktop_frame(int64_t, int64_t, int64_t, int64_t);
extern void nw_marble_test_read_shadow_holes(uintptr_t, float *);
extern void nw_marble_test_place_at_pit(uintptr_t);
extern void nw_marble_test_read_shadow(uintptr_t, float *);
extern int64_t nw_marble_create(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_marble_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_marble_destroy(int64_t);
extern int64_t nw_marble_info(int64_t, int64_t);
extern int64_t nw_sdl_marble_view(uintptr_t, int64_t, int64_t, double *, int64_t);
extern int nw_sdl_marble_physics(uintptr_t *, int64_t, int64_t, int64_t);
extern int nw_marble_gl_mesh_test(uint32_t program);
extern int nw_marble_gl_shadow_test(uint32_t program);
extern int nw_marble_gl_colour_test(void);
extern int nw_marble_gl_scene_test(void);
extern int nw_marble_gl_composite_test(uint32_t program);
extern void nw_marble_view_test(double *out);
extern uint32_t nw_sdl_marble_program_create(int64_t pair);
extern void nw_sdl_marble_program_destroy(uint32_t program);
extern void *nw_sdl_marble_shader(int64_t shader, size_t *length);
extern int64_t nw_marble_mujoco_replay(int64_t rung, int64_t seed, double *out);
extern int64_t nw_marble_geometry(int64_t rung, int64_t seed, int64_t part, double *out, int64_t capacity);
extern int64_t nw_marble_board_write(int64_t dest, int64_t capacity, int64_t rung, int64_t seed);

/* Capture at the replay's simulated time, independent of wall-clock jitter. */
static int advance_capture(uintptr_t *physics, int64_t handle, uintptr_t screenshot, Uint64 *tick) {
    if (!handle || screenshot || !tick) return 0;
    *tick = 1;
    return nw_sdl_marble_physics(physics, handle, 0, 0);
}

static int context_attempts, context_destroys;
extern void nw_sdl_marble_render_close(uintptr_t *, int);

#ifdef __APPLE__
#define SDL_TEST_LIBRARY "libSDL3.0.dylib"
#elif defined(_WIN32)
#define SDL_TEST_LIBRARY "SDL3.dll"
#else
#define SDL_TEST_LIBRARY "libSDL3.so.0"
#endif

bool SDL_GL_MakeCurrent(SDL_Window *window, SDL_GLContext context) {
    if (context == (SDL_GLContext)(uintptr_t)1) {
        ++context_attempts;
        return false;
    }
    SDL_SharedObject *library = SDL_LoadObject(SDL_TEST_LIBRARY);
    if (!library) return false;
    bool (*make_current)(SDL_Window *, SDL_GLContext) =
        (void *)SDL_LoadFunction(library, "SDL_GL_MakeCurrent");
    bool result = make_current && make_current(window, context);
    SDL_UnloadObject(library);
    return result;
}

bool SDL_GL_DestroyContext(SDL_GLContext context) {
    if (context == (SDL_GLContext)(uintptr_t)1) {
        ++context_destroys;
        return true;
    }
    SDL_SharedObject *library = SDL_LoadObject(SDL_TEST_LIBRARY);
    if (!library) return false;
    bool (*destroy)(SDL_GLContext) = (void *)SDL_LoadFunction(library, "SDL_GL_DestroyContext");
    bool result = destroy && destroy(context);
    SDL_UnloadObject(library);
    return result;
}

static int context_failure_cleanup(void) {
    /* With no current context the renderer can only free its CPU state. */
    uintptr_t cpu_state = (uintptr_t)malloc(1);
    if (!cpu_state) return 15;
    nw_sdl_marble_render_close(&cpu_state, 0);
    if (cpu_state) return 16;
    MarblePresentation state = {
        .context = (SDL_GLContext)(uintptr_t)1,
        .scene = (uintptr_t)malloc(1)
    };
    if (!state.scene) return 15;
    nw_marble_present_close(&state);
    nw_marble_present_close(&state);
    return state.scene || state.context || context_attempts != 1 || context_destroys != 1;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "png-unavailable") == 0)
        return nw_sdl_marble_assets_selftest() != 1 ||
               strstr(SDL_GetError(), "Marble textures require SDL 3.4 or newer") == NULL;
#if SDL_VERSION_ATLEAST(3, 4, 0)
    nw_marble_set_png_loader((uintptr_t)SDL_LoadPNG);
#endif
#ifdef _WIN32
    if (_setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    if (argc == 2 && strcmp(argv[1], "context-failure") == 0) return context_failure_cleanup();
    if ((argc == 2 && strcmp(argv[1], "gl") == 0) ||
        ((argc == 7 || argc == 9) && strcmp(argv[1], "pixels") == 0)) {
        const bool capture = strcmp(argv[1], "pixels") == 0;
        const int rung = capture ? atoi(argv[2]) : 3;
        const int seed = capture ? atoi(argv[3]) : 42;
        const int dark = capture ? atoi(argv[4]) : 0;
        const int ticks = capture ? atoi(argv[5]) : 0;
        const int outcome = capture ? atoi(argv[6]) : 0;
        const int width = argc == 9 ? atoi(argv[7]) : 320;
        const int height = argc == 9 ? atoi(argv[8]) : 240;
        if (width <= 0 || height <= 0) return 4;
        if (!SDL_Init(SDL_INIT_VIDEO)) { SDL_Log("%s", SDL_GetError()); return 4; }
        SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS, SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG);
        SDL_Window *window = SDL_CreateWindow("Marble GL test", 64, 64, SDL_WINDOW_OPENGL | SDL_WINDOW_HIDDEN);
        SDL_GLContext context = window ? SDL_GL_CreateContext(window) : NULL;
        if (!context) { SDL_Log("%s", SDL_GetError()); SDL_Quit(); return 5; }
        if (!nw_marble_prepare_gl()) {
            SDL_Log("%s", SDL_GetError());
            SDL_GL_DestroyContext(context);
            SDL_DestroyWindow(window);
            SDL_Quit();
            return 5;
        }
        int failed = 0;
        for (int pair = 0; pair < 3; ++pair) {
            uint32_t program = nw_sdl_marble_program_create(pair);
            if (!program) failed = 6;
            else if (pair == 1 && nw_marble_gl_mesh_test(program)) failed = 7;
            else if (pair == 1 && nw_marble_gl_shadow_test(program)) failed = 8;
            else if (pair == 2 && nw_marble_gl_composite_test(program)) failed = 10;
            nw_sdl_marble_program_destroy(program);
        }
        if (nw_marble_gl_colour_test()) failed = 9;
        if (nw_marble_gl_scene_test()) failed = 11;
        SDL_GL_DestroyContext(context);
        SDL_DestroyWindow(window);
        SDL_Surface *pixels = SDL_CreateSurface(width, height, SDL_PIXELFORMAT_RGBA32);
        SDL_Renderer *host = pixels ? SDL_CreateSoftwareRenderer(pixels) : NULL;
        MarblePresentation presentation = {0};
        uintptr_t physics = 0;
        int64_t handle = nw_marble_create(rung, 1, 0, 2600, 0, seed);
        Uint8 red = 0;
        if (handle <= 0 || nw_marble_action(handle, 0, 0, 0) != 1 ||
            !nw_sdl_marble_physics(&physics, handle, 0, 0)) failed = 12;
        if (ticks && !failed) {
            if (nw_marble_action(handle, 7, 0, 0) != 1) failed = 12;
            for (int i = 0; i < ticks && !failed; ++i)
                if (!nw_sdl_marble_physics(&physics, handle, 20, 0)) failed = 12;
        }
        if (outcome && !failed) {
            nw_marble_test_place_at_pit(physics);
            if (!nw_sdl_marble_physics(&physics, handle, 10, 0) ||
                nw_marble_info(handle, 0) != 2) failed = 14;
            if (outcome == 2 && !failed &&
                (nw_marble_action(handle, 5, 0, 0) != 1 ||
                 !nw_sdl_marble_physics(&physics, handle, 0, 0) ||
                 nw_marble_info(handle, 0) != 4)) failed = 14;
        }
        SDL_Window *desktop = SDL_CreateWindow("Marble desktop capture", width, height, SDL_WINDOW_HIDDEN);
        uint8_t frame[65536];
        uintptr_t state[] = {(uintptr_t)desktop, (uintptr_t)host, (uintptr_t)frame};
        int sizes[] = {width, height};
        enum { TaskSlots = 106 };
        int64_t handles[TaskSlots] = {[4] = handle}, trial = 1;
        unsigned char modes[TaskSlots] = {[4] = 1}, step = 0;
        uintptr_t rows[2 * TaskSlots], special[60] = {0};
        Uint64 last_marble = 0, last_step = 0, physics_tick = 0;
        nw_sdl_bind_rows(handles, modes, rows);
        if (failed || !host || !desktop ||
            nw_sdl_desktop_frame(state, sizes, rows, special, &last_marble, dark, sizeof frame,
                0, 0, 0, 0, 0, &step, &last_step, &trial, (uintptr_t)advance_capture,
                (uintptr_t)&physics, (uintptr_t)&physics_tick, (uintptr_t)nw_sdl_marble_finish_frame,
                (uintptr_t)&presentation, 0, 0, 0) != -1 || physics_tick != 1 ||
            !presentation.scene ||
            !SDL_ReadSurfacePixel(pixels, 160, 110, &red, NULL, NULL, NULL) ||
            (!capture && (red == 0 || red >= 228))) failed = 12;
        if (capture && !failed) {
            unsigned char board[65536];
            double view[587];
            int64_t size = nw_marble_board_write((intptr_t)board, sizeof board, rung, nw_marble_info(handle, 5));
            if (size <= 0 || !nw_sdl_marble_view(physics, width, height, view, 587) ||
                fwrite(&size, sizeof size, 1, stdout) != 1 || fwrite(board, 1, size, stdout) != (size_t)size ||
                fwrite(view, sizeof *view, 587, stdout) != 587)
                failed = 13;
            for (int y = 0; y < presentation.pixels->h && !failed; ++y) {
                const unsigned char *row = (const unsigned char *)presentation.pixels->pixels +
                                           y * presentation.pixels->pitch;
                if (fwrite(row, 4, presentation.pixels->w, stdout) !=
                    (size_t)presentation.pixels->w) failed = 13;
            }
            float uniforms[5] = {0};
            nw_marble_test_read_shadow_holes(presentation.scene, uniforms);
            if (fwrite(uniforms, sizeof *uniforms, 5, stdout) != 5) failed = 13;
            static float shadow[1024 * 1024];
            nw_marble_test_read_shadow(presentation.scene, shadow);
            if (fwrite(shadow, sizeof *shadow, 1024 * 1024, stdout) != 1024 * 1024) failed = 13;
            for (int y = 0; y < pixels->h && !failed; ++y) {
                const unsigned char *row = (const unsigned char *)pixels->pixels + y * pixels->pitch;
                if (fwrite(row, 4, pixels->w, stdout) != (size_t)pixels->w) failed = 13;
            }
        }
        nw_marble_present_close(&presentation);
        nw_sdl_marble_physics(&physics, 0, 0, 0);
        nw_marble_destroy(handle);
        if (host) SDL_DestroyRenderer(host);
        if (desktop) SDL_DestroyWindow(desktop);
        if (pixels) SDL_DestroySurface(pixels);
        SDL_Quit();
        return failed;
    }
    if (argc == 4 && strcmp(argv[1], "chrome") == 0) {
        unsigned char frame[65536];
        int64_t size = nw_marble_test_desktop_frame(atoi(argv[2]), atoi(argv[3]),
                                                    (intptr_t)frame, sizeof frame);
        return size <= 0 || fwrite(frame, 1, size, stdout) != (size_t)size;
    }
    if (argc == 1) return nw_marble_mujoco_selftest();
    if (argc == 3 && strcmp(argv[1], "shader") == 0) {
        size_t size = 0;
        char *source = nw_sdl_marble_shader(strtoll(argv[2], NULL, 10), &size);
        if (!source) return 3;
        int failed = source[size] != '\0' || fwrite(source, 1, size, stdout) != size;
        SDL_free(source);
        return failed;
    }
    if (argc == 2) {
        double matrices[84];
        nw_marble_view_test(matrices);
        return fwrite(matrices, sizeof *matrices, 84, stdout) != 84;
    }
    if (argc != 3 && argc != 4) return 1;
    int64_t rung = strtoll(argv[1], NULL, 10), seed = strtoll(argv[2], NULL, 10);
    unsigned char board[65536];
    static double trace[240 * (6 + 14 * 8)];
    int64_t bytes = nw_marble_board_write((intptr_t)board, sizeof board, rung, seed);
    if (argc == 4) {
        static double mesh[262144];
        int64_t size = nw_marble_geometry(rung, seed, strtoll(argv[3], NULL, 10), mesh, sizeof mesh / sizeof *mesh);
        return size <= 0 || fwrite(mesh, sizeof *mesh, size, stdout) != (size_t)size;
    }
    int64_t stride = nw_marble_mujoco_replay(rung, seed, trace);
    if (bytes <= 0 || stride <= 0) return 2;
    return fwrite(&bytes, sizeof bytes, 1, stdout) != 1 ||
           fwrite(board, 1, bytes, stdout) != (size_t)bytes ||
           fwrite(trace, sizeof *trace, 240 * stride, stdout) != (size_t)(240 * stride);
}
C
read -r -a sdl_flags <<< "$(pkg-config --cflags --libs sdl3)"
if [[ "$host_system" == Darwin ]]; then
    cc -I"$ROOT/shells/sdl3" -o "$test_binary" "$work/main.c" "$work/link.o" "$runtime" "$library" \
        -framework OpenGL -Wl,-dead_strip,-headerpad_max_install_names "${sdl_flags[@]}"
    install_name="$(otool -D "$library" | sed -n '2p')"
    if [[ "$install_name" != "$library" ]]; then
        install_name_tool -change "$install_name" "$library" "$test_binary"
        codesign --force --sign - "$test_binary"
    fi
elif [[ "$host_system" == MINGW* || "$host_system" == MSYS* || "$host_system" == UCRT* || "$host_system" == CYGWIN* ]]; then
    case "$(uname -m)" in
        aarch64|arm64)
            gl_input="$work/marble_windows_gl.o"
            python3 "$ROOT/scripts/prepare_marble_windows_gl.py" \
                "$work/source/src/native" "$work/marble_windows_gl.elisa"
            "$compiler" -emit obj -O2 -o "$gl_input" "$work/marble_windows_gl.elisa"
            ;;
        *) gl_input="$ROOT/shells/sdl3/marble_gl_windows.c" ;;
    esac
    cc -I"$ROOT/shells/sdl3" -o "$test_binary" "$work/main.c" "$gl_input" "$work/link.o" "$runtime" "$library" \
        -Wl,--allow-multiple-definition "${sdl_flags[@]}"
else
    cc -I"$ROOT/shells/sdl3" -o "$test_binary" "$work/main.c" "$work/link.o" "$runtime" "$library" \
        "-Wl,-rpath,$(dirname -- "$library")" -Wl,--allow-multiple-definition "${sdl_flags[@]}" -lGL -lm
fi
mkdir -p "$work/res"
cp -R "$ROOT/res/marblemaze" "$work/res/"
"$test_binary"
echo "Marble MuJoCo FFI lifecycle and stepping passed"
"$test_binary" context-failure
echo "Marble OpenGL context-failure cleanup passed"
"$test_binary" png-unavailable
if [[ -n "${NW_MARBLE_REFERENCE_PYTHON:-}" ]]; then
    "$NW_MARBLE_REFERENCE_PYTHON" "$ROOT/test/marble_mujoco_ffi_replay.py" "$test_binary"
fi
if [[ "${NW_TEST_MARBLE_GL:-0}" == 1 ]]; then
    "$test_binary" gl
    echo "Marble OpenGL programs, indexed drawing, shadow target, color resolve, and stage compositing passed"
fi
if [[ "${NW_TEST_MARBLE_GL:-0}" == 1 && -n "${NW_MARBLE_REFERENCE_PYTHON:-}" ]]; then
    "$NW_MARBLE_REFERENCE_PYTHON" "$ROOT/test/marble_mujoco_ffi_replay.py" "$test_binary" --pixels-only
fi
