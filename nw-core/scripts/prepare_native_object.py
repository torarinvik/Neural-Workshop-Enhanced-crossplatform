#!/usr/bin/env python3
"""Prepare an SDL object to use the selected runtime's shared arena state.

Stage1's native app object contains common definitions for these allocator
state cells, while its matching runtime object contains the implementations
that own and mutate them. In a private link copy, turn only the app object's
common entries into undefined references so both sets of code use the runtime
object's one canonical state. The original application object is left intact.
"""

from __future__ import annotations

import struct
import shutil
import sys
from pathlib import Path


MACHO_MAGIC_64 = 0xFEEDFACF
LC_SYMTAB = 0x2
N_TYPE = 0x0E
N_UNDF = 0x00
N_SECT = 0x0E
N_EXT = 0x01
SHARED_ARENA_STATE = (
    "__elisa_collection_stack_memo",
    "__elisa_region_cache",
    "__elisa_free_hint",
    "__elisa_free_hint_owner_cell",
    "__elisa_reserve_region_cache",
    "__elisa_profile_allocation_status_cell",
    "__elisa_profile_allocation_lock_cell",
    "__elisa_arena_cache_lock_cell",
)


def prepare(source_path: Path, output_path: Path) -> int:
    data = bytearray(source_path.read_bytes())
    if len(data) < 32 or struct.unpack_from("<I", data, 0)[0] != MACHO_MAGIC_64:
        shutil.copyfile(source_path, output_path)
        return 0

    command_count = struct.unpack_from("<I", data, 16)[0]
    command_offset = 32
    symtab: tuple[int, int, int, int] | None = None
    for _ in range(command_count):
        if command_offset + 8 > len(data):
            raise ValueError("truncated Mach-O load command")
        command, command_size = struct.unpack_from("<II", data, command_offset)
        if command_size < 8 or command_offset + command_size > len(data):
            raise ValueError("invalid Mach-O load command size")
        if command == LC_SYMTAB:
            if command_size < 24:
                raise ValueError("truncated Mach-O symbol-table command")
            symoff, nsyms, stroff, strsize = struct.unpack_from("<IIII", data, command_offset + 8)
            symtab = (symoff, nsyms, stroff, strsize)
        command_offset += command_size
    if symtab is None:
        raise ValueError("Mach-O object has no symbol table")

    symoff, nsyms, stroff, strsize = symtab
    if symoff + nsyms * 16 > len(data) or stroff + strsize > len(data):
        raise ValueError("Mach-O symbol table extends beyond the object")
    strings = data[stroff : stroff + strsize]
    wanted = {f"_{name}": 0 for name in SHARED_ARENA_STATE}
    for index in range(nsyms):
        entry = symoff + index * 16
        string_index = struct.unpack_from("<I", data, entry)[0]
        if string_index == 0 or string_index >= len(strings):
            continue
        terminator = strings.find(b"\0", string_index)
        if terminator < 0:
            raise ValueError("unterminated Mach-O symbol name")
        symbol_name = strings[string_index:terminator].decode("utf-8", errors="strict")
        if symbol_name not in wanted:
            continue

        symbol_type = data[entry + 4]
        section_index = data[entry + 5]
        value = struct.unpack_from("<Q", data, entry + 8)[0]
        if symbol_type & N_TYPE != N_SECT or symbol_type & N_EXT == 0 or section_index == 0 or value == 0:
            raise ValueError(f"{symbol_name} is not a common external definition")

        # LLVM emits these common globals as N_SECT entries in __common. Turn
        # the entry into N_UNDF|N_EXT with no section/value;
        # relocations in this object then resolve to the matching runtime object.
        data[entry + 4] = N_UNDF | N_EXT
        data[entry + 5] = 0
        struct.pack_into("<H", data, entry + 6, 0)
        struct.pack_into("<Q", data, entry + 8, 0)
        wanted[symbol_name] += 1

    missing = sorted(symbol for symbol, count in wanted.items() if count != 1)
    if missing:
        raise ValueError(f"expected exactly one common definition for each shared arena cell; invalid: {missing}")
    output_path.write_bytes(data)
    return sum(wanted.values())


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit("usage: prepare_native_object.py SDL_OBJECT OUTPUT_OBJECT")
    try:
        count = prepare(Path(argv[1]), Path(argv[2]))
    except (OSError, ValueError, UnicodeError) as error:
        print(f"prepare_native_object.py: {error}", file=sys.stderr)
        return 2
    print(f"prepared native SDL link object with {count} runtime-owned arena cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
