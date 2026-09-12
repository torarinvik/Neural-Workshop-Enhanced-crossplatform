#!/usr/bin/env python3
"""Differential harness for tasks/scramble.elisa against scramble.py.

Almost everything under test is module-level in the reference and is LIFTED by
AST and run as itself: `GRADES`, `grade_of`, `anchored`, `removals`,
`additions`, `bag_distance`, `feasible`, `scramble_word`, `_shuffled`,
`blocks`, `shuffle_order`, `respace`, `candidates`, `normalise`, `NEAR_KEYS`
and `LETTERS`. Only `Vocab` is replaced -- it reads a downloaded frequency list
off disk -- by a stand-in with the same three attributes `candidates` uses.

`deal_one` is transcribed rather than lifted for the same reason: it calls
`choose(...)` on the sentence corpus. What stays the reference's own inside it
is every RNG-spending step.

`read_off`/`read_back` receive a compatibility table of the first candidate
for each `(grade, token)` lookup. Python's tie break belongs to the temporary
SET built for that token, so a single global word order would be incorrect.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "scramble.py")
ORDER_PATH = "/tmp/nw_scramble_order.txt"

WANTED_FN = {"grade_of", "anchored", "removals", "additions", "bag_distance",
             "feasible", "scramble_word", "_shuffled", "blocks",
             "shuffle_order", "respace", "candidates", "read_off", "read_back",
             "normalise", "_recipe"}
WANTED_CLASS = {"Grade"}
WANTED_CONST = {"GRADES", "LETTERS", "NEAR_KEYS", "_FITS"}

LETTERS = "abcdefghijklmnopqrstuvwxyz"
SPACE, OTHER = 26, 27


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
            if WANTED_CONST.intersection(flat):
                keep.append(node)
    typing = __import__("typing")
    space = {"math": math, "re": __import__("re"), "random": random,
             "itertools": __import__("itertools"),
             "Counter": __import__("collections").Counter,
             "Tuple": typing.Tuple, "Optional": typing.Optional,
             "Dict": typing.Dict, "List": typing.List,
             "Sequence": typing.Sequence, "NamedTuple": typing.NamedTuple,
             # `candidates` is annotated `words: Optional[Vocab]`, and a
             # lifted subset has no `from __future__` line to keep annotations
             # unevaluated -- so the name has to be bound before the exec.
             "Vocab": object, "Deal": object,
             "Sentence": object, "vocab_for": lambda grade: None,
             "_TIDY": __import__("re").compile(r"[^a-z ]+")}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"), space)
    missing = (WANTED_FN | WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("scramble_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
GRADES = REF["GRADES"]
grade_of = REF["grade_of"]


class Vocab(object):
    """`Vocab` without the downloaded frequency list behind it.

    `candidates` reads exactly three attributes off it, and they are all built
    from the word list -- so the stand-in is the real indexing over a supplied
    one rather than a mock of the lookup.
    """

    def __init__(self, words, ranks):
        self.top_rank = 1 << 30
        self.words = list(words)
        self.rank = dict(zip(words, ranks))
        self.by_letters = {}
        for word in self.words:
            self.by_letters.setdefault("".join(sorted(word)), []).append(word)
        self.longest = max((len(word) for word in self.words), default=1)


def build_vocab(count):
    words, ranks = [], []
    for v in range(count):
        length = 3 + v % 6
        words.append("".join(LETTERS[(v * 7 + k * 5) % 26] for k in range(length)))
        ranks.append(v - v % 11)
    return words, ranks, Vocab(words, ranks)


def write_order(words, pool, bank):
    """Persist this process's per-token candidate choice for the Elisa side."""
    first = {}
    for index, word in enumerate(words):
        first.setdefault(word, index)
    rows = []
    for rung in range(1, 13):
        grade = grade_of(rung)
        for seed in range(1, 15):
            made = deal_one(grade, bank, pool, random.Random(rung * 100 + seed))
            blob = "".join(made["chunks"])
            if grade.spaces < 1:
                tokens = made["chunks"]
            else:
                tokens = (blob[start:stop]
                          for start in range(len(blob))
                          for stop in range(start + 1,
                                            min(len(blob), start + pool.longest + grade.drop) + 1))
            for token in tokens:
                fits = REF["candidates"](grade, token, pool)
                best = first[fits[0]] if fits else -1
                rows.append(" ".join([str(rung), str(len(token)),
                                       *(str(value) for value in coded(token)),
                                       str(best)]))
    Path(ORDER_PATH).write_text("\n".join(rows) + "\n")


def build_bank(words, sentences):
    return [[words[(s * 5 + w * 3) % len(words)] for w in range(6 + s % 8)]
            for s in range(sentences)]


def deal_one(grade, bank, pool, rng):
    """`deal_one`, around the reference's own corruption pipeline."""
    if not bank:
        return None
    index = rng.randrange(len(bank))
    words = tuple(bank[index])
    placing = REF["shuffle_order"](grade, len(words), rng)
    corrupted = tuple(REF["scramble_word"](grade, words[where], rng)
                      for where in placing)
    chunks = (corrupted if grade.spaces < 1
              else REF["respace"](grade, "".join(corrupted),
                                  [len(one) for one in corrupted], rng))
    counts = [max(1, len(REF["candidates"](grade, token, pool)))
              for token in corrupted]
    return dict(sentence=index, words=words, placing=placing,
                corrupted=corrupted, chunks=chunks,
                ambiguity=sum(math.log10(count) for count in counts),
                pinned=sum(1 for count in counts if count == 1))


def coded(text):
    return [LETTERS.index(one) for one in text]


class DealView(object):
    """The small part of `scramble.Deal` consumed by read_off/read_back."""

    def __init__(self, grade, chunks, truth):
        self.grade = grade
        self.chunks = chunks
        self.in_view = truth


def scaled(value):
    return int(round(value * 1000000.0))


def spell(codes):
    """The sweep's letter/space/other codes, as the text they stand for."""
    out = []
    for value in codes:
        out.append(" " if value == SPACE else ("#" if value == OTHER
                                               else LETTERS[value]))
    return "".join(out)


def reference():
    out = []
    for rung in range(-1, 16):
        g = grade_of(rung)
        out.append(["grade", rung, g.span[0], g.span[1], g.top_rank, g.swap,
                    1 if g.interior else 0, 1 if g.whole else 0, g.drop,
                    g.insert, g.substitute, g.spaces, g.order,
                    1 if REF["anchored"](g) else 0, REF["removals"](g),
                    REF["additions"](g)])

    for letter in range(26):
        row = ["near", letter]
        row.extend(LETTERS.index(one) for one in REF["NEAR_KEYS"][LETTERS[letter]])
        out.append(row)

    words, ranks, pool = build_vocab(240)
    bank = build_bank(words, 40)

    for rung in range(1, 13):
        g = grade_of(rung)
        row = ["feasible", rung]
        for token in range(20):
            for word in range(20):
                row.append(1 if REF["feasible"](g, words[token], words[word]) else 0)
        out.append(row)

    for rung in range(1, 13):
        g = grade_of(rung)
        REF["_FITS"].clear()
        row = ["candidates", rung]
        for token in range(24):
            row.append(len(REF["candidates"](g, words[token], pool)))
        out.append(row)

    for rung in range(1, 13):
        g = grade_of(rung)
        for seed in range(1, 15):
            rng = random.Random(rung * 100 + seed)
            made = deal_one(g, bank, pool, rng)
            row = ["deal", rung, seed, 0 if made is None else 1,
                   -1 if made is None else made["sentence"],
                   0 if made is None else len(made["words"]),
                   scaled(0.0 if made is None else made["ambiguity"]),
                   0 if made is None else made["pinned"]]
            if made is not None:
                row.extend(made["placing"])
                for token in made["corrupted"]:
                    row.append(len(token))
                    row.extend(coded(token))
                row.append(len(made["chunks"]))
                at = 0
                for chunk in made["chunks"]:
                    row.extend((at, len(chunk)))
                    at += len(chunk)
            out.append(row)
            if made is not None:
                view = DealView(g, made["chunks"],
                                tuple(made["words"][where] for where in made["placing"]))
                reading = REF["read_off"](view, pool)
                row = ["read", rung, seed, len(reading)]
                for word in reading:
                    row.append(len(word))
                    row.extend(coded(word))
                row.append(scaled(REF["read_back"](view, pool)))
                out.append(row)

    for sentence in range(24):
        words_here = bank[sentence]
        for spoiled in range(5):
            typed = []
            if spoiled == 1:
                typed.extend((OTHER, SPACE))
            for slot, word in enumerate(words_here):
                if slot > 0:
                    typed.append(SPACE)
                    if spoiled == 1:
                        typed.append(SPACE)
                keep = len(word) - 1 if spoiled == 2 and slot == 0 else len(word)
                for at in range(keep):
                    value = LETTERS.index(word[at])
                    if spoiled == 4 and slot == 1 and at == 0:
                        value = (value + 1) % 26
                    typed.append(value)
            if spoiled == 3:
                typed.extend((SPACE, 0))
            if spoiled == 1:
                typed.append(SPACE)
            text = spell(typed)
            tidy = REF["normalise"](text)
            out.append(["mark", sentence, spoiled,
                        1 if tidy == " ".join(words_here) else 0, len(tidy)])
    return [",".join(str(one) for one in row) for row in out]


def main():
    # The binary is launched after this function starts. Write before launching
    # it so the order belongs to exactly the same Python process whose output
    # `read_off` below is the oracle.
    words, _ranks, pool = build_vocab(240)
    write_order(words, pool, build_bank(words, 40))
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
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
