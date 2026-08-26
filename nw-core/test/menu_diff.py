#!/usr/bin/env python3
"""Differential harness: the Elisa menu scene vs the ORIGINAL's Menu class.

Every menu screen in the game is one Menu instance, so this compares the shared
layout rather than any single screen: title, footnote, the scrolled row window
with its ellipsis rows, and the selection marker.

The marker is compared with a wider tolerance than everything else, and for a
real reason: the original builds it from `w // 10`, `w // 9` and `int(row_y)` in
PHYSICAL pixels, so on this retina window it truncates at half a reference
pixel. The display list is resolution-independent and keeps the exact value, so
the two legitimately differ by up to half a unit.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from display_decode import decode  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
EXTRACTOR = os.path.join(ROOT, "scripts", "extract_menu.py")
PYTHON = os.path.join(ORIGINAL, ".venv", "bin", "python")

# Must match test/menu_sweep.elisa's emission order.
CASES = [
    (8, 0, False),
    (8, 7, False),
    (30, 0, False),
    (30, 15, False),
    (30, 29, False),
    (8, 3, True),
    (1, 0, False),
]

TOLERANCE = 0.01
MARKER_TOLERANCE = 0.6


def reference(count, select, black):
    argv = [PYTHON, EXTRACTOR, "--options", str(count), "--select", str(select)]
    if black:
        argv.append("--black")
    proc = subprocess.run(argv, cwd=ORIGINAL, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("cannot read the original's menu: %s"
                         % (proc.stderr.strip() or proc.returncode,))
    return json.loads(proc.stdout)


def rgba(color):
    return [(color >> 24) & 255, (color >> 16) & 255,
            (color >> 8) & 255, color & 255]


def check_text(cmd, ref, note, problems, want_text=None):
    text = ref["text"] if want_text is None else want_text
    if cmd["kind"] != "text":
        problems.append("%s: expected text, got %s" % (note, cmd["kind"]))
        return
    if cmd["text"] != text:
        problems.append("%s: text %r != %r" % (note, cmd["text"], text))
    for key, want in (("x", ref["x"]), ("y", ref["y"]), ("size", ref["size"])):
        if abs(cmd[key] - want) > TOLERANCE:
            problems.append("%s: %s %.4f != %.4f" % (note, key, cmd[key], want))
    if rgba(cmd["color"]) != ref["color"]:
        problems.append("%s: color %s != %s" % (note, rgba(cmd["color"]), ref["color"]))
    if cmd["anchor"] != ref["anchor"]:
        problems.append("%s: anchor %s != %s" % (note, cmd["anchor"], ref["anchor"]))


def check_frame(cmds, ref, label, problems):
    want_bg = [0, 0, 0, 255] if ref["black_background"] else [255, 255, 255, 255]
    if cmds[0]["kind"] != "rect" or rgba(cmds[0]["color"]) != want_bg:
        problems.append("%s: background %s != %s"
                        % (label, rgba(cmds[0]["color"]), want_bg))

    texts = [c for c in cmds if c["kind"] == "text"]
    if len(texts) < 2:
        problems.append("%s: frame has no title/footnote" % label)
        return
    check_text(texts[0], ref["title"], "%s title" % label, problems)
    check_text(texts[1], ref["footnote"], "%s footnote" % label, problems)

    # Row window. The original keeps one label per page slot and blanks the
    # unused ones; the display list simply does not emit an empty row. Compare
    # the slots that carry text, matched by their slot position.
    wanted = [(i, r) for i, r in enumerate(ref["rows"]) if r["text"] != ""]
    emitted = texts[2:]
    if len(emitted) != len(wanted):
        problems.append("%s: %d rows emitted, original shows %d"
                        % (label, len(emitted), len(wanted)))
        return
    for cmd, (slot, row) in zip(emitted, wanted):
        check_text(cmd, row, "%s row[%d]" % (label, slot), problems)

    # The marker triangle.
    points = [c for c in cmds if c["kind"] == "poly_point"]
    header = [c for c in cmds if c["kind"] == "polygon"]
    if not header or len(points) != 3:
        problems.append("%s: expected a 3-point marker, got %d point(s)"
                        % (label, len(points)))
        return
    if rgba(header[0]["color"]) != ref["marker_color"]:
        problems.append("%s: marker color %s != %s"
                        % (label, rgba(header[0]["color"]), ref["marker_color"]))
    for index, (cmd, want) in enumerate(zip(points, ref["marker"])):
        for axis, value in (("x", want[0]), ("y", want[1])):
            if abs(cmd[axis] - value) > MARKER_TOLERANCE:
                problems.append("%s: marker[%d].%s %.4f != %.4f"
                                % (label, index, axis, cmd[axis], value))

    if cmds[-1]["kind"] != "marker" or cmds[-1]["text"] != "frame-end":
        problems.append("%s: frame does not end with the frame-end marker" % label)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: menu_diff.py <menu_sweep binary>")
    if not os.path.exists(PYTHON):
        raise SystemExit("the original's interpreter is missing: %s" % PYTHON)

    out = subprocess.run([sys.argv[1]], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("sweep exited %d: %s" % (out.returncode, out.stderr.strip()))
    frames = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    if len(frames) != len(CASES):
        raise SystemExit("expected %d frames, got %d" % (len(CASES), len(frames)))

    problems = []
    for hexed, case in zip(frames, CASES):
        ref = reference(*case)
        label = "options=%d sel=%d black=%d" % case
        check_frame(decode(bytes.fromhex(hexed)), ref, label, problems)

    if problems:
        for line in problems[:20]:
            print("MISMATCH %s" % line)
        raise SystemExit("FAILED: %d mismatch(es)" % len(problems))
    print("PASS: %d menu screens identical" % len(CASES))


if __name__ == "__main__":
    main()
