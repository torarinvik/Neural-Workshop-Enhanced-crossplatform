"""Compare deals, imported dialogue text, and quiz timing with Python."""
import json
import os
import tempfile
from random import Random
import subprocess
import sys
from unittest.mock import patch

from crane_diff import compare
from neural_workshop import emotiondata, feelings, howstrongly

RUNGS = (0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 16, 20, 21, 25, 30, 99)


def check_text(lines, expected, where):
    actual = bytes.fromhex(next(lines)).decode()
    assert actual == expected, (where, actual, expected)


def check_deal(lines, candidate, draw, where):
    compare(lines, "deal", (candidate.need if candidate else 0, draw.random()), where)
    if candidate is None:
        return 0
    for item in candidate.items:
        check_text(lines, item.prompt, where)
        check_text(lines, item.title, where)
        compare(lines, "item", (item.seconds,), where)
        for step in item.steps:
            check_text(lines, step.ask, where)
            compare(lines, "step", (len(step.options), step.answer, int(step.wide)), where)
            for option in step.options:
                check_text(lines, option, where)
    return len(candidate.items)


def check_run(lines, candidate, policy, where):
    run = feelings.Run(candidate)
    ticks = 0
    while run.result is None:
        step = run.step_now()
        answer = step is not None and policy != 2
        if answer:
            right = policy == 0 or (policy == 3 and len(run.picks) > 0)
            index = step.answer if right else (step.answer + 1) % len(step.options)
            x, y, width, height = feelings.option_rect(index, len(step.options), step.wide)
            if y + height / 2 >= 0:
                run.hand.to(x + width / 2, y + height / 2)
                run.click()
            else:
                run.choose(index)
        run.step(1 / 30)
        result = 0 if run.result is None else (1 if run.result[0] else 2)
        compare(lines, "tick", (int(answer), run.k, len(run.picks), run.marks.count(True),
                                 run.marks.count(False), int(run.showing), run.t, run.since, result), (where, ticks))
        ticks += 1
    for cue in run.notes:
        compare(lines, "cue", (cue.t, cue.dur, cue.freq, cue.voice, cue.gain), where)
    return ticks


def check_pages(lines, candidate, where):
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui.howstrongly import HowStrongly

    scale = 389 / 640
    left = (912 - 1000 * scale) / 2
    bottom = 179

    def rgba(color):
        return int.from_bytes(bytes(color if len(color) == 4 else (*color, 255)), "big")

    class Page(HowStrongly):
        def __init__(self):
            pass

        def g(self):
            return None

        def _fit_buttons(self, *_args):
            return 12

        def _fit_text(self, *_args):
            return 20

        def rect(self, x, y, width, height, color, _group):
            right, top = min(1000, x + width), min(640, y + height)
            x, y = max(x, 0), max(y, 0)
            if right > x and top > y:
                compare(lines, "shape", (1, rgba(color), left + x * scale, bottom + y * scale,
                                         (right - x) * scale, (top - y) * scale), where, tolerance=0.00006)

        def disc(self, point, radius, color, _group):
            x, y = point
            compare(lines, "shape", (4, rgba(color), left + x * scale, bottom + y * scale,
                                     radius * scale, 0.0), where, tolerance=0.00006)

        def words(self, text, x, y, _size, **kw):
            # Figures emits multiline labels as positioned single lines.
            # Compare their text, palette and horizontal alignment together.
            from math import isclose

            words = text.split()
            collected = []
            positions = []
            while len(collected) < len(words):
                kind, color, px, py, size, bold, encoded = next(lines).split()
                assert kind == "label" and int(color) == rgba(kw["colour"]), (where, text)
                assert isclose(float(px), left + x * scale, abs_tol=0.00006), (where, text, px)
                assert int(bold) == kw.get("bold", False), (where, text)
                assert float(size) > 0
                collected.extend(bytes.fromhex(encoded).decode().split())
                positions.append(float(py))
            assert words == collected, (where, words, collected)
            if len(positions) == 1:
                assert isclose(positions[0], bottom + y * scale, abs_tol=0.00006), (where, text)
            else:
                assert positions == sorted(positions, reverse=True), (where, text)

    for policy in range(3):
        run = feelings.Run(candidate)
        if policy == 1:
            step = run.step_now()
            run.choose((step.answer + 1) % len(step.options))
        elif policy == 2:
            run.step(run.item().seconds)
        Page()._scene(run, scale)
        assert next(lines) == "end", (where, policy)


def check(binary, payload, invalid=""):
    stdout = subprocess.run([binary], input=(payload + invalid).encode(), capture_output=True, check=True).stdout.decode()
    lines = iter(stdout.splitlines())
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui import taskoptions

    for rung in taskoptions.STRONG.options[0].values:
        check_text(lines, taskoptions.howstrongly_note({"STRONG_RUNG": rung}), rung)
    items = ticks = pages = 0
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "eqbench.jsonl")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(payload)
    emotiondata.dialogues.cache_clear()
    with patch.object(emotiondata, "dialogues_path", return_value=path):
        for rung in RUNGS:
            grade = howstrongly.grade(rung)
            compare(lines, "level", (grade.rung, int(grade.strongest), grade.tolerance, grade.seconds, grade.items), rung)
            for seed in range(16):
                draw = Random(seed)
                items += check_deal(lines, howstrongly.build(grade, draw), draw, (rung, seed))
            draw = Random(17)
            try:
                candidate = howstrongly.deal(rung, rng=draw)
            except RuntimeError:
                candidate = None
            check_deal(lines, candidate, draw, (rung, "screened"))
            if candidate is None:
                continue
            check_pages(lines, candidate, rung)
            pages += 3
            ticks += check_run(lines, candidate, 0, rung)
            if rung == 10:
                ticks += check_run(lines, candidate, 1, rung)
                ticks += check_run(lines, candidate, 2, rung)
            ticks += check_run(lines, candidate, 3, rung)
    assert next(lines, None) is None
    return items, ticks, pages


def dialogue(text, who, emotions, scores):
    return json.dumps({"text": text, "who": who, "emotions": emotions, "scores": scores}, ensure_ascii=False) + "\n"


def main(binary):
    offline = check(binary, "")
    lines = [
        dialogue("Ana: We won!\nBo: By one point.", "Ana", ["Proud", "Relieved", "Bored", "Angry"], [9, 4, 0, 1]),
        dialogue("Cy: Where were you?\nDee: Stuck on the train.\nCy: Again.", "Cy", ["Annoyed", "Worried", "Amused", "Calm"], [7, 3, 1, 2]),
        dialogue("Eli: I kept the letter.\r\nFay: All these years?", "Fay", ["Touched", "Surprised", "Sad", "Guilty"], [6, 8, 3, 0]),
        dialogue("Gus: Tie.\nHal: Tie.", "Gus", ["Happy", "Sad", "Calm", "Tense"], [5, 5, 4, 4]),
        dialogue("Ivy: \"Sure\" 😀\u2003she said.", "Ivy", ["Sarcastic", "Glad", "Hurt", "Calm"], [8, 0, 5, 2]),
        dialogue("Jo: Odd scores.", "Jo", ["Up", "Down", "Left", "Right"], [3, 7, 9, 1]),
        dialogue("Kim: Only two.", "Kim", ["Warm", "Cold"], [10, 2]),
    ]
    # Lines the reference cannot read (it stops on them) go to Elisa only.
    custom = check(binary, "".join(lines), 'not json\n{"text": "missing fields"}\n' +
                   dialogue("Lee: Mismatched.", "Lee", ["One", "Two", "Three"], [1, 2]))
    # Two dialogues: they come round again; one too even for the first rungs.
    sparse = check(binary, lines[3] + lines[6])
    print(f"PASS: {3 * len(RUNGS) * 16} How Strongly candidate deals and {offline[0] + custom[0] + sparse[0]} "
          "dialogues match Python")
    print(f"PASS: {offline[2] + custom[2] + sparse[2]} How Strongly quiz pages and nine option descriptions match Python")
    print(f"PASS: {offline[1] + custom[1] + sparse[1]} click, score, timeout, and feedback ticks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
