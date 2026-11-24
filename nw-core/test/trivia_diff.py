#!/usr/bin/env python3
"""Differential harness for tasks/trivia.elisa against trivia.py.

Everything under test is module-level in the reference and is LIFTED by AST and
run as itself: `normalise`, `kind_of`, `question_from`, `Bank`, `distractors`,
`generate`, `grade_at`, `Question`, `Round`, `Grade`, `GRADES`, `PARTICLES`,
`KINDS` and the three regexes. Nothing here reads the corpus -- `question_from`
takes a row dict and `generate` takes a pool -- so the whole module runs as
written over rows built to the same recipe the sweep uses.
"""
import ast
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "trivia.py")

WANTED_FN = {"normalise", "kind_of", "question_from", "distractors",
             "generate", "grade_at", "correct"}
WANTED_CLASS = {"Question", "Round", "Grade", "Bank"}
WANTED_CONST = {"GRADES", "MOST_OPTIONS", "PARTICLES", "KINDS",
                "QUESTION_CHARS", "ANSWER_CHARS", "ALIASES", "_PUNCT",
                "_ARTICLE", "_NUMBER", "_YEAR", "_YESNO"}

KIND_INDEX = {"year": 0, "number": 1, "name": 2, "phrase": 3, "word": 4}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in WANTED_FN:
            keep.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in WANTED_CLASS:
            keep.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in WANTED_CONST:
                keep.append(node)
        elif isinstance(node, ast.Assign):
            flat = [t.id for t in node.targets if isinstance(t, ast.Name)]
            flat += [e.id for t in node.targets if isinstance(t, ast.Tuple)
                     for e in t.elts if isinstance(e, ast.Name)]
            if WANTED_CONST.intersection(flat):
                keep.append(node)
    typing = __import__("typing")
    space = {"re": __import__("re"), "random": random, "os": __import__("os"),
             "Tuple": typing.Tuple, "Optional": typing.Optional,
             "Dict": typing.Dict, "List": typing.List,
             "FrozenSet": typing.FrozenSet, "Sequence": typing.Sequence,
             "NamedTuple": typing.NamedTuple,
             "bank": lambda fetched_only=False: None}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"), space)
    missing = (WANTED_FN | WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("trivia_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()


def write_word(kind, salt):
    if kind == 0:
        return chr(65 + salt % 26) + "".join(
            chr(97 + (salt * 3 + k * 5) % 26) for k in range(2 + salt % 4))
    if kind == 1:
        return "".join(chr(97 + (salt * 7 + k * 3) % 26)
                       for k in range(3 + salt % 4))
    if kind == 2:
        value = 900 + salt * 37 % 1400
        out = "%04d" % value
        if (salt % 5) == 0:
            out += "s"
        if (salt % 7) == 0:
            out = out[:4] + "%"
        return out
    if kind == 3:
        return "van"
    return "the"


def write_text(words, recipe):
    out = ""
    for w in range(words):
        if w > 0:
            out += " "
            if ((recipe + w) % 5) == 0:
                out += " "
        out += write_word((recipe // 3 + w) % 5, recipe * 3 + w)
        if ((recipe + w) % 7) == 0:
            out += ","
    return out


def coded(text):
    return [ord(one) for one in text]


def reference():
    out = []
    for rung in range(-1, 11):
        g = REF["grade_at"](rung)
        out.append(["grade", rung, g.options, 1 if g.matched else 0])

    for recipe in range(120):
        words = 1 + recipe % 6
        text = write_text(words, recipe)
        tidy = REF["normalise"](text)
        out.append(["shape", recipe, len(text)] + coded(text)
                   + [len(tidy)] + coded(tidy)
                   + [KIND_INDEX[REF["kind_of"](text)]])

    questions = []
    for row in range(800):
        asked = write_text(3 + row % 9, row * 5 + 1)
        answer = write_text(1 + row % 3, row * 7 + 2)
        aliases = [write_text(1 + one, row * 11 + one) for one in range(row % 4)]
        made = REF["question_from"]({"question": asked,
                                     "answer": {"value": answer,
                                                "aliases": aliases}})
        if made is not None:
            questions.append(made)
        row_out = ["row", row, 0 if made is None else 1, len(questions)]
        if made is not None:
            row_out.extend((KIND_INDEX[made.kind], len(made.aliases),
                            len(made.answer), len(REF["normalise"](made.answer))))
        out.append(row_out)

    pool = REF["Bank"](questions)
    out.append(["pool", len(pool), pool.narrowest()]
               + [len(pool.alike(kind)) for kind in
                  ("year", "number", "name", "phrase", "word")])

    by_answer = {one.answer: at for at, one in enumerate(questions)}
    for rung in range(1, 8):
        for seed in range(1, 13):
            made = REF["generate"](rung, rung * 1000 + seed, pool)
            row = ["round", rung, seed, 0 if made is None else 1]
            if made is None:
                row.extend((-1, 0, 0, 0))
            else:
                row.extend((questions.index(made.question), len(made.options),
                            made.answer, made.rung))
                row.extend(by_answer[one] for one in made.options)
            out.append(row)
    return [",".join(str(one) for one in row) for row in out], [
        by_answer[one.answer] for one in questions
    ]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want, answer_ids = reference()
    # The Python round contains answer strings. Distinct corpus rows may
    # supply the same string, so compare options by their displayed answer.
    for index, line in enumerate(mine):
        cells = line.split(",")
        if cells[0] == "round" and cells[3] == "1":
            cells[8:] = [str(answer_ids[int(cell)]) for cell in cells[8:]]
            mine[index] = ",".join(cells)
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        for index, (a, b) in enumerate(zip(mine, want)):
            if a != b:
                print("  first differing line %d" % index)
                print("  elisa:  %s" % a[:140])
                print("  python: %s" % b[:140])
                break
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, python %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a[:140])
            print("  python: %s" % b[:140])
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
