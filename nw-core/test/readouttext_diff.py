#!/usr/bin/env python3
"""Differential harness for src/readouttext.elisa.

The reference strings are made by the real readouts.py rules. The Elisa side
only receives typed snapshots, so this harness reconstructs the same snapshot
from each emitted spec and compares every label separately.
"""
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
sys.path.insert(0, HERE)
os.chdir(ORIGINAL)

from neural_workshop import gamemode  # noqa: E402

ROWS = 20
SCORABLE = [
    "position1", "position2", "position3", "position4",
    "vis1", "vis2", "vis3", "vis4", "color", "visvis", "visaudio",
    "audiovis", "image", "audio", "audio2", "arithmetic",
]
MODALITY_CODE = {
    "position1": 0, "position2": 1, "position3": 2, "position4": 3,
    "color": 4, "image": 5, "vis1": 6, "vis2": 7, "vis3": 8,
    "vis4": 9, "visvis": 10, "visaudio": 11, "audiovis": 12,
    "audio": 13, "audio2": 14, "arithmetic": 15,
}
READOUT_INDEX = {name: index for index, name in enumerate(SCORABLE)}
MODALITY_SETS = {
    0: ["position1", "audio"],
    1: ["vis1", "vis2", "color", "visaudio", "image", "arithmetic"],
    2: ["visvis", "visaudio", "audiovis"],
    3: [*SCORABLE],
    4: ["arithmetic"],
}
KEYS = ["A", "B", "C", "D", "E", "F", "G", "H", "SEMICOLON",
        "J", "K", "L", "M", "N", "O"]


def decode(cell):
    assert cell.startswith("[") and cell.endswith("]"), cell
    body = cell[1:-1]
    return body.replace("\\\\", "\\").replace("\\n", "\n")


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
            current["records"] = []
            specs.append(current)
        elif line.startswith("analysis"):
            current["analysis"] = decode(line[len("analysis"):])
        elif line.startswith("summary"):
            current["summary"] = [int(value) for value in line.split("|")[1:]]
        elif line.startswith("title"):
            current["title"] = decode(line[len("title"):])
        elif line.startswith("chart"):
            pieces = line.split("|")
            current["records"].append(
                (int(pieces[1]), int(pieces[2]),
                 decode(pieces[3]), decode(pieces[4]), decode(pieces[5])))
        elif line.startswith("average"):
            current["average"] = decode(line[len("average"):])
        elif line.startswith("today"):
            current["today"] = decode(line[len("today"):])
        elif line.startswith("remaining"):
            current["remaining"] = decode(line[len("remaining"):])
    return specs


def percent(right, wrong):
    total = right + wrong
    return int(right * 100 / float(total)) if total else 0


def expected(spec, tables):
    modalities = MODALITY_SETS[spec["which"]]
    rights = [(index * 3 + spec["spec"]) % 7 for index in range(16)]
    wrongs = [(index + spec["spec"]) % 5 for index in range(16)]
    categories = [percent(rights[i], wrongs[i]) for i in range(16)]

    if spec["jaeggi"]:
        session_percent = min(categories[READOUT_INDEX[name]] for name in modalities)
    else:
        session_percent = percent(
            sum(rights[READOUT_INDEX[name]] for name in modalities),
            sum(wrongs[READOUT_INDEX[name]] for name in modalities),
        )

    if (spec["started"] or spec["session"] == 0 or spec["skip"]):
        analysis = ""
    else:
        parts = []
        if not spec["clinical"]:
            parts.append("Correct-Errors:   ")
            for name in SCORABLE[:-1]:
                if name not in modalities:
                    continue
                key = KEYS[MODALITY_CODE[name]]
                parts.append("%s:%d-%d   " %
                             (";" if key == "SEMICOLON" else key,
                              rights[READOUT_INDEX[name]],
                              wrongs[READOUT_INDEX[name]]))
            if "arithmetic" in modalities:
                parts.append("Arithmetic:%d-%d   " %
                             (rights[15], wrongs[15]))
        if spec["jaeggi"]:
            if not spec["clinical"]:
                parts.append("Lowest score: %d%%" % session_percent)
        else:
            parts.append("Score: %d%%" % session_percent)
        analysis = "".join(parts)

    history = []
    for index in range(spec["history"]):
        history.append({
            "session": -1 if index % 5 == 4 else 100 + index,
            "mode": 2 + index % 8,
            "back": 1 + index % 5,
            "percent": 30 + index * 3,
            "manual": index % 5 == 4,
        })
    active = history[-ROWS:]
    charts = []
    for row, entry in enumerate(active):
        if entry["manual"]:
            kind = 0
        elif entry["percent"] >= spec["advance"]:
            kind = 1
        elif entry["percent"] < spec["fallback"]:
            kind = 2
        else:
            kind = 0
        if entry["manual"]:
            first = "M"
        elif entry["session"] > -1:
            first = "#%d" % entry["session"]
        else:
            first = ""
        second = "%s%dB" % (tables.short_names[entry["mode"]], entry["back"])
        third = "%d%%" % entry["percent"]
        charts.append((row, kind, first, second, third))

    if spec["started"]:
        average = ""
    elif spec["clinical"]:
        average = ""
    else:
        matching = [entry for entry in history if entry["mode"] == spec["mode"]][-ROWS:]
        value = (sum(entry["back"] for entry in matching) / float(len(matching))
                 if matching else 0.0)
        average = "%sNB average: %1.2f" % (tables.short_names[spec["mode"]], value)

    today = "" if spec["started"] else (
        "%d min %d sec done today in %d sessions\n"
        "%d min %d sec done in last 24 hours in %d sessions" % (
            spec["time_today"] // 60, spec["time_today"] % 60,
            spec["sessions_today"], spec["time_hours"] // 60,
            spec["time_hours"] % 60, spec["sessions_hours"]))
    remaining = ("" if not spec["started"] or spec["hide"] else
                 "%d remaining" % (spec["total"] - spec["trial"]))

    return {
        "analysis": analysis,
        "summary": [session_percent] + categories,
        "title": "" if spec["started"] else "Today's Last 20:",
        "records": charts,
        "average": average,
        "today": today,
        "remaining": remaining,
    }


def main():
    specs = parse(sys.argv[1])
    tables = gamemode.ModeTables()
    bad = 0
    for spec in specs:
        want = expected(spec, tables)
        for key in ("analysis", "summary", "title", "records", "average",
                    "today", "remaining"):
            if spec.get(key) == want[key]:
                continue
            bad += 1
            if bad <= 6:
                print("MISMATCH spec=%d field=%s" % (spec["spec"], key))
                print("    elisa:  %r" % (spec.get(key),))
                print("    python: %r" % (want[key],))
    if bad:
        print("FAIL: %d differences" % bad)
        return 1
    print("PASS: %d readout states identical" % len(specs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
