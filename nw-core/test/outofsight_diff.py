#!/usr/bin/env python3
"""Differential harness for tasks/outofsight.elisa against ui/outofsight.py.

`Blind`, `Dot`, `area_in`, `hidden`, `rendezvous` and the ten timing constants
are module-level, so they are LIFTED by AST and run as themselves -- which
matters for `rendezvous` in particular, since it MUTATES the two dots it is
given and its return value is only the seconds. `bounced` comes from
ui/tracking.py, which is where outofsight imports it from. The round machinery
is methods on the pyglet-owning class and is transcribed; what stays the
reference's own there is the draw order.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "original-neural-workshop-enhanced" / "neural_workshop" / "ui"
SOURCE = UI / "outofsight.py"

WANTED_FN = {"area_in", "hidden", "rendezvous"}
WANTED_CLASS = {"Blind", "Dot"}
WANTED_CONST = {"FEWEST_DOTS", "MOST_DOTS", "CUE_SECONDS", "REVEAL_SECONDS",
                "PROBE_SECONDS", "VERDICT_SECONDS", "SHORTEST_GAP",
                "LONGEST_GAP", "RISK_SECONDS", "MOST_COVERED"}


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
             "Sequence": list, "pyglet": None,
             "NamedTuple": __import__("typing").NamedTuple,
             "_": lambda text: text}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(source), "exec"),
         space)
    missing = (want_fn | want_class | want_const) - set(space)
    if missing:
        raise SystemExit("outofsight_diff: could not lift %s from %s"
                         % (sorted(missing), source.name))
    return space


REF = lift(SOURCE, WANTED_FN, WANTED_CLASS, WANTED_CONST)
TRACK = lift(UI / "tracking.py", {"bounced"}, set(), set())

Blind = REF["Blind"]
Dot = REF["Dot"]
area_in = REF["area_in"]
hidden = REF["hidden"]
rendezvous = REF["rendezvous"]
bounced = TRACK["bounced"]
CUE_SECONDS = REF["CUE_SECONDS"]
REVEAL_SECONDS = REF["REVEAL_SECONDS"]
PROBE_SECONDS = REF["PROBE_SECONDS"]
VERDICT_SECONDS = REF["VERDICT_SECONDS"]
SHORTEST_GAP = REF["SHORTEST_GAP"]
LONGEST_GAP = REF["LONGEST_GAP"]
RISK_SECONDS = REF["RISK_SECONDS"]
MOST_COVERED = REF["MOST_COVERED"]

DEFAULT_WINDOW_HEIGHT = 684
PHASE = {"ready": 0, "cueing": 1, "tracking": 2, "revealing": 3, "done": 4}


def scale_to_height(height, fraction):
    return int(fraction * height / DEFAULT_WINDOW_HEIGHT)


class OutOfSight(object):
    """The reference's run attributes, and the methods that move them."""

    def __init__(self, rng):
        self.rng = rng
        self.blinds = []
        self.dots = []
        self.dot_count = 3
        self.start_targets = 1
        self.speed = 0.0
        self.blind_count = 0
        self.blind_width = 0.0
        self.cross_gap = 0.0
        self.probes_per_round = 0
        self.total_rounds = 0
        self.adaptive = False
        self.round = 0
        self.results = []
        self.held = 1
        self.hits = self.wrong = self.late = 0
        self.reaction_times = []
        self.schedule = []
        self.probes_done = 0
        self.round_right = 0
        self.probe = None
        self.probe_at = 0.0
        self.probe_ends = 0.0
        self.verdict = None
        self.verdict_until = 0.0
        self.next_probe = 0.0
        self.next_cross = 0.0
        self.phase = "ready"
        self.until = 0.0
        self.window_width = 912.0
        self.window_height = 684.0

    def radius(self):
        return max(7.0, float(scale_to_height(self.window_height, 19)))

    def _bounds(self):
        edge_x = self.radius() / self.window_width
        edge_y = self.radius() / self.window_height
        return (edge_x + 0.01, 1.0 - edge_x - 0.01,
                edge_y + 0.11, 1.0 - edge_y - 0.15)

    def _aspect(self):
        return self.window_height / max(1, self.window_width)

    def clamped_targets(self, count):
        return max(1, min(self.dot_count - 1, count))

    def _lay_blinds(self):
        self.blinds = []
        if self.blind_count <= 0 or self.blind_width <= 0:
            return
        field = self._bounds()
        low_x, high_x, low_y, high_y = field
        room = (high_x - low_x) * (high_y - low_y) * MOST_COVERED
        aspect = self._aspect()
        narrow, along = self.blind_width, self.blind_width * 2.6
        for _slab in range(self.blind_count):
            for _attempt in range(200):
                upright = self.rng.random() < 0.5
                width = (narrow if upright else along) * aspect
                height = along if upright else narrow
                candidate = Blind(
                    self.rng.uniform(low_x - width / 3., high_x - 2 * width / 3.),
                    self.rng.uniform(low_y - height / 3., high_y - 2 * height / 3.),
                    width, height)
                taken = area_in(candidate, field)
                if taken > room:
                    continue
                if not any(candidate.overlaps(laid) for laid in self.blinds):
                    self.blinds.append(candidate)
                    room -= taken
                    break

    def _scattered(self, dot_count):
        low_x, high_x, low_y, high_y = self._bounds()
        apart = 2.4 * self.radius() / self.window_height
        while True:
            spots = []
            for _attempt in range(dot_count * 80):
                spot = (self.rng.uniform(low_x, high_x),
                        self.rng.uniform(low_y, high_y))
                if hidden(self.blinds, spot[0], spot[1]):
                    continue
                if all((spot[0] - x) ** 2 + (spot[1] - y) ** 2 >= apart * apart
                       for x, y in spots):
                    spots.append(spot)
                    if len(spots) == dot_count:
                        return spots
            apart *= 0.8

    def _reset(self):
        self.dots = []
        self.probe = None
        self.blinds = []
        self.round = 0
        self.results = []
        self.hits = self.wrong = self.late = 0
        self.reaction_times = []
        self.held = self.clamped_targets(self.start_targets)
        self.phase = "ready"

    def _probe_schedule(self):
        return [self.rng.random() < 0.5
                for _question in range(self.probes_per_round)]

    def _next_round(self, now):
        if self.round >= self.total_rounds:
            self.phase = "done"
            self.probe = None
            return
        self.round += 1
        self.dots = []
        self.probe = None
        self._lay_blinds()
        count = self.clamped_targets(self.held)
        chosen = set(self.rng.sample(range(self.dot_count), count))
        dots = []
        for index, (x, y) in enumerate(self._scattered(self.dot_count)):
            heading = self.rng.uniform(0.0, 2 * math.pi)
            dots.append(Dot(x, y,
                            vx=self.speed * math.cos(heading),
                            vy=self.speed * math.sin(heading),
                            target=index in chosen))
        self.dots = dots
        self.schedule = self._probe_schedule()
        self.probes_done = 0
        self.round_right = 0
        self.verdict = None
        self.phase = "cueing"
        self.until = now + CUE_SECONDS

    def start_run(self, now):
        self._reset()
        self._next_round(now)

    def held_now(self):
        return sum(1 for dot in self.dots if dot.target)

    def _move(self, dt):
        low_x, high_x, low_y, high_y = self._bounds()
        aspect = self._aspect()
        for dot in self.dots:
            dot.x += dot.vx * dt * aspect
            dot.y += dot.vy * dt
            dot.x, dot.vx = bounced(dot.x, dot.vx, low_x, high_x)
            dot.y, dot.vy = bounced(dot.y, dot.vy, low_y, high_y)

    def _mark_risk(self, now):
        for dot in self.dots:
            if dot.busy_until and now >= dot.busy_until:
                dot.busy_until = 0.0
                dot.risky_until = now + RISK_SECONDS
            out_of_sight = hidden(self.blinds, dot.x, dot.y)
            if dot.was_hidden and not out_of_sight:
                dot.risky_until = now + RISK_SECONDS
            dot.was_hidden = out_of_sight

    def _maybe_cross(self, now):
        if self.cross_gap <= 0 or now < self.next_cross:
            return
        self.next_cross = now + self.rng.uniform(0.6, 1.4) * self.cross_gap
        free = [dot for dot in self.dots if not dot.busy_until]
        if len(free) < 2:
            return
        one, other = self.rng.sample(free, 2)
        meets = now + rendezvous(one, other, self.speed, self._aspect())
        one.busy_until = other.busy_until = meets

    def _probeable(self, want, now):
        open_air = [dot for dot in self.dots
                    if dot.target == want
                    and not hidden(self.blinds, dot.x, dot.y)]
        if not open_air:
            return None
        risky = [dot for dot in open_air if dot.risky_until > now]
        return self.rng.choice(risky or open_air)

    def _raise_probe(self, now):
        dot = self._probeable(self.schedule[self.probes_done], now)
        if dot is None:
            return
        self.probe = dot
        self.probe_at = now
        self.probe_ends = now + PROBE_SECONDS

    def answer(self, mine, now):
        if self.phase != "tracking" or self.probe is None:
            return
        if self.verdict is not None:
            return
        right = mine == self.probe.target
        self.reaction_times.append(now - self.probe_at)
        if right:
            self.hits += 1
        else:
            self.wrong += 1
        self._settle(right, now)

    def _too_slow(self, now):
        self.late += 1
        self._settle(False, now)

    def _settle(self, right, now):
        self.verdict = right
        self.verdict_until = now + VERDICT_SECONDS
        self.probes_done += 1
        self.round_right += int(right)

    def _retire_probe(self, now):
        self.probe = None
        self.verdict = None
        self.next_probe = now + self.rng.uniform(SHORTEST_GAP, LONGEST_GAP)

    def _end_round(self, now):
        asked, right = self.probes_done, self.round_right
        self.results.append((self.held_now(), asked, right))
        if self.adaptive:
            grown = self.held + 1 if right == asked else self.held - 1
            self.held = self.clamped_targets(grown)
        self.phase = "revealing"
        self.until = now + REVEAL_SECONDS

    def update(self, dt, now):
        if self.phase == "cueing":
            if now < self.until:
                return
            self.phase = "tracking"
            self.next_probe = now + self.rng.uniform(SHORTEST_GAP, LONGEST_GAP)
            self.next_cross = now + self.rng.uniform(0.3, 1.0)
            for dot in self.dots:
                dot.was_hidden = hidden(self.blinds, dot.x, dot.y)
        elif self.phase == "tracking":
            self._move(min(dt, 0.1))
            self._mark_risk(now)
            self._maybe_cross(now)
            if self.verdict is not None:
                if now >= self.verdict_until:
                    self._retire_probe(now)
            elif self.probe is not None:
                if now >= self.probe_ends:
                    self._too_slow(now)
            elif self.probes_done >= self.probes_per_round:
                self._end_round(now)
            elif now >= self.next_probe:
                self._raise_probe(now)
        elif self.phase == "revealing":
            self._move(min(dt, 0.1))
            if now >= self.until:
                self._next_round(now)

    def score(self):
        asked = self.hits + self.wrong + self.late
        mean = (sum(self.reaction_times) / len(self.reaction_times)
                if self.reaction_times else 0.0)
        return dict(
            rounds=len(self.results), asked=asked, hits=self.hits,
            wrong=self.wrong, late=self.late,
            accuracy=int(round(100. * self.hits / asked)) if asked else 0,
            mean_ms=int(round(mean * 1000)),
            most_held=max((held for held, ask, right in self.results
                           if ask and right == ask), default=0))


WIDTHS = (912.0, 640.0, 1366.0, 1101.0)
HEIGHTS = (684.0, 480.0, 768.0, 617.0)


def scaled(value):
    return int(round(value * 1000000.0))


def blind_cells(task):
    cells = [len(task.blinds)]
    for slab in task.blinds:
        cells.extend((scaled(slab.left), scaled(slab.bottom),
                      scaled(slab.width), scaled(slab.height)))
    return cells


def flock_cells(task):
    cells = [len(task.dots)]
    for dot in task.dots:
        cells.extend((scaled(dot.x), scaled(dot.y), scaled(dot.vx),
                      scaled(dot.vy), 1 if dot.target else 0,
                      scaled(dot.busy_until), scaled(dot.risky_until),
                      1 if dot.was_hidden else 0))
    return cells


def reference():
    out = []
    probe = OutOfSight(random.Random(0))
    for size in range(4):
        probe.window_width = WIDTHS[size]
        probe.window_height = HEIGHTS[size]
        low_x, high_x, low_y, high_y = probe._bounds()
        out.append(["edge", size, scaled(probe.radius()), scaled(low_x),
                    scaled(high_x), scaled(low_y), scaled(high_y),
                    scaled(probe._aspect())])

    for blinds in range(9):
        for wide in range(4):
            for seed in range(1, 3):
                task = OutOfSight(random.Random(blinds * 1000 + wide * 10 + seed))
                task.window_width, task.window_height = 912.0, 684.0
                task.blind_count = blinds
                task.blind_width = 0.05 + wide * 0.09
                task._lay_blinds()
                out.append(["blinds", blinds, wide, seed] + blind_cells(task))
                for dots in range(3, 10):
                    spots = task._scattered(dots)
                    row = ["spots", blinds, wide, seed, dots]
                    for x, y in spots:
                        row.extend((scaled(x), scaled(y)))
                    out.append(row)

    for cfg in range(5):
        task = OutOfSight(random.Random(700 + cfg))
        task.window_width = WIDTHS[cfg % 4]
        task.window_height = HEIGHTS[cfg % 4]
        task.dot_count = 4 + cfg
        task.start_targets = 1 + (cfg % 3)
        task.speed = 0.18 + cfg * 0.05
        task.blind_count = cfg % 4
        task.blind_width = 0.07 + cfg * 0.03
        task.cross_gap = 0.0 if cfg == 2 else 1.2
        task.probes_per_round = 3
        task.total_rounds = 2
        task.adaptive = (cfg % 2) == 0
        task.start_run(0.0)
        out.append(["start", cfg, PHASE[task.phase], task.round, task.held]
                   + blind_cells(task) + flock_cells(task)
                   + [1 if one else 0 for one in task.schedule])

        dt = 1.0 / 60.0
        now = 0.0
        tick = 0
        while task.phase != "done" and tick < 6000:
            now += dt
            task.update(dt, now)
            if (task.probe is not None and task.verdict is None
                    and (tick % 17) == 0):
                truth = bool(task.probe.target)
                said = truth if (tick % 5) != 0 else not truth
                task.answer(said, now)
            probe_index = (task.dots.index(task.probe)
                           if task.probe is not None else -1)
            out.append(["tick", cfg, tick, PHASE[task.phase], task.round,
                        task.held, probe_index,
                        -1 if task.verdict is None else int(task.verdict),
                        task.probes_done, task.round_right, task.hits,
                        task.wrong, task.late, scaled(task.next_probe),
                        scaled(task.next_cross)] + flock_cells(task))
            tick += 1

        tally = task.score()
        out.append(["score", cfg, tick, tally["rounds"], tally["asked"],
                    tally["hits"], tally["wrong"], tally["late"],
                    tally["accuracy"], tally["mean_ms"], tally["most_held"]])
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
