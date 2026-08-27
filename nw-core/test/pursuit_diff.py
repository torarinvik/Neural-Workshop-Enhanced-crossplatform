#!/usr/bin/env python3
"""Differential harness for tasks/pursuit.elisa against ui/pursuit.py.

`Quarry` and the eight tuning constants are module-level, so they are LIFTED by
AST and used as themselves; `bounced` comes from ui/tracking.py and `COLORS`
and `FORMS` from ui/lookout.py, which is where pursuit imports them from. The
round machinery is methods on the pyglet-owning class and is transcribed --
what stays the reference's own there is the draw order, four gaps per round and
each habit's own value before its next gap.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "original-neural-workshop-enhanced" / "neural_workshop" / "ui"
SOURCE = UI / "pursuit.py"

WANTED_CLASS = {"Quarry"}
WANTED_CONST = {"SLOWEST", "FASTEST", "STEP_UP", "STEP_DOWN", "RAISE_AT",
                "LOWER_AT", "GRACE", "CURSOR_STEP", "REVEAL_SECONDS"}


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
    space = {"math": math, "Tuple": tuple, "Optional": object,
             "NamedTuple": __import__("typing").NamedTuple,
             "_": lambda text: text}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(source), "exec"),
         space)
    missing = (want_fn | want_class | want_const) - set(space)
    if missing:
        raise SystemExit("pursuit_diff: could not lift %s from %s"
                         % (sorted(missing), source.name))
    return space


REF = lift(SOURCE, set(), WANTED_CLASS, WANTED_CONST)
TRACK = lift(UI / "tracking.py", {"bounced"}, set(), set())
LOOK = lift(UI / "lookout.py", set(), set(), {"COLORS", "FORMS"})

Quarry = REF["Quarry"]
bounced = TRACK["bounced"]
COLORS = LOOK["COLORS"]
FORMS = LOOK["FORMS"]
SLOWEST, FASTEST = REF["SLOWEST"], REF["FASTEST"]
STEP_UP, STEP_DOWN = REF["STEP_UP"], REF["STEP_DOWN"]
RAISE_AT, LOWER_AT = REF["RAISE_AT"], REF["LOWER_AT"]
GRACE = REF["GRACE"]
CURSOR_STEP = REF["CURSOR_STEP"]
REVEAL_SECONDS = REF["REVEAL_SECONDS"]

DEFAULT_WINDOW_HEIGHT = 684
PHASE = {"ready": 0, "chasing": 1, "feedback": 2, "done": 3}


def scale_to_height(height, fraction):
    return int(fraction * height / DEFAULT_WINDOW_HEIGHT)


class Pursuit(object):
    """The reference's round attributes, and the methods that move them."""

    def __init__(self, rng):
        self.rng = rng
        self.quarry = Quarry(0.5, 0.5, 0.0, 0.0, 0, 0)
        self.mouse = (0.0, 0.0)
        self.round = 0
        self.results = []
        self.on_time = 0.0
        self.run_time = 0.0
        self.off_sum = 0.0
        self.off_samples = 0
        self.multiplier = 1.0
        self.until = 0.0
        self.phase = "ready"
        self.verdict_shown = None
        self.speed = 0.0
        self.surge_depth = 0.0
        self.turn_gap = 1.0
        self.sharpness = 0.0
        self.base_radius = 17
        self.wobble = 0.0
        self.morph_gap = 0.0
        self.seconds = 10.0
        self.total_rounds = 0
        self.adaptive = False
        self.window_width = 912.0
        self.window_height = 684.0

    @property
    def verdict(self):
        if self.verdict_shown is None:
            return -1
        return 1 if self.verdict_shown[0] else 0

    def drawn_radius(self):
        if self.quarry is None:
            return 0.0
        return max(6.0, float(scale_to_height(self.window_height,
                                              self.quarry.radius)))

    def _bounds(self):
        edge_x = self.drawn_radius() / max(1, self.window_width)
        edge_y = self.drawn_radius() / max(1, self.window_height)
        return (edge_x + 0.01, 1.0 - edge_x - 0.01,
                edge_y + 0.11, 1.0 - edge_y - 0.17)

    def _reset(self):
        self.round = 0
        self.results = []
        self.multiplier = 1.0
        self.phase = "ready"
        self.verdict_shown = None

    def start_run(self, now):
        self._reset()
        self._next_round(now)

    def _next_round(self, now):
        if self.round >= self.total_rounds:
            self.phase = "done"
            return
        self.round += 1
        self.verdict_shown = None
        self.on_time = 0.0
        self.run_time = 0.0
        self.off_sum = 0.0
        self.off_samples = 0
        self.quarry = Quarry(
            x=0.5, y=0.5, heading=self.rng.uniform(0.0, 2 * math.pi),
            radius=self.base_radius,
            form=self.rng.randrange(len(FORMS)),
            color=self.rng.randrange(len(COLORS)))
        for stamp in ("next_turn", "next_surge", "next_resize", "next_morph"):
            setattr(self.quarry, stamp, now + self._gap())
        self.phase = "chasing"
        self.until = now + self.seconds

    def _gap(self):
        pace = max(0.05, self.turn_gap / max(0.1, self.multiplier))
        return self.rng.uniform(0.3, 1.7) * pace

    def _swerve(self, quarry, now):
        turn = self.rng.uniform(0.35, 1.0) * self.sharpness
        quarry.heading += turn if self.rng.random() < 0.5 else -turn
        quarry.next_turn = now + self._gap()

    def _lurch(self, quarry, now):
        quarry.surge = max(0.15, self.rng.uniform(1.0 - self.surge_depth,
                                                  1.0 + self.surge_depth))
        quarry.next_surge = now + self._gap()

    def _swell(self, quarry, now):
        quarry.radius = self.base_radius * self.rng.uniform(
            1.0 - self.wobble, 1.0 + self.wobble)
        quarry.next_resize = now + self._gap()

    def _shift(self, quarry, now):
        was = quarry.form
        while quarry.form == was:
            quarry.form = self.rng.randrange(len(FORMS))
        quarry.next_morph = now + self._gap()

    def _move(self, dt):
        quarry = self.quarry
        low_x, high_x, low_y, high_y = self._bounds()
        pace = self.speed * self.multiplier * quarry.surge
        aspect = self.window_height / max(1, self.window_width)
        vx = pace * math.cos(quarry.heading)
        vy = pace * math.sin(quarry.heading)
        quarry.x += vx * dt * aspect
        quarry.y += vy * dt
        quarry.x, folded_vx = bounced(quarry.x, vx, low_x, high_x)
        quarry.y, folded_vy = bounced(quarry.y, vy, low_y, high_y)
        if (folded_vx, folded_vy) != (vx, vy):
            quarry.heading = math.atan2(folded_vy, folded_vx)

    def update(self, dt, now):
        if self.phase == "chasing":
            quarry = self.quarry
            if now >= quarry.next_turn:
                self._swerve(quarry, now)
            if self.surge_depth and now >= quarry.next_surge:
                self._lurch(quarry, now)
            if self.wobble and now >= quarry.next_resize:
                self._swell(quarry, now)
            if self.morph_gap and now >= quarry.next_morph:
                self._shift(quarry, now)
            self._move(min(dt, 0.1))
            self._sample(min(dt, 0.1))
            if now >= self.until:
                self._score(now)
        elif self.phase == "feedback" and now >= self.until:
            self._next_round(now)

    def distance(self):
        return math.hypot(self.mouse[0] - self.quarry.x * self.window_width,
                          self.mouse[1] - self.quarry.y * self.window_height)

    def on_target(self):
        return self.distance() <= self.drawn_radius() * GRACE

    def _sample(self, dt):
        self.run_time += dt
        if self.on_target():
            self.on_time += dt
        else:
            self.off_sum += self.distance()
            self.off_samples += 1

    def _score(self, now):
        share = self.on_time / self.run_time if self.run_time else 0.0
        drift = (self.off_sum / self.off_samples if self.off_samples else 0.0)
        self.results.append((share, drift, self.multiplier))
        self.verdict_shown = (share >= RAISE_AT, "")
        if self.adaptive:
            if share >= RAISE_AT:
                self.multiplier = min(FASTEST, self.multiplier * STEP_UP)
            elif share < LOWER_AT:
                self.multiplier = max(SLOWEST, self.multiplier * STEP_DOWN)
        self.phase = "feedback"
        self.until = now + REVEAL_SECONDS

    def nudge(self, dx, dy):
        step = self.window_height * CURSOR_STEP
        self.mouse = (min(max(0.0, self.mouse[0] + dx * step),
                          float(self.window_width)),
                      min(max(0.0, self.mouse[1] + dy * step),
                          float(self.window_height)))

    def score(self):
        shares = [share for share, _drift, _mult in self.results]
        drifts = [drift for _share, drift, _mult in self.results]
        return dict(
            rounds=len(self.results),
            on_percent=int(round(100. * sum(shares) / len(shares))) if shares else 0,
            mean_off_px=int(round(sum(drifts) / len(drifts))) if drifts else 0,
            multiplier=int(round(self.multiplier * 100)))


WIDTHS = (912.0, 640.0, 1366.0, 1101.0)
HEIGHTS = (684.0, 480.0, 768.0, 617.0)


def scaled(value):
    return int(round(value * 1000000.0))


def toward(here, there):
    if there > here:
        return 1.0
    if there < here:
        return -1.0
    return 0.0


def quarry_cells(task):
    q = task.quarry
    return [scaled(q.x), scaled(q.y), scaled(q.heading), scaled(q.surge),
            scaled(q.radius), q.form, q.color, scaled(q.next_turn),
            scaled(q.next_surge), scaled(q.next_resize), scaled(q.next_morph)]


def reference():
    out = []
    for degrees in range(0, 181):
        out.append(["radians", degrees, scaled(math.radians(degrees))])

    task = Pursuit(random.Random(0))
    for size in range(4):
        for size_step in range(9):
            task.quarry.radius = 2.0 + size_step * 5.5
            task.window_width = WIDTHS[size]
            task.window_height = HEIGHTS[size]
            low_x, high_x, low_y, high_y = task._bounds()
            out.append(["edge", size, size_step, scaled(task.drawn_radius()),
                        scaled(low_x), scaled(high_x), scaled(low_y),
                        scaled(high_y)])

    for size in range(4):
        task.window_width = WIDTHS[size]
        task.window_height = HEIGHTS[size]
        task.mouse = (task.window_width / 2.0, task.window_height / 2.0)
        for step in range(60):
            dx = 1.0 if (step % 4) < 2 else -1.0
            dy = 1.0 if (step % 8) < 4 else -1.0
            task.nudge(dx * 3.0, dy * 2.0)
            out.append(["nudge", size, step, scaled(task.mouse[0]),
                        scaled(task.mouse[1])])

    for cfg in range(5):
        task = Pursuit(random.Random(900 + cfg))
        task.window_width = WIDTHS[cfg % 4]
        task.window_height = HEIGHTS[cfg % 4]
        task.speed = 0.25 + cfg * 0.08
        task.surge_depth = 0.0 if cfg == 3 else 0.35
        task.turn_gap = 0.6 + cfg * 0.15
        task.sharpness = math.radians(35.0 + cfg * 15.0)
        task.base_radius = 14.0 + cfg * 4.0
        task.wobble = 0.0 if cfg == 3 else 0.4
        task.morph_gap = 0.0 if cfg == 3 else 0.9
        task.seconds = 2.0
        task.total_rounds = 3
        task.adaptive = (cfg % 2) == 0
        task.mouse = (task.window_width / 2.0, task.window_height / 2.0)
        task.start_run(0.0)
        out.append(["start", cfg, PHASE[task.phase], task.round,
                    scaled(task.multiplier), scaled(task.until)]
                   + quarry_cells(task))

        dt = 1.0 / 60.0
        now = 0.0
        tick = 0
        while task.phase != "done" and tick < 4000:
            now += dt
            task.update(dt, now)
            task.nudge(toward(task.mouse[0], task.quarry.x * task.window_width),
                       toward(task.mouse[1], task.quarry.y * task.window_height))
            out.append(["tick", cfg, tick, PHASE[task.phase], task.round,
                        task.verdict, scaled(task.multiplier),
                        scaled(task.on_time), scaled(task.run_time),
                        scaled(task.off_sum), task.off_samples,
                        scaled(task.mouse[0]), scaled(task.mouse[1])]
                       + quarry_cells(task))
            tick += 1

        tally = task.score()
        row = ["score", cfg, tick, tally["rounds"], tally["on_percent"],
               tally["mean_off_px"], tally["multiplier"]]
        for share, drift, mult in task.results:
            row.extend((scaled(share), scaled(drift), scaled(mult)))
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
