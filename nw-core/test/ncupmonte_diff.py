#!/usr/bin/env python3
"""Differential harness for tasks/ncupmonte.elisa against ui/ncupmonte.py.

The rules are methods on a class whose constructor reaches for pyglet, so they
are transcribed here rather than lifted. What stays the reference's own is the
stream: `randrange` for the ball and `sample(range(cups), 2)` per swap, which
is the whole content of a deal.
"""
import random
import subprocess
import sys

FEWEST = 3
READY, REVEAL, SHUFFLE, GUESS, RESULT = 0, 1, 2, 3, 4


def clamp_cups(cups, most):
    return min(max(FEWEST, cups), most)


class Table:
    def __init__(self, start_cups, most_cups, adaptive, swap_count):
        self.most_cups = max(start_cups, most_cups)
        self.cups = clamp_cups(start_cups, self.most_cups)
        self.adaptive = adaptive
        self.swap_count = swap_count
        self.phase = READY
        self.order = []
        self.ball = 0
        self.guess = -1
        self.swaps = []
        self.swap_at = 0

    def place_cups(self):
        self.order = list(range(self.cups))

    def start_round(self, rng):
        self.place_cups()
        self.ball = rng.randrange(self.cups)
        self.guess = -1
        self.swaps = []
        self.swap_at = 0
        self.phase = REVEAL

    def plan_swaps(self, rng):
        count = max(1, self.swap_count + self.cups)
        self.swaps = [tuple(rng.sample(range(self.cups), 2))
                      for _swap in range(count)]
        self.swap_at = 0
        self.phase = SHUFFLE

    def settle_all(self):
        while self.swap_at < len(self.swaps):
            a, b = self.swaps[self.swap_at]
            self.order[a], self.order[b] = self.order[b], self.order[a]
            self.swap_at += 1
            if self.swap_at >= len(self.swaps):
                self.phase = GUESS

    def cup_in_slot(self, slot):
        return self.order[slot] if 0 <= slot < self.cups else -1

    def choose_cup(self, cup):
        if self.phase != GUESS:
            return False
        self.guess = cup
        self.phase = RESULT
        caught = cup == self.ball
        if self.adaptive:
            self.cups = (clamp_cups(self.cups + 1, self.most_cups) if caught
                         else clamp_cups(self.cups - 1, self.most_cups))
        self.place_cups()
        return caught


def reference():
    out = []
    for cups in range(0, 14):
        for ceiling in range(3, 12):
            out.append(["clamp", cups, ceiling, clamp_cups(cups, ceiling)])
    for cups in range(3, 10):
        for swap_count in range(-2, 5):
            for seed in range(1, 4):
                rng = random.Random(cups * 1000 + (swap_count + 2) * 100 + seed)
                table = Table(cups, 12, True, swap_count)
                table.start_round(rng)
                table.plan_swaps(rng)
                row = ["round", cups, swap_count, seed, table.ball,
                       len(table.swaps)]
                for a, b in table.swaps:
                    row.extend((a, b))
                table.settle_all()
                row.append(table.phase)
                row.extend(table.cup_in_slot(slot) for slot in range(table.cups))
                out.append(row)
    for cups in range(3, 8):
        for right in range(0, 2):
            rng = random.Random(cups * 31 + right)
            table = Table(cups, 9, True, 2)
            row = ["guess", cups, right,
                   1 if table.choose_cup(0) else 0, table.cups]
            table.start_round(rng)
            table.plan_swaps(rng)
            table.settle_all()
            pick = table.ball if right == 1 else (table.ball + 1) % table.cups
            row.extend((1 if table.choose_cup(pick) else 0, table.cups,
                        table.phase, table.guess))
            out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            print("MISMATCH line %d\n  elisa:  %s\n  python: %s" % (index, a, b))
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
