"""Compare Emotion's drawn faces, deals, pages, and quiz timing with Python."""
from random import Random
import subprocess
import sys

from crane_diff import compare
from unittest.mock import patch

from neural_workshop import emotion, emotiondata, feelings
from neural_workshop.ui import taskoptions

RUNGS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 20, 25, 30, 99)


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
    from neural_workshop.ui.emotion import Emotion

    scale = 389 / 640
    left = (912 - 1000 * scale) / 2
    bottom = 179

    def rgba(color):
        return int.from_bytes(bytes(color if len(color) == 4 else (*color, 255)), "big")

    class Page(Emotion):
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

        def poly(self, points, color, _group):
            compare(lines, "shape", (8, rgba(color), left + points[0][0] * scale, bottom + points[0][1] * scale, 0.0, 0.0),
                    where, tolerance=0.00006)
            for x, y in points:
                compare(lines, "shape", (9, 0, left + x * scale, bottom + y * scale, 0.0, 0.0), where, tolerance=0.00006)

        def line(self, start, end, width, color, _group):
            compare(lines, "shape", (6, rgba(color), left + start[0] * scale, bottom + start[1] * scale,
                                     left + end[0] * scale, bottom + end[1] * scale), where, tolerance=0.00006)

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

    for policy in range(4):
        run = feelings.Run(candidate)
        if policy == 1:
            step = run.step_now()
            run.choose((step.answer + 1) % len(step.options))
        elif policy == 2:
            run.step(run.item().seconds)
        elif policy == 3:
            flash = candidate.level.flash
            run.step(flash + 0.05 if flash > 0 else 1.0)
            assert run.face_visible() == (flash <= 0), where
        Page()._scene(run, scale)
        assert next(lines) == "end", (where, policy)
    return 4


def check_faces(lines, candidate, index_of, where):
    if candidate is None:
        return
    for item in candidate.items:
        compare(lines, "face", (index_of[id(item.face)], {"": 0, "eyes": 1, "mouth": 2}[item.crop]), where)


def check(binary):
    stdout = subprocess.run([binary], input=b"", capture_output=True, check=True).stdout.decode()
    lines = iter(stdout.splitlines())
    for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30):
        check_text(lines, taskoptions.emotion_note({"EMO_RUNG": rung}), rung)
    drawn = tuple(emotiondata._drawn_faces())
    ulps = 0
    index_of = {id(face): k for k, face in enumerate(drawn)}
    for k, face in enumerate(drawn):
        # Votes exactly; the jittered shape to an ulp or so, as the
        # gaussian goes through the platform's log, sin and cos.
        token, *fields = next(lines).split()
        assert token == "drawn" and len(fields) == 14, (k, token, fields)
        assert [int(v) for v in fields[:8]] == list(face.votes), (k, fields, face.votes)
        for raw, value in zip(fields[8:], face.drawn):
            assert abs(float(raw) - value) <= 1e-12, (k, raw, value)
            ulps += float(raw) != value
    items = ticks = pages = 0
    with patch.object(emotiondata, "faces", return_value=drawn):
        for rung in RUNGS:
            grade = emotion.grade(rung)
            compare(lines, "level", (grade.rung, len(grade.options), grade.agree[0], grade.agree[1], grade.flash, grade.crop,
                                     int(grade.two), grade.seconds, grade.skill), rung, tolerance=0.0)
            for seed in range(16):
                draw = Random(seed)
                candidate = emotion.build(grade, draw)
                items += check_deal(lines, candidate, draw, (rung, seed))
                check_faces(lines, candidate, index_of, (rung, seed))
            draw = Random(17)
            try:
                candidate = emotion.deal(rung, rng=draw)
            except RuntimeError:
                candidate = None
            check_deal(lines, candidate, draw, (rung, "screened"))
            check_faces(lines, candidate, index_of, (rung, "screened"))
            if candidate is None:
                continue
            pages += check_pages(lines, candidate, rung)
            ticks += check_run(lines, candidate, 0, rung)
            if rung == 10:
                ticks += check_run(lines, candidate, 1, rung)
                ticks += check_run(lines, candidate, 2, rung)
            ticks += check_run(lines, candidate, 3, rung)
    assert next(lines, None) is None
    return items, ticks, pages, len(drawn), ulps


def main(binary):
    items, ticks, pages, drawn, ulps = check(binary)
    print(f"PASS: {drawn} drawn Emotion faces ({ulps} of {drawn * 6} shape values an ulp off), {len(RUNGS) * 16} candidate deals and {items} faces match Python")
    print(f"PASS: {pages} Emotion pages, faces, crops and covers included, and nine option descriptions match Python")
    print(f"PASS: {ticks} click, score, timeout, and feedback ticks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
