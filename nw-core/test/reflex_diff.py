#!/usr/bin/env python3
"""Differential harness for tasks/reflex.elisa against ui/reflex.py.

The four constants and the two pure functions are LIFTED out of the reference
by AST -- importing it would drag in pyglet -- so a change to MIN_SCALE or to
either adaptation rate is picked up here rather than quietly compared against a
copy. `Target.remaining` and `Target.contains` are methods on a __slots__ class
with a plain constructor, so they are lifted with the class.

The run's score is transcribed: it lives on the pyglet-owning class.
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "reflex.py")

WANTED = {"MIN_SCALE", "TIGHTEN_ON_HIT", "EASE_ON_MISS", "MIN_LIFETIME",
          "MAX_LIFETIME_FACTOR"}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if WANTED.intersection(names + tuples):
                keep.append(node)
    space = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = WANTED - set(space)
    if missing:
        raise SystemExit("reflex_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()


def remaining(born, lifetime, now):
    if lifetime <= 0:
        return 0.0
    return max(0.0, 1.0 - (now - born) / lifetime)


def is_gone(born, lifetime, now):
    return remaining(born, lifetime, now) <= REF["MIN_SCALE"]


def contains(cx, cy, side, x, y):
    half = side / 2
    return cx - half <= x <= cx + half and cy - half <= y <= cy + half


def adapt(lifetime, base, hit):
    if hit:
        return max(REF["MIN_LIFETIME"], lifetime * REF["TIGHTEN_ON_HIT"])
    return min(base * REF["MAX_LIFETIME_FACTOR"], lifetime * REF["EASE_ON_MISS"])


class Run:
    def __init__(self, base, adaptive):
        self.adaptive = adaptive
        self.base = base
        self.lifetime = base
        self.hits = self.misses = 0
        self.reactions = []

    def hit(self, reaction):
        self.hits += 1
        self.reactions.append(reaction)
        if self.adaptive:
            self.lifetime = adapt(self.lifetime, self.base, True)

    def miss(self):
        self.misses += 1
        if self.adaptive:
            self.lifetime = adapt(self.lifetime, self.base, False)

    def presented(self):
        return self.hits + self.misses

    def accuracy(self):
        shown = self.presented()
        return int(round(100.0 * self.hits / shown)) if shown else 0

    def mean_ms(self):
        if not self.reactions:
            return 0
        return int(round(1000.0 * sum(self.reactions) / len(self.reactions)))


def scaled(value):
    return int(round(value * 1000000.0))


def reference():
    out = []
    for life_step in range(1, 9):
        lifetime = life_step * 0.25
        for tick in range(0, 26):
            now = 100.0 + tick * 0.1
            out.append(["life", life_step, tick,
                        scaled(remaining(100.0, lifetime, now)),
                        1 if is_gone(100.0, lifetime, now) else 0])
    out.append(["life", 0, 0, scaled(remaining(100.0, 0.0, 100.0)),
                1 if is_gone(100.0, 0.0, 100.0) else 0])
    for step in range(0, 13):
        x = 100.0 + step * 5.0 - 30.0
        out.append(["box", step,
                    1 if contains(100.0, 50.0, 40.0, x, 50.0) else 0,
                    1 if contains(100.0, 50.0, 40.0, 100.0, x - 50.0) else 0])
    for pattern in range(0, 4):
        for base_step in range(1, 5):
            base = base_step * 0.5
            run = Run(base, True)
            for step in range(40):
                hit = (True if pattern == 0 else
                       False if pattern == 1 else
                       step % 2 == 0 if pattern == 2 else
                       step % 3 != 0)
                if hit:
                    run.hit(0.2 + step * 0.01)
                else:
                    run.miss()
            out.append(["adapt", pattern, base_step, scaled(run.lifetime),
                        run.hits, run.misses, run.presented(),
                        run.accuracy(), run.mean_ms()])
    steady = Run(1.0, False)
    steady.hit(0.5)
    steady.miss()
    out.append(["steady", scaled(steady.lifetime), steady.accuracy(),
                steady.mean_ms()])
    empty = Run(1.0, True)
    out.append(["empty", empty.presented(), empty.accuracy(), empty.mean_ms()])
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
