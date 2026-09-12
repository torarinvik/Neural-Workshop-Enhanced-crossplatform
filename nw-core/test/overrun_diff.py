#!/usr/bin/env python3
"""Differential harness for tasks/overrun.elisa against neural_workshop/overrun.py.

`Grade`, `GRADES`, `Wave`, `starts_of`, `words_a_minute`, `left_cell`,
`right_cell`, `deadline`, `overrun` and the six constants are module-level in
the rules module, so they are LIFTED by AST and run as themselves -- `Wave` in
particular is a NamedTuple whose properties are the arithmetic under test. The
UI half (`write`, `erase`, `_settle`, `update`, `score`) is methods on the
pyglet-owning class and is transcribed.

The bank is not lifted: it is a fetched corpus with a seed fallback, so both
sides build the same synthetic pool from a fixed recipe instead.

`letter_share` and `pace` are covered by the sweep as integer-scaled values;
the fetched sentence bank remains outside the core port.
"""
import ast
from fractions import Fraction
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "overrun.py")

WANTED_FN = {"starts_of", "words_a_minute", "left_cell", "right_cell",
             "deadline", "overrun", "grade_of"}
WANTED_CLASS = {"Grade", "Wave"}
WANTED_CONST = {"CELLS", "SHORTEST", "LONGEST", "TOP_RANK", "START_LIVES",
                "MOST_LIVES", "GRADES"}


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
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            tuples = [e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)]
            if WANTED_CONST.intersection(names + tuples):
                keep.append(node)
    space = {"math": math, "Tuple": tuple, "Sequence": list, "Optional": object,
             "NamedTuple": __import__("typing").NamedTuple,
             "_": lambda text: text}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = (WANTED_FN | WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("overrun_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Grade = REF["Grade"]
Wave = REF["Wave"]
GRADES = REF["GRADES"]
CELLS = REF["CELLS"]
START_LIVES = REF["START_LIVES"]
MOST_LIVES = REF["MOST_LIVES"]
starts_of = REF["starts_of"]
words_a_minute = REF["words_a_minute"]
left_cell = REF["left_cell"]
right_cell = REF["right_cell"]
deadline = REF["deadline"]
overrun = REF["overrun"]
grade_of = REF["grade_of"]

SETTLE_SECONDS = 0.7
LETTERS = "abcdefghijklmnopqrstuvwxyz"
PHASE = {"ready": 0, "typing": 1, "settled": 2, "done": 3}


def build_pool(sentences):
    """The synthetic bank, from the same recipe the sweep uses."""
    pool = []
    for s in range(sentences):
        words = []
        for w in range(3 + s % 6):
            width = 3 + (s * 7 + w * 5) % 8
            words.append("".join(LETTERS[(s * 13 + w * 11 + at * 3) % 26]
                                 for at in range(width)))
        pool.append(tuple(words))
    return pool


class Overrun(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self, rng, pool):
        self.rng = rng
        self.pool = pool
        self.start_rung = 1
        self.total_waves = 0
        self.adaptive = False
        self.coach = False
        self.rung = 1
        self.trial = 0
        self.wave = None
        self.cleared = 0
        self.typed = ""
        self.drift = 0.0
        self.lives = START_LIVES
        self.landed = 0
        self.missed = 0
        self.seconds = 0.0
        self.started_at = 0.0
        self.until = 0.0
        self.phase = "ready"
        self.results = []
        self.verdict_shown = None

    @property
    def verdict(self):
        if self.verdict_shown is None:
            return -1
        return 1 if self.verdict_shown[0] else 0

    @staticmethod
    def clamped(rung):
        return max(1, min(len(GRADES), rung))

    def _reset(self):
        self.trial = 0
        self.results = []
        self.wave = None
        self.cleared = 0
        self.typed = ""
        self.drift = 0.0
        self.lives = START_LIVES
        self.landed = 0
        self.missed = 0
        self.seconds = 0.0
        self.rung = self.clamped(self.start_rung)
        self.phase = "ready"
        self.verdict_shown = None

    def _deal(self):
        seed = self.rng.randrange(1 << 30)
        picker = random.Random(seed)
        words = self.pool[picker.randrange(len(self.pool))]
        return Wave(words, starts_of(words), grade_of(self.rung))

    def _next_trial(self, now):
        if self.lives <= 0 or self.trial >= self.total_waves:
            self.phase = "done"
            return
        if not self.pool:
            self.phase = "done"
            return
        made = self._deal()
        self.trial += 1
        self.wave = made
        self.cleared = 0
        self.typed = ""
        self.drift = 0.0
        self.verdict_shown = None
        self.started_at = now
        self.phase = "typing"

    def start_run(self, now):
        self._reset()
        self._next_trial(now)

    def _target(self):
        if self.wave is None or self.cleared >= len(self.wave.words):
            return ""
        return self.wave.words[self.cleared]

    def _paid(self, landed):
        if not self.coach:
            return
        self.verdict_shown = (landed, "yes" if landed else "no")

    def _paid_nothing(self):
        if not self.coach:
            return
        self.verdict_shown = None

    def write(self, letter, now):
        if self.phase != "typing" or letter not in LETTERS:
            return
        word = self._target()
        if not word or len(self.typed) >= len(word):
            self._paid_nothing()
            return
        landed = letter == word[len(self.typed)]
        self.typed += letter
        if landed:
            self.landed += 1
        else:
            self.missed += 1
        if self.typed == word:
            self.cleared += 1
            self.typed = ""
            if self.cleared >= len(self.wave.words):
                self._wave_clear(now)
                return
        self._paid(landed)

    def erase(self):
        if self.phase != "typing" or not self.typed:
            self._paid_nothing()
            return
        self.typed = self.typed[:-1]
        self._paid_nothing()

    def _wave_clear(self, now):
        self.lives = min(MOST_LIVES, self.lives + 1)
        self._settle(True, now)

    def _spoil(self, now):
        self.lives -= 1
        self._settle(False, now)

    def _settle(self, cleared, now):
        took = max(1e-6, now - self.started_at)
        self.seconds += took
        self.results.append((self.rung, cleared, self.cleared, took))
        if self.adaptive:
            self.rung = self.clamped(self.rung + (1 if cleared else -1))
        self.verdict_shown = (cleared, "")
        self.phase = "settled"
        self.until = now + SETTLE_SECONDS

    def update(self, dt, now):
        if self.phase == "typing" and self.wave is not None:
            self.drift += self.wave.grade.speed * min(dt, 0.1)
            if overrun(self.wave, self.cleared, self.drift):
                self._spoil(now)
        elif self.phase == "settled" and now >= self.until:
            self._next_trial(now)

    def score(self):
        return dict(
            waves=len(self.results),
            cleared=sum(1 for _r, done, _l, _t in self.results if done),
            lives=self.lives,
            best_rung=max((rung for rung, done, _l, _t in self.results if done),
                          default=0),
            wpm=int(round(words_a_minute(self.landed, self.seconds))),
            missed=self.missed)


def scaled(value):
    return int(round(value * 1000000.0))


def reference():
    out = []
    for rung in range(-2, 17):
        grade = grade_of(rung)
        out.append(["grade", rung, max(1, min(len(GRADES), rung)),
                    GRADES.index(grade), scaled(grade.speed)])

    for letters in range(40):
        for tenths in range(12):
            out.append(["wpm", letters, tenths,
                        scaled(words_a_minute(letters, tenths * 0.85))])

    pool = build_pool(64)

    exact_share = sum(
        (Fraction(sum(map(len, words)), len(" ".join(words)))
         for words in pool), Fraction(0)) / len(pool)
    out.append(["share", exact_share.numerator, exact_share.denominator])
    share = float(exact_share)
    out[-1].extend(scaled(12.0 * grade_of(rung).speed * share)
                   for rung in range(1, 13))

    for s in range(64):
        for grade in range(len(GRADES)):
            if (s + grade) % 5 != 0:
                continue
            words = pool[s]
            wave = Wave(words, starts_of(words), GRADES[grade])
            row = ["wave", s, grade, len(wave.words), wave.length,
                   wave.letters, wave.start_cell, scaled(wave.seconds),
                   scaled(wave.demand)]
            for at in range(len(wave.words)):
                row.extend((wave.starts[at], len(wave.words[at])))
            out.append(row)
            for cleared in range(len(wave.words) + 1):
                stop = deadline(wave, cleared)
                finite = 0 if math.isinf(stop) else 1
                row = ["lane", s, grade, cleared, finite,
                       scaled(stop) if finite else 0]
                for step in range(9):
                    drift = step * 11.0
                    row.extend((scaled(left_cell(wave, drift)),
                                scaled(right_cell(wave, cleared, drift)),
                                1 if overrun(wave, cleared, drift) else 0))
                out.append(row)

    for cfg in range(6):
        task = Overrun(random.Random(300 + cfg), pool)
        task.start_rung = 1 + cfg * 2
        task.total_waves = 4
        task.adaptive = (cfg % 2) == 0
        task.coach = (cfg % 3) != 0
        task.start_run(0.0)
        out.append(["start", cfg, PHASE[task.phase], task.trial, task.rung,
                    task.lives, len(task.wave.words), task.wave.length,
                    task.wave.letters])

        dt = 1.0 / 60.0
        now = 0.0
        tick = 0
        while task.phase != "done" and tick < 20000:
            now += dt
            task.update(dt, now)
            if task.phase == "typing" and (tick % 3) == 0:
                if (tick % 19) == 0:
                    task.erase()
                else:
                    word = task._target()
                    key = LETTERS[0]
                    if (tick % 7) == 0:
                        key = "1"          # not a letter: refused outright
                    elif word and len(task.typed) < len(word):
                        wanted = word[len(task.typed)]
                        key = (wanted if (tick % 11) != 0
                               else LETTERS[(LETTERS.index(wanted) + 1) % 26])
                    task.write(key, now)
            if (tick % 20) == 0:
                row = ["tick", cfg, tick, PHASE[task.phase], task.trial,
                       task.rung, task.lives, task.cleared, len(task.typed),
                       task.landed, task.missed, task.verdict,
                       scaled(task.drift), scaled(task.seconds),
                       len(task.wave.words) if task.wave else 0,
                       task.wave.length if task.wave else 0]
                row.extend(LETTERS.index(one) for one in task.typed)
                out.append(row)
            tick += 1

        tally = task.score()
        row = ["score", cfg, tick, tally["waves"], tally["cleared"],
               tally["lives"], tally["best_rung"], tally["wpm"],
               tally["missed"]]
        for rung, done, words, took in task.results:
            row.extend((rung, 1 if done else 0, words, scaled(took)))
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
