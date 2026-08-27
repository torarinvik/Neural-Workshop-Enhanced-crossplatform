#!/usr/bin/env python3
"""Differential harness for tasks/crossword.elisa against crossword.py.

Everything under test is module-level in the reference and is LIFTED by AST and
run as itself: `runs`, `well_formed`, `connected`, `longest`, `split_points`,
`shape`, `a_shape`, `number`, `_down_runs`, `fill`, `_Budget`, `deal_one`,
`_dress`, `grade_of` and the `Grade`/`Slot`/`Puzzle` types. Only `Lexicon` is
replaced -- it reads a downloaded, rank-ordered corpus with clues off disk --
by a stand-in doing the same indexing over a supplied word list.
"""
import ast
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "crossword.py")

LETTERS = "abcdefghijklmnopqrstuvwxyz"
ALPHABET = "aent"

WANTED_FN = {"runs", "well_formed", "connected", "longest", "split_points",
             "shape", "a_shape", "number", "_down_runs", "fill", "deal_one",
             "_dress", "grade_of"}
WANTED_CLASS = {"Slot", "Puzzle", "Grade", "_Budget"}
WANTED_CONST = {"GRADES", "MIN_ENTRY", "MAX_ENTRY", "RESTARTS"}


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
    space = {"random": random,
             "Tuple": typing.Tuple, "Optional": typing.Optional,
             "Dict": typing.Dict, "List": typing.List, "Set": typing.Set,
             "Sequence": typing.Sequence, "NamedTuple": typing.NamedTuple,
             "Lexicon": object, "pool": lambda top_rank: None}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"), space)
    missing = (WANTED_FN | WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("crossword_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Grade = REF["Grade"]


class Entry(object):
    __slots__ = ("word", "rank", "clue")

    def __init__(self, word, rank, clue):
        self.word = word
        self.rank = rank
        self.clue = clue


class Lexicon(object):
    """`Lexicon` without the downloaded corpus behind it, indexed as it is."""

    def __init__(self, entries):
        self.entries = tuple(entries)
        self.at = {one.word: one for one in self.entries}
        self.words = frozenset(self.at)
        by_length = {}
        for one in self.entries:
            by_length.setdefault(len(one.word), []).append(one)
        self.by_length = {length: tuple(group)
                          for length, group in by_length.items()}
        self._prefixes = {}
        self._fits = {}

    def valid(self, word):
        return word in self.words

    def clue(self, word):
        one = self.at.get(word)
        return one.clue if one else ""

    def prefixes(self, length=0):
        if length not in self._prefixes:
            found = set()
            for one in self.entries:
                if length and len(one.word) != length:
                    continue
                for cut in range(1, len(one.word)):
                    found.add(one.word[:cut])
            self._prefixes[length] = frozenset(found)
        return self._prefixes[length]

    def narrowed(self, lo=1, hi=1 << 30, lengths=()):
        """`Lexicon.narrowed`, which `deal_one` calls before it fills.

        The sweep's pool is already exactly the narrowed one -- lengths three
        to five, ranks far below any rung's cap -- so this is a no-op here, and
        that is why tasks/crossword.elisa takes the narrowed pool rather than
        narrowing one.
        """
        keep = set(lengths)
        return Lexicon(one for one in self.entries
                       if lo <= one.rank < hi
                       and (not keep or len(one.word) in keep))

    def fitting(self, pattern):
        if pattern in self._fits:
            return self._fits[pattern]
        pooled = self.by_length.get(len(pattern), ())
        if "." not in pattern:
            one = self.at.get(pattern)
            found = (one,) if one is not None else ()
        else:
            wanted = [(at, ch) for at, ch in enumerate(pattern) if ch != "."]
            found = tuple(one for one in pooled
                          if all(one.word[at] == ch for at, ch in wanted))
        self._fits[pattern] = found
        return found


def build_lexicon():
    """The synthetic corpus, ranked from one as the real one is.

    Ranks start at one and not at zero because `Lexicon.narrowed` takes
    `lo=1` and drops anything below it -- a pool ranked from zero loses its
    first word the moment `deal_one` narrows, and the sweep is written on
    the promise that narrowing here changes nothing.
    """
    entries = []
    count = 0
    for length in range(3, 6):
        for index in range(4 ** length):
            letters = [""] * length
            left = index
            for k in range(length):
                letters[length - 1 - k] = ALPHABET[left % 4]
                left //= 4
            rank = count + 1
            entries.append(Entry("".join(letters), rank,
                                 "" if (rank % 3) == 0 else str(rank)))
            count += 1
    return Lexicon(entries)


def clue_id(text):
    return -1 if not text else int(text)


def reference():
    out = []
    for rung in range(-1, 13):
        g = REF["grade_of"](rung)
        out.append(["grade", rung, g.size, g.longest_entry, g.top_rank,
                    int(g.given * 1000000.0), int(g.withheld * 1000000.0),
                    g.tries])

    for length in range(16):
        found = REF["split_points"](length)
        out.append(["splits", length, len(found)] + list(found))

    lex = build_lexicon()

    for size in range(4, 8):
        for entry in range(3, 7):
            for seed in range(1, 5):
                rng = random.Random(size * 1000 + entry * 100 + seed)
                blocks = REF["shape"](size, entry, rng)
                out.append(["shape", size, entry, seed,
                            REF["longest"](size, set(blocks)),
                            1 if REF["well_formed"](size, set(blocks)) else 0,
                            1 if REF["connected"](size, set(blocks)) else 0]
                           + [1 if cell in blocks else 0
                              for cell in range(size * size)])
                blocks = REF["a_shape"](size, entry, rng)
                numbers = REF["number"](size, set(blocks))
                out.append(["ashape", size, entry, seed,
                            REF["longest"](size, set(blocks))]
                           + [1 if cell in blocks else 0
                              for cell in range(size * size)]
                           + [numbers.get(cell, 0) for cell in range(size * size)]
                           + [rng.randrange(1000000)])

    for pattern in range(24):
        size = 5 + pattern % 2
        blocks = frozenset(cell for cell in range(size * size)
                           if (((cell // size) * 7 + (cell % size) * 5
                                + pattern * 3) % 11) == 0)
        ok_shape = (REF["well_formed"](size, set(blocks))
                    and REF["connected"](size, set(blocks)))
        rng = random.Random(5000 + pattern)
        budget = REF["_Budget"](900)
        letters = REF["fill"](size, blocks, lex, rng, budget) if ok_shape else None
        row = ["fill", pattern, size, 1 if ok_shape else 0,
               0 if letters is None else 1, budget.spent if ok_shape else 0,
               rng.randrange(1000000)]
        row.extend(1 if cell in blocks else 0 for cell in range(size * size))
        if letters is not None:
            row.extend(-1 if not one else LETTERS.index(one) for one in letters)
        out.append(row)

    for spec in range(36):
        tight = spec >= 24
        step = spec - 24 if tight else spec
        rng = random.Random((7000 + step) if tight else (3000 + step))
        at = (3 if step % 2 == 0 else 2) if tight else 1 + step % 4
        rung = REF["grade_of"](at)
        grade = Grade(rung.name, rung.size, rung.longest_entry, rung.top_rank,
                      rung.given, rung.withheld,
                      (96 if step % 2 == 0 else 60) if tight else 2400)
        made = REF["deal_one"](grade, rng, lex)
        probe = rng.randrange(1000000)
        row = ["deal", spec, probe, 0 if made is None else 1,
               0 if made is None else made.size,
               0 if made is None else made.tried]
        if made is not None:
            row.extend((made.blanks(), made.unclued()))
            for cell in range(made.size * made.size):
                row.append(1 if cell in made.blocks else 0)
                letter = made.solution[cell]
                row.append(-1 if not letter else LETTERS.index(letter))
                row.append(1 if cell in made.givens else 0)
            row.append(len(made.slots))
            for slot in made.slots:
                row.extend((slot.number, 1 if slot.down else 0,
                            len(slot.cells), clue_id(slot.clue)))
                row.extend(slot.cells)
        out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
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
