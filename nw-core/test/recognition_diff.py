#!/usr/bin/env python3
"""Differential harness for tasks/recognition.elisa against ui/recognition.py.

`Trial` and the two answer constants are module-level, so they are LIFTED by
AST and used as themselves -- which keeps `(choice == SEEN) == trial.repeat`
the reference's own expression rather than a retyped one. `build_run` and the
phase machine are methods on the pyglet-owning class and are transcribed; what
stays the reference's own there is the draw order, one `randrange(100)` per
position whether or not anything is eligible.

The geometry comes from geometry.py's reference-window scaling, transcribed
against an explicit window size because the originals read a live window.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "recognition.py")

WANTED_CLASS = {"Trial"}
WANTED_CONST = {"SEEN", "NEW"}


def lifted():
    tree = ast.parse(SOURCE.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in WANTED_CLASS:
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
    space = {"NamedTuple": __import__("typing").NamedTuple, "math": math}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = (WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("recognition_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Trial = REF["Trial"]
SEEN = REF["SEEN"]
NEW = REF["NEW"]

DEFAULT_WINDOW_WIDTH = 912
DEFAULT_WINDOW_HEIGHT = 684

PHASE = {"ready": 0, "showing": 1, "hidden": 2, "feedback": 3, "done": 4}
CHOICE = {0: NEW, 1: SEEN}


def width_center(width):
    return int(width / 2)


def height_center(height):
    return int(height / 2)


def from_bottom_edge(height, from_edge):
    return int(from_edge * (height / DEFAULT_WINDOW_HEIGHT))


def stage_rect(width, height):
    side = min(width * 0.5, height * 0.5)
    return (float(width_center(width)),
            height_center(height) + height * 0.04, side)


def button_rects(width, height):
    button_w = min(width * 0.24, width / 3.2)
    button_h = max(40.0, height * 0.075)
    gap = width * 0.04
    bottom = from_bottom_edge(height, 90)
    left = (width - (button_w * 2 + gap)) / 2
    return [(left, bottom, button_w, button_h, SEEN),
            (left + button_w + gap, bottom, button_w, button_h, NEW)]


def button_hit(width, height, x, y):
    for left, bottom, box_w, box_h, choice in button_rects(width, height):
        if left <= x <= left + box_w and bottom <= y <= bottom + box_h:
            return 1 if choice == SEEN else 0
    return -1


class Task(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self):
        self.total_trials = 0
        self.min_lag = 0
        self.repeat_percent = 0
        self.study_ms = 0
        self.feedback = False
        self.sound = False
        self.trials = []
        self.index = 0
        self.answers = []
        self.phase = "ready"
        self.shown_at = 0.0
        self.feedback_until = 0.0
        self.last_correct = None

    def reset(self):
        self.trials = []
        self.answers = []
        self.index = 0
        self.phase = "ready"
        self.last_correct = None

    def needed_items(self):
        return max(2, self.total_trials)

    def build_run(self, available, rng):
        fresh = list(range(min(available, self.needed_items())))
        if len(fresh) < 2:
            return []
        trials = []
        shown = []
        repeated = set()
        next_fresh = 0
        for position in range(self.total_trials):
            eligible = [path for when, path in shown
                        if position - when >= self.min_lag
                        and path not in repeated]
            wants_repeat = rng.randrange(100) < self.repeat_percent
            if wants_repeat and eligible:
                path = rng.choice(eligible)
                repeated.add(path)
                trials.append(Trial(path, True))
            elif next_fresh < len(fresh):
                path = fresh[next_fresh]
                next_fresh += 1
                shown.append((position, path))
                trials.append(Trial(path, False))
            elif eligible:
                path = rng.choice(eligible)
                repeated.add(path)
                trials.append(Trial(path, True))
            else:
                break
        return trials

    def current(self):
        if 0 <= self.index < len(self.trials):
            return self.trials[self.index]
        return None

    def _finish(self):
        self.phase = "done"

    def _present(self, now):
        trial = self.current()
        if trial is None:
            self._finish()
            return
        self.phase = "showing"
        self.shown_at = now

    def start_run(self, available, now, rng):
        trials = self.build_run(available, rng)
        if not trials:
            self.phase = "ready"
            return False
        self.trials = trials
        self.index = 0
        self.answers = []
        self.last_correct = None
        self._present(now)
        return True

    def answer(self, choice, now):
        trial = self.current()
        if trial is None or self.phase not in ("showing", "hidden"):
            return
        self.answers.append((trial, choice))
        self.last_correct = (choice == SEEN) == trial.repeat
        self.index += 1
        if self.feedback:
            self.phase = "feedback"
            self.feedback_until = now + 0.35
        else:
            self._present(now)

    def update(self, now):
        if self.phase == "feedback" and now >= self.feedback_until:
            self._present(now)
        elif (self.phase == "showing" and self.study_ms > 0
                and not self.sound
                and now - self.shown_at >= self.study_ms / 1000.):
            self.phase = "hidden"

    def score(self):
        hits = misses = false_alarms = correct_rejections = 0
        for trial, choice in self.answers:
            if trial.repeat:
                if choice == SEEN:
                    hits += 1
                else:
                    misses += 1
            elif choice == SEEN:
                false_alarms += 1
            else:
                correct_rejections += 1
        answered = len(self.answers)
        correct = hits + correct_rejections
        return dict(hits=hits, misses=misses, false_alarms=false_alarms,
                    correct_rejections=correct_rejections,
                    repeats=hits + misses, answered=answered,
                    accuracy=int(round(100. * correct / answered)) if answered else 0)


WIDTHS = (912.0, 640.0, 1366.0, 1920.0, 1101.0)
HEIGHTS = (684.0, 480.0, 768.0, 1080.0, 617.0)
TRIALS = (2, 6, 12, 24)
PERCENTS = (0, 30, 60, 100)
AVAILABLE = (2, 5, 30)


def scaled(value):
    return int(round(value * 1000000.0))


def reference():
    out = []
    for size in range(5):
        width = WIDTHS[size]
        height = HEIGHTS[size]
        stage = stage_rect(width, height)
        out.append(["stage", size] + [scaled(one) for one in stage])
        for which, box in enumerate(button_rects(width, height)):
            out.append(["button", size, which,
                        1 if box[4] == SEEN else 0,
                        scaled(box[0]), scaled(box[1]),
                        scaled(box[2]), scaled(box[3])])
        row = ["hit", size]
        for px in range(13):
            for py in range(9):
                x = width * (px + 0.5) / 13.0
                y = height * (py + 0.5) / 9.0
                row.append(button_hit(width, height, x, y))
        out.append(row)

    task = Task()
    for cfg in range(24):
        rng = random.Random(100 + cfg)
        task.reset()
        task.total_trials = TRIALS[cfg % 4]
        task.min_lag = 1 + ((cfg // 4) % 3)
        task.repeat_percent = PERCENTS[(cfg // 3) % 4]
        task.study_ms = 0 if (cfg % 5) == 0 else 100
        task.feedback = (cfg % 2) == 0
        task.sound = (cfg % 7) == 0
        available = AVAILABLE[(cfg // 8) % 3]

        ok = task.start_run(available, 0.0, rng)
        row = ["plan", cfg, 1 if ok else 0, len(task.trials),
               PHASE[task.phase], task.needed_items()]
        for trial in task.trials:
            row.extend((trial.path, 1 if trial.repeat else 0))
        out.append(row)

        wait = 3 + (cfg % 4)
        held = 0
        now = 0.0
        step = 0
        while task.phase != "done" and step < 2000:
            now += 0.05
            task.update(now)
            out.append(["tick", cfg, step, PHASE[task.phase], task.index,
                        len(task.answers)])
            if task.phase in ("showing", "hidden"):
                held += 1
                if held >= wait:
                    held = 0
                    trial = task.current()
                    item = trial.path if trial is not None else -1
                    said = 1 if ((step * 7 + item * 3) % 5) < 2 else 0
                    task.answer(CHOICE[said], now)
                    out.append(["ans", cfg, step, item, said,
                                PHASE[task.phase],
                                -1 if task.last_correct is None
                                else (1 if task.last_correct else 0),
                                task.index, len(task.answers)])
            step += 1

        tally = task.score()
        out.append(["score", cfg, step, tally["hits"], tally["misses"],
                    tally["false_alarms"], tally["correct_rejections"],
                    tally["repeats"], tally["answered"], tally["accuracy"]])
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
