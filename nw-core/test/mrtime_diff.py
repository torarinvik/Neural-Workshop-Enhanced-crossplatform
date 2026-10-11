#!/usr/bin/env python3
"""Differential harness for tasks/mrtime.elisa against ui/mrtime.py.

`Rung`, `RUNGS`, `Mark`, `KINDS`, `rung_at`, `tolerance` and the seven
constants are module-level, so they are LIFTED by AST and run as themselves --
`tolerance` in particular, since the band is the whole of the difficulty.
`band_rows`/`above_the_band` come from ui/verdict.py the same way. The run
machinery is methods on the pyglet-owning class and is transcribed.

`quantity` is included as a small formatting stream as well; the task owns the
rung ladder, while the scene owns where the label is drawn.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "original-neural-workshop-enhanced" / "neural_workshop" / "ui"
SOURCE = UI / "mrtime.py"
VERDICT = UI / "verdict.py"

WANTED_FN = {"rung_at", "tolerance"}
WANTED_CLASS = {"Rung", "Mark"}
WANTED_CONST = {"RUNGS", "KINDS", "MIN_RUNG", "MAX_RUNG", "MIN_PRODUCE",
                "FEEDBACK_SECONDS", "LATE_GRACE", "MAX_ANSWER", "EPSILON",
                "RECALL", "PRODUCE", "BOTH",
                # KINDS is built from these, so the tuple assign has to come
                # along or the lifted module cannot evaluate it.
    "CIRCLE", "TRIANGLE", "SQUARE", "PENTAGON", "STAR", "CROSS"}


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
    # The real typing names, not stand-ins: `band_rows` is annotated
    # `Optional[int]`, and a lifted subset has no `from __future__` line to
    # keep annotations unevaluated.
    space = {"math": math, "Tuple": typing.Tuple, "Optional": typing.Optional,
             "Dict": typing.Dict, "List": typing.List,
             "NamedTuple": typing.NamedTuple, "_": lambda text: text}
    space.update(extra or {})
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(source), "exec"),
         space)
    missing = (want_fn | want_class | want_const) - set(space)
    if missing:
        raise SystemExit("mrtime_diff: could not lift %s from %s"
                         % (sorted(missing), source.name))
    return space


REF = lift(SOURCE, WANTED_FN, WANTED_CLASS, WANTED_CONST)
BAND = lift(VERDICT, {"band_rows", "above_the_band"}, set(), {"BAND_TOP", "CLEARANCE"},
            extra={"pixel_size": lambda: (0, 0)})

Rung = REF["Rung"]
RUNGS = REF["RUNGS"]
Mark = REF["Mark"]
KINDS = REF["KINDS"]
MIN_RUNG, MAX_RUNG = REF["MIN_RUNG"], REF["MAX_RUNG"]
MIN_PRODUCE = REF["MIN_PRODUCE"]
FEEDBACK_SECONDS = REF["FEEDBACK_SECONDS"]
LATE_GRACE = REF["LATE_GRACE"]
MAX_ANSWER = REF["MAX_ANSWER"]
EPSILON = REF["EPSILON"]
RECALL, PRODUCE, BOTH = REF["RECALL"], REF["PRODUCE"], REF["BOTH"]
rung_at = REF["rung_at"]
tolerance = REF["tolerance"]
rung_per_second = lambda number: rung_at(number).per_second
rung_short = lambda number: rung_at(number).short
BAND_TOP = BAND["BAND_TOP"]
CLEARANCE = BAND["CLEARANCE"]

DEFAULT_WINDOW_WIDTH = 912
DEFAULT_WINDOW_HEIGHT = 684

PHASE = {"ready": 0, "showing": 1, "waiting": 2, "asking": 3, "counting": 4,
         "feedback": 5, "done": 6}
MODE_INDEX = {RECALL: 0, PRODUCE: 1, BOTH: 2}
MODE_BY_INDEX = {0: RECALL, 1: PRODUCE, 2: BOTH}


def band_first_row(height):
    return int(height * BAND_TOP)


def above_the_band(height, y):
    return max(int(y), int(height) - band_first_row(height) + CLEARANCE)


def from_bottom_edge(height, from_edge):
    return int(from_edge * (height / DEFAULT_WINDOW_HEIGHT))


def from_top_edge(height, from_edge):
    return int(height - from_edge * height / DEFAULT_WINDOW_HEIGHT)


def scale_to_height(height, fraction):
    return int(fraction * height / DEFAULT_WINDOW_HEIGHT)


class MrTime(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self, rng):
        self.rng = rng
        self.mode = RECALL
        self.start_rung = 1
        self.total_trials = 0
        self.max_gap_ms = 0
        self.flash_ms = 0
        self.adaptive = False
        self.rung = 1
        self.trial = 0
        self.correct = 0
        self.trial_mode = RECALL
        self.mark = None
        self.answer_text = ""
        self.appeared_at = 0.0
        self.ask_at = 0.0
        self.deadline = 0.0
        self.feedback_until = 0.0
        self.target = 0.0
        self.interval = 0.0
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

    def canvas(self):
        width = self.window_width * 0.78
        bottom = above_the_band(self.window_height,
                                from_bottom_edge(self.window_height, 176))
        top = from_top_edge(self.window_height, 104)
        height = max(float(scale_to_height(self.window_height, 80)), top - bottom)
        return (self.window_width - width) / 2, float(bottom), width, height

    def _to_pixels(self, x, y):
        left, bottom, width, height = self.canvas()
        return left + x * width, bottom + y * height

    def _radius_pixels(self, mark):
        _left, _bottom, width, height = self.canvas()
        return mark.radius * min(width, height)

    def _random_mark(self):
        radius = self.rng.uniform(0.10, 0.20)
        return Mark(kind=self.rng.choice(KINDS),
                    x=self.rng.uniform(radius, 1.0 - radius),
                    y=self.rng.uniform(radius, 1.0 - radius),
                    radius=radius, turn=self.rng.uniform(0.0, math.tau))

    def _deal_mode(self):
        if self.mode == BOTH:
            return self.rng.choice((RECALL, PRODUCE))
        return PRODUCE if self.mode == PRODUCE else RECALL

    def _reset(self):
        self.mark = None
        self.answer_text = ""
        self.trial = 0
        self.correct = 0
        self.results = []
        self.phase = "ready"
        self.rung = max(MIN_RUNG, min(MAX_RUNG, self.start_rung))
        self.verdict_shown = None

    def start_run(self, now):
        self._reset()
        self._next_trial(now)

    def _next_trial(self, now):
        if self.trial >= self.total_trials:
            self.phase = "done"
            self.mark = None
            return
        self.trial += 1
        self.answer_text = ""
        self.mark = self._random_mark()
        self.trial_mode = self._deal_mode()
        self.verdict_shown = None
        self.appeared_at = now
        if self.trial_mode == PRODUCE:
            per = rung_at(self.rung).per_second
            raw = self.rng.uniform(0.0, self.max_gap_ms / 1000.)
            units = max(1, int(round(raw * per)))
            if units / per < MIN_PRODUCE:
                units = int(math.ceil(MIN_PRODUCE * per))
            self.target = units / per
            self.interval = self.target
            self.deadline = now + self.target + LATE_GRACE
            self.phase = "counting"
        else:
            self.target = 0.0
            gap = self.rng.uniform(0.0, self.max_gap_ms / 1000.)
            self.ask_at = now + self.flash_ms / 1000. + gap
            self.interval = 0.0
            self.phase = "showing"

    def _ask(self, now):
        self.interval = now - self.appeared_at
        self.phase = "asking"

    def type_digit(self, digit):
        if self.phase != "asking" or len(self.answer_text) >= MAX_ANSWER:
            return
        if self.answer_text == "0" and digit != "0":
            self.answer_text = digit
        elif self.answer_text == "0" and digit == "0":
            return
        else:
            self.answer_text += digit

    def type_point(self):
        if self.phase != "asking" or len(self.answer_text) >= MAX_ANSWER:
            return
        if "." in self.answer_text:
            return
        self.answer_text = (self.answer_text or "0") + "."

    def backspace(self):
        if self.phase != "asking" or not self.answer_text:
            return
        self.answer_text = self.answer_text[:-1]

    def answer_seconds(self):
        text = self.answer_text
        if not text or text in (".", "0."):
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def submit(self, now):
        if self.phase != "asking":
            return
        answered = self.answer_seconds()
        if answered is None:
            return
        self._settle(answered, now)

    def act_now(self, now):
        if self.phase != "counting":
            return
        self._settle(now - self.appeared_at, now)

    def _adapt(self, right):
        if not self.adaptive:
            return
        self.rung = (min(MAX_RUNG, self.rung + 1) if right
                     else max(MIN_RUNG, self.rung - 1))

    def _settle(self, answered, now):
        band = tolerance(self.interval, self.rung)
        right = (answered is not None
                 and abs(answered - self.interval) <= band + EPSILON)
        self.results.append((self.trial_mode, self.interval, answered,
                             band, self.rung))
        if right:
            self.correct += 1
        self.phase = "feedback"
        self.feedback_until = now + FEEDBACK_SECONDS
        self.verdict_shown = (right, "")
        self._adapt(right)

    def mark_showing(self):
        return self.mark is not None and self.phase in ("showing", "counting")

    def mark_at(self, x, y):
        if not self.mark_showing():
            return False
        centre_x, centre_y = self._to_pixels(self.mark.x, self.mark.y)
        return math.hypot(x - centre_x, y - centre_y) <= self._radius_pixels(self.mark)

    def update(self, now):
        if self.phase == "showing" and now - self.appeared_at >= self.flash_ms / 1000.:
            self.phase = "waiting"
        if self.phase == "waiting" and now >= self.ask_at:
            self._ask(now)
        elif self.phase == "counting" and now >= self.deadline:
            self._settle(None, now)
        elif self.phase == "feedback" and now >= self.feedback_until:
            self._next_trial(now)

    def score(self):
        trials = len(self.results)
        answered = [row for row in self.results if row[2] is not None]
        shares = [abs(row[2] - row[1]) / row[1] for row in answered if row[1] > 0]
        errors = [abs(row[2] - row[1]) for row in answered]
        return {
            "trials": trials,
            "correct": self.correct,
            "accuracy": int(round(100. * self.correct / trials)) if trials else 0,
            "weber": (sum(shares) / len(shares)) if shares else 0.0,
            "mean_error_ms": (1000. * sum(errors) / len(errors)) if errors else 0.0,
            "best_rung": max((row[4] for row in self.results), default=0),
        }


WIDTHS = (912.0, 640.0, 1366.0, 1101.0)
HEIGHTS = (684.0, 480.0, 768.0, 617.0)
POINT = 10


def scaled(value):
    return int(round(value * 1000000.0))


def field_cells(text):
    cells = [len(text)]
    for one in text:
        cells.append(POINT if one == "." else int(one))
    return cells


def reference():
    out = []
    for number in range(-2, 10):
        rung = rung_at(number)
        row = ["rung", number, max(MIN_RUNG, min(MAX_RUNG, number)),
               scaled(rung.per_second), scaled(rung.share)]
        for step in range(13):
            interval = -1.5 + step * 0.75
            row.append(scaled(tolerance(interval, number)))
        out.append(row)

    task = MrTime(random.Random(0))
    for size in range(4):
        task.window_width = WIDTHS[size]
        task.window_height = HEIGHTS[size]
        left, bottom, width, height = task.canvas()
        out.append(["canvas", size, band_first_row(task.window_height),
                    above_the_band(task.window_height, 0.0),
                    scaled(left), scaled(bottom), scaled(width), scaled(height)])

    for rung in range(-2, 10):
        for step in range(7):
            seconds = -2.5 + step * 2.5
            reach = abs(seconds) * rung_per_second(rung)
            text = f"{reach:.2f}" if reach < 10.0 else f"{round(reach):,}"
            out.append([f"quantity|{text} {rung_short(rung)}"])

    for recipe in range(24):
        task = MrTime(random.Random(0))
        task.phase = "asking"
        task.answer_text = ""
        row = ["field", recipe]
        for press in range(18):
            what = (recipe * 5 + press * 7) % 13
            if what == 11:
                task.type_point()
            elif what == 12:
                task.backspace()
            else:
                task.type_digit(str(what % 10))
            row.extend(field_cells(task.answer_text))
        given = task.answer_seconds()
        row.append(0 if given is None else 1)
        row.append(scaled(0.0 if given is None else given))
        out.append(row)

    # Compare answer and production ACT behavior at the source's interval
    # bands: clearly short/long, exact interval, exact tolerance edges, and
    # values just beyond each edge. Exercise both controller paths at every
    # rung, including their adaptive rung changes.
    for rung in range(MIN_RUNG, MAX_RUNG + 1):
        interval = 2.0
        band = tolerance(interval, rung)
        answers = (1.0, interval - band,
                   interval - band - 2.0 * EPSILON, interval,
                   interval + band, interval + band + 2.0 * EPSILON, 3.0)
        for case, answered in enumerate(answers):
            recall = MrTime(random.Random(0))
            recall.phase = "asking"
            recall.interval = interval
            recall.rung = rung
            recall.adaptive = True
            recall.trial = 1
            recall.total_trials = 1
            recall.trial_mode = RECALL
            recall._settle(answered, 5.0)
            out.append(["boundary", 0, rung, case, scaled(answered),
                        scaled(band), recall.verdict, recall.rung])

            produce = MrTime(random.Random(0))
            produce.phase = "counting"
            produce.appeared_at = 0.0
            produce.interval = interval
            produce.target = interval
            produce.rung = rung
            produce.adaptive = True
            produce.trial = 1
            produce.total_trials = 1
            produce.trial_mode = PRODUCE
            produce.act_now(answered)
            out.append(["boundary", 1, rung, case, scaled(answered),
                        scaled(band), produce.verdict, produce.rung])

    for cfg in range(9):
        task = MrTime(random.Random(400 + cfg))
        task.mode = MODE_BY_INDEX[cfg % 3]
        task.start_rung = 1 + (cfg % 6)
        task.total_trials = 5
        task.max_gap_ms = 1200 + cfg * 400
        task.flash_ms = 150 + cfg * 30
        task.adaptive = (cfg % 2) == 0
        task.start_run(0.0)
        out.append(["start", cfg, PHASE[task.phase], task.trial,
                    MODE_INDEX[task.trial_mode], task.rung,
                    KINDS.index(task.mark.kind), scaled(task.mark.x),
                    scaled(task.mark.y), scaled(task.mark.radius),
                    scaled(task.mark.turn), scaled(task.target),
                    scaled(task.ask_at), scaled(task.deadline)])

        dt = 1.0 / 60.0
        now = 0.0
        tick = 0
        while task.phase != "done" and tick < 6000:
            now += dt
            task.update(now)
            if task.phase == "asking":
                if len(task.answer_text) < 3:
                    if len(task.answer_text) == 1:
                        task.type_point()
                    else:
                        task.type_digit(str((tick // 7) % 10))
                else:
                    task.submit(now)
            if task.phase == "counting":
                if task.trial % 3 != 0 and now - task.appeared_at >= task.target * 0.94:
                    task.act_now(now)
            if (tick % 5) == 0:
                probe = MrTime(random.Random(0))
                probe.__dict__.update(task.__dict__)
                probe.window_width, probe.window_height = 912.0, 684.0
                out.append(["tick", cfg, tick, PHASE[task.phase], task.trial,
                            MODE_INDEX[task.trial_mode], task.rung,
                            task.correct, task.verdict, len(task.answer_text),
                            scaled(task.interval), scaled(task.target),
                            1 if task.mark_showing() else 0,
                            1 if probe.mark_at(480.0, 400.0) else 0])
            tick += 1

        tally = task.score()
        row = ["score", cfg, tick, tally["trials"], tally["correct"],
               tally["accuracy"], scaled(tally["weber"]),
               scaled(tally["mean_error_ms"]), tally["best_rung"]]
        for mode, interval, answered, band, rung in task.results:
            row.extend((MODE_INDEX[mode], scaled(interval),
                        0 if answered is None else 1,
                        scaled(0.0 if answered is None else answered),
                        scaled(band), rung))
        out.append(row)

    # This is the default browser-menu route's complete 15-trial run. The
    # browser replay types zero and submits once the source has entered ASKING;
    # keep the generated stream and displayed summary comparable to the same
    # seeded run from the original MrTime controller.
    task = MrTime(random.Random(17))
    task.total_trials = 15
    task.max_gap_ms = 3000
    task.flash_ms = 400
    task.adaptive = True
    task.start_run(0.0)
    out.append(["default15-start", PHASE[task.phase], task.trial,
                MODE_INDEX[task.trial_mode], task.rung,
                KINDS.index(task.mark.kind), scaled(task.mark.x),
                scaled(task.mark.y), scaled(task.mark.radius),
                scaled(task.mark.turn), scaled(task.ask_at)])
    while task.phase != "done":
        if task.phase in ("showing", "waiting"):
            task.update(task.ask_at)
        elif task.phase == "asking":
            task.type_digit("0")
            task.submit(task.ask_at)
            mode, interval, answered, band, result_rung = task.results[-1]
            out.append(["default15-trial", task.trial, MODE_INDEX[mode],
                        scaled(interval), 0 if answered is None else 1,
                        scaled(0.0 if answered is None else answered),
                        scaled(band), result_rung, PHASE[task.phase],
                        task.rung, task.correct, len(task.results)])
        elif task.phase == "feedback":
            task.update(task.feedback_until)
    tally = task.score()
    out.append(["default15-summary", PHASE[task.phase], task.total_trials,
                tally["trials"], tally["correct"], tally["accuracy"],
                scaled(tally["weber"]), scaled(tally["mean_error_ms"]),
                tally["best_rung"]])
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
