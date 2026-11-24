"""Replay the Cipher Abyss run controller against the Python game model."""
import json
from math import isclose
from random import Random
import subprocess
import sys

from neural_workshop import cipherabyss as task, cipherlang as lang, drshape

VERDICTS = ("", "Cracked it.", "Wrong.", "They differ there.", "Both give the same there.",
            "Yes, the same machine.", "No, they differ.", "Cracked it, rule and all:",
            "Not the same machine.", "Out of time.")


def fields(row):
    return (len(row), *row)


def compare_state(run, rows, where):
    actual = tuple(map(float, next(rows).split()[1:]))
    result = 0 if run.result is None else next(i for i, text in enumerate(VERDICTS[1:], 1)
                                             if run.result[1].startswith(text))
    good = sum(run.checked.values())
    if run.check_text:
        good, total = (int(run.check_text.split()[1]), int(run.check_text.split()[3]))
    else:
        total = len(run.checked)
    expected = (run.want(), len(run.log), run.testing, run.test_no, len(run.answers), result,
                -1 if run.said_same is None else run.said_same, run.twins_q, len(run.board),
                run.cursor, good, total, run.predicting, run.scroll, run.numbers, run.order == "input",
                run.state.runs, run.hand.x, run.hand.y, run.hand.down)
    assert actual == expected, (where, actual, expected)
    assert next(rows) == f"flash {run.flash}", where
    marks = tuple(sorted(i if kind == "run" else -1 - i for kind, i in run.marks))
    pending = () if run.pending is None else run.pending
    expected = (*fields(run.entry), *fields(pending), *fields(marks), *fields(tuple(map(int, run.checked.values()))))
    assert tuple(map(int, next(rows).split()[1:])) == expected, where
    if run.log:
        given, result = run.log[-1]
        prediction = run.predictions.get(len(run.log) - 1, ())
        assert tuple(map(int, next(rows).split()[1:])) == (*fields(given), *fields(result), *fields(prediction)), where
    if run.answers:
        given, result, correct = run.answers[-1]
        assert tuple(map(int, next(rows).split()[1:])) == (correct, *fields(given), *fields(result)), where


def compare_notes(run, rows, mode, header):
    assert int(header.split()[1]) == len(run.notes), (mode, header, len(run.notes))
    for cue in run.notes:
        actual = tuple(map(float, next(rows).split()))
        expected = (cue.seed, cue.voice, cue.t, cue.dur, cue.freq, cue.gain, cue.pan, cue.bright)
        assert len(actual) == len(expected) and all(isclose(a, b, abs_tol=1e-10) for a, b in zip(actual, expected)), (
            mode, actual, expected)


def compare_pcm(run, rows, mode):
    patches = [drshape.make_patch(name, Random(i + 1)) for i, name in enumerate(task.PATCHES)]
    for _ in range(4):
        marker, value = next(rows).split()
        assert marker == "pcm"
        begin = float(value)
        expected = drshape.synth(run.notes, begin, begin + 0.1, patches)
        actual = bytes.fromhex(next(rows))
        assert actual == expected, (mode, begin, len(actual), len(expected))


def compare_records(run, rows, mode, summary):
    actual = json.loads(next(rows))
    expected = task.metrics(run)
    if expected["accuracy"] is not None:
        assert isclose(actual.pop("accuracy"), expected.pop("accuracy"), rel_tol=1e-15), mode
    assert actual == expected, (mode, actual, expected)
    best = -1 if summary["best"] is None else summary["best"]
    assert next(rows) == f"summary {best} {summary['standing']}", mode
    assert next(rows) == summary["words"], mode
    for line in task.notebook_text(run).splitlines():
        assert next(rows) == line, (mode, line)
    assert next(rows) == "end notebook"


def compare_blocks(rows, level):
    blocks = task.blocks(level)
    assert next(rows) == f"blocks {len(blocks)}"
    kinds = ("form", "rule", "test", "sym")
    forms = tuple(task.FORMS)
    for item in blocks:
        encoded = forms.index(item.value) if item.kind == "form" else (
            item.value if item.kind == "sym" else lang.code(item.value))
        assert next(rows) == f"{kinds.index(item.kind)} {encoded}", (level.rung, item)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = 0
    for mode in range(9):
        rung = {2: 19, 6: 1, 8: 13}.get(mode, 10)
        level = task.grade(rung)
        rule = lang.parse("alt(rev,shift(1))" if mode == 8 else ("rev" if mode == 6 else "shift(1)"))
        other = lang.parse("shift(2)" if mode == 3 else "seq(shift(2),shift(3))")
        given = (0, 1, 1) if mode == 6 else (0, 1, 2, 3, 1, 0)
        kind = "invert" if mode == 2 else ("twins" if mode in (3, 4) else "crack")
        run = task.Run(task.Machine(level, rule, (given, given), 37, (), kind, other))
        assert next(rows) == f"mode {mode} {rung}"
        compare_blocks(rows, level)
        for action in rows:
            event, value = action.split()
            if event == "notes":
                summary = task.summary(run)
                task.end_tones(run, summary["bits"])
                compare_notes(run, rows, mode, action)
                compare_pcm(run, rows, mode)
                compare_records(run, rows, mode, summary)
                break
            if event == "choose":
                continue
            if event == "advance":
                run.step(float(value))
            elif event == "board":
                run.add_block(int(value))
            else:
                assert event == "event"
                task.act(run, int(value))
                run.step(0.075)
            compare_state(run, rows, (mode, action))
            cases += 1
    assert int(next(rows).split()[1]) >= 0
    rule = lang.parse("meta(has(1),prog(0:shift(1),1:feistel(rev)),seq(xor(1),perm([1,0])))")
    library = task.learn({}, rule, 9)
    library = task.learn(library, lang.parse("xor(1)"), 3)
    library = task.learn(library, lang.parse("rev"), 14)
    recalled = task.remembered(library, rule, 10)
    assert next(rows) == (
        f"You met {', '.join(op for op, _ in recalled[:3])} at rung {min(rung for _, rung in recalled)}"
    )
    assert json.loads(next(rows)) == library
    check_session(rows)
    assert next(rows, None) is None
    print(f"PASS: {cases} gameplay steps, 36 stereo PCM windows, and nine round records match Python")
    print("PASS: Cipher Abyss scene states, notebook pointer coordinates, and nine options descriptions")


def scene(rows, name, expected):
    assert next(rows) == f"scene {name}"
    actual = []
    for line in rows:
        if line == "scene end":
            break
        actual.append(line)
    for line in expected:
        assert line in actual, (name, line, actual)
    return actual


def check_session(rows):
    for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30):
        level = task.grade(rung)
        assert next(rows) == (
            f"Rung {rung} ({task.stage_name(level)}): {level.k} symbols, "
            f"rows of {level.length}, {level.budget} experiments."
        )
    scene(rows, "ready", ("The Cipher Abyss", "Press Space or click to start"))
    assert next(rows) == "session start 1 1 1 0 0 0 0 0"
    scene(rows, "start", ("CIPHER MACHINE", "HYPOTHESIS BOARD", "NOTEBOOK",
                          "1. click symbols to build an input", "PREDICT: off", "sort: by time"))
    assert next(rows) == "prediction As you said"
    assert next(rows) == "mark 1"
    frame = scene(rows, "marked", ("3. watch what comes out", "2", "1"))
    marks = [float(line.split()[1]) for line in frame if line.startswith("marked ")]
    note_y = task.note_y(0)
    assert len(marks) == 1 and isclose(marks[0], 179 + (note_y - 17) * 389 / 640, abs_tol=1e-4)
    scene(rows, "test", ("TEST 1 of 2: what does it give for", "ANSWER", "4. when you know, take the test"))
    assert next(rows) == "session judged 2 2 1 1 1 2 2 2"
    scene(rows, "judged", ("CRACKED", "Cracked it.", "What each experiment told (bits)", "A careful experimenter ran"))
    assert [next(rows) for _ in range(4)] == [
        "session feedback 2 2 1 1 1 2 2 2",
        "session next 1 2 2 1 0 0 0 0",
        "session wrong 2 1 2 1 2 0 1 0",
        "session done 3 1 2 1 2 0 1 0",
    ]
    scene(rows, "done", ("1 of 2 cracked",))


if __name__ == "__main__":
    check(sys.argv[1])
