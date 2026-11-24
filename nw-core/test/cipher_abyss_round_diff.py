"""Compare Cipher Abyss question selection, twins, and seeded machine candidates."""
import inspect
import os
import subprocess
import sys

from neural_workshop import cipherabyss as task, cipherlang as lang
from random import Random

RUNGS = (1, 4, 13, 19, 21, 25, 28, 30, 40)
BUILD_RUNGS = (1, 4, 10, 13, 19, 20, 25, 30, 40)


def reference_questions():
    # Isolate the crack-question block so we can give both implementations
    # identical survivor sets and observe exactly how they consume the RNG.
    source = inspect.getsource(task.build)
    body = source[source.index("    st = L.START                             # the test"):source.index("    other = None")]
    names = dict(vars(task), _reject=lambda index: (index, ()))
    exec("def questions(level, rule, final, earlier, rivals, draw):\n"
         "    k = level.k\n" + body + "    return 0, tuple(asked)\n", names)
    return names["questions"]


def rows_from_stream(rows, count):
    result = []
    for _ in range(count):
        length, *row = map(int, next(rows).split())
        assert length == len(row), (length, row)
        result.append(tuple(row))
    return tuple(result)


def compare_builds(rows):
    modes = {"crack": 0, "twins": 1, "invert": 2}
    accepted = dict.fromkeys(modes, 0)
    rejections = 0
    for rung in BUILD_RUNGS:
        level = task.grade(rung)
        eligible = task.truths(level)
        target = eligible[len(eligible) // 2]
        near = {lang.code(rule) for rule in task._twins(level, target)}
        assert next(rows).strip() == f"twins {rung} {len(near)}"
        assert {next(rows).strip() for _ in near} == near
        for seed in range(12):
            draw = Random(seed)
            alternate, same = task._twin_for(level, target, draw)
            expected = f"twin {rung} {seed} {int(alternate is not None)} {int(same)} {draw.getrandbits(32)}"
            actual = next(rows).strip()
            assert actual == expected, (actual, expected)
            if alternate is not None:
                assert next(rows).strip() == lang.code(alternate)
            draw = Random(seed)
            task.REJECTS.clear()
            machine = task.build(level, draw)
            actual = next(rows).split()
            assert actual[:3] == ["build", str(rung), str(seed)]
            rejected, kind, mind_seed, tests, plan, tail = map(int, actual[3:])
            if machine is None:
                expected = (next(iter(task.REJECTS)), 0, 0, 0, 0, draw.getrandbits(32))
                assert (rejected, kind, mind_seed, tests, plan, tail) == expected, (rung, seed, actual, expected)
                rejections += 1
                continue
            expected = (0, modes[machine.kind], machine.seed, len(machine.tests), len(machine.plan),
                        draw.getrandbits(32))
            assert (rejected, kind, mind_seed, tests, plan, tail) == expected, (rung, seed, actual, expected)
            assert next(rows).strip() == lang.code(machine.rule)
            if machine.other is not None:
                assert next(rows).strip() == lang.code(machine.other)
            problem_rows = rows_from_stream(rows, tests)
            if machine.kind == "invert":
                # Python scores a truncated set of rivals in process-specific
                # hash order, so output choices can differ with that order.
                inverses = task.preimages(machine.rule, level)
                assert len(set(problem_rows)) == tests
                assert all(row in inverses and inverses[row] != row and len(set(row)) > 1 for row in problem_rows)
            else:
                assert problem_rows == machine.tests, (rung, seed, problem_rows, machine.tests)
            assert rows_from_stream(rows, plan) == machine.plan
            won, _ = task.play(machine._replace(tests=problem_rows))
            assert next(rows).strip() == f"wins {int(won)}", (rung, seed, machine.kind)
            accepted[machine.kind] += 1
    assert all(accepted.values()), accepted
    return rejections, accepted


def compare_deals(rows):
    modes = ("crack", "twins", "invert")
    count = 0
    for rung in (1, 10, 19, 30):
        draw = Random(17)
        for index in range(2):
            source = task.deal(rung, rng=draw)
            actual = next(rows).split()
            assert actual[:3] == ["deal", str(rung), str(index)]
            rejected, kind, mind_seed, tests, plan = map(int, actual[3:])
            assert (rejected, modes[kind], mind_seed, tests, plan) == (
                0, source.kind, source.seed, len(source.tests), len(source.plan)), (rung, index, actual, source)
            assert next(rows).strip() == lang.code(source.rule)
            if source.other is not None:
                assert next(rows).strip() == lang.code(source.other)
            problems = rows_from_stream(rows, tests)
            if source.kind != "invert":
                assert problems == source.tests
            assert rows_from_stream(rows, plan) == source.plan
            assert task.play(source._replace(tests=problems))[0]
            count += 1
        assert next(rows).strip() == f"end {draw.getrandbits(32)}"
    return count


def check(binary):
    assert os.environ.get("PYTHONHASHSEED") == "0", "run with PYTHONHASHSEED=0"
    questions = reference_questions()
    count = 0
    with subprocess.Popen([binary], text=True, stdout=subprocess.PIPE) as child:
        try:
            rows = iter(child.stdout)
            for rung in RUNGS:
                level = task.grade(rung)
                for seed in range(4):
                    target = lang.parse("seq(tshift(1),rot(1))" if rung == 13 else "seq(rot(1),shift(1))")
                    earlier = list(map(lang.parse, ("rev", "shift(1)", "if(same,rot(1),shift(2))",
                                                   "alt(shift(1),shift(2))")))
                    rivals = set(earlier[2:])
                    draw = Random(seed)
                    inverse = task._invert_tests(level, target, [target], earlier, draw) or ()
                    assert next(rows).strip() == f"inverse {rung} {seed} {len(inverse)} {draw.getrandbits(32)}"
                    assert rows_from_stream(rows, len(inverse)) == inverse
                    draw = Random(seed)
                    rejected, asked = questions(level, target, [target], earlier, rivals, draw)
                    assert next(rows).strip() == f"crack {rung} {seed} {rejected} {len(asked)} {draw.getrandbits(32)}"
                    assert rows_from_stream(rows, len(asked)) == asked
                    count += 2
            rejected, accepted = compare_builds(rows)
            deals = compare_deals(rows)
            assert next(rows, None) is None
            assert child.wait() == 0
        finally:
            if child.poll() is None:
                child.terminate()
    print(f"PASS: {count} Cipher Abyss question selections, including inverse and longer rows, match Python")
    print(f"Seeded machine selection and screening match Python across {rejected} rejections and {accepted}")
    print(f"PASS: {deals} reference-screened deals and their RNG state match Python")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.execve(sys.executable, [sys.executable, *sys.argv], dict(os.environ, PYTHONHASHSEED="0"))
    check(sys.argv[1])
