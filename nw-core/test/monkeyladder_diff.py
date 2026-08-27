#!/usr/bin/env python3
"""Differential harness for tasks/monkeyladder.elisa against ui/monkeyladder.py.

Monkey Ladder has no core module in the reference -- its rules live in the UI
file beside the drawing, inside a class that reaches for pyglet in __init__ --
so this restates the four rules the port implements and holds them against it.
Unlike hanoi's harness there is nothing liftable here: the rules ARE methods,
and a method needs the object the constructor cannot build headless.

What is compared is therefore the rules as written in that file, transcribed
once, plus `random.sample` itself, which is the real content of the deal.
"""
import random
import subprocess
import sys

SHORTEST = 2
IGNORED, RIGHT, DONE, WRONG = 0, 1, 2, 3
READY, SHOW, INPUT, RESULT = 0, 1, 2, 3


def clamp_level(level, grid):
    return min(max(SHORTEST, level), grid * grid)


class Round:
    def __init__(self, grid, start_level, adaptive):
        self.grid = grid
        self.level = clamp_level(start_level, grid)
        self.adaptive = adaptive
        self.phase = READY
        self.sequence = []
        self.next_index = 0
        self.clicked = []
        self.wrong = -1
        self.cursor_row = 0
        self.cursor_col = 0

    def start(self, rng):
        cells = list(range(self.grid * self.grid))
        count = min(self.level, len(cells))
        self.sequence = rng.sample(cells, count)
        self.next_index = 0
        self.clicked = []
        self.wrong = -1
        self.cursor_row = self.cursor_col = 0
        self.phase = SHOW

    def begin_input(self):
        if self.phase == SHOW:
            self.phase = INPUT

    def move_cursor(self, d_row, d_col):
        self.cursor_row = min(max(0, self.cursor_row + d_row), self.grid - 1)
        self.cursor_col = min(max(0, self.cursor_col + d_col), self.grid - 1)

    def cursor_cell(self):
        return self.cursor_row * self.grid + self.cursor_col

    def click(self, cell):
        if self.phase != INPUT or cell in self.clicked:
            return IGNORED
        if cell == self.sequence[self.next_index]:
            self.clicked.append(cell)
            self.next_index += 1
            if self.next_index >= len(self.sequence):
                if self.adaptive:
                    self.level = clamp_level(self.level + 1, self.grid)
                self.phase = RESULT
                return DONE
            return RIGHT
        self.wrong = cell
        if self.adaptive:
            self.level = clamp_level(self.level - 1, self.grid)
        self.phase = RESULT
        return WRONG


def reference():
    out = []
    for grid in range(2, 10):
        for level in range(0, 26):
            out.append(["clamp", grid, level, clamp_level(level, grid)])
    for grid in range(3, 10):
        for level in range(2, 9):
            for seed in range(1, 4):
                rng = random.Random(grid * 10000 + level * 100 + seed)
                round = Round(grid, level, True)
                round.start(rng)
                row = ["deal", grid, level, seed, len(round.sequence)]
                row.extend(round.sequence)
                out.append(row)
    for grid in range(3, 6):
        for miss_at in range(0, 6):
            rng = random.Random(grid * 77 + miss_at)
            round = Round(grid, 5, True)
            round.start(rng)
            row = ["walk", grid, miss_at, round.click(round.sequence[0])]
            round.begin_input()
            for step in range(len(round.sequence)):
                if round.phase == RESULT:
                    break
                right = round.sequence[step]
                cell = right if step != miss_at else (right + 1) % (grid * grid)
                row.append(round.click(cell))
            row.extend((round.phase, round.level, round.wrong,
                        len(round.clicked), round.click(round.sequence[0])))
            out.append(row)
    for grid in range(2, 7):
        round = Round(grid, 3, False)
        for step in range(12):
            d_row = 1 if step % 4 == 0 else (-1 if step % 4 == 1 else 0)
            d_col = 1 if step % 4 == 2 else (-1 if step % 4 == 3 else 0)
            round.move_cursor(d_row * (step // 4 + 1), d_col * (step // 4 + 1))
            out.append(["cursor", grid, step, round.cursor_row,
                        round.cursor_col, round.cursor_cell()])
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
