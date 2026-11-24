/* SDL header ABI checks and the injectable entry point for native replays.
 * The shipped desktop entry point is implemented in Elisa.
 */
#include <SDL3/SDL.h>
#include <stddef.h>
#include "numberology_results.h"

typedef struct {
    uintptr_t pixel_format;
    uintptr_t png_writer;
    uintptr_t png_loader;
    uintptr_t font;
    uintptr_t poll;
    uintptr_t pointer;
    uintptr_t writer;
    uintptr_t shutdown;
    uintptr_t marble_advance;
    uintptr_t marble_key;
    uintptr_t marble_finish;
    uintptr_t marble_close;
    uintptr_t marble_set_png_loader;
    uintptr_t marble_startup_status;
} SDLDesktopBindings;

extern int nw_sdl_desktop_main(int, char **, const SDLDesktopBindings *);

typedef struct { void *current, *pending; } syllogism_results;

#ifdef NW_MARBLE_MUJOCO
#include "marble_present.h"
extern int nw_sdl_marble_finish_frame(MarblePresentation *, SDL_Renderer *, uintptr_t, uintptr_t,
    const uint8_t *, int64_t, int, int, int64_t, int64_t);
extern int nw_sdl_marble_key(MarblePresentation *, uintptr_t *, const uintptr_t *, int64_t, Uint64 *);
extern void nw_sdl_marble_close(MarblePresentation *, uintptr_t *);
extern int nw_sdl_marble_advance(uintptr_t *, int64_t, uintptr_t, Uint64 *);
#endif
extern void nw_sdl_close_desktop(uintptr_t *, uintptr_t, const uintptr_t *,
    syllogism_results *, nw_numberology_results *, uintptr_t, uintptr_t, uintptr_t);
extern int nw_sdl_window_pointer(SDL_Window *, const uintptr_t *, const uintptr_t *, int64_t, int64_t, float, float, uint32_t);
#ifdef NW_TEST_FRAME_WRITER
extern int64_t NW_TEST_FRAME_WRITER(int64_t, int64_t, const int64_t *, const int64_t *, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
#endif
#ifdef NW_SDL_TTF
extern int nw_sdl_attach_font(SDL_Renderer *, uintptr_t, uintptr_t);
#endif


#ifdef NW_MARBLE_MUJOCO
extern int nw_sdl_marble_startup_status(int64_t, char **);
extern void nw_marble_set_png_loader(uintptr_t);
#endif

_Static_assert(SDL_PIXELFORMAT_RGBA8888 == 0x16462004u &&
               SDL_PIXELFORMAT_ABGR8888 == 0x16762004u, "SDL pixel formats");

/* Check the event storage and fields read in Elisa against SDL's headers. */
_Static_assert(sizeof(SDL_Event) == 16 * sizeof(uint64_t) &&
               _Alignof(SDL_Event) <= _Alignof(uint64_t), "SDL event storage");
_Static_assert(SDL_EVENT_QUIT == 0x100 && SDL_EVENT_WINDOW_FOCUS_LOST == 0x20f &&
               SDL_EVENT_WINDOW_CLOSE_REQUESTED == 0x210 && SDL_EVENT_KEY_DOWN == 0x300 &&
               SDL_EVENT_KEY_UP == 0x301 && SDL_EVENT_TEXT_INPUT == 0x303 &&
               SDL_EVENT_MOUSE_MOTION == 0x400 && SDL_EVENT_MOUSE_BUTTON_DOWN == 0x401,
               "SDL event types");
_Static_assert(offsetof(SDL_Event, type) == 0 && offsetof(SDL_WindowEvent, windowID) == 16 &&
               offsetof(SDL_TextInputEvent, text) == (sizeof(void *) == 8 ? 24 : 20) &&
               offsetof(SDL_KeyboardEvent, key) == 28 && offsetof(SDL_KeyboardEvent, mod) == 32 &&
               sizeof(SDL_Keymod) == 2 && offsetof(SDL_KeyboardEvent, repeat) == 37 &&
               offsetof(SDL_MouseMotionEvent, state) == 24 && offsetof(SDL_MouseMotionEvent, x) == 28 &&
               offsetof(SDL_MouseMotionEvent, y) == 32 && offsetof(SDL_MouseButtonEvent, button) == 24 &&
               offsetof(SDL_MouseButtonEvent, x) == 28 && offsetof(SDL_MouseButtonEvent, y) == 32,
               "SDL event fields");

int main(int argc, char **argv) {
    const SDLDesktopBindings bindings = {
        .pixel_format = SDL_PIXELFORMAT_RGBA32,
#if SDL_VERSION_ATLEAST(3, 4, 0)
        .png_writer = (uintptr_t)SDL_SavePNG,
        .png_loader = (uintptr_t)SDL_LoadPNG,
#endif
#ifdef NW_SDL_TTF
        .font = (uintptr_t)nw_sdl_attach_font,
#endif
        .poll = (uintptr_t)SDL_PollEvent,
        .pointer = (uintptr_t)nw_sdl_window_pointer,
#ifdef NW_TEST_FRAME_WRITER
        .writer = (uintptr_t)NW_TEST_FRAME_WRITER,
#endif
        .shutdown = (uintptr_t)nw_sdl_close_desktop,
#ifdef NW_MARBLE_MUJOCO
        .marble_advance = (uintptr_t)nw_sdl_marble_advance,
        .marble_key = (uintptr_t)nw_sdl_marble_key,
        .marble_finish = (uintptr_t)nw_sdl_marble_finish_frame,
        .marble_close = (uintptr_t)nw_sdl_marble_close,
        .marble_set_png_loader = (uintptr_t)nw_marble_set_png_loader,
        .marble_startup_status = (uintptr_t)nw_sdl_marble_startup_status,
#endif
    };
    return nw_sdl_desktop_main(argc, argv, &bindings);
}
