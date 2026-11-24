"""Compare Why They Feel stories, deals, and quiz timing with Python."""
from random import Random
import subprocess
import sys

from crane_diff import compare
from neural_workshop import feelings, whytheyfeel

RUNGS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 20, 21, 25, 30, 99)


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
    from neural_workshop.ui.whytheyfeel import WhyTheyFeel

    scale = 389 / 640
    left = (912 - 1000 * scale) / 2
    bottom = 179

    def rgba(color):
        return int.from_bytes(bytes(color if len(color) == 4 else (*color, 255)), "big")

    class Page(WhyTheyFeel):
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


def check(binary):
    stdout = subprocess.run([binary], input=b"", capture_output=True, check=True).stdout.decode()
    lines = iter(stdout.splitlines())
    import pyglet

    pyglet.options.shadow_window = False
    from neural_workshop.ui import taskoptions

    for rung in taskoptions.WHY.options[0].values:
        check_text(lines, taskoptions.whytheyfeel_note({"WHY_RUNG": rung}), rung)
    items = ticks = pages = 0
    if True:
        for rung in RUNGS:
            grade = whytheyfeel.grade(rung)
            compare(lines, "level", (grade.rung, len(grade.kinds), grade.twist, grade.depth, grade.options, grade.seconds), rung)
            for seed in range(48):
                draw = Random(seed)
                items += check_deal(lines, whytheyfeel.build(grade, draw), draw, (rung, seed))
            draw = Random(17)
            try:
                candidate = whytheyfeel.deal(rung, rng=draw)
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


def main(binary):
    items, ticks, pages = check(binary)
    print(f"PASS: {len(RUNGS) * 48} Why They Feel candidate deals and {items} stories match Python")
    print(f"PASS: {pages} Why They Feel quiz pages and nine option descriptions match Python")
    print(f"PASS: {ticks} click, score, timeout, and feedback ticks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
