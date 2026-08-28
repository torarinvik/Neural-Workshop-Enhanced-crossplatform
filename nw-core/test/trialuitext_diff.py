#!/usr/bin/env python3
"""Differential harness for src/trialuitext.elisa."""
from decimal import Decimal
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIGINAL = os.path.join(os.path.dirname(ROOT), "original-neural-workshop-enhanced")
VENV = os.path.join(ORIGINAL, ".venv", "bin", "python")

if not os.environ.get("NW_SCENE_REEXEC") and os.path.exists(VENV):
    if len(sys.argv) > 1:
        sys.argv[1] = os.path.abspath(sys.argv[1])
    os.environ["NW_SCENE_REEXEC"] = "1"
    os.execv(VENV, [VENV] + sys.argv)

sys.path.insert(0, ORIGINAL)
os.chdir(ORIGINAL)
from neural_workshop import gamemode  # noqa: E402


MODALITIES = {
    0: ["position1", "audio"],
    1: ["position1", "visaudio", "audiovis", "arithmetic"],
    2: ["vis1", "vis2", "vis3", "color", "image"],
    3: [
        "position1", "position2", "position3", "position4", "color",
        "image", "vis1", "vis2", "vis3", "vis4", "visvis", "visaudio",
        "audiovis", "audio", "audio2",
    ],
    4: ["position1", "arithmetic"],
}
MODALITY_CODE = {
    "position1": 0, "position2": 1, "position3": 2, "position4": 3,
    "color": 4, "image": 5, "vis1": 6, "vis2": 7, "vis3": 8,
    "vis4": 9, "visvis": 10, "visaudio": 11, "audiovis": 12,
    "audio": 13, "audio2": 14,
}
KEYS = ["A", "B", "C", "D", "E", "F", "G", "H", "SEMICOLON",
        "J", "K", "L", "M", "N", "O"]
SEQUENCES = ["", ".", "12.50", "-12.5", "--7", ".5", "1..2", "000",
             "-0.00"]


def decode(cell):
    assert cell.startswith("[") and cell.endswith("]"), cell
    return cell[1:-1].replace("\\\\", "\\").replace("\\n", "\n")


def parse(binary):
    proc = subprocess.run([binary], capture_output=True, text=True, check=True)
    specs = []
    current = None
    for line in proc.stdout.splitlines():
        if line.startswith("names|"):
            names = line.split("|")[1:]
        elif line.startswith("spec|"):
            values = [int(value) for value in line.split("|")[1:]]
            current = dict(zip(names, values))
            current["feedback"] = []
            specs.append(current)
        elif line.startswith("feedback|"):
            pieces = line.split("|")
            current["feedback"].append(
                (int(pieces[1]), int(pieces[2]), int(pieces[3]), decode(pieces[4])))
        elif line.startswith("answer|"):
            pieces = line.split("|")
            current["answer"] = (decode(pieces[1]), int(pieces[2]))
        elif line.startswith("session|"):
            current["session_text"] = decode(line.split("|", 1)[1])
        elif line.startswith("threshold|"):
            current["threshold"] = decode(line.split("|", 1)[1])
        elif line.startswith("space|"):
            current["space"] = decode(line.split("|", 1)[1])
    return specs


def modality_name(name, multi):
    if name.endswith("vis"):
        return name[:-3] + " & n-vis"
    if name.endswith("audio") and name != "audio":
        return name[:-5] + " & n-audio"
    if multi == 1 and name == "position1":
        return "position"
    return name


def feedback_text(name, multi, pos, total, jaeggi, mouse):
    prefix = ""
    if total == 2 and not jaeggi and mouse:
        prefix = "Left-click or" if pos == 0 else "Right-click or"
    key = KEYS[MODALITY_CODE[name]]
    key = ";" if key == "SEMICOLON" else key
    text = "%s %s: %s" % (prefix, key, modality_name(name, multi))
    if total < 4:
        text += " match"
    return text


def answer_render(sequence):
    negative = False
    decimal_seen = False
    chars = []
    for char in sequence:
        if char == "-":
            negative = not negative
        elif char == ".":
            if not decimal_seen:
                decimal_seen = True
                chars.append(char)
        else:
            chars.append(char)
    raw = "".join(chars)
    number = Decimal("0") if raw in ("", ".") else Decimal(raw)
    if negative:
        number = -number
    return str(number)


def expected(spec, tables):
    names = MODALITIES[spec["which"]]
    total = len(names)
    expected_feedback = []
    for pos, name in enumerate(names):
        if name == "arithmetic":
            continue
        if spec["verdict"] == 0:
            state = 1 if spec["pressed"] and spec["showfeedback"] else 0
        elif spec["verdict"] == 3:
            state = 2 if spec["pressed"] and spec["showfeedback"] else 0
        else:
            state = 3 if spec["pressed"] and spec["showfeedback"] else 0
        if (not state and spec["showfeedback"] and not spec["audiovis"]
                and spec["showmissed"] and spec["missed"]):
            state = 2
        expected_feedback.append(
            (pos, int(spec["started"] and not spec["hide"]), state,
             feedback_text(name, spec["multi"], pos, total,
                           spec["jaeggi"], spec["mouse"])))

    active_arithmetic = spec["which"] in (1, 4)
    arithmetic_text = ""
    if active_arithmetic and spec["started"] and not spec["hide"]:
        arithmetic_text = "Answer: " + answer_render(SEQUENCES[spec["answer_case"]])
    if (spec["showfeedback"] and spec["showmissed"]
            and spec["verdict"] in (0, 1)):
        arithmetic_state = 1 if spec["verdict"] == 0 else 3
    else:
        arithmetic_state = 0

    if spec["started"] or spec["clinical"]:
        session_text = ""
    else:
        if spec["interval"] < 1000:
            timing = "%d ms/trial" % spec["interval"]
        else:
            timing = "%1.2f sec/trial" % (spec["interval"] / 1000.0)
        seconds = int(spec["interval"] / 1000.0 * spec["total"])
        if spec["grid3d"]:
            grid = "%d cubes (%d face patterns)" % (spec["cubes"], spec["cells"])
        elif spec["active"] < spec["cells"]:
            n = 3 + spec["spec"] % 4
            grid = "Grid %d×%d (%d/%d cells)" % (
                n, n, spec["active"], spec["cells"])
        else:
            n = 3 + spec["spec"] % 4
            grid = "Grid %d×%d" % (n, n)
        session_text = "Session:\n%s\n%d+%d trials\n%d seconds\n%s" % (
            timing, spec["numtrials"], spec["total"] - spec["numtrials"],
            seconds, grid)

    threshold = ""
    if not (spec["started"] or spec["spec"] % 4 == 0 or spec["clinical"]):
        threshold = ("Thresholds:\nRaise level: ≥ %d%%\nLower level: < %d%%"
                     % (spec["advance"], spec["fallback"]))

    if spec["started"]:
        space = ""
    else:
        long_name = tables.long_names[spec["mode"]]
        space = "Press SPACE to begin session #%d: %s %s%d-Back" % (
            spec["session"] + 1, long_name,
            "V. " if spec["varnback"] else "", spec["back"])
        if spec["mode"] == 10:
            space += " (%d/%d cells, %d trials)" % (
                spec["active"], spec["cells"], spec["total"])

    return {
        "feedback": expected_feedback,
        "answer": (arithmetic_text, arithmetic_state),
        "session_text": session_text,
        "threshold": threshold,
        "space": space,
    }


def main():
    specs = parse(sys.argv[1])
    tables = gamemode.ModeTables()
    failures = 0
    for spec in specs:
        want = expected(spec, tables)
        for key in ("feedback", "answer", "session_text", "threshold", "space"):
            got = spec[key]
            if got == want[key]:
                continue
            failures += 1
            if failures <= 8:
                print("MISMATCH spec=%d field=%s" % (spec["spec"], key))
                print("    elisa:  %r" % (got,))
                print("    python: %r" % (want[key],))
    if failures:
        print("FAIL: %d differences" % failures)
        return 1
    print("PASS: %d trial-UI states identical" % len(specs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
