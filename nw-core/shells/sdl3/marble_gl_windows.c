#include <SDL3/SDL.h>

/* The same list defines the names, slots, and Windows calling conventions. */
enum MarbleGLProcedure {
#define GL_PROC(result, name, parameters, arguments) SLOT_##name,
#include "marble_gl_windows_procs.inc"
#undef GL_PROC
    MARBLE_GL_COUNT
};

static const char *const names[] = {
#define GL_PROC(result, name, parameters, arguments) #name,
#include "marble_gl_windows_procs.inc"
#undef GL_PROC
};

static SDL_FunctionPointer procedures[MARBLE_GL_COUNT];

const char *nw_marble_windows_gl_name(uint32_t index) {
    return index < MARBLE_GL_COUNT ? names[index] : NULL;
}

void nw_marble_bind_windows_gl(uint32_t index, SDL_FunctionPointer procedure) {
    if (index < MARBLE_GL_COUNT) procedures[index] = procedure;
}

#define GL_PROC(result, name, parameters, arguments) \
    result name parameters { return ((result (__stdcall *) parameters)procedures[SLOT_##name]) arguments; }
#include "marble_gl_windows_procs.inc"
#undef GL_PROC
