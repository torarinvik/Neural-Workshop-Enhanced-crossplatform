"""Compare deals, imported question text, and quiz timing with Python."""
import json
from random import Random
import subprocess
import sys
from unittest.mock import patch

from crane_diff import compare
from neural_workshop import betweenlines, feelings, socialdata

RUNGS = (0, 1, 3, 4, 6, 7, 9, 10, 16, 24, 30, 99)


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
            index = step.answer if policy == 0 else (step.answer + 1) % len(step.options)
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
    from neural_workshop.ui.betweenlines import BetweenTheLines

    scale = 389 / 640
    left = (912 - 1000 * scale) / 2
    bottom = 179

    def rgba(color):
        return int.from_bytes(bytes(color if len(color) == 4 else (*color, 255)), "big")

    class Page(BetweenTheLines):
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


def check(binary, imported, invalid=""):
    payload = "\n".join(json.dumps(q._asdict(), ensure_ascii=i % 2 == 0)
                        for i, q in enumerate(imported))
    payload += invalid
    stdout = subprocess.check_output([binary], input=payload, text=True)
    lines = iter(stdout.splitlines())
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui import taskoptions

    for rung in taskoptions.LINES.options[0].values:
        check_text(lines, taskoptions.betweenlines_note({"LINES_RUNG": rung}), rung)
    items = ticks = 0
    socialdata.questions.cache_clear()
    with patch.object(socialdata, "_load", return_value=imported):
        for rung in RUNGS:
            grade = betweenlines.grade(rung)
            compare(lines, "level", (grade.rung, len(grade.kinds), *grade.pace), rung)
            for seed in range(16):
                draw = Random(seed)
                items += check_deal(lines, betweenlines.build(grade, draw), draw, (rung, seed))
            draw = Random(17)
            candidate = betweenlines.deal(rung, rng=draw)
            check_deal(lines, candidate, draw, (rung, "screened"))
            check_pages(lines, candidate, rung)
            ticks += check_run(lines, candidate, 0, rung)
            if rung == 10:
                ticks += check_run(lines, candidate, 1, rung)
                ticks += check_run(lines, candidate, 2, rung)
    assert next(lines, None) is None
    return items, ticks


def main(binary):
    imported = [
        socialdata.Question("implicature", prompt, "Does B mean yes or no?", ("yes", "no"), answer)
        for prompt, answer in (("A: \u201cTea?\u201d\u2003B: \u201cI just had\u00a0one.\u201d", 1),
                               ("A: \u201cReady?\u201d\r\nB: \u201cCoat\u2019s on.\u201d\n", 0),
                               ("A: \"quoted\"\nB: \"Sure 😀\"", 0), ("A: Lunch?\nB: I ate at ten.", 1),
                               ("A: Is it far?\nB: Bring water.", 0))
    ]
    imported += [
        socialdata.Question("sarcasm", "1.  " + "a" * 30 + "é\n\n2.  plain", "Which one is sarcastic?",
                            ("the first remark, which is longer than thirty", "the second"), 0),
        socialdata.Question("sarcasm", "1.  Lovely weather.\n\n2.  Wonderful, more rain.", "Which one is sarcastic?",
                            ("the first", "the second", "neither", "both"), 1),
        socialdata.Question("irony", "The lifeguard nearly drowned.", "Ironic or not?", ("ironic", "not ironic"), 0),
        socialdata.Question("metaphor", "Ignored kind", "What does it mean?", ("a", "b"), 0),
    ]
    offline = check(binary, [])
    custom = check(binary, imported, '\n{"kind":"irony","answer":99}\n{broken\n'
                   '{"kind":"irony","prompt":"p","ask":"a","options":["1","2","3","4","5","6","7","8","9"],"answer":0}\n')
    print(f"PASS: {2 * len(RUNGS) * 16} Between the Lines candidate deals and {offline[0] + custom[0]:,} questions match "
          f"Python")
    print("PASS: 72 Between the Lines quiz pages and nine option descriptions match Python")
    print(f"PASS: {offline[1] + custom[1]} click, score, timeout, and feedback ticks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
