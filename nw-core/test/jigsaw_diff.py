#!/usr/bin/env python3
"""Differential harness for tasks/jigsaw.elisa against ui/jigsaw.py.

`scramble`, `minimum_swaps` and the five constants are module-level, so they
are LIFTED by AST and run as themselves -- `minimum_swaps` in particular, since
the par it computes is what green means. `above_the_band` comes from
ui/verdict.py the same way. The run machinery is methods on the pyglet-owning
class and is transcribed.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "original-neural-workshop-enhanced" / "neural_workshop" / "ui"
SOURCE = UI / "jigsaw.py"
VERDICT = UI / "verdict.py"

WANTED_FN = {"scramble", "minimum_swaps"}
WANTED_CONST = {"SMALLEST_SIDE", "LARGEST_SIDE", "SEAM", "GROW_AT", "SHRINK_AT"}


def lift(source, want_fn, want_class, want_const, extra=None):
    tree = ast.parse(source.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in want_fn:
            keep.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in want_class:
            keep.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in want_const:
                keep.append(node)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if want_const.intersection(names + tuples):
                keep.append(node)
    typing = __import__("typing")
    space = {"math": math, "random": random, "Tuple": typing.Tuple,
             "Optional": typing.Optional, "Dict": typing.Dict,
             "List": typing.List, "NamedTuple": typing.NamedTuple,
             "_": lambda text: text}
    space.update(extra or {})
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(source), "exec"),
         space)
    missing = (want_fn | want_class | want_const) - set(space)
    if missing:
        raise SystemExit("jigsaw_diff: could not lift %s from %s"
                         % (sorted(missing), source.name))
    return space


REF = lift(SOURCE, WANTED_FN, set(), WANTED_CONST)
BAND = lift(VERDICT, {"band_rows", "above_the_band"}, set(),
            {"BAND_TOP", "CLEARANCE"}, extra={"pixel_size": lambda: (0, 0)})

scramble = REF["scramble"]
minimum_swaps = REF["minimum_swaps"]
SMALLEST_SIDE, LARGEST_SIDE = REF["SMALLEST_SIDE"], REF["LARGEST_SIDE"]
SEAM = REF["SEAM"]
GROW_AT, SHRINK_AT = REF["GROW_AT"], REF["SHRINK_AT"]
BAND_TOP = BAND["BAND_TOP"]
CLEARANCE = BAND["CLEARANCE"]

DEFAULT_WINDOW_HEIGHT = 684
PHASE = {"ready": 0, "solving": 1, "solved": 2, "done": 3}


def above_the_band(height, y):
    return max(int(y), int(height) - int(height * BAND_TOP) + CLEARANCE)


def from_bottom_edge(height, from_edge):
    return int(from_edge * (height / DEFAULT_WINDOW_HEIGHT))


def from_top_edge(height, from_edge):
    return int(height - from_edge * height / DEFAULT_WINDOW_HEIGHT)


class Jigsaw(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self, rng):
        self.rng = rng
        self.start_side = SMALLEST_SIDE
        self.total_puzzles = 0
        self.adaptive = False
        self.preview = False
        self.side = SMALLEST_SIDE
        self.trial_side = SMALLEST_SIDE
        self.puzzle = 0
        self.order = []
        self.par = 0
        self.swaps = 0
        self.picked = None
        self.started_at = 0.0
        self.feedback_until = 0.0
        self.phase = "ready"
        self.results = []
        self.verdict_shown = None
        self.window_width = 912.0
        self.window_height = 684.0

    @property
    def verdict(self):
        if self.verdict_shown is None:
            return -1
        return 1 if self.verdict_shown[0] else 0

    @staticmethod
    def clamped(side):
        return max(SMALLEST_SIDE, min(LARGEST_SIDE, side))

    def _canvas(self):
        top = from_top_edge(self.window_height, 96)
        bottom = above_the_band(self.window_height,
                                from_bottom_edge(self.window_height, 56))
        return (self.window_width * 0.04, bottom,
                self.window_width * 0.92, max(40.0, top - bottom))

    def _board_rect(self):
        left, bottom, width, height = self._canvas()
        room = width * (0.72 if self.preview else 1.0)
        size = min(room, height)
        return (left + (room - size) / 2, bottom + (height - size) / 2, size)

    def _preview_rect(self):
        left, bottom, width, height = self._canvas()
        size = min(width * 0.24, height * 0.5)
        return (left + width - size, bottom + height - size, size)

    def _tile_rects(self):
        board_left, board_bottom, size = self._board_rect()
        span = (size - SEAM * (self.trial_side - 1)) / self.trial_side
        rects = []
        for position in range(self.trial_side * self.trial_side):
            row, column = divmod(position, self.trial_side)
            left = board_left + column * (span + SEAM)
            top = board_bottom + size - row * (span + SEAM)
            rects.append((left, top - span, span, span))
        return rects

    def _at(self, x, y):
        for position, (left, bottom, span, height) in enumerate(self._tile_rects()):
            if left <= x <= left + span and bottom <= y <= bottom + height:
                return position
        return None

    def _reset(self):
        self.puzzle = 0
        self.results = []
        self.order = []
        self.picked = None
        self.phase = "ready"
        self.verdict_shown = None

    def start_run(self, now):
        self._reset()
        self.side = self.clamped(self.start_side)
        self._next_puzzle(now)

    def _next_puzzle(self, now):
        if self.puzzle >= self.total_puzzles:
            self.phase = "done"
            self.order = []
            return
        self.puzzle += 1
        self.trial_side = self.side
        self.order = scramble(self.trial_side, self.rng)
        self.par = minimum_swaps(self.order)
        self.swaps = 0
        self.picked = None
        self.verdict_shown = None
        self.started_at = now
        self.phase = "solving"

    def pick(self, position, now):
        if self.phase != "solving" or not 0 <= position < len(self.order):
            return
        if self.picked is None:
            self.picked = position
        elif self.picked == position:
            self.picked = None
        else:
            self.order[self.picked], self.order[position] = \
                self.order[position], self.order[self.picked]
            self.swaps += 1
            self.picked = None
            if all(tile == where for where, tile in enumerate(self.order)):
                self._solved(now)

    def _solved(self, now):
        took = now - self.started_at
        efficiency = self.par / max(self.par, self.swaps)
        self.results.append((self.trial_side, efficiency, took))
        if self.adaptive:
            if efficiency >= GROW_AT:
                self.side = self.clamped(self.side + 1)
            elif efficiency < SHRINK_AT:
                self.side = self.clamped(self.side - 1)
        self.phase = "solved"
        self.feedback_until = now + 1.6
        self.verdict_shown = (self.swaps <= self.par, "")

    def update(self, now):
        if self.phase == "solved" and now >= self.feedback_until:
            self._next_puzzle(now)

    def score(self):
        puzzles = len(self.results)
        return {
            "puzzles": puzzles,
            "efficiency": int(round(100 * sum(eff for _s, eff, _t in self.results)
                                    / puzzles)) if puzzles else 0,
            "mean_seconds": (sum(took for _s, _e, took in self.results)
                             / puzzles) if puzzles else 0.0,
            "best_side": max((side for side, _e, _t in self.results), default=0),
        }


WIDTHS = (912.0, 640.0, 1366.0, 1101.0)
HEIGHTS = (684.0, 480.0, 768.0, 617.0)


def scaled(value):
    return int(round(value * 1000000.0))


def reference():
    out = []
    for want in range(14):
        out.append(["clamp", want, max(SMALLEST_SIDE, min(LARGEST_SIDE, want))])

    for side in range(2, 11):
        seeds = 40 if side < 4 else 6
        for seed in range(1, seeds + 1):
            rng = random.Random(side * 1000 + seed)
            order = scramble(side, rng)
            out.append(["scramble", side, seed, minimum_swaps(order)] + list(order))

    task = Jigsaw(random.Random(0))
    for size in range(4):
        for preview_on in range(2):
            task.preview = preview_on == 1
            task.window_width = WIDTHS[size]
            task.window_height = HEIGHTS[size]
            left, bottom, width, height = task._canvas()
            b_left, b_bottom, b_size = task._board_rect()
            p_left, p_bottom, p_size = task._preview_rect()
            out.append(["layout", size, preview_on, scaled(left), scaled(bottom),
                        scaled(width), scaled(height), scaled(b_left),
                        scaled(b_bottom), scaled(b_size), scaled(p_left),
                        scaled(p_bottom), scaled(p_size)])
            for side in range(2, 11):
                task.trial_side = side
                row = ["tiles", size, preview_on, side]
                for one in task._tile_rects():
                    row.extend(scaled(cell) for cell in one)
                out.append(row)
                row = ["hit", size, preview_on, side]
                for px in range(13):
                    for py in range(9):
                        x = task.window_width * (px + 0.5) / 13.0
                        y = task.window_height * (py + 0.5) / 9.0
                        found = task._at(x, y)
                        row.append(-1 if found is None else found)
                out.append(row)

    for cfg in range(8):
        task = Jigsaw(random.Random(600 + cfg))
        task.start_side = 2 + (cfg % 4)
        task.total_puzzles = 4
        task.adaptive = (cfg % 2) == 0
        task.preview = (cfg % 3) != 0
        task.start_run(0.0)
        out.append(["start", cfg, PHASE[task.phase], task.puzzle,
                    task.trial_side, task.par] + list(task.order))

        waste_every = 4 + cfg
        dt = 1.0 / 30.0
        now = 0.0
        step = 0
        while task.phase != "done" and step < 4000:
            now += dt
            task.update(now)
            if task.phase == "solving":
                count = task.trial_side * task.trial_side
                if task.picked is None:
                    first = -1
                    for at in range(count):
                        if first < 0 and task.order[at] != at:
                            first = at
                    task.pick(first, now)
                else:
                    held = task.picked
                    target = task.order[held]
                    if (step % waste_every) == 0:
                        target = (held + 1 + step % count) % count
                    task.pick(target, now)
            if (step % 3) == 0:
                row = ["step", cfg, step, PHASE[task.phase], task.puzzle,
                       task.trial_side, task.side, task.par, task.swaps,
                       -1 if task.picked is None else task.picked, task.verdict]
                row.extend(task.order[:task.trial_side * task.trial_side])
                out.append(row)
            step += 1

        tally = task.score()
        row = ["score", cfg, step, tally["puzzles"], tally["efficiency"],
               scaled(tally["mean_seconds"]), tally["best_side"]]
        for side, efficiency, took in task.results:
            row.extend((side, scaled(efficiency), scaled(took)))
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
