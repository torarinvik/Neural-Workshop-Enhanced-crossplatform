# Native desktop shell (SDL3)

    brew install sdl3 pkg-config      # or the platform equivalent
    scripts/build_sdl3.sh             # builds AND runs the headless selftest
    build/nw-sdl3                     # the window
    build/nw-sdl3 --selftest 180      # headless title/display-list smoke
    build/nw-sdl3 --selftest-tetris   # headless Freeform Tetris lifecycle smoke

## Current boundary

The SDL shell exposes the shared title/task-hub display-list contract plus the
native task adapters listed by `scripts/build_sdl3.sh`. It does not manufacture
a preview or placeholder task session. Additional desktop task adapters are
added only when they can drive a real controller and preserve the same
state/action/clock contract.

Marble Maze currently has its shared controller and a 2D display-list fallback.
The SDL ABI exposes the controller's canonical generated-board bytes via
`nw_marble_board_write`, the transport boundary needed by a native MuJoCo/3D
host; it is not yet a native physics or 3D-render implementation.

The title call uses the source renderer's presentation flags that suppress
the original-only accelerator block. Consequently every visible SDL control
describes an action this port actually implements.

## What it is

This is the SDL3 consumer for the same encoded display list used by the other
host shells. The Elisa core decides what a frame contains; this shell turns
commands into pixels and owns only the window, clock, and event loop.

The title, task hub, and current native task adapters have scalar C ABIs in
src/native/sdl_exports.elisa. `nw_frame_alloc` returns a real native pointer
(malloc cast to i64), so the shell casts it back before decoding. Freeform
Tetris uses the same controller kernel and display scene as the browser and
Python adapters.

## Elisa migration

Syllogism option validation, command-line parsing and settings persistence now
live in `src/native/syllogism_options*.elisa`. They call SDL3 through its native
FFI for environment, clock and file operations; writes use an exclusive temporary
file and atomic rename. `test/syllogism_sdl_options_test.py` compiles this unit
with Stage0 and tests the C ABI directly through Python `ctypes`, without a C
implementation or a window. The main SDL event loop, renderer, display-list
decoder and Numberology results helper still contain C and remain to be ported.
A fresh Stage1 product is required to verify the full SDL artifact.

## Coverage

The decoder handles RECT, BORDERED_RECT, BOX, CIRCLE, ARC, LINE, TRIANGLE,
POLYGON/POLY_POINT, TEXT, VERDICT, and MARKER. Circles, triangles, and
polygons use SDL_RenderGeometry; arcs are polylines because SDL3 has no arc
primitive.

SPRITE and SOUND remain separate renderer work. The title selftest still
checks pooled text and the frame-end marker instead of treating a command
count as proof of a valid frame.

## Still to check

1. Build against the real latest Stage1 core object on each supported desktop
   platform.
2. Compare title frames against the browser at the same banner and theme.
3. Keep test/display_decode.py and src/native/display_decode.elisa consistent as the
   display-list protocol evolves.

The headless selftests prove ABI decoding, the Tetris lifecycle, and
resource-free rendering paths; they are not evidence that full visual parity
or every task's desktop adapter is done.
