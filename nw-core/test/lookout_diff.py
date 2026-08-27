#!/usr/bin/env python3
"""Differential harness for tasks/lookout.elisa against ui/lookout.py.

`COLORS`, `FORMS`, `Cue`, `channel_match`, the two channel names and the three
timing constants are module-level, so they are LIFTED by AST and used as
themselves. `bounced` is lifted from ui/tracking.py, which is where lookout
imports it from. The flock and the run are methods on the pyglet-owning class
and are transcribed; what stays the reference's own there is the draw order --
every spot before any drifter, and inside a drifter heading, pace, colour,
form, next morph.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "original-neural-workshop-enhanced" / "neural_workshop" / "ui"
SOURCE = UI / "lookout.py"
TRACKING = UI / "tracking.py"

WANTED_FN = {"channel_match"}
WANTED_CLASS = {"Cue"}
WANTED_CONST = {"COLORS", "FORMS", "COLOR_CHANNEL", "FORM_CHANNEL",
                "FEWEST_SHAPES", "MOST_SHAPES", "DROUGHT_SECONDS",
                "REVEAL_SECONDS"}


def lift(source, want_fn, want_class, want_const):
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
    space = {"math": math, "Tuple": tuple,
             "NamedTuple": __import__("typing").NamedTuple,
             "_": lambda text: text}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(source), "exec"),
         space)
    missing = (want_fn | want_class | want_const) - set(space)
    if missing:
        raise SystemExit("lookout_diff: could not lift %s from %s"
                         % (sorted(missing), source.name))
    return space


REF = lift(SOURCE, WANTED_FN, WANTED_CLASS, WANTED_CONST)
TRACK = lift(TRACKING, {"bounced"}, set(), set())

COLORS = REF["COLORS"]
FORMS = REF["FORMS"]
Cue = REF["Cue"]
channel_match = REF["channel_match"]
bounced = TRACK["bounced"]
COLOR_CHANNEL = REF["COLOR_CHANNEL"]
FORM_CHANNEL = REF["FORM_CHANNEL"]
FEWEST_SHAPES = REF["FEWEST_SHAPES"]
MOST_SHAPES = REF["MOST_SHAPES"]
DROUGHT_SECONDS = REF["DROUGHT_SECONDS"]
REVEAL_SECONDS = REF["REVEAL_SECONDS"]

DEFAULT_WINDOW_HEIGHT = 684

PHASE = {"ready": 0, "watching": 1, "feedback": 2, "done": 3}
CHANNEL_BY_INDEX = {0: COLOR_CHANNEL, 1: FORM_CHANNEL}
WATCHING = {0: "color", 1: "form", 2: "both"}


def scale_to_height(height, fraction):
    return int(fraction * height / DEFAULT_WINDOW_HEIGHT)


def clamped(count):
    return max(FEWEST_SHAPES, min(MOST_SHAPES, count))


class Drifter(object):
    __slots__ = ("x", "y", "vx", "vy", "color", "form", "next_morph")

    def __init__(self, x, y, vx, vy, color, form, next_morph):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.form = form
        self.next_morph = next_morph


class Lookout(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self, rng):
        self.rng = rng
        self.shapes = []
        self.watching = "both"
        self.speed = 0.0
        self.morph_gap = 1.0
        self.total_cues = 0
        self.adaptive = False
        self.start_count = FEWEST_SHAPES
        self.count = FEWEST_SHAPES
        self.cue_number = 0
        self.cue = Cue(0, 0)
        self.cued_at = 0.0
        self.seen = {}
        self.hits = 0
        self.misses = 0
        self.false_alarms = 0
        self.reaction_times = []
        self.phase = "ready"
        self.until = 0.0
        self.verdict_shown = None
        self.window_width = 912.0
        self.window_height = 684.0

    @property
    def verdict(self):
        if self.verdict_shown is None:
            return -1
        return 1 if self.verdict_shown else 0

    def channels(self):
        if self.watching == "color":
            return (COLOR_CHANNEL,)
        if self.watching == "form":
            return (FORM_CHANNEL,)
        return (COLOR_CHANNEL, FORM_CHANNEL)

    def radius(self):
        return max(7.0, float(scale_to_height(self.window_height, 17)))

    def _bounds(self):
        edge_x = self.radius() / self.window_width
        edge_y = self.radius() / self.window_height
        return (edge_x + 0.01, 1.0 - edge_x - 0.01,
                edge_y + 0.11, 1.0 - edge_y - 0.17)

    def _reset(self):
        self.shapes = []
        self.cue_number = 0
        self.hits = 0
        self.misses = 0
        self.false_alarms = 0
        self.reaction_times = []
        self.seen = {}
        self.count = clamped(self.start_count)
        self.phase = "ready"
        self.verdict_shown = None

    def _fresh_drifter(self, x, y, now):
        heading = self.rng.uniform(0.0, 2 * math.pi)
        pace = self.speed * self.rng.uniform(0.5, 1.5)
        return Drifter(
            x, y, pace * math.cos(heading), pace * math.sin(heading),
            color=self.rng.randrange(len(COLORS)),
            form=self.rng.randrange(len(FORMS)),
            next_morph=now + self.rng.uniform(0.3, self.morph_gap))

    def _spawn_flock(self, now):
        self.shapes = []
        low_x, high_x, low_y, high_y = self._bounds()
        apart = 2.4 * self.radius() / self.window_height
        spots = []
        while len(spots) < self.count:
            for _attempt in range(self.count * 60):
                spot = (self.rng.uniform(low_x, high_x),
                        self.rng.uniform(low_y, high_y))
                if all((spot[0] - x) ** 2 + (spot[1] - y) ** 2
                       >= apart * apart for x, y in spots):
                    spots.append(spot)
                    if len(spots) == self.count:
                        break
            else:
                apart *= 0.8
        self.shapes = [self._fresh_drifter(x, y, now) for x, y in spots]

    def _absent_cue(self):
        candidates = [Cue(color, form)
                      for color in range(len(COLORS))
                      for form in range(len(FORMS))]
        self.rng.shuffle(candidates)
        live = self.channels()
        cue = min(candidates, key=lambda option:
                  sum(1 for s in self.shapes for channel in live
                      if channel_match(s.color, s.form, option, channel)))
        for drifter in self.shapes:
            while any(channel_match(drifter.color, drifter.form,
                                    cue, channel) for channel in live):
                if COLOR_CHANNEL in live and drifter.color == cue.color:
                    drifter.color = self.rng.randrange(len(COLORS))
                if FORM_CHANNEL in live and drifter.form == cue.form:
                    drifter.form = self.rng.randrange(len(FORMS))
        return cue

    def _next_cue(self, now):
        if self.cue_number >= self.total_cues:
            self.phase = "done"
            return
        self.cue_number += 1
        self.verdict_shown = None
        self.cue = self._absent_cue()
        self.cued_at = now
        self.seen = {channel: None for channel in self.channels()}
        self.phase = "watching"

    def start_run(self, now):
        self._reset()
        self._spawn_flock(now)
        self._next_cue(now)

    def _move(self, dt):
        low_x, high_x, low_y, high_y = self._bounds()
        aspect = self.window_height / max(1, self.window_width)
        for drifter in self.shapes:
            drifter.x += drifter.vx * dt * aspect
            drifter.y += drifter.vy * dt
            drifter.x, drifter.vx = bounced(drifter.x, drifter.vx, low_x, high_x)
            drifter.y, drifter.vy = bounced(drifter.y, drifter.vy, low_y, high_y)

    def _dry_channels(self):
        return [channel for channel in self.channels()
                if self.seen.get(channel) is None]

    def _morph(self, drifter, now):
        drifter.next_morph = now + self.rng.uniform(0.6, 1.4) * self.morph_gap
        dry = self._dry_channels()
        if (self.phase == "watching" and dry
                and now - self.cued_at > DROUGHT_SECONDS):
            channel = self.rng.choice(dry)
            if channel == COLOR_CHANNEL:
                drifter.color = self.cue.color
            else:
                drifter.form = self.cue.form
            return
        was = (drifter.color, drifter.form)
        while (drifter.color, drifter.form) == was:
            if self.rng.random() < 0.7:
                drifter.color = self.rng.randrange(len(COLORS))
            else:
                drifter.form = self.rng.randrange(len(FORMS))

    def channel_on_screen(self, channel):
        return any(channel_match(s.color, s.form, self.cue, channel)
                   for s in self.shapes)

    def update(self, dt, now):
        if self.phase == "watching":
            self._move(min(dt, 0.1))
            for drifter in self.shapes:
                if now >= drifter.next_morph:
                    self._morph(drifter, now)
            for channel in self.channels():
                present = self.channel_on_screen(channel)
                if present and self.seen[channel] is None:
                    self.seen[channel] = now
                elif not present and self.seen[channel] is not None:
                    self._miss(now)
                    return
        elif self.phase == "feedback":
            self._move(min(dt, 0.1))
            if now >= self.until:
                self._next_cue(now)

    def answer(self, channel, now):
        if self.phase != "watching" or channel not in self.channels():
            return
        hit = self.seen.get(channel) is not None
        if hit:
            self.hits += 1
            self.reaction_times.append(now - self.seen[channel])
        else:
            self.false_alarms += 1
        self._adapt(right=hit)
        self._show_feedback(hit, now)

    def _miss(self, now):
        self.misses += 1
        self._adapt(right=False)
        self._show_feedback(False, now)

    def _adapt(self, right):
        if not self.adaptive:
            return
        grown = self.count + 1 if right else self.count - 1
        self.count = clamped(grown)

    def _show_feedback(self, right, now):
        self.verdict_shown = right
        self.phase = "feedback"
        self.seen = {}
        self.until = now + REVEAL_SECONDS
        while len(self.shapes) > self.count:
            self.shapes.pop()
        low_x, high_x, low_y, high_y = self._bounds()
        while len(self.shapes) < self.count:
            self.shapes.append(self._fresh_drifter(
                self.rng.uniform(low_x, high_x),
                self.rng.uniform(low_y, high_y), now))

    def score(self):
        mean = (sum(self.reaction_times) / len(self.reaction_times)
                if self.reaction_times else 0.0)
        return dict(hits=self.hits, misses=self.misses,
                    false_alarms=self.false_alarms,
                    mean_ms=int(round(mean * 1000)),
                    most_shapes=self.count)


WIDTHS = (912.0, 640.0, 1366.0, 1101.0)
HEIGHTS = (684.0, 480.0, 768.0, 617.0)


def scaled(value):
    return int(round(value * 1000000.0))


def flock_cells(task):
    cells = [len(task.shapes)]
    for one in task.shapes:
        cells.extend((scaled(one.x), scaled(one.y), scaled(one.vx),
                      scaled(one.vy), one.color, one.form,
                      scaled(one.next_morph)))
    return cells


def cfg_morph_gap(cfg):
    if cfg == 0:
        return 3.0
    return 1.2 if (cfg % 2) == 1 else 0.8


def cfg_count(cfg):
    if cfg == 0:
        return 3
    return 5 if (cfg % 3) == 1 else 12


def reference():
    out = []
    probe = Lookout(random.Random(0))
    for size in range(4):
        probe.window_width = WIDTHS[size]
        probe.window_height = HEIGHTS[size]
        low_x, high_x, low_y, high_y = probe._bounds()
        out.append(["edge", size, scaled(probe.radius()), scaled(low_x),
                    scaled(high_x), scaled(low_y), scaled(high_y)])

    for want in range(-2, 36):
        out.append(["clamp", want, clamped(want)])

    for which in range(len(COLORS)):
        red, green, blue = COLORS[which][1]
        out.append(["rgb", which, red, green, blue])

    for count in range(3, 16):
        for seed in range(1, 3):
            task = Lookout(random.Random(count * 100 + seed))
            task.window_width, task.window_height = 912.0, 684.0
            task.count = count
            task.speed = 0.6
            task.morph_gap = 1.0
            task._spawn_flock(0.0)
            out.append(["spawn", count, seed] + flock_cells(task))
            for watching in range(3):
                task.watching = WATCHING[watching]
                cue = task._absent_cue()
                out.append(["cue", count, seed, watching, cue.color, cue.form]
                           + flock_cells(task))

    for cfg in range(6):
        task = Lookout(random.Random(500 + cfg))
        task.window_width = WIDTHS[cfg % 4]
        task.window_height = HEIGHTS[cfg % 4]
        task.watching = WATCHING[cfg % 3]
        task.speed = 0.4 + cfg * 0.1
        task.morph_gap = cfg_morph_gap(cfg)
        task.total_cues = 5
        task.adaptive = (cfg % 2) == 0
        task.start_count = cfg_count(cfg)
        task.start_run(0.0)
        out.append(["start", cfg, task.count, task.cue_number, task.cue.color,
                    task.cue.form, PHASE[task.phase]] + flock_cells(task))

        dt = 1.0 / 30.0
        now = 0.0
        tick = 0
        while task.phase != "done" and tick < 3000:
            now += dt
            task.update(dt, now)
            if (tick % 5) == 0:
                task.answer(CHANNEL_BY_INDEX[(tick // 5) % 2], now)
            out.append(["tick", cfg, tick, PHASE[task.phase], task.cue_number,
                        task.cue.color, task.cue.form, task.count,
                        len(task.shapes), task.hits, task.misses,
                        task.false_alarms, task.verdict,
                        1 if task.seen.get(COLOR_CHANNEL) is not None else 0,
                        1 if task.seen.get(FORM_CHANNEL) is not None else 0]
                       + flock_cells(task))
            tick += 1

        tally = task.score()
        out.append(["score", cfg, tick, tally["hits"], tally["misses"],
                    tally["false_alarms"], tally["mean_ms"],
                    tally["most_shapes"]] + flock_cells(task))
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
