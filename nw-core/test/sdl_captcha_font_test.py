"""Exercise faced display-list glyphs on an SDL software renderer."""

import ctypes
from ctypes.util import find_library
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tempfile

SIZE = 160
SDL_RGBA32 = 0x16762004
SYMBOLS = ("nw_sdl_present_frame_theme", "nw_sdl_select_font", "nw_sdl_attach_font")


def bind(library, name, result, *arguments):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = arguments
    return function


def check_rendering(library, library_path):
    sdl = ctypes.CDLL(library_path)
    pointer, integer = ctypes.c_void_p, ctypes.c_int
    create_surface = bind(sdl, "SDL_CreateSurfaceFrom", pointer, integer, integer,
                          ctypes.c_uint32, pointer, integer)
    destroy_surface = bind(sdl, "SDL_DestroySurface", None, pointer)
    create_renderer = bind(sdl, "SDL_CreateSoftwareRenderer", pointer, pointer)
    destroy_renderer = bind(sdl, "SDL_DestroyRenderer", None, pointer)
    draw = bind(library, "nw_sdl_present_frame_theme", integer, pointer, pointer, ctypes.c_int64,
                integer, integer, ctypes.c_int64, ctypes.c_int64)
    select_font = bind(library, "nw_sdl_select_font", None, pointer, pointer)
    pixels = ctypes.create_string_buffer(SIZE * SIZE * 4)
    surface = create_surface(SIZE, SIZE, SDL_RGBA32, pixels, SIZE * 4)
    assert surface
    renderer = create_renderer(surface)
    assert renderer

    def letter(angle, face, character="I"):
        command = struct.pack("<B3xI6fII", 11, 0x000000ff, 456, 342, 220, 0,
                              angle, face, 0, (4 << 24) | 1)
        packet = ctypes.create_string_buffer(struct.pack("<4I", 1313426254, 1, 1, 1)
                                               + command + character.encode("ascii"))
        assert draw(renderer, packet, len(packet) - 1, SIZE, SIZE, 0, 0)
        points = [(x, y) for y in range(SIZE) for x in range(SIZE)
                  if pixels[(y * SIZE + x) * 4][0] < 128]
        assert points, (angle, face, character)
        xs, ys = zip(*points)
        return (max(xs) - min(xs), max(ys) - min(ys)), points

    def check_rotation():
        (width, height), _ = letter(0, 1)
        (rotated_width, rotated_height), _ = letter(90, 1)
        assert width < height and rotated_width > rotated_height
        assert abs(width - rotated_height) <= 2 and abs(height - rotated_width) <= 2

    try:
        check_rotation()
        if sys.platform == "darwin":
            os.environ.pop("NW_SDL_FONT", None)
            select_font(renderer, ctypes.cast(library.nw_sdl_attach_font, pointer))
            check_rotation()
            assert letter(0, 1, "Q")[1] != letter(0, 2, "Q")[1], "Arial and Times rendered the same glyph"
    finally:
        destroy_renderer(renderer)
        destroy_surface(surface)


def main(objects):
    flags = shlex.split(subprocess.check_output(
        ["pkg-config", "--libs", "sdl3", "sdl3-ttf"], text=True))
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        out = directory / ("font-check.dylib" if sys.platform == "darwin" else "font-check.so")
        if sys.platform == "darwin":
            exports = directory / "exports"
            exports.write_text("".join(f"_{name}\n" for name in SYMBOLS))
            link = ["-dynamiclib", "-Wl,-dead_strip", f"-Wl,-exported_symbols_list,{exports}"]
        else:
            link = ["-shared", "-Wl,--allow-multiple-definition", "-lm"]
        subprocess.run(["cc", *link, "-o", str(out), *objects, *flags], check=True)
        sdl_path = find_library("SDL3")
        if not sdl_path:
            libdir = subprocess.check_output(["pkg-config", "--variable=libdir", "sdl3"], text=True).strip()
            sdl_path = str(Path(libdir) / ("libSDL3.dylib" if sys.platform == "darwin" else "libSDL3.so"))
        check_rendering(ctypes.CDLL(str(out)), sdl_path)
    print("PASS: SDL Captcha fallback glyph rotation and macOS typeface selection")


if __name__ == "__main__":
    main(sys.argv[1:])
