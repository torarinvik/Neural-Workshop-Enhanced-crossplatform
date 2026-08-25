#!/usr/bin/env python3
"""Reference decoder for the nw-core display list.

This is the shell-side contract: every platform shell walks the stream the way
this module does. Kept small and dependency-free so it can be transliterated
into TypeScript, Swift or Kotlin directly.

Format:  [u32 magic][u32 version][u32 cmd_count][u32 pool_len][cmds...][pool]
Command: 40 bytes -- u8 kind, 3 pad, u32 color, 6 x f32, u32 ref, u32 len
"""
from __future__ import annotations

import struct
from typing import Any, Dict, List

MAGIC = 1313426254
VERSION = 1
CMD_SIZE = 40

KIND_NAMES = {
    1: "rect", 2: "bordered_rect", 3: "box", 4: "circle", 5: "arc",
    6: "line", 7: "triangle", 8: "polygon", 9: "poly_point", 10: "sprite",
    11: "text", 12: "verdict", 13: "sound", 14: "marker",
}

ANCHOR_NAMES = ["left_bottom", "center_bottom", "right_bottom",
                "left_center", "center_center", "right_center",
                "left_top", "center_top", "right_top"]


class DisplayListError(Exception):
    pass


def decode(blob: bytes) -> List[Dict[str, Any]]:
    if len(blob) < 16:
        raise DisplayListError("truncated header")
    magic, version, count, pool_len = struct.unpack_from("<IIII", blob, 0)
    if magic != MAGIC:
        raise DisplayListError(f"bad magic {magic:#x}")
    if version != VERSION:
        raise DisplayListError(f"unsupported version {version}")
    need = 16 + count * CMD_SIZE + pool_len
    if len(blob) != need:
        raise DisplayListError(f"length {len(blob)} != expected {need}")
    pool = blob[16 + count * CMD_SIZE:]

    commands = []
    for i in range(count):
        off = 16 + i * CMD_SIZE
        kind, color, a, b, c, d, e, f, ref, ln = struct.unpack_from(
            "<BxxxIffffffII", blob, off)
        cmd: Dict[str, Any] = {"kind": KIND_NAMES.get(kind, f"unknown_{kind}")}
        if kind in (11, 14):  # text, marker -- string in the pool
            length = ln & 0xFFFFFF
            if ref + length > len(pool):
                raise DisplayListError(f"string [{ref},{ref + length}) outside pool")
            cmd["text"] = pool[ref:ref + length].decode("utf-8")
            if kind == 11:
                cmd["anchor"] = ANCHOR_NAMES[(ln >> 24) & 0xFF]
        _fill(cmd, kind, color, a, b, c, d, e, f, ref, ln)
        commands.append(cmd)
    return commands


def _fill(cmd, kind, color, a, b, c, d, e, f, ref, ln):
    """Name the generic slots according to the command tag."""
    if kind in (1, 2, 3):                      # rect family
        cmd.update(x=a, y=b, w=c, h=d, color=color)
        if kind == 2:
            cmd.update(border=ref, border_width=e)
        if kind == 3:
            cmd.update(thickness=e)
    elif kind == 4:
        cmd.update(x=a, y=b, radius=c, color=color)
    elif kind == 5:
        cmd.update(x=a, y=b, radius=c, start_angle=e, sweep=f, color=color)
    elif kind == 6:
        cmd.update(x1=a, y1=b, x2=c, y2=d, width=e, color=color)
    elif kind == 7:
        cmd.update(x1=a, y1=b, x2=c, y2=d, x3=e, y3=f, color=color)
    elif kind == 8:
        cmd.update(points=ln, color=color)
    elif kind == 9:
        cmd.update(x=a, y=b)
    elif kind == 10:
        cmd.update(asset=ref, x=a, y=b, scale=c, rotation=e, color=color)
    elif kind == 11:
        cmd.update(x=a, y=b, size=c, color=color)
    elif kind == 12:
        cmd.update(verdict=ref)
    elif kind == 13:
        cmd.update(asset=ref, gain=a)


def rgba(color: int):
    return ((color >> 24) & 255, (color >> 16) & 255,
            (color >> 8) & 255, color & 255)


def canonical(commands: List[Dict[str, Any]]) -> List[str]:
    """One stable line per command; floats at fixed precision so a last-bit
    difference shows up as text rather than hiding inside a hash."""
    lines = []
    for cmd in commands:
        parts = [cmd["kind"]]
        for key in sorted(k for k in cmd if k != "kind"):
            value = cmd[key]
            if isinstance(value, float):
                parts.append(f"{key}={value:.4f}")
            elif key == "color" or key == "border":
                parts.append(f"{key}=" + ":".join(str(v) for v in rgba(value)))
            else:
                parts.append(f"{key}={value}")
        lines.append(" ".join(parts))
    return lines
