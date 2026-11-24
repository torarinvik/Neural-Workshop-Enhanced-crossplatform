"""Compare the Cipher Abyss grading and interpreter against the Python originals."""
import subprocess
import sys

from neural_workshop import cipherabyss, cipherlang as lang


def programs(k):
    nodes = []
    for op in lang.KEEP + lang.RESIZE + lang.TESTS:
        args = ()
        if op == "perm":
            args = ((2, 4, 3, 1, 0),)
        elif op == "sub":
            args = (tuple(reversed(range(k))),)
        elif op == "conv":
            args = (3, 2, 1)
        elif op == "affine":
            args = (3, 1)
        elif op in {"rot", "shift", "mul", "tshift", "oddshift", "xor", "gf", "stride", "first", "last", "has", "evens", "echo"}:
            args = (2,)
        nodes.append((lang.Test if op in lang.TESTS else lang.Prim)(op, args))
    seq = lang.Seq((lang.Prim("weave"), lang.Prim("tshift", (2,)), lang.Prim("prefix")))
    choose = lang.If(lang.Test("pal"), lang.Prim("diff"), lang.Prim("mem"))
    alternating = lang.Alt(choose, lang.Prim("gf", (2,)))
    excepted = lang.Except(alternating, lang.Prim("dedupe"))
    data = lang.Prog(((0, lang.Prim("rev")), (1, lang.Prim("shift", (2,))), (0, lang.Prim("swap"))))
    meta = lang.Meta((excepted, data, seq), lang.Test("evens", (2,)))
    nodes[lang.KEEP.index("feistel")] = lang.Prim("feistel", (seq,))
    return nodes + [seq, choose, alternating, excepted, data, meta, lang.Meta((meta, choose), lang.Test("same"))]


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    rungs = (*range(-2, 160), 2**63 - 1)
    for rung in rungs:
        grade = cipherabyss.grade(rung)
        fields = (*grade[:-1], int(grade.seconds), int(cipherabyss.plain(grade)))
        expected = "grade " + " ".join(map(str, fields)) + " " + cipherabyss.stage_name(grade)
        actual = next(rows)
        assert actual == expected, (rung, actual, expected)
    cases = 0
    for k in (4, 8):
        nodes = programs(k)
        for index in range(130):
            row = tuple((index + i * (index // 13) + i * i) % k for i in range(index % 13))
            last = tuple((index + 3 * i) % k for i in range(index % 7))
            state = lang.State(index, last, last, 2 * index)
            for op, node in enumerate(nodes):
                if isinstance(node, lang.Test):
                    fields = (int(lang.test(node, row, k, state)),)
                else:
                    output = lang.run(node, row, k, state)
                    new = lang.advance(node, state, row, output, k)
                    fields = (len(output), *output, new.runs, new.meta)
                actual = tuple(map(int, next(rows).split()))
                expected = (k, index, op, *fields)
                assert actual == expected, (lang.code(node), row, state, actual, expected)
                cases += 1
        log = [(row, (3,)) for row in ((0, 0, 0), (1, 2, 3, 0), (2, 2), (2, 0, 1, 3))]
        state = lang.replay(nodes[-1], log, k)
        expected = (k, state.runs, state.meta, len(state.last_in), *state.last_in, len(state.last_out), *state.last_out)
        marker, *fields = next(rows).split()
        assert marker == "replay" and tuple(map(int, fields)) == expected
        cases += 1
    for k in (4, 8):
        nodes = programs(k)
        ops = ("shift", "shift", "rev", "rev", "weave", "unweave", "sort", "sort")
        target = lang.Seq(tuple(nodes[lang.KEEP.index(op)] for op in ops))
        branch = lang.If(lang.Test("first", (2,)), target, target)
        nested = lang.Seq((target, branch, lang.Prim("shift", (2,))))
        notation = nodes + [target, branch, nested]
        for index, node in enumerate(notation):
            words = ["code", k, index]
            for version in (node, lang.canon(node, 5, k)):
                words.extend((lang.size(version), int(lang.uses_state(version)),
                              int(lang.fixed_length(version)), lang.code(version)))
            expected = " ".join(map(str, words))
            actual = next(rows)
            assert actual == expected, (actual, expected)
            cases += 1
        for index, node in enumerate(notation):
            version = lang.parse(lang.code(node))
            words = ("parsed", k, index, lang.size(version), int(lang.uses_state(version)),
                     int(lang.fixed_length(version)), lang.code(version))
            actual = next(rows)
            expected = " ".join(map(str, words[:3])) + "  " + " ".join(map(str, words[3:]))
            assert actual == expected, (actual, expected)
            cases += 1
        for index, node in enumerate(notation):
            words = lang.say_test(node) if isinstance(node, lang.Test) else lang.say(node)
            assert next(rows) == f"words {k} {index} {words}"
            cases += 1
    for k in (4, 8):
        for probe in lang.probes(5, k):
            assert tuple(map(int, next(rows).split()[1:])) == (k, len(probe), *probe)
            cases += 1
        nodes = programs(k)
        primitives = nodes[:len(lang.KEEP + lang.RESIZE)]
        candidates = [node for node in nodes if not isinstance(node, lang.Test)]
        candidates.extend(lang.Seq((a, b)) for a in primitives for b in primitives)
        best = lang.dedupe(candidates, 5, k)
        assert next(rows) == f"family {k} {len(best)}"
        for node in best:
            expected = f"{lang.size(node)} {int(lang.uses_state(node))} {int(lang.fixed_length(node))} {lang.code(node)}"
            actual = next(rows).strip()
            assert actual == expected, (actual, expected)
            cases += 1
    assert next(rows) == "invalid 1 2 -1 -1 -1 -1 2"
    cases += 4
    assert next(rows, None) is None
    print(f"PASS: {cases} Cipher Abyss interpreter cases and {len(rungs)} grades match Python")


if __name__ == "__main__":
    check(sys.argv[1])
