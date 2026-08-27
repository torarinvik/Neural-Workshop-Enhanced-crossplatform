#!/usr/bin/env python3
"""Differential harness for tasks/graphmapping.elisa against ui/graphmapping.py.

The graph arithmetic and the deal are module-level in the reference and are
LIFTED by AST and run as themselves: `subtle_floor`, `edge`, `adjacency`,
`degrees`, `connected`, `isomorphic`, `relabel`, `shuffled`, `edge_count`,
`random_graph`, `_swap_partners`, `_move_a_line`, `rewired`, `build_pair`,
`ring_positions` and the `Graph`/`Pair` types. The run around them -- the deck,
the phase machine, the adaptive step and the score -- is methods on the
pyglet-owning class and is transcribed, as is the layout, which reads a live
window.

Edges cross the boundary as `low * MAX_NODES + high`, which sorts exactly the
way the reference's `(low, high)` tuples do.
"""
import ast
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "ui" / "graphmapping.py")

WANTED_FN = {"subtle_floor", "edge", "adjacency", "degrees", "connected",
             "isomorphic", "relabel", "shuffled", "edge_count", "random_graph",
             "_swap_partners", "_move_a_line", "rewired", "build_pair",
             "ring_positions"}
WANTED_CLASS = {"Pair", "Graph"}
WANTED_CONST = {"MAX_NODES", "MIN_NODES", "DENSITY_FACTORS", "MAX_FILL",
                "REWIRE_ATTEMPTS", "BASE_ATTEMPTS", "SUBTLE_FLOOR",
                "SAME", "DIFFERENT"}


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
    # The lifted subset has no `from __future__ import annotations`, so every
    # annotation is evaluated -- the real typing names have to be here.
    typing = __import__("typing")
    space = {"math": math, "random": random,
             "NamedTuple": typing.NamedTuple, "Dict": typing.Dict,
             "List": typing.List, "Optional": typing.Optional,
             "Sequence": typing.Sequence, "Set": typing.Set,
             "Tuple": typing.Tuple}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    missing = (WANTED_FN | WANTED_CLASS | WANTED_CONST) - set(space)
    if missing:
        raise SystemExit("graphmapping_diff: could not lift %s" % sorted(missing))
    return space


REF = lifted()
Graph = REF["Graph"]
Pair = REF["Pair"]
edge = REF["edge"]
MAX_NODES = REF["MAX_NODES"]
MIN_NODES = REF["MIN_NODES"]
SAME, DIFFERENT = REF["SAME"], REF["DIFFERENT"]

#: The density ids the sweep sends. Anything outside them is a name the
#: reference's two dicts have no entry for, which is a real branch: both
#: `.get` calls fall back rather than raise.
DENSITY = {0: "sparse", 1: "medium", 2: "dense"}

DEFAULT_WINDOW_HEIGHT = 684

PHASE = {"ready": 0, "asking": 1, "hidden": 2, "feedback": 3, "done": 4}


def density_name(which):
    return DENSITY.get(which, "nonesuch")


def code(pair):
    return pair[0] * MAX_NODES + pair[1]


def codes(graph):
    return [code(one) for one in graph.edges]


# --- the layout, which reads a live window in the reference ----------------

def from_bottom_edge(height, from_edge):
    return int(from_edge * (height / DEFAULT_WINDOW_HEIGHT))


def from_top_edge(height, from_edge):
    """Written as geometry.py writes it: the multiply binds before the divide,
    and the two groupings are not the same double."""
    return int(height - from_edge * height / DEFAULT_WINDOW_HEIGHT)


def above_the_band(height, y):
    """`verdict.above_the_band`: hold *y* UP, clear of the band the agent
    boundary reads off the bottom of the frame."""
    return max(int(y), int(height) - int(height * 0.75) + 8)


def button_rects(width, height):
    button_w = min(width * 0.22, width / 3.2)
    button_h = max(40.0, height * 0.07)
    gap = width * 0.04
    bottom = above_the_band(height, from_bottom_edge(height, 84))
    left = (width - (button_w * 2 + gap)) / 2
    return [(left, bottom, button_w, button_h, SAME),
            (left + button_w + gap, bottom, button_w, button_h, DIFFERENT)]


def canvas(width, height):
    canvas_w = width * 0.90
    _bl, button_bottom, _bw, button_height, _tag = button_rects(width, height)[0]
    bottom = button_bottom + button_height + height * 0.03
    canvas_h = max(80.0, from_top_edge(height, 96) - bottom)
    return ((width - canvas_w) / 2, bottom, canvas_w, canvas_h)


def panels(width, height):
    left, bottom, canvas_w, canvas_h = canvas(width, height)
    gap = canvas_w * 0.05
    half = (canvas_w - gap) / 2
    side = min(half, canvas_h)
    return [(left + half / 2, bottom + canvas_h / 2, side),
            (left + half + gap + half / 2, bottom + canvas_h / 2, side)]


def to_pixels(width, height, panel, point):
    centre_x, centre_y, side = panels(width, height)[panel]
    return (centre_x + (point[0] - 0.5) * side,
            centre_y + (point[1] - 0.5) * side)


# --- the run, which is methods on the pyglet-owning class ------------------

class Run(object):
    """`GraphMapping` without the window: the deck, the phases and the score."""

    def __init__(self, rng, start_nodes, density, total_trials, subtle,
                 exposure_ms, adaptive, feedback):
        self.rng = rng
        self.start_nodes = start_nodes
        self.density = density
        self.total_trials = total_trials
        self.subtle = subtle
        self.exposure_ms = exposure_ms
        self.adaptive = adaptive
        self.feedback = feedback
        self.nodes = self.clamped(start_nodes)
        self.trial = 0
        self.correct = 0
        self.settled_for = 0
        self.really_same = True
        self.asked_at = 0.0
        self.feedback_until = 0.0
        self.results = []
        self.phase = "ready"
        self._deck = []
        self.pair = None
        self.spots = []

    def floor(self):
        return REF["subtle_floor"](self.density) if self.subtle else MIN_NODES

    def clamped(self, nodes):
        return max(self.floor(), min(MAX_NODES, nodes))

    def _reset(self):
        self.trial = 0
        self.correct = 0
        self.settled_for = 0
        self.results = []
        self._deck = []
        self.phase = "ready"

    def _draw_answer(self):
        if not self._deck:
            self._deck = [True] * 3 + [False] * 3
            self.rng.shuffle(self._deck)
        return self._deck.pop()

    def start_run(self, now):
        self._reset()
        self.nodes = self.clamped(self.start_nodes)
        self._next_trial(now)

    def _next_trial(self, now):
        if self.trial >= self.total_trials:
            self.phase = "done"
            return
        self.trial += 1
        lines = REF["edge_count"](self.nodes, self.density)
        pair = REF["build_pair"](self.nodes, lines, self._draw_answer(),
                                 self.subtle, self.rng)
        if self.subtle and not pair.same and not pair.subtle:
            self.settled_for += 1
        self.pair = pair
        self.spots = [REF["ring_positions"](self.nodes, self.rng),
                      REF["ring_positions"](self.nodes, self.rng)]
        self.really_same = pair.same
        self.asked_at = now
        self.phase = "asking"

    def answer(self, choice, now):
        if self.phase not in ("asking", "hidden"):
            return
        said_same = choice == SAME
        right = said_same == self.really_same
        self.results.append((self.really_same, said_same, now - self.asked_at))
        if right:
            self.correct += 1
        self._adapt(right)
        if self.feedback:
            self.phase = "feedback"
            self.feedback_until = now + 0.9
        else:
            self._next_trial(now)

    def _adapt(self, right):
        if not self.adaptive:
            return
        self.nodes = self.clamped(self.nodes + (1 if right else -1))

    def update(self, now):
        if self.phase == "feedback" and now >= self.feedback_until:
            self._next_trial(now)
        elif (self.phase == "asking" and self.exposure_ms > 0
                and now - self.asked_at >= self.exposure_ms / 1000.):
            self.phase = "hidden"

    def score(self):
        trials = len(self.results)
        same_total = sum(1 for was, _s, _t in self.results if was)
        same_right = sum(1 for was, said, _t in self.results if was and said)
        different_right = sum(1 for was, said, _t in self.results
                              if not was and not said)
        times = [took for _w, _s, took in self.results]
        return {
            'trials': trials, 'correct': self.correct,
            'accuracy': int(round(100. * self.correct / trials)) if trials else 0,
            'same_total': same_total, 'same_right': same_right,
            'different_total': trials - same_total,
            'different_right': different_right,
            'mean_seconds': (sum(times) / len(times)) if times else 0.0,
        }


def micro(value):
    """A float as the sweep emits it: rounded to six places, half to even."""
    return int(round(value * 1000000.0))


def hand_made(size, pattern):
    """A graph with no randomness in it, for the arithmetic on its own."""
    kept = {edge(first, second)
            for first in range(size) for second in range(first + 1, size)
            if ((first * 3 + second * 5 + pattern * 7) % (pattern + 3)) == 0}
    return Graph(size, tuple(sorted(kept)))


def reference():
    out = []

    for which in range(-1, 4):
        name = density_name(which)
        row = ["density", which, micro(REF["DENSITY_FACTORS"].get(name, 1.4)),
               REF["subtle_floor"](name)]
        row.extend(REF["edge_count"](size, name)
                   for size in range(MIN_NODES, MAX_NODES + 1))
        out.append(row)

    for size in range(4, 9):
        for pattern in range(6):
            graph = hand_made(size, pattern)
            rotated = REF["relabel"](graph, [(node + pattern) % size
                                             for node in range(size)])
            mirrored = REF["relabel"](graph, [size - 1 - node
                                              for node in range(size)])
            neighbour = hand_made(size, pattern + 1)
            row = ["graph", size, pattern, len(graph.edges),
                   1 if REF["connected"](graph) else 0,
                   1 if REF["isomorphic"](graph, rotated) else 0,
                   1 if REF["isomorphic"](graph, mirrored) else 0,
                   1 if REF["isomorphic"](graph, neighbour) else 0]
            row.extend(REF["degrees"](graph))
            row.extend(codes(graph))
            out.append(row)

    for size in range(4, 13):
        for which in range(3):
            name = density_name(which)
            lines = REF["edge_count"](size, name)
            for seed in range(1, 4):
                rng = random.Random(size * 100 + which * 10 + seed)
                graph = REF["random_graph"](size, lines, rng)
                row = ["random", size, which, seed, lines, len(graph.edges),
                       1 if REF["connected"](graph) else 0,
                       rng.randrange(1000000)]
                row.extend(codes(graph))
                out.append(row)

                swapped = REF["_swap_partners"](graph, rng)
                moved = REF["_move_a_line"](graph, rng)
                row = ["rewire", size, which, seed,
                       -1 if swapped is None else len(swapped.edges),
                       -1 if moved is None else len(moved.edges),
                       rng.randrange(1000000)]
                row.extend(codes(swapped) if swapped is not None else [])
                row.append(-1)
                row.extend(codes(moved) if moved is not None else [])
                out.append(row)

                kept = REF["rewired"](graph, rng, keep_degrees=True)
                free = REF["rewired"](graph, rng, keep_degrees=False)
                row = ["rewired", size, which, seed,
                       -1 if kept is None else len(kept.edges),
                       -1 if free is None else len(free.edges),
                       rng.randrange(1000000)]
                row.extend(codes(kept) if kept is not None else [])
                row.append(-1)
                row.extend(codes(free) if free is not None else [])
                out.append(row)

    for size in range(4, 11):
        for which in range(3):
            name = density_name(which)
            lines = REF["edge_count"](size, name)
            for subtle in (False, True):
                for same in (False, True):
                    for seed in range(1, 3):
                        rng = random.Random(size * 1000 + which * 100
                                            + (2 if subtle else 0)
                                            + (4 if same else 0) + seed * 10)
                        pair = REF["build_pair"](size, lines, same, subtle, rng)
                        row = ["pair", size, which, 1 if subtle else 0,
                               1 if same else 0, seed,
                               1 if pair.same else 0, 1 if pair.subtle else 0,
                               len(pair.first.edges), len(pair.second.edges),
                               rng.randrange(1000000)]
                        row.extend(codes(pair.first))
                        row.append(-1)
                        row.extend(codes(pair.second))
                        out.append(row)

    for size in range(4, 13):
        for seed in range(1, 4):
            rng = random.Random(size * 7 + seed)
            spots = REF["ring_positions"](size, rng)
            row = ["ring", size, seed, rng.randrange(1000000)]
            for point in spots:
                row.extend((micro(point[0]), micro(point[1])))
            out.append(row)

    for spec in range(12):
        rng = random.Random(4000 + spec)
        run = Run(rng, start_nodes=4 + spec % 5, density=density_name(spec % 3),
                  total_trials=4 + spec % 3, subtle=(spec % 2) == 0,
                  # No exposure, one a tick crosses on its own, one that
                  # needs a skipped tick to cross, and one that never runs out
                  # -- so `hidden` is reached both ways and not reached at all.
                  exposure_ms=(0, 300, 700, 1500)[spec % 4],
                  adaptive=(spec % 3) != 2, feedback=(spec % 5) == 0)
        clock = 0.0
        run.start_run(clock)
        guard = 0
        while run.phase != "done" and guard < 200:
            guard += 1
            clock += 0.35
            run.update(clock)
            # Every fifth tick is left unanswered, so a rung with an exposure
            # runs out of it and the question survives into `hidden` -- which
            # `answer` still takes, and `update` must not keep re-entering.
            if run.phase in ("asking", "hidden") and guard % 5:
                run.answer(SAME if (guard + spec) % 3 else DIFFERENT, clock)
        tally = run.score()
        out.append(["run", spec, run.floor(), run.nodes, run.trial,
                    run.correct, run.settled_for, PHASE[run.phase],
                    tally['trials'], tally['accuracy'], tally['same_total'],
                    tally['same_right'], tally['different_total'],
                    tally['different_right'], micro(tally['mean_seconds']),
                    rng.randrange(1000000)])

    for width, height in ((912, 684), (1280, 720), (640, 480), (1920, 1080)):
        row = ["layout", width, height]
        for one in canvas(width, height):
            row.append(micro(one))
        for centre_x, centre_y, side in panels(width, height):
            row.extend((micro(centre_x), micro(centre_y), micro(side)))
        for left, bottom, wide, tall, _tag in button_rects(width, height):
            row.extend((micro(left), micro(bottom), micro(wide), micro(tall)))
        for panel in (0, 1):
            for point in ((0.0, 0.0), (0.5, 0.5), (1.0, 0.25)):
                spot = to_pixels(width, height, panel, point)
                row.extend((micro(spot[0]), micro(spot[1])))
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
                print("  elisa:  %s" % a[:150])
                print("  python: %s" % b[:150])
                break
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, python %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a[:150])
            print("  python: %s" % b[:150])
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
