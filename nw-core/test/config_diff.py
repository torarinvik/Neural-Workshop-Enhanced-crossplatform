#!/usr/bin/env python3
"""Differential harness: config.elisa's typed parser vs the reference's eval().

Writes the REAL configdefaults.py template to /tmp, has the Elisa side parse it,
and checks every entry against what Python's eval() produces for the same value
— which is exactly what neural_workshop/config.py does.
"""
from pathlib import Path
import math
import re
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import configdefaults  # noqa: E402

TEMPLATE_PATH = "/tmp/nw_config_defaults.ini"

CONFIG_INT, CONFIG_BOOL, CONFIG_FLOAT = 1, 2, 3
CONFIG_TUPLE, CONFIG_LIST, CONFIG_TEXT = 4, 5, 6


def template_text():
    for name in dir(configdefaults):
        value = getattr(configdefaults, name)
        if isinstance(value, str) and "=" in value and len(value) > 2000:
            return value
    raise SystemExit("could not find the config template string")


def classify(raw):
    """The (kind, payload) the Elisa parser should produce for one raw value."""
    text = raw.strip()
    if text in ("True", "False"):
        return CONFIG_BOOL, "1" if text == "True" else "0"
    if re.fullmatch(r"[+-]?\d+", text):
        return CONFIG_INT, str(int(text))
    if (text.startswith("(") and text.endswith(")")) or \
       (text.startswith("[") and text.endswith("]")):
        kind = CONFIG_TUPLE if text.startswith("(") else CONFIG_LIST
        inner = text[1:-1]
        nums = [p.strip() for p in inner.split(",")]
        nums = [int(p) for p in nums if re.fullmatch(r"[+-]?\d+", p)]
        payload = str(len(nums)) + "".join(f":{n}" for n in nums)
        return kind, payload
    if text[:1] in ("'", '"') and text[-1:] == text[:1] and len(text) >= 2:
        return CONFIG_TEXT, text[1:-1]
    try:
        value = float(text)
        return CONFIG_FLOAT, str(int(math.trunc(value * 1000000.0)))
    except ValueError:
        return CONFIG_TEXT, text


def python_lines(body):
    out = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in "#;[":
            continue
        if "=" not in stripped:
            continue
        name, _, raw = stripped.partition("=")
        name = name.strip()
        if not name:
            continue
        kind, payload = classify(raw)
        out.append(f"{name},{kind},{payload}")
    return out


def main():
    body = template_text()
    with open(TEMPLATE_PATH, "w") as handle:
        handle.write(body)

    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines(body)

    if len(got) != len(want):
        print(f"FAIL: {len(got)} entries vs {len(want)} expected")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g}\n  python: {w}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:10]:
        print(f"MISMATCH entry {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
