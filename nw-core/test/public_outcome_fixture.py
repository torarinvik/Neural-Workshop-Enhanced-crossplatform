"""Generate RGBA fixtures and expected label runs with the Python reader."""
import base64
import hashlib
import json
import random
import sys
import types
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"
sys.path.insert(0, str(APP))
from bwaccel.pixels import count_feedback_label_runs_py


def fixture(width, height, pixels):
    frame = bytearray(width * height * 4)
    for x, y, rgba in pixels:
        offset = (y * width + x) * 4
        frame[offset:offset + 4] = bytes(rgba)
    positive, negative, oops = count_feedback_label_runs_py(frame, width, height, height * 3 // 4, height)
    total = positive + negative + oops
    return {
        "width": width,
        "height": height,
        "rgba": base64.b64encode(frame).decode("ascii"),
        "digest": hashlib.sha256(frame).hexdigest(),
        "counts": [positive, negative, oops],
        "scalar": (positive - negative - oops) / total if total else None,
    }


def samples():
    green = (140, 180, 140, 0)
    red = (180, 140, 140, 255)
    blue = (140, 140, 180, 127)
    cases = [fixture(1, 1, []), fixture(24, 8, [(1, 5, green), (1, 6, green)])]
    for width in (40, 360):
        gap = max(8, width // 40)
        # One gap small enough to close and one at the exact threshold.
        columns = [(0, green), (gap, green), (2 * gap + 1, green),
                   (2 * gap + 2, red), (2 * gap + 3, blue)]
        cases.append(fixture(width, 8, [(x, y, color) for x, color in columns for y in (6, 7)]))
    cases.append(fixture(4, 20, [(0, y, red) for y in range(15)]))
    # Ties between all three colours pick green. Red wins a red/blue tie.
    cases.append(fixture(8, 24, [
        (x, y + 18, color)
        for x, colors in enumerate(((green, red, blue), (red, blue), (blue,)))
        for y, color in enumerate(color for color in colors for _ in (0, 1))
    ]))
    rng = random.Random(17)
    palette = [green, red, blue, (0, 0, 0, 255), (255, 255, 255, 255),
               (141, 255, 0, 255), (0, 179, 0, 255)]
    for width, height in ((17, 15), (79, 31), (352, 27), (600, 32)):
        for density in (0.12, 0.45, 0.9):
            cases.append(fixture(width, height, [
                (x, y, rng.choice(palette)) for y in range(height) for x in range(width)
                if rng.random() < density
            ]))
    return cases


def evidence_samples():
    # Load the verifier without importing task environments and their GUI dependencies.
    namespace = types.ModuleType("nwenv")
    namespace.__path__ = [str(APP / "nwenv")]
    sys.modules.setdefault("nwenv", namespace)
    from nwenv.outcome import verify_public_outcome
    # The verifier is pure. Import its production factory without loading the GUI.
    sys.modules.setdefault("pyglet", types.ModuleType("pyglet"))
    from nwenv.taskenv import TaskEnv
    task_verify = TaskEnv.verifier()

    cases = samples()
    stimulus = cases[0]
    feedback = next(case for case in cases if case["scalar"] is not None)
    frame = base64.b64decode(feedback["rgba"])
    first, last = stimulus["digest"], feedback["digest"]
    evidence = [first, last]
    archive = {first: stimulus["rgba"], last: feedback["rgba"]}
    receipt = {
        "receipt_id": 19, "trial_seq": 19, "stimulus_digest": first,
        "feedback_digest": last, "evidence_digests": evidence,
    }
    outcome = {"receipt_id": 19, "evidence_digests": evidence, "scalar": feedback["scalar"]}
    scenarios = [
        ("bound receipt", outcome, archive, {19: receipt}),
        ("no ledger", outcome, archive, None),
        ("no archive", outcome, None, {19: receipt}),
        ("missing receipt", {**outcome, "receipt_id": 20}, archive, {19: receipt}),
        ("swapped valid receipt", {**outcome, "receipt_id": 20}, archive, {
            19: receipt,
            20: {"receipt_id": 20, "trial_seq": 20, "stimulus_digest": last,
                 "feedback_digest": first, "evidence_digests": [last, first]},
        }),
        ("truncated binding", outcome, archive, {19: {**receipt, "evidence_digests": [first]}}),
        ("different trial", outcome, archive, {19: {**receipt, "trial_seq": 20}}),
        ("different stimulus", outcome, archive, {19: {**receipt, "stimulus_digest": last}}),
        ("different feedback", outcome, archive, {19: {**receipt, "feedback_digest": first}}),
        ("reordered binding", outcome, archive, {19: {**receipt, "evidence_digests": [last, first]}}),
        ("absent stimulus frame", outcome, {last: feedback["rgba"]}, {19: receipt}),
        ("altered stimulus bytes", outcome, {**archive, first: feedback["rgba"]}, {19: receipt}),
        ("false scalar", {**outcome, "scalar": outcome["scalar"] + 1}, archive, {19: receipt}),
        ("no receipt, one frame", {**outcome, "receipt_id": None, "evidence_digests": [last]}, None, None),
        ("no receipt, two frames", {**outcome, "receipt_id": None}, None, None),
        ("no receipt, complete archive", {**outcome, "receipt_id": None}, archive, None),
        ("legacy receipt", outcome, archive, {19: {"stimulus_digest": first}}),
    ]
    results = []
    for name, claim, frames, ledger in scenarios:
        decoded = {key: base64.b64decode(value) for key, value in frames.items()} if frames is not None else None
        args = (frame, feedback["width"], feedback["height"], decoded, ledger)
        results.append({
            "name": name, "outcome": claim, "archive": frames, "ledger": ledger,
            "expected": verify_public_outcome(claim, *args),
            "expected_task_zero": task_verify({**claim, "scalar": 0.0}, *args),
        })
    return {"feedback": feedback, "scenarios": results}


if __name__ == "__main__":
    print(json.dumps(evidence_samples() if sys.argv[1:] == ["--evidence"] else samples()))
