"""Check ordered Cipher Abyss hypotheses and eligible rules against Python."""
import subprocess
import sys

from neural_workshop import cipherabyss as task, cipherlang as lang

RUNGS = (1, 2, 3, 4, 5, 7, 8, 9, 10, 13, 14, 16, 18, 19, 20, 21,
         22, 23, 25, 26, 28, 30, 35, 40, 52, 100, 180)


def compare(rung, rows, name, expected):
    header = next(rows).strip()
    assert header == f"count {len(expected)}", (rung, name, header, len(expected))
    for index, rule in enumerate(expected):
        actual = next(rows).strip()
        wanted = f"{lang.size(rule)} {lang.code(rule)}"
        assert actual == wanted, (rung, name, index, actual, wanted)
    return len(expected)


def compare_looks(rung, rows, level):
    looks = task._one_look(level)
    count = 0
    for truth in task.truths(level):
        expected = {f"{lang.size(rule)} {lang.code(rule)}" for rule in looks.get(truth, ())}
        header = next(rows).strip()
        assert header == f"count {len(expected)}", (rung, lang.code(truth), header, len(expected))
        actual = {next(rows).strip() for _ in range(len(expected))}
        assert actual == expected, (rung, lang.code(truth), actual, expected)
        count += 1
    return count


def compare_play(rows, level):
    eligible = task.truths(level)
    target = eligible[len(eligible) // 2]
    mind = task.Mind(level, 37)
    state, log = lang.START, []
    for _ in range(level.budget):
        given = mind.experiment()
        if given is None:
            break
        result = lang.run(target, given, level.k, state)
        state = lang.advance(target, state, given, result, level.k)
        log.append((given, result))
        mind.update(log)
        fields = ("experiment", len(mind.alive), len(given), *given, len(result), *result)
        actual = next(rows).strip()
        assert actual == " ".join(map(str, fields)), (level.rung, actual, fields)
    assert next(rows).strip() == f"after {mind.draw.getrandbits(32)}"
    compare(level.rung, rows, "earlier survivors", mind.snapshots[max(0, len(mind.snapshots) - 3)])
    mind.begin_test()
    state = lang.START
    for i in range(3):
        given = (i + 1) % level.k, i % level.k, i % level.k, 0
        guess = mind.answer(given)
        result = lang.run(target, given, level.k, state)
        state = lang.advance(target, state, given, result, level.k)
        mind.tested_on(given, result)
        fields = ("answer", len(mind.testing), mind.split, len(guess), *guess, len(result), *result)
        actual = next(rows).strip()
        assert actual == " ".join(map(str, fields)), (level.rung, actual, fields)
    return len(log)


def check(binary):
    count = 0
    rival_sets = 0
    experiments = 0
    with subprocess.Popen([binary], text=True, stdout=subprocess.PIPE) as child:
        try:
            rows = iter(child.stdout)
            for rung in RUNGS:
                assert next(rows).strip() == f"rung {rung}"
                level = task.grade(rung)
                raw, truths = task._raw(level)
                count += compare(rung, rows, "raw hypotheses", raw)
                count += compare(rung, rows, "raw truths", truths)
                count += compare(rung, rows, "family", task.family(level))
                count += compare(rung, rows, "eligible", task.truths(level))
                if rung in (1, 4, 13, 22, 40):
                    rival_sets += compare_looks(rung, rows, level)
                    experiments += compare_play(rows, level)
            assert next(rows, None) is None
            assert child.wait() == 0
        finally:
            if child.poll() is None:
                child.terminate()
    print(f"PASS: {count} ordered Cipher Abyss rules at {len(RUNGS)} rungs and {rival_sets} one-look rival sets match Python")
    print(f"Reference players match {experiments} experiments and 15 test answers")


if __name__ == "__main__":
    check(sys.argv[1])
