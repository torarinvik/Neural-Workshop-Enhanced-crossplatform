#!/usr/bin/env python3
"""Check the optional Elisa runtime fallback's exported ABI headlessly."""
import ctypes
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compiler = Path(os.environ.get('ELISACORE_BIN', root / 'toolchain/elisac-stage0-seed'))
with tempfile.TemporaryDirectory() as temporary:
    obj = Path(temporary) / 'shim.o'
    library_path = Path(temporary) / 'shim.dylib'
    subprocess.run([str(compiler), '-emit', 'obj', '-O2', '-o', str(obj),
                    str(root / 'src/native/pymodule_runtime_shim.elisa')], check=True)
    subprocess.run(['cc', '-shared', '-o', str(library_path), str(obj)], check=True)
    library = ctypes.CDLL(str(library_path))
    for name in ('elisa_profile_allocation_negotiate', 'elisa_profile_region_layout_negotiate'):
        function = getattr(library, name); function.argtypes = [ctypes.c_uint32]; function.restype = ctypes.c_uint32
        assert function(123) == 0
    for name, integer, fallback in [('u32', ctypes.c_uint32, 0xfedcba98),
                                     ('i32', ctypes.c_int32, -12345),
                                     ('usize', ctypes.c_size_t, 123456789),
                                     ('isize', ctypes.c_ssize_t, -123456789)]:
        function = getattr(library, 'elisa_native_callback_call_' + name + '_voidp')
        function.argtypes = [ctypes.c_void_p, ctypes.c_void_p, integer]; function.restype = integer
        assert function(None, None, fallback) == fallback
    for name in ('elisa_native_callback_spawn_join_u32_voidp',):
        function = getattr(library, name)
        function.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]; function.restype = ctypes.c_uint32
        assert function(None, None, 321) == 321
    for name in ('elisa_native_callback_context_result_u32', 'elisa_native_callback_context_spawn_join_u32_voidp'):
        function = getattr(library, name)
        function.argtypes = [ctypes.c_void_p, ctypes.c_uint32]; function.restype = ctypes.c_uint32
        assert function(None, 123) == 123
    join = library.elisa_native_callback_context_join_u32_voidp
    join.argtypes = [ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint32]; join.restype = ctypes.c_uint32
    assert join(0, None, 456) == 456
    start = library.elisa_native_callback_context_start_u32_voidp
    start.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]; start.restype = ctypes.c_int32
    assert start(None, None) == -1
    ptr = library.elisa_native_callback_ptr
    ptr.argtypes = [ctypes.c_void_p]; ptr.restype = ctypes.c_void_p
    assert ptr(None) is None
    entry = library.elisa_native_callback_context_entry_u32_voidp
    entry.argtypes = []; entry.restype = ctypes.c_void_p
    assert entry() is None
    create = library.elisa_native_callback_context_new_u32_voidp
    create.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]; create.restype = ctypes.c_void_p
    assert create(None, None, 5) is None
print('Python runtime fallback: optional profiler and callback ABI pass')
