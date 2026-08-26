#!/usr/bin/env python3
"""Differential harness: the Elisa title screen vs the ORIGINAL's pyglet one.

Not a snapshot test. For every flag combination the sweep emits, this boots the
real application, reads its laid-out title labels, and compares them against the
decoded display list command by command.

Two things it exists to catch, both of which bit during the port:

  * the window pyglet gives back here is retina-doubled, so hud.py's written
    numbers lay out at twice their value. The extractor divides by the window's
    own measured scale, so the comparison is in reference space on both sides.
  * the key list is assembled from two flags, and a listed key that does nothing
    is worse than a missing one. Each combination is driven for real rather than
    reasoned about.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from display_decode import decode  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
EXTRACTOR = os.path.join(ROOT, "scripts", "extract_title.py")
PYTHON = os.path.join(ORIGINAL, ".venv", "bin", "python")

# Must match test/title_sweep.elisa's emission order.
COMBOS = [
    (False, False, False),
    (True, False, False),
    (False, True, False),
    (False, False, True),
    (True, True, True),
]

TOLERANCE = 0.01


def reference(black, jaeggi, clinical):
    flags = []
    if black:
        flags.append("--black")
    if jaeggi:
        flags.append("--jaeggi")
    if clinical:
        flags.append("--clinical")
    proc = subprocess.run([PYTHON, EXTRACTOR] + flags, cwd=ORIGINAL,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("cannot read the original's title screen: %s"
                         % (proc.stderr.strip() or proc.returncode,))
    return json.loads(proc.stdout)


def rgba(color):
    return [(color >> 24) & 255, (color >> 16) & 255,
            (color >> 8) & 255, color & 255]


def close(a, b):
    return abs(a - b) <= TOLERANCE


def check_text(cmd, ref, note, problems):
    if cmd["kind"] != "text":
        problems.append("%s: expected text, got %s" % (note, cmd["kind"]))
        return
    if cmd["text"] != ref["text"]:
        problems.append("%s: text %r != %r" % (note, cmd["text"], ref["text"]))
    for key, want in (("x", ref["x"]), ("y", ref["y"]), ("size", ref["size"])):
        if not close(cmd[key], want):
            problems.append("%s: %s %.4f != %.4f" % (note, key, cmd[key], want))
    if rgba(cmd["color"]) != ref["color"]:
        problems.append("%s: color %s != %s" % (note, rgba(cmd["color"]), ref["color"]))
    if cmd["anchor"] != ref["anchor"]:
        problems.append("%s: anchor %s != %s" % (note, cmd["anchor"], ref["anchor"]))


def check_frame(cmds, ref, label, problems):
    # background
    if cmds[0]["kind"] != "rect":
        problems.append("%s: first command is %s, not the background" % (label, cmds[0]["kind"]))
        return
    want_bg = [0, 0, 0, 255] if ref["black_background"] else [255, 255, 255, 255]
    if rgba(cmds[0]["color"]) != want_bg:
        problems.append("%s: background %s != %s" % (label, rgba(cmds[0]["color"]), want_bg))

    # the splash, named as a room the shell fits the artwork into. The original
    # places an already-scaled sprite; the invariant that survives both is that
    # the fitted rectangle is centred in the room and inside it.
    fit = cmds[1]
    if fit["kind"] != "sprite_fit":
        problems.append("%s: second command is %s, not the splash" % (label, fit["kind"]))
    else:
        want_asset = 2 if ref["splash_variant"] == "splash-black" else 1
        if fit["asset"] != want_asset:
            problems.append("%s: splash asset %d != %d (%s)"
                            % (label, fit["asset"], want_asset, ref["splash_variant"]))
        s = ref["splash"]
        for axis, centre in (("x", s["x"] + s["w"] / 2.0), ("y", s["y"] + s["h"] / 2.0)):
            if not close(fit[axis], centre):
                problems.append("%s: splash centre %s %.4f != %.4f" % (label, axis, fit[axis], centre))
        if s["w"] > fit["room_w"] + TOLERANCE or s["h"] > fit["room_h"] + TOLERANCE:
            problems.append("%s: fitted splash %.1fx%.1f escapes room %.1fx%.1f"
                            % (label, s["w"], s["h"], fit["room_w"], fit["room_h"]))

    check_text(cmds[2], ref["title"], "%s title" % label, problems)
    check_text(cmds[3], ref["version"], "%s version" % label, problems)
    check_text(cmds[4], ref["native"], "%s native" % label, problems)
    check_text(cmds[5], ref["space"], "%s prompt" % label, problems)

    # The key list. A trailing empty entry is dropped: in clinical mode the
    # original's last part still ends in "\n", so its text splits into one
    # visible line plus an empty one. That is a property of building the label
    # by concatenation, not a line anybody sees.
    lines = list(ref["key_lines"])
    while lines and lines[-1] == "":
        lines.pop()
    keys, height = ref["keys"], ref["key_line_height"]
    emitted = [c for c in cmds if c["kind"] == "text"][4:]
    if len(emitted) != len(lines):
        problems.append("%s: %d key lines emitted, original shows %d (%r)"
                        % (label, len(emitted), len(lines), lines))
        return
    for index, (cmd, text) in enumerate(zip(emitted, lines)):
        check_text(cmd, dict(text=text, x=keys["x"], y=keys["y"] - index * height,
                             size=keys["size"], color=keys["color"],
                             anchor=keys["anchor"]),
                   "%s key[%d]" % (label, index), problems)

    if cmds[-1]["kind"] != "marker" or cmds[-1]["text"] != "frame-end":
        problems.append("%s: frame does not end with the frame-end marker" % label)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: title_diff.py <title_sweep binary>")
    if not os.path.exists(PYTHON):
        raise SystemExit("the original's interpreter is missing: %s" % PYTHON)

    out = subprocess.run([sys.argv[1]], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("sweep exited %d: %s" % (out.returncode, out.stderr.strip()))
    frames = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    if len(frames) != len(COMBOS):
        raise SystemExit("expected %d frames, got %d" % (len(COMBOS), len(frames)))

    problems = []
    checked = 0
    for hexed, combo in zip(frames, COMBOS):
        ref = reference(*combo)
        label = "black=%d jaeggi=%d clinical=%d" % combo
        check_frame(decode(bytes.fromhex(hexed)), ref, label, problems)
        checked += 1

    if problems:
        for line in problems[:20]:
            print("MISMATCH %s" % line)
        raise SystemExit("FAILED: %d mismatch(es)" % len(problems))
    print("PASS: %d title screens identical" % checked)


if __name__ == "__main__":
    main()
