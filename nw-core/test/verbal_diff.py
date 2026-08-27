#!/usr/bin/env python3
"""Differential harness for tasks/verbal.elisa against verbal.py + ui/verbal.py.

The corpus is a Parquet dataset on disk, so `QuestionBank._open`/`_row` cannot
run here at all. What CAN run as itself is the part under test: `_question`,
the displayable guard, is LIFTED by AST and fed synthetic rows built to the
same recipe the sweep uses -- strings of the right length rather than real
prose, because the guard measures lengths and nothing else. `draw` is
transcribed around it (it is a method on the bank, which owns the file), and so
is the run machinery from ui/verbal.py.
"""
import ast
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
SOURCE = PKG / "verbal.py"

WANTED_CLASS = {"Question", "QuestionBank"}
WANTED_CONST = {"MAX_CHOICES", "MAX_PROMPT", "MAX_CHOICE"}


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
            flat = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if WANTED_CONST.intersection(flat):
                keep.append(node)
    typing = __import__("typing")
    space = {"dataclass": __import__("dataclasses").dataclass,
             "Path": Path, "os": __import__("os"),
             "Callable": typing.Callable, "List": typing.List,
             "Optional": typing.Optional, "Sequence": typing.Sequence,
             "Type": typing.Type,
             "DatasetUnavailable": type("DatasetUnavailable", (RuntimeError,), {}),
             "dataset_root": lambda root=None: Path("."),
             "_parquet_file_class": lambda: object}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"), space)
    missing = (WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("verbal_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Question = REF["Question"]
QuestionBank = REF["QuestionBank"]
MAX_CHOICES = REF["MAX_CHOICES"]
MAX_PROMPT = REF["MAX_PROMPT"]
MAX_CHOICE = REF["MAX_CHOICE"]

PHASE = {"ready": 0, "asking": 1, "judged": 2, "done": 3, "unavailable": 4}


def build_bank(rows):
    """The recipe both sides build their bank from, as real corpus rows."""
    made = []
    for r in range(rows):
        count = 1 + r % 6
        answer = count - 1 if (r % 3) == 0 else r % 7
        choices = []
        for slot in range(count):
            width = 0 if (r % 23) == 0 and slot == 1 else 255 + (r * 3 + slot) % 12
            choices.append("x" * width)
        made.append({
            "language": "de" if (r % 13) == 0 else "en",
            "answer": "no" if (r % 17) == 0 else str(answer),
            "choices": choices,
            "prompt": "p" * (1395 + (r % 4) * 4),
            "answer_text": "", "explanation": "", "task_type": "",
        })
    return made


def barren_bank(rows):
    return [{"language": "de", "answer": "0", "choices": ["xxxxx"] * 3,
             "prompt": "pppppppppp", "answer_text": "", "explanation": "",
             "task_type": ""} for _r in range(rows)]


def draw(rows, rng):
    """`QuestionBank.draw`, around the reference's own `_question`."""
    for _attempt in range(256):
        index = rng.randrange(len(rows))
        question = QuestionBank._question(rows[index])
        if question is None:
            continue
        order = list(range(len(question.choices)))
        rng.shuffle(order)
        return index, len(question.choices), order.index(question.answer)
    return None


class Verbal(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self, rows, rng):
        self.rows = rows
        self.rng = rng
        self.total_trials = 0
        self.trial = 0
        self.choice = 0
        self.answered = None
        self.question = None
        self.started_at = 0.0
        self.phase = "ready"
        self.results = []
        self.verdict_shown = None

    @property
    def verdict(self):
        if self.verdict_shown is None:
            return -1
        return 1 if self.verdict_shown[0] else 0

    def _reset(self):
        self.question = None
        self.choice = 0
        self.answered = None
        self.trial = 0
        self.results = []
        self.phase = "ready"
        self.verdict_shown = None

    def _next_trial(self, now):
        if self.trial >= self.total_trials:
            self.question = None
            self.phase = "done"
            return
        made = draw(self.rows, self.rng)
        if made is None:
            self.question = None
            self.phase = "unavailable"
            return
        self.trial += 1
        self.question = made
        self.choice = 0
        self.answered = None
        self.verdict_shown = None
        self.started_at = now
        self.phase = "asking"

    def start_run(self, now):
        self._reset()
        self._next_trial(now)

    def move(self, step):
        if self.phase == "asking" and self.question is not None:
            self.choice = (self.choice + step) % self.question[1]

    def choose(self, number, now):
        if self.phase != "asking" or self.question is None:
            return
        if not 0 <= int(number) < self.question[1]:
            return
        self.choice = int(number)
        right = self.choice == self.question[2]
        self.answered = self.choice
        self.results.append((right, now - self.started_at))
        self.verdict_shown = (right, "")
        self.phase = "judged"

    def submit(self, now):
        if self.phase == "asking":
            self.choose(self.choice, now)

    def score(self):
        return {"asked": len(self.results),
                "right": sum(1 for right, _s in self.results if right),
                "seconds": int(sum(s for _r, s in self.results))}


def scaled(value):
    return int(round(value * 1000000.0))


def reference():
    out = []
    rows = build_bank(400)

    for row in range(400):
        question = QuestionBank._question(rows[row])
        out.append(["row", row, 0 if question is None else 1,
                    len(rows[row]["choices"]),
                    int(rows[row]["answer"]) if rows[row]["answer"].isdigit()
                    else -1])

    for seed in range(1, 25):
        rng = random.Random(seed * 31)
        made_row = ["draw", seed]
        for _pull in range(12):
            made = draw(rows, rng)
            if made is None:
                made_row.extend((0, -1, 0, 0))
            else:
                made_row.extend((1, made[0], made[1], made[2]))
        out.append(made_row)

    barren = barren_bank(8)
    made = draw(barren, random.Random(99))
    out.append(["barren", 0 if made is None else 1,
                -1 if made is None else made[0]])

    for cfg in range(10):
        task = Verbal(rows, random.Random(800 + cfg))
        task.total_trials = 6
        task.start_run(0.0)
        out.append(["start", cfg, PHASE[task.phase], task.trial,
                    -1 if task.question is None else task.question[0],
                    0 if task.question is None else task.question[1],
                    0 if task.question is None else task.question[2]])

        now = 0.0
        step = 0
        while task.phase not in ("done", "unavailable") and step < 400:
            now += 0.25
            if task.phase == "asking":
                if (step % 4) != 3:
                    task.move(1 if (step % 3) != 2 else -2)
                elif (step % 8) == 3:
                    task.choose(task.question[2], now)
                else:
                    task.submit(now)
            elif task.phase == "judged":
                task._next_trial(now)
            out.append(["step", cfg, step, PHASE[task.phase], task.trial,
                        task.choice,
                        -1 if task.answered is None else task.answered,
                        task.verdict,
                        -1 if task.question is None else task.question[0],
                        0 if task.question is None else task.question[1],
                        0 if task.question is None else task.question[2]])
            step += 1

        tally = task.score()
        row = ["score", cfg, step, PHASE[task.phase], tally["asked"],
               tally["right"], tally["seconds"]]
        for right, seconds in task.results:
            row.extend((1 if right else 0, scaled(seconds)))
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
