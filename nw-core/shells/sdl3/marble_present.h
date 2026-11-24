/* Bridge the Marble OpenGL stage into the existing SDL renderer. */
#include <stddef.h>

typedef struct {
    SDL_Window *window;
    SDL_GLContext context;
    SDL_Texture *texture;
    SDL_Surface *pixels;
    uintptr_t scene;
} MarblePresentation;

/* Keep the public SDL surface prefix and the presentation slots aligned with Elisa. */
_Static_assert(offsetof(SDL_Surface, w) == 8 &&
               offsetof(SDL_Surface, h) == 12 &&
               offsetof(SDL_Surface, pitch) == 16 &&
               offsetof(SDL_Surface, pixels) == (sizeof(void *) == 8 ? 24 : 20),
               "SDL surface ABI");
_Static_assert(sizeof(MarblePresentation) == 5 * sizeof(uintptr_t), "Marble presentation ABI");
_Static_assert(offsetof(MarblePresentation, window) == 0 &&
               offsetof(MarblePresentation, context) == sizeof(uintptr_t) &&
               offsetof(MarblePresentation, texture) == 2 * sizeof(uintptr_t) &&
               offsetof(MarblePresentation, pixels) == 3 * sizeof(uintptr_t) &&
               offsetof(MarblePresentation, scene) == 4 * sizeof(uintptr_t),
               "Marble presentation field order");

extern int nw_marble_present(MarblePresentation *, SDL_Renderer *, uintptr_t, int, int, int64_t);
extern void nw_marble_present_close(MarblePresentation *);
