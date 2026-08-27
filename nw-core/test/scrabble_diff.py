#!/usr/bin/env python3
"""Differential harness for tasks/scrabble.elisa against scrabble.py.

Everything under test is module-level in the reference and is LIFTED by AST and
run as itself: `VALUES`, `BAG`, `GRADES`, `grade_of`, `premiums`,
`blank_board`, `written`, `_run`, `score_play`, `legal`, `anchors`,
`_cross_check`, `plays`, `_extend`, `_walk`, `best_play`, `draw` and the
`Board`/`Play`/`Grade` types. Only `Lexicon` is replaced -- it reads a
downloaded, rank-ordered corpus off disk -- by a stand-in that answers the
three questions the solver asks it, over a supplied word list.
"""
import ast
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "scrabble.py")

LETTERS = "abcdefghijklmnopqrstuvwxyz"
PREMIUM_INDEX = {"": 0, "DL": 1, "TL": 2, "DW": 3, "TW": 4}

WANTED_FN = {"grade_of", "premiums", "blank_board", "written", "_run",
             "score_play", "legal", "anchors", "_cross_check", "plays",
             "_line_of", "_extend", "_walk", "best_play", "draw"}
WANTED_CLASS = {"Play", "Board", "Grade"}
WANTED_CONST = {"VALUES", "BAG", "GRADES", "BINGO", "RACK", "PLAIN",
                "DOUBLE_LETTER", "TRIPLE_LETTER", "DOUBLE_WORD",
                "TRIPLE_WORD"}


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
    space = {"random": random, "math": __import__("math"),
             "Tuple": typing.Tuple, "Optional": typing.Optional,
             "Dict": typing.Dict, "List": typing.List, "Set": typing.Set,
             "Sequence": typing.Sequence, "NamedTuple": typing.NamedTuple,
             "Lexicon": object, "Entry": object,
             "pool": lambda top_rank: None}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"), space)
    missing = (WANTED_FN | WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("scrabble_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Board = REF["Board"]
RACK = REF["RACK"]


class Lexicon(object):
    """`Lexicon` without the downloaded corpus behind it.

    The solver asks it three things -- is this a word, what are the openings of
    words, and what words are in the pool -- so the stand-in is the real
    indexing over a supplied list rather than a mock of the answers.
    """

    def __init__(self, words):
        self.words = frozenset(words)
        self._prefixes = frozenset(word[:cut] for word in words
                                   for cut in range(1, len(word)))

    def valid(self, word):
        return word in self.words

    def prefixes(self, length=0):
        return self._prefixes


ALPHABET = "aeinorst"


def build_lexicon(count):
    words = []
    for w in range(count):
        length = 2 + w % 4
        words.append("".join(ALPHABET[(w // 8 + k * 3 + w % 8) % 8]
                             for k in range(length)))
    return words, Lexicon(words)


def coded(text):
    return [LETTERS.index(one) for one in text]


def reference():
    out = []
    for rung in range(-1, 14):
        g = REF["grade_of"](rung)
        out.append(["grade", rung, g.size, g.top_rank, g.seeded,
                    int(g.share * 1000000.0), g.rack])

    out.append(["values"] + [REF["VALUES"][one] for one in LETTERS])
    out.append(["bag"] + [REF["BAG"][one] for one in LETTERS])

    words, lex = build_lexicon(120)

    for size in range(7, 16):
        board = REF["blank_board"](size)
        out.append(["premiums", size]
                   + [PREMIUM_INDEX[one] for one in board.premiums])

    for seed in range(1, 20):
        rng = random.Random(seed * 17)
        row = ["draw", seed]
        for _pull in range(3):
            tiles = REF["draw"](rng, RACK)
            row.append(len(tiles))
            row.extend(coded(tiles))
        out.append(row)

    for spec in range(18):
        size = 7 + (spec % 3) * 2
        board = REF["blank_board"](size)
        seed_word = words[(spec * 7) % len(words)]
        middle = size // 2
        at = middle * size + (size - len(seed_word)) // 2
        board = REF["written"](board, [(at + k, letter)
                                       for k, letter in enumerate(seed_word)])
        if (spec % 2) == 1:
            down_word = words[(spec * 11 + 3) % len(words)]
            column = at % size
            top = middle - len(down_word) // 2
            if top >= 0 and top + len(down_word) <= size:
                board = REF["written"](board, [
                    ((top + k) * size + column, letter)
                    for k, letter in enumerate(down_word)])
        out.append(["board", spec, size, board.filled()]
                   + [-1 if one == "" else LETTERS.index(one)
                      for one in board.letters])

        spots = REF["anchors"](board)
        out.append(["anchors", spec, len(spots)] + list(spots))

        for down_at in range(2):
            down = down_at == 1
            row = ["cross", spec, down_at]
            for cell in spots:
                allowed = REF["_cross_check"](board, cell, down, lex)
                row.append(cell)
                row.extend(1 if one in allowed else 0 for one in LETTERS)
            out.append(row)

        taken = 4 + spec % 4
        rack = "".join(sorted(ALPHABET[(spec * 3 + at * 2) % 8]
                              for at in range(taken)))
        found = REF["plays"](board, rack, lex)
        out.append(["plays", spec, len(rack)] + coded(rack)
                   + [len(found), 0])
        for slot, play in enumerate(found):
            row = ["play", spec, slot, 1 if play.down else 0, play.score,
                   len(play.laid)]
            for cell, letter in play.laid:
                row.extend((cell, LETTERS.index(letter)))
            row.append(len(play.word))
            row.extend(coded(play.word))
            row.append(len(play.words))
            for word in play.words:
                row.append(len(word))
                row.extend(coded(word))
            out.append(row)
        best = REF["best_play"](board, rack, lex)
        row = ["best", spec, -1 if best is None else found.index(best)]
        if best is not None:
            row.extend((best.score, 1 if best.down else 0))
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
