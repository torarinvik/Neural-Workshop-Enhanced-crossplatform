#!/usr/bin/env python3
"""Build and exercise SDL Numberology result storage without a window."""
import argparse
import ctypes
import json
import os
import platform
import shlex
import struct
import sys
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--binary')
parser.add_argument('--runtime-object', type=Path)
parser.add_argument('--compiler', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'sdl3'], text=True))
with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    elisa_object = directory / 'settings.o'
    compiler = args.compiler or Path(os.environ.get('ELISACORE_BIN', root / 'toolchain/elisac-stage0-seed'))
    subprocess.run([str(compiler), '-emit', 'obj', '-O2', '-o', str(elisa_object),
                    str(root / 'src/native/sdl_host.elisa')], check=True)
    shared = directory / 'settings.dylib'
    runtime = args.runtime_object or root / 'toolchain/elisacore_runtime.o'
    subprocess.run(['cc', '-shared', '-o', str(shared), str(elisa_object), str(runtime), *flags], check=True)
    path_function = ctypes.CDLL(str(shared)).nw_numberology_results_directory
    path_function.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    path_function.restype = ctypes.c_int32
    profile_keys = ('APPDATA', 'USERPROFILE') if os.name == 'nt' else ('HOME',)
    names = ('NW_NUMBEROLOGY_RESULTS_DIR', 'NW_NUMBEROLOGY_SETTINGS_PATH', *profile_keys)
    original = {name: os.environ.get(name) for name in names}
    def resolved(capacity=4096):
        buffer = ctypes.create_string_buffer(capacity)
        return path_function(buffer, capacity), os.fsdecode(buffer.value)
    try:
        os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(directory / 'explicit')
        os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = str(directory / 'ignored')
        assert resolved() == (1, str(directory / 'explicit'))
        assert resolved(len(os.fsencode(directory / 'explicit')))[0] == 0
        del os.environ['NW_NUMBEROLOGY_RESULTS_DIR']
        status, location = resolved()
        assert (status, os.path.normpath(location)) == (1, str(directory / 'results/numberology'))
        os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = 'settings'
        assert resolved() == (1, './results/numberology')
        os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = '/settings'
        assert resolved() == (1, '/results/numberology')
        del os.environ['NW_NUMBEROLOGY_SETTINGS_PATH']
        settings_dir = 'Neural Workshop' if os.name == 'nt' else '.neural-workshop'
        expected = directory / settings_dir / 'results' / 'numberology'
        for name in profile_keys:
            os.environ.pop(name, None)
        assert resolved()[0] == 0
        for name in profile_keys:
            os.environ[name] = str(directory)
            status, location = resolved()
            assert (status, os.path.normpath(location)) == (1, str(expected))
            del os.environ[name]
        assert path_function(None, 0) == 0
    finally:
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    commit = ctypes.CDLL(str(shared)).nw_numberology_results_commit
    commit.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    commit.restype = ctypes.c_int32
    target = directory / 'atomic-record'
    temporary = directory / 'atomic-record.tmp'
    target.write_text('old')
    temporary.write_text('new')
    assert commit(os.fsencode(temporary), os.fsencode(target)) == 1
    assert target.read_text() == 'new' and not temporary.exists()
    assert commit(os.fsencode(target), os.fsencode(target)) == 0
    assert target.read_text() == 'new'
    temporary.write_text('uncommitted')
    assert commit(os.fsencode(temporary), os.fsencode(directory / 'missing/record')) == 0
    assert not temporary.exists() and target.read_text() == 'new'
    write = ctypes.CDLL(str(shared)).nw_numberology_results_write
    write.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
    write.restype = ctypes.c_int32
    payload = ctypes.create_string_buffer(b'new\x00bytes')
    temporary.write_text('someone else')
    assert write(os.fsencode(temporary), os.fsencode(target), payload, 9) == 0
    assert temporary.read_text() == 'someone else' and target.read_text() == 'new'
    temporary.unlink()
    assert write(os.fsencode(temporary), os.fsencode(target), payload, 9) == 1
    assert target.read_bytes() == b'new\x00bytes' and not temporary.exists()
    assert write(os.fsencode(target), os.fsencode(target), payload, 9) == 0
    assert target.read_bytes() == b'new\x00bytes'
    native = ctypes.CDLL(str(shared))
    row = native.nw_numberology_results_row
    row.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int32, ctypes.c_int64,
                    ctypes.c_int64, ctypes.c_int32, ctypes.c_double]
    row.restype = ctypes.c_int32
    buffer = ctypes.create_string_buffer(512)
    count = row(buffer, len(buffer), 0, 15, -(2**63), 1, 123.25)
    assert json.loads(buffer.value) == {'trial': 15, 'level': str(-(2**63)), 'correct': True, 'judged_at': 123.25}
    short = ctypes.create_string_buffer(4)
    assert row(short, len(short), 0, 15, 2, 0, 1.0) >= len(short)
    assert count == len(buffer.value)
    paths = native.nw_numberology_results_paths
    paths.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t,
                      ctypes.c_char_p, ctypes.c_uint64]
    paths.restype = ctypes.c_int32
    old_override = os.environ.get('NW_NUMBEROLOGY_RESULTS_DIR')
    try:
        os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(directory / 'created')
        final = ctypes.create_string_buffer(4096)
        temp_path = ctypes.create_string_buffer(4096)
        assert paths(final, len(final), temp_path, len(temp_path), b'example', 17) == 1
        assert os.fsdecode(final.value) == str(directory / 'created/example.json')
        assert os.fsdecode(temp_path.value) == str(directory / 'created/example.json.17.tmp')
        assert paths(final, 3, temp_path, len(temp_path), b'example', 17) == 0
        assert paths(final, len(final), temp_path, 3, b'example', 17) == 0
    finally:
        if old_override is None:
            os.environ.pop('NW_NUMBEROLOGY_RESULTS_DIR', None)
        else:
            os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = old_override
    class Row(ctypes.Structure):
        _fields_ = [('trial', ctypes.c_int64), ('level', ctypes.c_int64),
                    ('correct', ctypes.c_bool), ('judged', ctypes.c_double)]
    rows = (Row * 2)(Row(1, 9, True, 3.25), Row(2, 10, False, 4.5))
    encode = native.nw_numberology_results_encode
    encode.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_double,
                       ctypes.c_int64, ctypes.c_int64, ctypes.c_int32, ctypes.c_int32,
                       ctypes.c_int32, ctypes.c_int64, *([ctypes.c_int64] * 5)]
    encode.restype = ctypes.c_int64
    base = ctypes.addressof(rows)
    fields = [base + getattr(Row, name).offset for name in ('trial', 'level', 'correct', 'judged')]
    encoded = ctypes.create_string_buffer(1024)
    arguments = (b'example', 1.5, 9, 2, 1, 2, 1, 1, *fields, ctypes.sizeof(Row))
    length = encode(encoded, len(encoded), *arguments)
    result = json.loads(encoded.value)
    assert length == len(encoded.value) and result['right'] == 1
    assert [(r['trial'], r['level'], r['correct']) for r in result['results']] == [(1, '9', True), (2, '10', False)]
    assert encode(encoded, 10, *arguments) == -1
    create = native.nw_numberology_record_create
    create.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_int32, ctypes.c_uint64, ctypes.c_uint64]
    create.restype = ctypes.c_int64
    judge = native.nw_numberology_record_judge
    judge.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int32]
    judge.restype = ctypes.c_int32
    finish = native.nw_numberology_record_finish
    finish.argtypes = [ctypes.c_int64, ctypes.c_int64]
    persist_record = native.nw_numberology_record_persist
    persist_record.argtypes = [ctypes.c_int64, ctypes.c_uint64]
    persist_record.restype = ctypes.c_int32
    destroy = native.nw_numberology_record_destroy
    destroy.argtypes = [ctypes.c_int64]
    old_override = os.environ.get('NW_NUMBEROLOGY_RESULTS_DIR')
    try:
        os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(directory / 'record-native')
        handle = create(2, 2, 1, 123, 456)
        assert handle and judge(handle, 1, 2, 1) == 1
        assert judge(handle, 1, 2, 0) == 0
        assert judge(handle, 2, 3, 0) == 1
        finish(handle, 1)
        assert persist_record(handle, 1) == 1
        records = list((directory / 'record-native').glob('*.json'))
        assert len(records) == 1
        record = json.loads(records[0].read_text())
        assert record['id'].endswith('-123-456') and record['right'] == 1
        assert [(r['trial'], r['level'], r['correct']) for r in record['results']] == [(1, '2', True), (2, '3', False)]
        destroy(handle)
    finally:
        if old_override is None:
            os.environ.pop('NW_NUMBEROLOGY_RESULTS_DIR', None)
        else:
            os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = old_override
    class Frame(ctypes.Structure):
        _fields_ = [('commands', ctypes.c_void_p), ('count', ctypes.c_uint32),
                    ('pool', ctypes.c_void_p), ('pool_len', ctypes.c_uint32)]
    decode_frame = native.nw_decode
    decode_frame.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(Frame)]
    decode_frame.restype = ctypes.c_int32
    command = struct.pack('<B3xI6fII', 11, 0x12345678, 1, 2, 3, 4, 5, 6, 0, 3)
    payload = struct.pack('<IIII', 1313426254, 1, 1, 3) + command + b'abc'
    source = ctypes.create_string_buffer(payload)
    scratch = ctypes.create_string_buffer(40)
    frame = Frame()
    assert decode_frame(source, len(payload), scratch, 1, ctypes.byref(frame)) == 1
    assert scratch.raw == command and frame.count == 1 and frame.pool_len == 3
    assert ctypes.string_at(frame.pool, frame.pool_len) == b'abc'
    text_of = native.nw_text_of
    text_of.argtypes = [ctypes.POINTER(Frame), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    text_of.restype = ctypes.c_uint32
    text_pointer = ctypes.c_void_p()
    assert text_of(ctypes.byref(frame), scratch, ctypes.byref(text_pointer)) == 3
    assert ctypes.string_at(text_pointer, 3) == b'abc'
    struct.pack_into('<I', scratch, 32, 0xffffffff)
    assert text_of(ctypes.byref(frame), scratch, ctypes.byref(text_pointer)) == 0
    assert text_pointer.value is None
    assert decode_frame(source, len(payload) - 1, scratch, 1, ctypes.byref(frame)) == 0
    assert decode_frame(source, len(payload), scratch, 0, ctypes.byref(frame)) == 0
    malformed = ctypes.create_string_buffer(struct.pack('<IIII', 1313426254, 1, 0xffffffff, 0))
    assert decode_frame(malformed, 16, scratch, 1, ctypes.byref(frame)) == 0
    setup = native.nw_sdl_view_setup
    setup.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_int32, ctypes.c_int32]
    xcoord, ycoord = native.nw_sdl_view_x, native.nw_sdl_view_y
    for function in (xcoord, ycoord):
        function.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_float]
        function.restype = ctypes.c_float
    view = (ctypes.c_float * 4)()
    setup(view, 1824, 1000)
    assert abs(view[0] - 1000 / 684) < 1e-6
    assert abs(xcoord(view, 456) - 912) < 1e-3
    assert abs(ycoord(view, 0) - 1000) < 1e-3
    assert abs(ycoord(view, 684)) < 1e-3
    setup(view, 912, 1000)
    assert abs(xcoord(view, 0)) < 1e-3
    assert abs(ycoord(view, 0) - 842) < 1e-3
    create_surface = native.SDL_CreateSurface
    create_surface.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    create_surface.restype = ctypes.c_void_p
    create_renderer = native.SDL_CreateSoftwareRenderer
    create_renderer.argtypes = [ctypes.c_void_p]
    create_renderer.restype = ctypes.c_void_p
    read_pixel = native.SDL_ReadSurfacePixel
    read_pixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int] + [ctypes.POINTER(ctypes.c_uint8)] * 4
    read_pixel.restype = ctypes.c_bool
    native.SDL_RenderPresent.argtypes = [ctypes.c_void_p]
    native.SDL_DestroyRenderer.argtypes = [ctypes.c_void_p]
    native.SDL_DestroySurface.argtypes = [ctypes.c_void_p]
    set_color = native.nw_sdl_set_color
    set_color.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    arc = native.nw_sdl_stroke_arc
    arc.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)] + [ctypes.c_float] * 5 + [ctypes.c_uint32]
    surface = create_surface(100, 100, 0x16462004)  # SDL_PIXELFORMAT_RGBA8888
    renderer = create_renderer(surface)
    assert surface and renderer
    arc_view = (ctypes.c_float * 4)(1, 0, 0, 100)
    arc(renderer, arc_view, 50, 50, 10, 0, 90, 0xff0000ff)
    native.SDL_RenderPresent(renderer)
    def pixel(x, y):
        components = [ctypes.c_uint8() for _ in range(4)]
        assert read_pixel(surface, x, y, *(ctypes.byref(c) for c in components))
        return tuple(c.value for c in components)
    assert any(pixel(x, y)[0] > 200 for x in range(58, 62) for y in range(48, 52))
    assert any(pixel(x, y)[0] > 200 for x in range(48, 52) for y in range(38, 42))
    circle = native.nw_sdl_fill_circle
    circle.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)] + [ctypes.c_float] * 3 + [ctypes.c_uint32]
    triangle = native.nw_sdl_fill_triangle
    triangle.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)] + [ctypes.c_float] * 6 + [ctypes.c_uint32]
    circle(renderer, arc_view, 25, 25, 8, 0x00ff00ff)
    triangle(renderer, arc_view, 65, 10, 85, 10, 75, 30, 0x0000ffff)
    native.SDL_RenderPresent(renderer)
    assert pixel(25, 75)[1] > 200
    assert pixel(75, 85)[2] > 200
    draw_text = native.nw_sdl_draw_text
    draw_text.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_char_p,
                          ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint32, ctypes.c_uint8]
    draw_text(renderer, arc_view, b'A', 5, 95, 8, 0xffffffff, 6)
    native.SDL_RenderPresent(renderer)
    assert any(all(channel > 200 for channel in pixel(x, y)[:3])
               for x in range(5, 13) for y in range(5, 13))
    # In a right-aligned two-cell label, A occupies the final eight pixels
    # regardless of how many UTF-8 bytes the first character occupies.
    draw_text(renderer, arc_view, 'éA'.encode(), 95, 95, 8, 0xffffffff, 8)
    native.SDL_RenderPresent(renderer)
    assert any(pixel(x, y)[0] > 200 for x in range(88, 95) for y in range(5, 13))
    draw_text(renderer, arc_view, '→'.encode(), 70, 95, 8, 0x00ffffff, 6)
    native.SDL_RenderPresent(renderer)
    assert any(pixel(x, y)[1] > 200 and pixel(x, y)[2] > 200
               for x in range(70, 78) for y in range(5, 13))
    native.SDL_GetRenderScale.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
    scale_x, scale_y = ctypes.c_float(), ctypes.c_float()
    assert native.SDL_GetRenderScale(renderer, ctypes.byref(scale_x), ctypes.byref(scale_y))
    assert scale_x.value == scale_y.value == 1.0
    multiline = native.nw_sdl_draw_multiline
    multiline.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(Frame),
                          ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint32, ctypes.c_uint8]
    text_pool = ctypes.create_string_buffer(b'A\nA')
    text_command = ctypes.create_string_buffer(struct.pack('<B3xI6fII', 11, 0xffffffff, 0, 0, 0, 0, 0, 0, 0, 3))
    text_frame = Frame(ctypes.addressof(text_command), 1, ctypes.addressof(text_pool), 3)
    multiline(renderer, arc_view, ctypes.byref(text_frame), text_command, 5, 50, 8, 0xffffffff, 6)
    native.SDL_RenderPresent(renderer)
    assert any(all(c > 200 for c in pixel(x, y)[:3]) for x in range(5, 13) for y in range(45, 53))
    assert any(all(c > 200 for c in pixel(x, y)[:3]) for x in range(5, 13) for y in range(55, 63))
    star = native.nw_sdl_star
    star.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)] + [ctypes.c_float] * 4 + [ctypes.c_int32, ctypes.c_float, ctypes.c_uint32]
    rotated = native.nw_sdl_rotated_rect
    rotated.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)] + [ctypes.c_float] * 7 + [ctypes.c_uint32]
    star(renderer, arc_view, 80, 50, 10, 4, 5, 0, 0xff00ffff)
    rotated(renderer, arc_view, 30, 50, 12, 8, 6, 4, 30, 0xffff00ff)
    native.SDL_RenderPresent(renderer)
    assert pixel(80, 50)[0] > 200 and pixel(80, 50)[2] > 200
    assert pixel(30, 50)[0] > 200 and pixel(30, 50)[1] > 200
    class Events(ctypes.Structure):
        _fields_ = [('verdict', ctypes.c_int32), ('sounds', ctypes.c_int32), ('marker', ctypes.c_char * 64)]
    render = native.nw_sdl_render_frame
    render.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(Frame), ctypes.POINTER(Events)]
    def command(kind, color=0, values=(0, 0, 0, 0, 0, 0), ref=0, length=0):
        return struct.pack('<B3xI6fII', kind, color, *values, ref, length)
    present = native.nw_sdl_present_frame
    present.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int32, ctypes.c_int32, ctypes.c_int64]
    present.restype = ctypes.c_int32
    encoded = ctypes.create_string_buffer(struct.pack('<IIII', 1313426254, 1, 1, 0) +
                                          command(1, 0xff0000ff, (0, 0, 912, 684, 0, 0)))
    fresh_surface = create_surface(100, 100, 0x16462004)
    fresh_renderer = create_renderer(fresh_surface)
    assert fresh_surface and fresh_renderer
    def fresh_pixel(x, y):
        components = [ctypes.c_uint8() for _ in range(4)]
        assert read_pixel(fresh_surface, x, y, *(ctypes.byref(c) for c in components))
        return tuple(c.value for c in components)
    reference_surface = create_surface(100, 100, 0x16462004)
    reference_renderer = create_renderer(reference_surface)
    assert reference_surface and reference_renderer
    native.SDL_SetRenderDrawColor.argtypes = [ctypes.c_void_p] + [ctypes.c_uint8] * 4
    native.SDL_RenderClear.argtypes = [ctypes.c_void_p]
    native.SDL_SetRenderDrawColor(reference_renderer, 255, 255, 255, 255)
    native.SDL_RenderClear(reference_renderer)
    reference_view = (ctypes.c_float * 4)()
    setup(reference_view, 100, 100)
    reference_scratch = ctypes.create_string_buffer(40960)
    reference_frame, reference_events = Frame(), Events()
    assert decode_frame(encoded, len(encoded) - 1, reference_scratch, 1024, ctypes.byref(reference_frame)) == 1
    render(reference_renderer, reference_view, ctypes.byref(reference_frame), ctypes.byref(reference_events))
    native.SDL_RenderPresent(reference_renderer)
    assert present(fresh_renderer, encoded, len(encoded) - 1, 100, 100, 1) == 1
    for x, y in ((0, 0), (50, 50), (99, 99)):
        components = [ctypes.c_uint8() for _ in range(4)]
        assert read_pixel(reference_surface, x, y, *(ctypes.byref(c) for c in components))
        assert fresh_pixel(x, y) == tuple(c.value for c in components)
    native.SDL_DestroyRenderer(reference_renderer)
    native.SDL_DestroySurface(reference_surface)
    assert present(fresh_renderer, encoded, 4, 100, 100, 2) == 0
    assert fresh_pixel(50, 50)[:3] == (255, 255, 255)
    native.SDL_DestroyRenderer(fresh_renderer)
    native.SDL_DestroySurface(fresh_surface)
    assert present(None, encoded, len(encoded) - 1, 100, 100, 3) == 0
    commands = ctypes.create_string_buffer(b''.join([
        command(1, 0x00ffffff, (10, 10, 12, 8, 0, 0)),
        command(12, ref=42), command(13), command(14, ref=0, length=6)]))
    marker_pool = ctypes.create_string_buffer(b'marker')
    display = Frame(ctypes.addressof(commands), 4, ctypes.addressof(marker_pool), 6)
    events = Events()
    render(renderer, arc_view, ctypes.byref(display), ctypes.byref(events))
    native.SDL_RenderPresent(renderer)
    assert events.verdict == 42 and events.sounds == 1 and events.marker == b'marker'
    assert pixel(15, 85)[1] > 200 and pixel(15, 85)[2] > 200
    native.SDL_RenderClear.argtypes = [ctypes.c_void_p]
    def render_scene(items, pool=b''):
        set_color(renderer, 0x000000ff)
        native.SDL_RenderClear(renderer)
        packed = ctypes.create_string_buffer(b''.join(items))
        string_pool = ctypes.create_string_buffer(pool)
        scene = Frame(ctypes.addressof(packed), len(items), ctypes.addressof(string_pool), len(pool))
        result = Events()
        render(renderer, arc_view, ctypes.byref(scene), ctypes.byref(result))
        native.SDL_RenderPresent(renderer)
        return result
    red = 0xff0000ff
    cases = [
        ([command(1, red, (10, 10, 20, 20, 0, 0))], (20, 80)),
        ([command(2, red, (10, 10, 20, 20, 0, 0), 0x00ff00ff)], (20, 80)),
        ([command(4, red, (20, 20, 10, 0, 0, 0))], (20, 80)),
        ([command(7, red, (10, 10, 30, 10, 20, 30))], (20, 85)),
        ([command(17, red, (20, 20, 10, 4, 5, 0))], (20, 80)),
        ([command(8, red, length=3), command(9, values=(10, 10, 0, 0, 0, 0)),
          command(9, values=(30, 10, 0, 0, 0, 0)), command(9, values=(20, 30, 0, 0, 0, 0))], (20, 85)),
        ([command(16, red, values=(10, 20, 8, 0, 0, 0), length=2), command(9, values=(10, 20, 0, 0, 0, 0)),
          command(9, values=(30, 20, 0, 0, 0, 0))], (20, 80)),
    ]
    for scene, (x, y) in cases:
        result = render_scene(scene)
        assert result.verdict == -1 and result.sounds == 0 and result.marker == b''
        assert any(pixel(px, py)[0] > 200 for px in range(x-1, x+2) for py in range(y-1, y+2)), scene
    for scene in ([command(6, red, (10, 20, 30, 20, 8, 0))], cases[-1][0]):
        render_scene(scene)
        assert pixel(20, 77)[0] > 200
        assert pixel(20, 85)[0] < 200
    render_scene([command(3, red, (10, 10, 20, 20, 5, 0))])
    assert pixel(20, 73)[0] > 200 and pixel(20, 80)[0] < 200
    render_scene([command(2, red, (10, 10, 20, 20, 5, 0), 0x00ff00ff)])
    assert pixel(20, 73)[1] > 200 and pixel(20, 80)[0] > 200
    corner_pixels = []
    for points in (((10, 20), (30, 20), (30, 40)),
                   ((10, 20), (10, 20), (30, 20), (30, 20), (30, 40))):
        scene = [command(16, red, (10, 20, 8, 0, 0, 0), length=len(points))]
        scene += [command(9, values=(x, y, 0, 0, 0, 0)) for x, y in points]
        render_scene(scene)
        corner_pixels.append({(x, y) for x in range(5, 38) for y in range(55, 87) if pixel(x, y)[0] > 200})
    assert (32, 82) in corner_pixels[0]
    assert corner_pixels[0] == corner_pixels[1]
    glyph_pixels = []
    for weight in (0, 1):
        render_scene([command(11, red, (10, 90, 8, weight, 0, 0), 0, (6 << 24) | 1)], b'I')
        glyph_pixels.append({(x, y) for x in range(10, 22) for y in range(10, 20) if pixel(x, y)[0] > 200})
    assert glyph_pixels[0] and glyph_pixels[0] < glyph_pixels[1]
    rotation_bits = struct.unpack('<I', struct.pack('<f', 30.0))[0]
    render_scene([command(1, red, (20, 20, 12, 8, 6, 4), rotation_bits)])
    assert pixel(20, 80)[0] > 200
    render_scene([command(11, 0xffffffff, (5, 95, 8, 0, 0, 0), 0, (6 << 24) | 5000)], b'A' * 5000)
    assert any(pixel(x, y)[0] > 200 for x in range(5, 13) for y in range(5, 13))
    bad_marker = render_scene([command(14, ref=0xffffffff, length=6)], b'marker')
    assert bad_marker.marker == b''
    native.SDL_DestroyRenderer(renderer)
    native.SDL_DestroySurface(surface)
    settings_read = native.nw_numberology_settings_read
    settings_read.argtypes = [ctypes.POINTER(ctypes.c_int64)]
    settings_write = native.nw_numberology_settings_write
    settings_write.argtypes = [ctypes.POINTER(ctypes.c_int64)]
    settings_write.restype = ctypes.c_int32
    saved_override = os.environ.get('NW_NUMBEROLOGY_SETTINGS_PATH')
    settings_file = directory / 'numberology-options'
    try:
        os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = str(settings_file)
        options = (ctypes.c_int64 * 4)(9223372036854775807, 15, 77, 1)
        assert settings_write(options) == 1
        assert settings_file.read_text() == '9223372036854775807 15 1\n'
        loaded = (ctypes.c_int64 * 4)(1, 1, 99, 0)
        settings_read(loaded)
        assert list(loaded) == [9223372036854775807, 15, 99, 1]
        for invalid in (b'0 1 1', b'1 4 1', b'1 1 2', b'9223372036854775808 1 1', b'1 1 1\x00bad', b'1 1 1 ' + b' ' * 300):
            settings_file.write_bytes(invalid)
            settings_read(loaded)
            assert list(loaded) == [9223372036854775807, 15, 99, 1]
        settings_file.write_text(' +03 6 -0\n')
        settings_read(loaded)
        assert list(loaded) == [3, 6, 99, 0]
    finally:
        if saved_override is None:
            os.environ.pop('NW_NUMBEROLOGY_SETTINGS_PATH', None)
        else:
            os.environ['NW_NUMBEROLOGY_SETTINGS_PATH'] = saved_override
    task_read, task_write = native.nw_task_settings_read, native.nw_task_settings_write
    task_read.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
    task_write.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
    task_write.restype = ctypes.c_int32
    task_envs = ['NW_CROSSWORD_SETTINGS_PATH', 'NW_SCRABBLE_SETTINGS_PATH',
                 'NW_ALGEBRA_SETTINGS_PATH', 'NW_SCRAMBLE_SETTINGS_PATH']
    saved_envs = {key: os.environ.get(key) for key in task_envs}
    try:
        for task, key in enumerate(task_envs):
            task_file = directory / ('task-' + str(task))
            os.environ[key] = str(task_file)
            value = (ctypes.c_int64 * 4)(10 if task < 2 else 12, 6 if task == 2 else 5, 1, 0)
            assert task_write(task, value) == 1
            loaded = (ctypes.c_int64 * 4)(1, 1, 0, 1)
            task_read(task, loaded)
            assert list(loaded) == list(value)
            task_file.write_text('1 6 1 1\n')
            task_read(task, loaded)
            assert list(loaded) == ([1, 6, 1, 1] if task == 2 else list(value))
            before = list(loaded)
            task_file.write_bytes(b'1 1 1 1\x00junk')
            task_read(task, loaded)
            assert list(loaded) == before
    finally:
        for key, value in saved_envs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    parse_task = native.nw_task_settings_parse
    parse_task.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p),
                           ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_char_p), ctypes.c_int64]
    parse_task.restype = ctypes.c_int32
    for task, name in enumerate(('crossword', 'scrabble', 'algebra', 'scramble')):
        def parse_options(arguments):
            encoded = [b'app'] + [item.encode() for item in arguments]
            argv = (ctypes.c_char_p * len(encoded))(*encoded)
            values = (ctypes.c_int64 * 4)()
            lexicon = ctypes.c_char_p()
            status = parse_task(task, len(encoded), argv, values, ctypes.byref(lexicon), 0)
            return status, list(values), lexicon.value
        status, defaults, path = parse_options([])
        assert status == 0 and defaults == ([2, 3, 1, 1] if task == 0 else [3, 6 if task == 2 else 5, 1, 1]) and path is None
        status, values, path = parse_options([f'--{name}-level', ' +5', f'--{name}-trials', '8', f'--{name}-no-adaptive'])
        assert status == 0 and values == [5, 8, 1, 0]
        assert parse_options([f'--{name}-level'])[0] == 2
        assert parse_options([f'--{name}-trials', '4'])[0] == 2
        if task < 2:
            assert parse_options([f'--{name}-lexicon', '/tmp/words'])[2] == b'/tmp/words'
    parse_numberology = native.nw_numberology_options_parse
    parse_numberology.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p),
                                  ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_char_p), ctypes.c_int64]
    parse_numberology.restype = ctypes.c_int32
    def parse_numberology_args(arguments):
        data = [b'app'] + [arg.encode() for arg in arguments]
        argv = (ctypes.c_char_p * len(data))(*data)
        values = (ctypes.c_int64 * 4)()
        path = ctypes.c_char_p()
        status = parse_numberology(len(data), argv, values, ctypes.byref(path), 0)
        return status, list(values)
    assert parse_numberology_args([]) == (0, [1, 6, 0, 1])
    assert parse_numberology_args(['--numberology-level', ' +9223372036854775807', '--numberology-trials', '15', '--numberology-no-adaptive']) == (0, [9223372036854775807, 15, 0, 0])
    for bad in ('0', '-1', '9223372036854775808', '1_', 'abc'):
        assert parse_numberology_args(['--numberology-level', bad])[0] == 2
    assert parse_numberology_args(['--numberology-trials', '4'])[0] == 2
    assert parse_numberology_args(['--numberology-level'])[0] == 2
    read_corpus = native.nw_sdl_read_corpus
    read_corpus.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int64)]
    read_corpus.restype = ctypes.c_void_p
    native.SDL_free.argtypes = [ctypes.c_void_p]
    corpus = directory / 'corpus'
    corpus.write_bytes(b'alpha\x00beta\n')
    corpus_length = ctypes.c_int64(99)
    corpus_data = read_corpus(os.fsencode(corpus), ctypes.byref(corpus_length))
    assert corpus_data and corpus_length.value == 11
    assert ctypes.string_at(corpus_data, corpus_length.value) == b'alpha\x00beta\n'
    native.SDL_free(corpus_data)
    corpus.write_bytes(b'')
    assert not read_corpus(os.fsencode(corpus), ctypes.byref(corpus_length)) and corpus_length.value == -1
    with corpus.open('wb') as stream: stream.truncate(67108865)
    assert not read_corpus(os.fsencode(corpus), ctypes.byref(corpus_length)) and corpus_length.value == -1
    assert not read_corpus(os.fsencode(directory / 'missing-corpus'), ctypes.byref(corpus_length)) and corpus_length.value == 0
    assert not read_corpus(os.fsencode(corpus), None)
    modify, pack = native.nw_task_options_modify, native.nw_task_options_pack
    modify.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64), ctypes.c_int64, ctypes.c_int64]
    modify.restype = ctypes.c_int32
    pack.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
    pack.restype = ctypes.c_int64
    for task in range(4):
        trial_choices = ([1, 2, 3, 5, 8, 10] if task == 0 else
                         [1, 2, 3, 5, 6, 8, 10, 15] if task == 2 else [1, 2, 3, 5, 8, 10, 15])
        groups = [list(range(1, 11 if task < 2 else 13)), trial_choices, [0, 1], [0, 1]]
        for row, choices in enumerate(groups):
            for index, choice in enumerate(choices):
                for step in (-1, 1):
                    options = (ctypes.c_int64 * 4)(1, 1, 0, 0)
                    options[row] = choice
                    assert modify(task, options, row, step) == 1
                    assert options[row] == choices[(index + step) % len(choices)]
        if task < 2:
            for index, choice in enumerate(trial_choices):
                options = (ctypes.c_int64 * 4)(3, choice, 1, 1)
                assert pack(task, options) == 3 | (index << 4) | (1 << 7) | (1 << 8)
    edit_digit, backspace, modify_number = (native.nw_numberology_edit_digit,
        native.nw_numberology_edit_backspace, native.nw_numberology_modify_option)
    edit_digit.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int64), ctypes.c_int32]
    edit_text = native.nw_numberology_edit_text
    edit_text.argtypes = edit_digit.argtypes[:3] + [ctypes.c_char_p]
    backspace.argtypes = edit_digit.argtypes[:3]
    modify_number.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.c_int64, ctypes.c_int64]
    options = (ctypes.c_int64 * 4)(42, 6, 0, 1)
    editing, edit_value = ctypes.c_uint8(0), ctypes.c_int64(0)
    edit_text(options, ctypes.byref(editing), ctypes.byref(edit_value), 'a0é5!'.encode())
    assert (options[0], editing.value, edit_value.value) == (5, 1, 5)
    edit_text(options, ctypes.byref(editing), ctypes.byref(edit_value), b'9\x00ignored7')
    assert options[0] == 59
    options[0] = edit_value.value = 9223372036854775807
    edit_text(options, ctypes.byref(editing), ctypes.byref(edit_value), b'9')
    assert options[0] == 9223372036854775807
    options[0], editing.value, edit_value.value = 42, 0, 0
    edit_digit(options, ctypes.byref(editing), ctypes.byref(edit_value), 0)
    assert options[0] == 1 and editing.value == 1 and edit_value.value == 0
    edit_digit(options, ctypes.byref(editing), ctypes.byref(edit_value), 5)
    assert options[0] == 5
    backspace(options, ctypes.byref(editing), ctypes.byref(edit_value))
    assert options[0] == 1 and edit_value.value == 0
    edit_value.value = options[0] = 9223372036854775807
    edit_digit(options, ctypes.byref(editing), ctypes.byref(edit_value), 9)
    assert options[0] == edit_value.value == 9223372036854775807
    modify_number(options, 0, 1)
    assert options[0] == 9223372036854775807
    modify_number(options, 1, 1)
    modify_number(options, 2, 1)
    assert options[1] == 8 and options[3] == 0
    parse_shell = native.nw_sdl_task_options_parse
    parse_shell.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int64)]
    parse_shell.restype = ctypes.c_int32
    def shell_options(arguments):
        data = [b'app'] + [arg.encode() for arg in arguments]
        argv = (ctypes.c_char_p * len(data))(*data)
        options = (ctypes.c_int64 * 15)()
        return parse_shell(len(data), argv, options), list(options)
    assert shell_options([]) == (0, [3, 3, 1, 1, 3, 3, 1, 1, 0, 1, 10, 3, 5, 1, 1])
    numeric = [('--sudoku-level', 0, range(1, 13)), ('--sudoku-puzzles', 1, [1, 2, 3, 5, 8, 10]),
               ('--jigsaw-side', 4, [2, 3, 4, 5, 6, 7, 8, 10]), ('--jigsaw-puzzles', 5, [1, 2, 3, 5, 8, 12, 20]),
               ('--go-level', 9, range(1, 11)), ('--go-trials', 10, [1, 3, 5, 8, 10, 15, 20, 30, 50]),
               ('--crossed-wires-level', 11, range(1, 13)), ('--crossed-wires-rounds', 12, [1, 2, 3, 5, 8, 10, 15, 20])]
    for name, field, choices in numeric:
        for choice in choices:
            status, values = shell_options([name, str(choice)])
            assert status == 0 and values[field] == choice
        assert shell_options([name, '999'])[0] == 2
        assert shell_options([name])[0] == 2
    status, values = shell_options(['--sudoku-no-clashes', '--sudoku-no-adaptive', '--jigsaw-no-adaptive',
        '--jigsaw-no-preview', '--jigsaw-mark-placed', '--crossed-wires-no-adaptive', '--crossed-wires-no-grid'])
    assert status == 0 and [values[i] for i in (2, 3, 6, 7, 8, 13, 14)] == [0, 0, 0, 0, 1, 0, 0]
    corpus_path = native.nw_sdl_corpus_path
    corpus_path.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64]
    corpus_path.restype = ctypes.c_int32
    home_key = 'APPDATA' if os.name == 'nt' else 'HOME'
    old_home = os.environ.get(home_key)
    try:
        os.environ[home_key] = str(directory)
        folder = ('Brain Workshop/data/words' if os.name == 'nt' else
                  'Library/Application Support/Brain Workshop/data/words' if platform.system() == 'Darwin' else '.brainworkshop/data/words')
        for kind, name in enumerate(('lexicon.tsv', 'sentences.txt')):
            buffer = ctypes.create_string_buffer(4096)
            assert corpus_path(buffer, len(buffer), kind, 0) == 1
            assert os.fsdecode(buffer.value) == str(directory / folder / name)
            assert corpus_path(buffer, 3, kind, 0) == 0
        del os.environ[home_key]
        assert corpus_path(buffer, len(buffer), 0, 0) == 0
        assert corpus_path(buffer, len(buffer), 0, 1) == 1
        assert corpus_path(buffer, len(buffer), 3, 1) == 0
    finally:
        if old_home is None:
            os.environ.pop(home_key, None)
        else:
            os.environ[home_key] = old_home
    option_row = native.nw_sdl_option_row
    option_row.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32, ctypes.c_int64]
    option_row.restype = ctypes.c_int64
    for width, height, offset_x, offset_y in ((912, 684, 0, 0), (1824, 684, 456, 0), (912, 1000, 0, 158)):
        for row in range(4):
            x, y = offset_x + 456, height - offset_y - (474 - row * 48)
            assert option_row(x, y, width, height, 4) == row
        assert option_row(offset_x + 101, height - offset_y - 474, width, height, 4) == -1
    assert option_row(456, 210, 0, 684, 4) == -1
    click = native.nw_sdl_option_click
    click.argtypes = [ctypes.c_int64, ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int64)]
    click.restype = ctypes.c_int32
    for task in range(5):
        selection = ctypes.c_int32(0)
        values = (ctypes.c_int64 * 4)(1, 1, 1, 1)
        assert click(task, 456, 258, 912, 684, ctypes.byref(selection), values) == 1
        assert selection.value == 1 and values[1] == 1
        assert click(task, 456, 258, 912, 684, ctypes.byref(selection), values) == 1
        assert values[1] == 2
        assert click(task, 456, 306, 912, 684, ctypes.byref(selection), values) == 1
        assert selection.value == 2
        assert click(task, 456, 306, 912, 684, ctypes.byref(selection), values) == 1
        assert values[3 if task == 4 else 2] == 0
        assert click(task, 10, 10, 912, 684, ctypes.byref(selection), values) == 0
        assert selection.value == 2
    assert click(5, 456, 210, 912, 684, ctypes.byref(selection), values) == 0
    assert click(0, 456, 210, 912, 684, None, values) == 0
    black_background = native.nw_sdl_black_background
    black_background.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p)]
    black_background.restype = ctypes.c_int64
    theme_args = (ctypes.c_char_p * 2)(b'app', b'--black-background')
    assert black_background(1, theme_args) == 0 and black_background(2, theme_args) == 1
    title_key = native.nw_sdl_title_key
    title_key.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
    title_key.restype = ctypes.c_int32
    trial = ctypes.c_int64(1)
    for key, expected in ((1073741904, 4), (1073741906, 3), (32, 4), (13, 1),
                          (1073741903, 2), (1073741905, 3)):
        assert title_key(key, ctypes.byref(trial)) == 1 and trial.value == expected
    assert title_key(27, ctypes.byref(trial)) == 0 and trial.value == 3
    title_trial = native.nw_sdl_title_trial
    title_trial.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int64)]
    title_trial.restype = ctypes.c_int32
    for raw, expected in ((b'-12', 1), (b'0', 1), (b'1', 1), (b'3', 3), (b'99', 4), (b'+4', 4)):
        arguments = (ctypes.c_char_p * 3)(b'app', b'--trial', raw)
        trial = ctypes.c_int64()
        assert title_trial(3, arguments, ctypes.byref(trial)) == 0 and trial.value == expected
    invalid_trial = (ctypes.c_char_p * 3)(b'app', b'--trial', b'3x')
    assert title_trial(3, invalid_trial, ctypes.byref(trial)) == 2
    assert title_trial(2, invalid_trial, ctypes.byref(trial)) == 2
    window_args = native.nw_sdl_window_arguments
    window_args.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int32)]
    window_args.restype = ctypes.c_int32
    dimensions = (ctypes.c_int32 * 2)()
    arguments = (ctypes.c_char_p * 5)(b'app', b'--height', b'720', b'--width', b'1280')
    assert window_args(5, arguments, dimensions) == 0 and list(dimensions) == [1280, 720]
    assert window_args(1, arguments, dimensions) == 0 and list(dimensions) == [912, 684]
    invalid_size = (ctypes.c_char_p * 3)(b'app', b'--width', b'0')
    assert window_args(3, invalid_size, dimensions) == 2
    assert window_args(2, invalid_size, dimensions) == 2
    screen_id = native.nw_sdl_screen_id
    screen_id.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p)]
    screen_id.restype = ctypes.c_int64
    screens = ('taskhub', '3d-maze', 'sokoban', 'monkey-ladder', 'nback3d', 'marble', 'tetris',
               'count', 'mr-time', 'graph-mapping', 'matrix-reasoning', 'in-the-dark', 'fog-of-war',
               'removals', 'chain-of-custody', 'concentration', 'recognition', 'trivia', 'reflex',
               'algebra', 'syllogism', 'numberology', 'jigsaw', 'sudoku', 'go', 'crossed-wires',
               'scrabble', 'scramble', 'crossword', 'ncup-monte', 'moving-targets', 'lookout',
               'pursuit', 'out-of-sight', 'buzz-wire', 'donkey', 'two-hands', 'overrun', 'hanoi', 'salesman', 'ninarow', 'maze')
    for expected, name in enumerate(screens, 1):
        argv = (ctypes.c_char_p * 4)(b'app', b'--screen', name.encode(), b'--extra')
        assert screen_id(4, argv) == expected
        reordered = (ctypes.c_char_p * 5)(b"app", b"--seed", b"17", b"--screen", name.encode())
        assert screen_id(5, reordered) == expected
        assert screen_id(2, argv) == -1
    python_alias = (ctypes.c_char_p * 3)(b'app', b'--screen', b'you-are-here')
    assert screen_id(3, python_alias) == 2
    invalid = (ctypes.c_char_p * 3)(b'app', b'--screen', b'unknown')
    assert screen_id(3, invalid) == -1
    invalid[1] = b'--other'
    invalid[2] = b'go'
    assert screen_id(3, invalid) == 0 and screen_id(3, None) == 0
    screen_check = native.nw_sdl_screen_creation_check
    screen_check.argtypes = [ctypes.c_int64, ctypes.c_int64]
    screen_check.restype = ctypes.c_int32
    assert screen_check(0, 0) == 0 and screen_check(1, 0) == 0
    assert screen_check(75, 0) == 0 and screen_check(-1, 0) == 0
    for screen in range(2, 73):
        assert screen_check(screen, 1) == 0
        assert screen_check(screen, -1) == 0
        assert screen_check(screen, 0) == 1
    hub_screen = native.nw_sdl_hub_screen_id
    hub_screen.argtypes = [ctypes.c_int64] * 3
    hub_screen.restype = ctypes.c_int64
    hub_routes = ((5, 4, 12, 13, 14, 15), (16, 17, 18, 53),
                  (19, 30, 31, 32, 33, 35, 34, 36, 37, 38, 6), (8, 9),
                  (10, 11, 47, 48, 23, 45, 46, 24, 25, 26, 29, 27, 28, 20, 22, 21),
                  (39, 40, 3, 42, 2, 43, 7, 41), (44, 51, 50, 52))
    for category, routes in enumerate(hub_routes):
        for selected, expected in enumerate(routes):
            assert hub_screen(category, selected, 0) == expected
            has_options = (category == 4 and (2 <= selected <= 9 or 11 <= selected <= 15)) or (category == 1 and selected != 2)
            has_options = has_options or (category == 5 and selected in (0, 1, 3, 5, 7)) or category == 6
            assert hub_screen(category, selected, 1) == (expected if has_options else 0)
        assert hub_screen(category, len(routes) + 100, 0) == 0
    assert hub_screen(-1, 0, 0) == 0 and hub_screen(0, -1, 0) == 0
    drone_argv = (ctypes.c_char_p * 3)(b'app', b'--screen', b'drone-hoops')
    assert screen_id(3, drone_argv) == 69
    assert hub_screen(2, 19, 0) == 69 and hub_screen(2, 19, 1) == 69
    field_argv = (ctypes.c_char_p * 3)(b'app', b'--screen', b'field-manual')
    assert screen_id(3, field_argv) == 70
    assert hub_screen(2, 20, 0) == 70 and hub_screen(2, 20, 1) == 70
    safe_argv = (ctypes.c_char_p * 3)(b'app', b'--screen', b'safecracker')
    assert screen_id(3, safe_argv) == 71
    assert hub_screen(2, 21, 0) == 71 and hub_screen(2, 21, 1) == 71
    stage_argv = (ctypes.c_char_p * 3)(b'app', b'--screen', b'stagehand')
    assert screen_id(3, stage_argv) == 72
    assert hub_screen(2, 22, 0) == 72 and hub_screen(2, 22, 1) == 72
    corpus_args = native.nw_sdl_scramble_corpus_args
    corpus_args.argtypes = [ctypes.c_int64, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_char_p)]
    corpus_args.restype = ctypes.c_int32
    def parse_corpus(*arguments):
        data = [b'app', *(arg.encode() for arg in arguments)]
        argv = (ctypes.c_char_p * len(data))(*data)
        index, sentences = ctypes.c_char_p(), ctypes.c_char_p()
        result = corpus_args(len(data), argv, ctypes.byref(index), ctypes.byref(sentences))
        return result, index.value, sentences.value
    assert parse_corpus() == (0, None, None)
    assert parse_corpus('--scramble-index', 'a path', '--scramble-sentences', 'sentences') == (0, b'a path', b'sentences')
    assert parse_corpus('--scramble-index', 'first', '--scramble-index', 'last') == (0, b'last', None)
    assert parse_corpus('--scramble-index', '--scramble-sentences') == (0, b'--scramble-sentences', None)
    assert parse_corpus('--scramble-sentences')[0] == 2
    assert parse_corpus('--scramble-index')[0] == 2
    page_at = native.nw_numberology_page_at
    page_at.argtypes = [ctypes.c_float, ctypes.c_float]
    page_at.restype = ctypes.c_int32
    assert page_at(170, 342) == 4 and page_at(742, 388) == 5
    assert page_at(456, 365) == 0 and page_at(170, 341) == 0
    normalize = native.nw_sdl_normalize_pointer
    normalize.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64)]
    normalize.restype = ctypes.c_int64
    x, y = ctypes.c_int64(-1), ctypes.c_int64(-1)
    assert normalize(0, 0, 800, 600, ctypes.byref(x), ctypes.byref(y)) == 1 and (x.value, y.value) == (0, 1000000)
    assert normalize(400, 300, 800, 600, ctypes.byref(x), ctypes.byref(y)) == 1 and (x.value, y.value) == (500000, 500000)
    assert normalize(800, 600, 800, 600, ctypes.byref(x), ctypes.byref(y)) == 1 and (x.value, y.value) == (1000000, 0)
    assert normalize(1, 1, 0, 600, ctypes.byref(x), ctypes.byref(y)) == 0
    assert normalize(1, 1, 800, 600, None, ctypes.byref(y)) == 0
    map_key = native.nw_sdl_task_key
    map_key.argtypes = [ctypes.c_int64] * 5 + [ctypes.POINTER(ctypes.c_int64)]
    map_key.restype = ctypes.c_int64
    paste_modifier = native.nw_sdl_paste_modifier
    paste_modifier.argtypes = [ctypes.c_uint32]
    paste_modifier.restype = ctypes.c_int64
    enabled = (0x0400, 0x0800) if sys.platform == 'darwin' else (0x0040, 0x0080)
    for modifier in (0, 1, 0x0040, 0x0080, 0x0400, 0x0800):
        assert paste_modifier(modifier) == int(modifier in enabled)

    def mapped(task, key, phase=1, cursor=0, count=8):
        payload = ctypes.c_int64(999)
        result = map_key(task, key, phase, cursor, count, ctypes.byref(payload))
        return result, payload.value
    left, right, up, down = 0x40000050, 0x4000004f, 0x40000052, 0x40000051
    assert mapped(0, 32, 0) == (0, 0) and mapped(0, 13, 1) == (3, 0)
    assert mapped(0, ord('9')) == (1, 9) and mapped(0, 8) == (2, 0)
    assert mapped(1, 13, 3) == (4, 0) and mapped(1, 0x40000063) == (2, 0)
    assert mapped(2, ord('y')) == (1, 0) and mapped(2, right) == (2, 0)
    assert mapped(3, 32, 1) == (-1, 0) and mapped(3, ord('8')) == (1, 7)
    for task in (4, 5): assert mapped(task, ord('5')) == (5, 4)
    assert mapped(6, ord('z')) == (3, 0)
    assert mapped(7, left, 2, 0, 8) == (2, 0)
    assert mapped(7, right, 2, 7, 8) == (2, 7)
    assert mapped(7, down, 2, 2, 8) == (2, 6)
    assert mapped(7, 13, 2, 3, 8) == (1, 3)
    assert mapped(8, left, 1) == (1, 0) and mapped(8, right, 3) == (-1, 0)
    assert mapped(9, 32, 0) == (0, 0) and mapped(9, 32, 2) == (12, 0)
    assert mapped(9, ord('8'), 1) == (11, 0)
    assert mapped(10, 32) == (0, 0) and mapped(11, ord('p')) == (3, 0)
    assert mapped(12, down) == (3, 0) and mapped(13, ord('6')) == (11, 0)
    assert mapped(13, ord('7')) == (-1, 0)
    for task in (14, 15):
        for key, action in ((32, 0), (13, 0), (up, 1), (down, 2), (left, 3), (right, 4)):
            assert mapped(task, key) == (action, 0)
    assert mapped(14, ord('r')) == (5, 0) and mapped(14, ord('u')) == (-1, 0)
    assert mapped(15, ord('r')) == (6, 0) and mapped(15, ord('u')) == (5, 0)
    assert mapped(16, 32, 2) == (7, 0) and mapped(16, 13, 1) == (0, 0)
    for key, action in ((up, 3), (down, 4), (left, 5), (right, 6)):
        assert mapped(16, key) == (action, 0)
    assert mapped(17, 32, 1) == (4, 0) and mapped(17, ord('0'), 1) == (1, 0)
    assert mapped(17, 1073741903, 1) == (3, 3)
    assert mapped(17, ord('9'), 0) == (-1, 0)
    for key, action in ((up, 1), (down, 2), (left, 3), (right, 4), (8, 6), (127, 6), (ord('0'), 6), (ord('n'), 7)):
        assert mapped(18, key, 1) == (action, 0)
        assert mapped(18, key, 0) == (-1, 0)
    assert mapped(18, ord('9'), 1) == (5, 9)
    assert mapped(18, 1073741913, 1) == (5, 1)
    assert mapped(18, 1073741921, 1) == (5, 9)
    assert mapped(18, 1073741922, 1) == (6, 0)
    assert mapped(18, ord('c'), 1, 0, 11) == (-1, 0)
    assert mapped(18, ord('c'), 1, 0, 12) == (5, 12)
    assert mapped(18, ord('g'), 1) == (5, 16)
    assert mapped(19, 32, 0) == (0, 0) and mapped(19, 13, 1, 42) == (1, 42)
    assert mapped(19, 32, 2) == (2, 0) and mapped(19, 32, 4) == (-1, 0)
    assert mapped(19, ord('0'), 3) == (7, 10) and mapped(19, ord('9'), 0) == (7, 9)
    for key, action in ((up, 3), (down, 4), (left, 5), (right, 6)):
        assert mapped(19, key, 1) == (action, 0)
    for task, final in ((20, 4), (21, 5), (22, 3), (23, 3), (24, 4), (25, 2), (26, 4), (27, 4), (28, 3)):
        assert mapped(task, 32, 0) == (0, 0)
        assert mapped(task, 13, final) == (0, 0)
    for task, phase in ((22, 1), (24, 2)):
        assert mapped(task, ord('j'), phase) == (1, 0)
        assert mapped(task, ord('f'), phase) == (2, 0)
        assert mapped(task, ord('j'), 0) == (-1, 0)
    for key, action in ((up, 1), (down, 2), (left, 3), (right, 4)):
        assert mapped(23, key, 1) == (action, 0)
    for key, port in ((up, 0), (down, 1), (left, 2), (right, 3), (ord('w'), 4), (ord('s'), 5), (ord('i'), 6), (ord('k'), 7), (ord('j'), 8), (ord('l'), 9), (0x400000e1, 10), (0x400000e5, 10)):
        assert mapped(25, key, 1) == (1, port)
        assert mapped(25, key, 0) == (-1, 0)
    assert mapped(26, 32, 2) == (1, 0) and mapped(26, 13, 2) == (-1, 0)
    for key, port in ((left, 1), (ord('a'), 1), (right, 2), (up, 4), (down, 5), (ord('i'), 6), (ord('l'), 7), (ord('o'), 8), (ord('k'), 9), (32, 10)):
        assert mapped(27, key, 2) == (1, port)
    assert mapped(28, 8, 1) == (2, 0) and mapped(28, ord('z'), 1) == (1, 25)
    assert mapped(28, ord('z'), 0) == (-1, 0)
    for keys, directions in ((4, ((up, ord('w'), 8), (right, ord('d'), 6), (down, ord('s'), 2), (left, ord('a'), 4))),
                             (8, ((up, ord('w'), 8), (None, ord('e'), 9), (right, ord('d'), 6), (None, ord('c'), 3), (down, ord('x'), 2), (None, ord('z'), 1), (left, ord('a'), 4), (None, ord('q'), 7)))):
        for direction, alternatives in enumerate(directions):
            arrow, letter, keypad = alternatives
            for key in (arrow, letter, 0x40000058 + keypad):
                if key is not None:
                    assert mapped(29, key, 1, 0, keys) == (1, direction)
                    assert mapped(29, key, 0, 0, keys) == (-1, 0)
    assert mapped(29, ord('s'), 1, 0, 8) == (-1, 0)
    assert mapped(29, 32, 0, 0, 4) == (0, 0)
    for key, action in ((13, 1), (0x40000058, 1), (left, 2), (right, 3), (9, 4), (up, 5), (down, 6), (8, 8), (127, 8)):
        assert mapped(30, key, 1) == (action, 0)
    for key in range(7):
        assert mapped(30, ord('1') + key, 1) == (7, key)
        assert mapped(30, 0x40000059 + key, 1) == (7, key)
    assert mapped(30, ord('1'), 0) == (-1, 0)
    for key, action in ((left, 2), (right, 3), (up, 4), (down, 5), (9, 6), (8, 8), (127, 8)):
        assert mapped(31, key, 1) == (action, 0)
    assert mapped(31, ord('z'), 1) == (7, 25) and mapped(31, 32, 2) == (0, 0)
    assert mapped(32, 32, 0) == (0, 0) and mapped(32, 32, 2) == (5, 0)
    assert mapped(32, 13, 0) == (-1, 0)
    for key, press, release in ((up, 6, 4), (right, 7, 5), (down, 8, 6), (left, 9, 3)):
        assert mapped(32, key) == (press, 0) and mapped(33, key) == (release, 0)
    assert mapped(32, ord('l')) == (2, 0) and mapped(32, ord('r')) == (1, 0)
    assert mapped(33, ord('r')) == (-1, 0)
    assert mapped(34, up, cursor=0, count=4) == (-1, 0)
    assert mapped(34, up, cursor=1, count=4) == (101, 0)
    assert mapped(34, down, cursor=2, count=4) == (102, 0)
    assert mapped(34, down, cursor=3, count=4) == (-1, 0)
    assert mapped(34, left) == (103, -1) and mapped(34, right) == (103, 1)
    assert mapped(34, 32) == (103, 1) and mapped(34, 13) == (104, 0)
    assert mapped(34, 8) == (105, 0) and mapped(34, 127) == (105, 0)
    for task in (35, 36, 37):
        assert mapped(task, ord('v'), 1, 0, 1) == (100, 0)
        assert mapped(task, ord('v'), 1, 0, 0) == (-1, 0)
        assert mapped(task, ord('o'), 0) == (101, 0)
        assert mapped(task, 32, 0) == (102, 0)
        assert mapped(task, 8, 1) == (104, 0)
    assert mapped(35, 127, 1) == (104, 0) and mapped(36, 127, 1) == (104, 0)
    assert mapped(35, 13, 0) == (-1, 0) and mapped(36, 13, 1) == (103, 0)
    assert mapped(37, 13, 0) == (103, 0) and mapped(37, 0x40000058, 1) == (103, 0)
    assert mapped(36, 0x4000004b) == (105, 0) and mapped(36, 0x4000004e) == (106, 0)
    assert mapped(38, 27, cursor=1, count=1) == (1, 0)
    assert mapped(38, ord('q'), cursor=0, count=0) == (1, 0)
    assert mapped(38, ord('q'), cursor=1, count=0) == (-1, 0)
    assert mapped(38, ord('q'), cursor=0, count=1) == (-1, 0)
    assert mapped(39, left, 0) == (0, 11) and mapped(39, right, 7) == (0, 8) and mapped(39, right, 11) == (0, 0)
    assert mapped(39, up, cursor=0, count=6) == (1, 5) and mapped(39, down, cursor=5, count=6) == (1, 0)
    assert mapped(39, 13) == (2, 0) and mapped(39, ord('c')) == (3, 0)
    failed = directory / 'not-a-directory'
    failed.write_text('retain me')
    saved = directory / 'results'
    start = native.nw_numberology_results_start
    start.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int64, ctypes.c_int64, ctypes.c_int32]
    manager_judge = native.nw_numberology_results_judge
    manager_judge.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int64, ctypes.c_int64, ctypes.c_int32]
    manager_finish = native.nw_numberology_results_finish
    manager_finish.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int64]
    manager_close = native.nw_numberology_results_close
    manager_close.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
    manager = (ctypes.c_size_t * 2)()
    old_results = os.environ.get('NW_NUMBEROLOGY_RESULTS_DIR')
    try:
        os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(failed)
        start(manager, 1, 1, 1)
        manager_judge(manager, 1, 1, 1)
        manager_judge(manager, 1, 1, 1)
        manager_finish(manager, 1)
        start(manager, 2, 1, 0)
        assert manager[1], 'failed save must stay pending after a new session'
        os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = str(saved)
        manager_judge(manager, 1, 2, 0)
        manager_close(manager)
        assert list(manager) == [0, 0]
    finally:
        if old_results is None:
            os.environ.pop('NW_NUMBEROLOGY_RESULTS_DIR', None)
        else:
            os.environ['NW_NUMBEROLOGY_RESULTS_DIR'] = old_results
    records = [json.loads(path.read_text()) for path in saved.glob('*.json')]
    assert len(records) == 2
    first = next(record for record in records if record['completed'])
    partial = next(record for record in records if not record['completed'])
    assert first['right'] == 1 and first['options'] == [1, 1, 1]
    assert [(row['trial'], row['level'], row['correct']) for row in first['results']] == [(1, '1', True)]
    assert partial['options'] == [2, 1, 0] and partial['results'][0]['correct'] is False
    assert len({record['id'] for record in records}) == 2
    assert failed.read_text() == 'retain me'
    assert not list(saved.glob('*.tmp'))
    if args.binary:
        lifecycle = directory / 'lifecycle'
        env = os.environ.copy()
        env['NW_NUMBEROLOGY_RESULTS_DIR'] = str(lifecycle)
        env['NW_NUMBEROLOGY_SETTINGS_PATH'] = str(directory / 'settings')
        subprocess.run([args.binary, '--selftest-numberology-result-lifecycle'], check=True, env=env)
        rows = [json.loads(path.read_text()) for path in lifecycle.glob('*.json')]
        assert len(rows) == 1 and rows[0]['completed'] and rows[0]['right'] == 1
        assert rows[0]['results'][0]['correct'] and rows[0]['results'][0]['trial'] == 1

print('Numberology SDL results: atomic records, duplicate prevention and failed-save retry pass')
