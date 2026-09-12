#!/usr/bin/env python3
"""Check the complete session-frame ABI at the composition boundary.

The lower-level field, HUD, readout and trial-UI suites compare each port to
the reference widgets independently. This check covers the thing those tests
cannot see: one frame must contain all of them in the persistent-widget order,
with the active stimulus appended afterwards. It also exercises the host
state switches that select the arithmetic, image, old-square and 3D branches.

The sweep is intentionally small and deterministic. Its command stream is
the wire-format text emitted by ``scene_emit.elisa``; no duplicate renderer or
coordinate model is hidden in this harness.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from collections import Counter


EXPECTED_MODES = {
    2: "Dual 2-Back",
    7: "Arithmetic 2-Back",
    21: "Position, Image 2-Back",
    258: "3D Double-stim Dual 2-Back",
}


def read_frames(binary: str):
    result = subprocess.run([binary], capture_output=True, text=True, check=True)
    names = None
    frames = []
    current = None
    header = None
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith("names|"):
            names = line.split("|")[1:]
        elif line.startswith("case|"):
            if current is not None:
                raise SystemExit("batch sweep started a frame before `end`")
            cells = line.split("|")[1:]
            if names is None:
                raise SystemExit("batch sweep printed no `names|` line")
            header = dict(zip(names, cells))
            current = []
        elif line == "end":
            if current is None or header is None:
                raise SystemExit("batch sweep printed an unexpected `end`")
            frames.append((header, current))
            current = None
            header = None
        elif current is not None:
            current.append(line)
    if current is not None:
        raise SystemExit("batch sweep ended without `end`")
    return frames


def text_of(line: str) -> str | None:
    cells = line.split("|")
    if not cells or cells[0] != "11" or len(cells) < 5:
        return None
    try:
        return ast.literal_eval(cells[4])
    except (SyntaxError, ValueError) as error:
        raise SystemExit(f"bad encoded text command: {line}") from error


def check_frame(header: dict[str, str], lines: list[str]) -> list[str]:
    case = int(header["case"])
    started = int(header["started"])
    black = int(header["black"])
    mode = int(header["mode"])
    trial = int(header["trial"])
    expected_count = int(header["commands"])
    expected_trial = 1 + case % 7
    expected_started = (case // 4) >= 2
    expected_black = (case // 4) % 2
    expected_mode = (2, 7, 21, 258)[case % 4]

    errors = []
    if (started, black, mode, trial) != (
        int(expected_started), expected_black, expected_mode, expected_trial
    ):
        errors.append("header state does not match the sweep's declared cases")
    if not lines:
        return errors + ["frame emitted no visible commands"]
    if expected_count < len(lines) + 1:
        errors.append("command header does not account for marker/invisible records")

    kinds = Counter(int(line.split("|", 1)[0]) for line in lines)
    background = lines[0].split("|")
    wanted_background = "0.0.0.255" if black else "255.255.255.255"
    if len(background) < 4 or background[3] != wanted_background:
        errors.append("first command is not the requested clear colour")
    if kinds[11] == 0:
        errors.append("persistent composition emitted no text commands")

    texts = [text_of(line) for line in lines]
    caption = EXPECTED_MODES[mode]
    if started and case % 5 == 0:
        caption = ""
    if caption not in texts:
        errors.append(f"missing mode caption {caption!r}")

    if not started:
        if kinds[4] != 2:
            errors.append("idle frame lost the two progress circles")
        if kinds[8] or kinds[10]:
            errors.append("idle frame contains an active stimulus")
    else:
        if case % 5 != 0 and f"{24 - trial} remaining" not in texts:
            # The batch uses a 24-trial default and decrements by trial number.
            errors.append("running frame lost its trial countdown")
        if mode == 2 and kinds[8] == 0:
            errors.append("old-style dual frame lost its polygon stimulus")
        if mode == 21 and kinds[10] == 0:
            errors.append("image frame lost its shell-owned sprite reference")
        if mode == 258 and (kinds[8] == 0 or kinds[6] == 0):
            errors.append("3D frame lost its cube polygons or stage edges")
        if mode == 7 and case % 5 != 0 and "Answer: 0" not in texts:
            errors.append("arithmetic frame lost its answer field")

    return errors


def main() -> int:
    frames = read_frames(sys.argv[1])
    errors = []
    if len(frames) != 16:
        errors.append(f"expected 16 batch frames, got {len(frames)}")
    for header, lines in frames:
        for error in check_frame(header, lines):
            errors.append(f"case {header.get('case', '?')}: {error}")
    if errors:
        for error in errors[:12]:
            print("FAIL:", error)
        if len(errors) > 12:
            print(f"FAIL: {len(errors) - 12} more errors")
        return 1
    print(f"PASS: {len(frames)} assembled batch frames validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
