#!/usr/bin/env python3
"""Generate the Windows ARM64 OpenGL FFI from the Marble declarations."""
from pathlib import Path
import re
import sys


DECLARATION = re.compile(
    r"extern (gl\w+)\(([^)]*)\)(?: -> (\w+))?(?: can\[[^\]]+\])?"
)


def generate(native: Path) -> str:
    sources = sorted(native.glob("marble_gl_*.elisa")) + [native / "sdl_mujoco_exports.elisa"]
    procedures = {}
    for source in sources:
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.startswith("extern gl"):
                continue
            match = DECLARATION.fullmatch(line)
            if match is None:
                raise ValueError(f"{source}: invalid OpenGL declaration {line!r}")
            name, parameters, result = match.groups()
            if name in procedures:
                raise ValueError(f"{source}: duplicate OpenGL procedure {name}")
            procedures[name] = (parameters, result or "void")
    if not procedures:
        raise ValueError("No Marble OpenGL declarations found")

    lines = [
        "# Generated from the Marble OpenGL FFI declarations.",
        "# ARM64 procedure addresses are instruction-aligned, so no address",
        "# can collide with Elisa's low-bit closure tag.",
        f"global mutable marble_windows_gl: usize[{len(procedures)}] = zeroed",
        "",
        "def marble_windows_gl_name(index: u32) -> u8&?:",
        "    can Unsafe.PointerCast:",
        "        trusted Unsafe.PointerCast:",
    ]
    for index, name in enumerate(procedures):
        lines.append(f'            return "{name}".uintptr().cast[u8&] if index == {index}.u32()')
    lines.extend([
        "            return null",
        "",
        "def marble_windows_bind_gl(index: u32, procedure: void&):",
        "    can Abort.Panic, Global.Write, Unsafe.PointerCast:",
        f"        return if index >= {len(procedures)}.u32()",
        "        trusted Unsafe.PointerCast:",
        "            marble_windows_gl[index.usize()] <- procedure.uintptr()",
        "",
        "export fn nw_marble_windows_gl_name(index: u32) -> u8&? = marble_windows_gl_name",
        "export fn nw_marble_bind_windows_gl(index: u32, procedure: void&) = marble_windows_bind_gl",
    ])
    for index, (name, (parameters, result)) in enumerate(procedures.items()):
        pairs = [pair.split(": ", 1) for pair in parameters.split(", ")] if parameters else []
        arguments = ", ".join(argument for argument, _ in pairs)
        types = ", ".join(type_ for _, type_ in pairs)
        signature = f"fn({types}) -> {result}"
        invoke = f"dispatch({arguments})"
        if result != "void":
            invoke = f"return {invoke}"
        lines.extend([
            "",
            f"def marble_windows_{name}({parameters}) -> {result}:",
            "    can Abort.Panic, Global.Read, Unsafe.PointerCast:",
            "        trusted Unsafe.PointerCast:",
            f"            dispatch: {signature} = marble_windows_gl[{index}].cast[{signature}]",
            f"            {invoke}",
            f"export fn {name}({parameters}) -> {result} = marble_windows_{name}",
        ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    native, output = map(Path, sys.argv[1:])
    output.write_text(generate(native), encoding="utf-8")
