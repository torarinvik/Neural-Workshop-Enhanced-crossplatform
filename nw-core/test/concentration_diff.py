#!/usr/bin/env python3
"""Differential harness for tasks/concentration.elisa against ui/concentration.py.

`Card` is a module-level class, so it is LIFTED by AST and used as itself --
which matters more here than in most of these harnesses, because `seen` is
keyed on `id(card)` and only real objects have real identities. Everything else
is a method on the pyglet-owning class and is transcribed; what stays the
reference's own there is the order: one shuffle over 2n cards, and inside a
flip, `seen` read before the card is added to it.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "concentration.py")

WANTED_CLASS = {"Card"}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = [node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name in WANTED_CLASS]
    space = {"Tuple": tuple, "math": math}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = WANTED_CLASS - set(space)
    if missing:
        raise SystemExit("concentration_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Card = REF["Card"]

PHASE = {"ready": 0, "peek": 1, "playing": 2, "done": 3}


def board_room(floor, ceiling):
    return max(80.0, ceiling - floor)


def grid_shape(card_count, pairs, window_width, floor, ceiling):
    count = max(2, card_count or pairs * 2)
    room = board_room(floor, ceiling)
    aspect = max(0.2, (window_width * 0.9) / room)
    columns = max(2, min(count, int(round(math.sqrt(count * aspect)))))
    rows = int(math.ceil(count / float(columns)))
    while columns * rows - count >= rows and columns > 2:
        columns -= 1
        rows = int(math.ceil(count / float(columns)))
    return columns, rows


def layout_board(card_count, pairs, window_width, floor, ceiling):
    columns, rows = grid_shape(card_count, pairs, window_width, floor, ceiling)
    span_w = window_width * 0.9
    span_h = board_room(floor, ceiling)
    gap = max(4.0, min(span_w / columns, span_h / rows) * 0.09)
    card_w = (span_w - gap * (columns - 1)) / columns
    card_h = (span_h - gap * (rows - 1)) / rows
    side = min(card_w, card_h)
    total_w = side * columns + gap * (columns - 1)
    total_h = side * rows + gap * (rows - 1)
    left = (window_width - total_w) / 2
    top = floor + total_h + (span_h - total_h) / 2
    return dict(columns=columns, rows=rows, side=side, gap=gap, left=left, top=top)


def card_rect(plan, position):
    column = position % plan["columns"]
    row = position // plan["columns"]
    return (plan["left"] + column * (plan["side"] + plan["gap"]),
            plan["top"] - (row + 1) * plan["side"] - row * plan["gap"],
            plan["side"], plan["side"])


def card_at(plan, card_count, x, y):
    for position in range(card_count):
        probe = Card("", position)
        probe.rect = card_rect(plan, position)
        if probe.contains(x, y):
            return position
    return -1


def card_fill(face_up, matched, black_background):
    if matched:
        return (46, 170, 92, 255)
    if face_up:
        return (236, 239, 245, 255)
    if black_background:
        return (44, 50, 66, 255)
    return (86, 110, 168, 255)


class Board(object):
    """The reference's board attributes, and the methods that move them."""

    def __init__(self):
        self.pairs = 0
        self.cards = []
        self.flipped = []
        self.turns = 0
        self.lapses = 0
        self.seen = {}
        self.phase = "ready"
        self.owed = False
        self.coach = False
        self.verdict_shown = None

    @property
    def verdict(self):
        if self.verdict_shown is None:
            return -1
        return 1 if self.verdict_shown[0] else 0

    def reset(self):
        self.cards = []
        self.flipped = []
        self.turns = 0
        self.seen = {}
        self.lapses = 0
        self.phase = "ready"
        self.verdict_shown = None
        self.owed = False

    def deal(self, pairs, peek_ms, sound, rng):
        self.pairs = pairs
        cards = [Card(str(index), index)
                 for index in range(pairs) for _copy in (0, 1)]
        rng.shuffle(cards)
        self.cards = cards
        self.flipped = []
        self.turns = 0
        self.seen = {}
        self.lapses = 0
        self.verdict_shown = None
        self.owed = False
        if peek_ms > 0 and not sound:
            for card in self.cards:
                card.face_up = True
            self.phase = "peek"
        else:
            self.phase = "playing"

    def peek_over(self):
        if self.phase != "peek":
            return
        for card in self.cards:
            card.face_up = False
        self.phase = "playing"

    def _resolve(self):
        for card in self.flipped:
            if not card.matched:
                card.face_up = False
        self.flipped = []

    def _check_finished(self):
        if any(not card.matched for card in self.cards):
            return
        self.phase = "done"

    def _coach_verdict(self, good):
        if not self.coach:
            return
        if good is None:
            self.verdict_shown = None
            return
        self.verdict_shown = (good, "Pair" if good else "Forgotten")

    def _known_pair(self):
        matched = {card.index for card in self.cards if card.matched}
        return any(len(where) == 2 and index not in matched
                   for index, where in self.seen.items())

    def flip(self, card):
        if self.phase != "playing" or card.face_up or card.matched:
            return
        if len(self.flipped) >= 2:
            self._resolve()
        seen_before = id(card) in self.seen.get(card.index, ())
        card.face_up = True
        self.flipped.append(card)
        self.seen.setdefault(card.index, set()).add(id(card))
        if len(self.flipped) == 1:
            self._coach_verdict(None)
            self.owed = self._known_pair()
        else:
            self.turns += 1
            first, second = self.flipped
            if first.index == second.index:
                first.matched = second.matched = True
                self.flipped = []
                self._check_finished()
                self.owed = False
                if self.phase == "playing":
                    self._coach_verdict(True)
            else:
                lapsed = self.owed or seen_before
                if lapsed:
                    self.lapses += 1
                self._coach_verdict(False if lapsed else None)


WIDTHS = (800.0, 1280.0, 1920.0)
FLOORS = (120.0, 80.0, 200.0)
CEILINGS = (596.0, 130.0, 900.0)


def scaled(value):
    return int(round(value * 1000000.0))


def choices(board):
    return [card for card in board.cards if not card.face_up and not card.matched]


def reference():
    out = []
    for pairs in range(2, 13):
        for shape_case in range(0, 9):
            width = WIDTHS[shape_case // 3]
            floor = FLOORS[shape_case % 3]
            ceiling = CEILINGS[shape_case % 3]
            empty = grid_shape(0, pairs, width, floor, ceiling)
            plan = layout_board(pairs * 2, pairs, width, floor, ceiling)
            out.append(["grid", pairs, shape_case, empty[0], empty[1],
                        plan["columns"], plan["rows"], scaled(plan["side"]),
                        scaled(plan["gap"]), scaled(plan["left"]),
                        scaled(plan["top"])])
            row = ["rect", pairs, shape_case]
            for position in range(pairs * 2):
                row.extend(scaled(one) for one in card_rect(plan, position))
            out.append(row)

    for pairs in range(3, 9):
        for shape_case in range(0, 9):
            width = WIDTHS[shape_case // 3]
            floor = FLOORS[shape_case % 3]
            ceiling = CEILINGS[shape_case % 3]
            plan = layout_board(pairs * 2, pairs, width, floor, ceiling)
            room = board_room(floor, ceiling)
            row = ["hit", pairs, shape_case]
            for px in range(0, 11):
                for py in range(0, 7):
                    x = width * (px + 0.5) / 11.0
                    y = floor + room * (py + 0.5) / 7.0
                    row.append(card_at(plan, pairs * 2, x, y))
            out.append(row)

    for combo in range(0, 8):
        face_up = (combo % 2) == 1
        matched = ((combo // 2) % 2) == 1
        dark = (combo // 4) == 1
        out.append(["fill", combo] + list(card_fill(face_up, matched, dark)))

    board = Board()
    for pairs in range(3, 9):
        for seed in range(1, 4):
            rng = random.Random(pairs * 1000 + seed)
            board.reset()
            board.coach = (seed % 2) == 1
            peek_ms = 0 if seed == 2 else 800
            sound = seed == 3
            board.deal(pairs, peek_ms, sound, rng)
            row = ["deal", pairs, seed, len(board.cards), PHASE[board.phase]]
            for card in board.cards:
                row.extend((card.index, 1 if card.face_up else 0))
            out.append(row)

            board.peek_over()
            row = ["peeked", pairs, seed, PHASE[board.phase]]
            row.extend(1 if card.face_up else 0 for card in board.cards)
            out.append(row)

            step = 0
            playing = True
            while playing and step < 400:
                if len(board.flipped) == 2 and (step % 3) == 0:
                    board._resolve()
                picks = choices(board)
                if not picks:
                    board._resolve()
                    picks = choices(board)
                if not picks:
                    playing = False
                    continue
                card = picks[rng.randrange(len(picks))]
                position = board.cards.index(card)
                board.flip(card)
                row = ["flip", pairs, seed, step, position, board.turns,
                       board.lapses, PHASE[board.phase],
                       1 if board.owed else 0, board.verdict,
                       len(board.flipped)]
                for one in board.cards:
                    row.extend((1 if one.face_up else 0,
                                1 if one.matched else 0))
                out.append(row)
                step += 1
                if board.phase == "done":
                    playing = False

            out.append(["end", pairs, seed, step, board.turns, board.lapses,
                        PHASE[board.phase], 1 if board._known_pair() else 0])
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
