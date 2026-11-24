#!/usr/bin/env python3
"""Check SDL window failure cleanup using a temporary process-local stub."""
import shlex
import subprocess
import sys
import os
import tempfile
from pathlib import Path

linked, runtime = map(Path, sys.argv[1:3])
try:
    flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'sdl3'], text=True))
except (OSError, subprocess.CalledProcessError):
    flags = ['-I/opt/homebrew/include', '-L/opt/homebrew/lib', '-lSDL3']
link_flags = ['-Wl,-dead_strip'] if sys.platform == 'darwin' else ['-Wl,--allow-multiple-definition']
if sys.platform.startswith('linux'):
    flags.append('-lm')
source = r'''
#include <SDL3/SDL.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
extern int64_t nw_sdl_window_open(uintptr_t *, int, int, int64_t);
extern void nw_sdl_window_close(uintptr_t *);
extern int nw_sdl_open_output(uintptr_t *, int, int, int64_t, uintptr_t, uintptr_t, uint32_t, uintptr_t *);
static int fault, used, events[16], w, r, image;
static void mark(int n) { events[used++] = n; }
SDL_Surface *SDL_CreateSurface(int width, int height, SDL_PixelFormat format) {
    assert(width == 912 && height == 684 && format == SDL_PIXELFORMAT_RGBA32);
    mark(8);
    return fault == 8 ? NULL : (SDL_Surface *)&image;
}
SDL_Renderer *SDL_CreateSoftwareRenderer(SDL_Surface *surface) {
    assert(surface == (SDL_Surface *)&image);
    mark(9);
    return fault == 9 ? NULL : (SDL_Renderer *)&r;
}
void SDL_DestroySurface(SDL_Surface *surface) {
    assert(surface == (SDL_Surface *)&image);
    mark(10);
}
bool SDL_Init(SDL_InitFlags f) { (void)f; mark(1); return fault != 1; }
SDL_Window *SDL_CreateWindow(const char *t,int x,int y,SDL_WindowFlags f) { (void)t;(void)x;(void)y;assert(f == (SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY));mark(2);return fault == 2 ? 0 : (SDL_Window *)&w; }
SDL_Renderer *SDL_CreateRenderer(SDL_Window *p,const char *n) { (void)p;(void)n;mark(3);return fault == 3 ? 0 : (SDL_Renderer *)&r; }
bool SDL_SetRenderDrawBlendMode(SDL_Renderer *p,SDL_BlendMode m) { (void)p;(void)m;mark(4);return fault != 5 && fault != 11; }
void SDL_DestroyRenderer(SDL_Renderer *p) { (void)p;mark(5); }
void SDL_DestroyWindow(SDL_Window *p) { (void)p;mark(6); }
void SDL_Quit(void) { mark(7); }
const char *SDL_GetError(void) { return "injected failure"; }
int main(void) {
    static const int expected[5][7] = {{1}, {1,2,7}, {1,2,3,6,7}, {1,2,3,4,5,6,7}, {1,2,3,4,5,6,7}};
    static const int lengths[5] = {1,3,5,7,7};
    uintptr_t state[3] = {0};
    for (fault = 1; fault <= 5; fault++) {
        used = 0; memset(events, 0, sizeof(events));
        assert(nw_sdl_window_open(state, 912, 684, fault == 4 ? -1 : 65536) == 0);
        assert(state[0] == 0 && state[1] == 0 && state[2] == 0 && used == lengths[fault-1]);
        assert(memcmp(events, expected[fault-1], (size_t)used * sizeof(int)) == 0);
        nw_sdl_window_close(state); assert(used == lengths[fault-1]);
    }
    fault = 0; used = 0;
    assert(nw_sdl_window_open(state, 912, 684, 65536) == 1);
    assert(state[0] && state[1] && state[2]);
    nw_sdl_window_close(state); nw_sdl_window_close(state);
    assert(!state[0] && !state[1] && !state[2] && used == 6 && events[4] == 5 && events[5] == 6);
    used = 0;
    uintptr_t surface = 1;
    assert(nw_sdl_open_output(state, 912, 684, 65536, (uintptr_t)"test.png", 0,
                              SDL_PIXELFORMAT_RGBA32, &surface) == 0);
    assert(!state[0] && !state[1] && !state[2] && !surface && used == 0);
    static const int screenshot_events[4][5] = {{8}, {8,9,10}, {8,9,4,5,10}, {8,9,4,5,10}};
    static const int screenshot_lengths[4] = {1,3,5,5};
    for (fault = 8; fault <= 11; ++fault) {
        used = 0;
        assert(nw_sdl_open_output(state, 912, 684, fault == 10 ? -1 : 65536,
                                  (uintptr_t)"test.png", 1, SDL_PIXELFORMAT_RGBA32, &surface) == 0);
        assert(!state[0] && !state[1] && !state[2] && !surface);
        assert(used == screenshot_lengths[fault-8]);
        assert(memcmp(events, screenshot_events[fault-8], (size_t)used * sizeof(int)) == 0);
    }
    puts("SDL window and screenshot allocation fault cleanup: PASS");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    stub = tmp / 'stub.c'
    binary = tmp / ('test.exe' if os.name == 'nt' else 'test')
    stub.write_text(source)
    subprocess.run(['cc', '-O2', '-std=c11', '-o', str(binary), str(stub), str(linked), str(runtime),
                    *link_flags, *flags], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=15)
