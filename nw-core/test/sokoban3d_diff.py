#!/usr/bin/env python3
"""Differential harness for tasks/sokoban3d.elisa against sokoban3d.py.

Almost everything under test is module-level in the reference, so it is LIFTED
by AST and run as itself: `Solid`, `blocking`, `look_around`, `facing_at`,
`step_to`, `move`, `costs`, `solved`, `stuck`, `floor_of`, `walk_cost`,
`_pushes_from`, `solve_bounded`, `par`, `certified`, `marks`, `clear_between`.
`live_cells` and `deadlocked` come from sokoban.py and `look`, `Pose`, `Sight`,
`FACINGS`, `FOV`, `COLUMNS`, `AHEAD`/`BACK`/`LEFT`/`RIGHT` from youarehere.py,
which is where sokoban3d imports them from.

The warehouses are BUILT from a fixed recipe rather than generated: the flat
game's generator runs its own solver on every attempt, which is minutes per
rung in pure Python, and what is under test here is the arithmetic on top of a
level rather than the generator.

The route and the two foils are included here. Route actions are emitted as
the integer ordering used by the Elisa ABI (`AHEAD`, `BACK`, `LEFT`, `RIGHT`).
"""
import ast
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "original-neural-workshop-enhanced" / "neural_workshop"


def lift(source, names, extra=None):
    """Every top-level def/class/assign named in `names`, in source order."""
    tree = ast.parse(source.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            keep.append(node)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in names:
                keep.append(node)
        elif isinstance(node, ast.Assign):
            flat = [t.id for t in node.targets if isinstance(t, ast.Name)]
            flat += [e.id for t in node.targets if isinstance(t, ast.Tuple)
                     for e in t.elts if isinstance(e, ast.Name)]
            if names.intersection(flat):
                keep.append(node)
    typing = __import__("typing")
    space = {"math": math, "random": __import__("random"),
             "heapq": __import__("heapq"),
             "deque": __import__("collections").deque,
             "Tuple": typing.Tuple, "Optional": typing.Optional,
             "Dict": typing.Dict, "List": typing.List,
             "Sequence": typing.Sequence, "FrozenSet": typing.FrozenSet,
             "NamedTuple": typing.NamedTuple, "_": lambda text: text}
    space.update(extra or {})
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(source), "exec"), space)
    missing = names - set(space)
    if missing:
        raise SystemExit("sokoban3d_diff: could not lift %s from %s"
                         % (sorted(missing), source.name))
    return space


FLAT = lift(PKG / "sokoban.py",
            {"Level", "live_cells", "deadlocked", "_floor_flags", "_stuck",
             "_steps", "_reachable"})
# `look` and `cast` are annotated `maze: Maze`, which youarehere IMPORTS from
# maze.py, and a lifted subset has no `from __future__` line to keep
# annotations unevaluated. Lift the name it needs from where it comes from.
MAZE = lift(PKG / "maze.py", {"Maze"})
MAZE3D = lift(PKG / "youarehere.py",
              {"Pose", "Sight", "Mote", "FACINGS", "FOV", "COLUMNS",
               "FAR", "AHEAD", "BACK", "LEFT", "RIGHT", "MOVES", "_cast",
               "look"},
              extra={"Maze": MAZE["Maze"]})

REF = lift(PKG / "sokoban3d.py",
           {"Solid", "Outcome", "blocking", "look_around", "facing_at", "step_to",
            "move", "costs", "solved", "stuck", "floor_of", "walk_cost",
            "_pushes_from", "solve_bounded", "_unwind", "_way", "_walk_route",
            "par", "certified", "route", "_run", "push_perfect",
            "push_forgetful", "push_slipping", "marks", "clear_between",
            "STEP_BUDGET"},
           extra={"Level": FLAT["Level"], "live_cells": FLAT["live_cells"],
                  "deadlocked": FLAT["deadlocked"],
                  "Pose": MAZE3D["Pose"], "Sight": MAZE3D["Sight"],
                  "Mote": MAZE3D["Mote"], "FACINGS": MAZE3D["FACINGS"],
                  "FOV": MAZE3D["FOV"], "COLUMNS": MAZE3D["COLUMNS"],
                  "AHEAD": MAZE3D["AHEAD"], "BACK": MAZE3D["BACK"],
                  "LEFT": MAZE3D["LEFT"], "RIGHT": MAZE3D["RIGHT"],
                  "look": MAZE3D["look"]})

Level = FLAT["Level"]
Pose = MAZE3D["Pose"]
FOV = MAZE3D["FOV"]
MOVES_ORDER = (MAZE3D["AHEAD"], MAZE3D["BACK"], MAZE3D["LEFT"], MAZE3D["RIGHT"])


def build_level(spec):
    """The recipe both sides raise their warehouses from."""
    width = 7 + spec % 3
    height = 6 + (spec // 4) % 3
    cells = width * height
    walls = set()
    for cell in range(cells):
        x, y = cell % width, cell // width
        border = x == 0 or y == 0 or x == width - 1 or y == height - 1
        if border or ((x * 3 + y * 5 + spec) % 11) == 0:
            walls.add(cell)
    floor_list = [cell for cell in range(cells) if cell not in walls]
    boxes_wanted = 2 + spec % 2
    if len(floor_list) < 2 * boxes_wanted + 2:
        return None
    player = floor_list[0]
    goals = frozenset(floor_list[len(floor_list) - 1 - k]
                      for k in range(boxes_wanted))
    boxes = frozenset(floor_list[1 + 2 * k] for k in range(boxes_wanted))
    return Level(width, height, frozenset(walls), goals, boxes, player,
                 None, 2, 20, frozenset())


def scaled(value):
    return int(round(value * 1000000.0))


def grid(level, members):
    return [1 if cell in members else 0 for cell in range(level.width * level.height)]


def reference():
    out = []
    for spec in range(24):
        level = build_level(spec)
        if level is None:
            out.append(["level", spec, 0])
            continue
        out.append(["level", spec, 1, level.width, level.height, level.player]
                   + grid(level, level.walls) + grid(level, level.goals)
                   + grid(level, level.boxes))

        floor_ok = REF["floor_of"](level)
        out.append(["floor", spec, REF["facing_at"](level)]
                   + [1 if one else 0 for one in floor_ok])

        row = ["steps", spec]
        for cell in range(level.width * level.height):
            for facing in range(4):
                step = REF["step_to"](level, cell, facing)
                row.append(-1 if step is None else step)
        out.append(row)

        boxes = level.boxes
        pose = Pose(level.player, REF["facing_at"](level))
        spent = 0
        for press in range(80):
            doing = MOVES_ORDER[(press * 7 + spec * 3) % 4]
            pose, boxes, moved, pushed = REF["move"](level, boxes, pose, doing)
            spent += REF["costs"](doing, moved)
            out.append(["walk", spec, press, MOVES_ORDER.index(doing),
                        pose.cell, pose.facing, 1 if moved else 0,
                        1 if pushed else 0, spent,
                        1 if REF["solved"](level, boxes) else 0,
                        1 if REF["stuck"](level, boxes) else 0]
                       + grid(level, boxes))

        for which in range(2):
            start = (Pose(level.player, REF["facing_at"](level)) if which == 0
                     else pose)
            reach = REF["walk_cost"](level, level.boxes, start, floor_ok)
            out.append(["reach", spec, which] + list(reach))

        for budget in (40, 4000):
            found, bound, route = REF["solve_bounded"](level, budget)
            out.append(["par", spec, budget, 0 if found is None else 1,
                        0 if found is None else found, bound, 0])
            out.append(["route", spec, budget, len(route)]
                       + [MOVES_ORDER.index(one) for one in route])

        if spec < 8:
            for mode, name in enumerate(("push_forgetful", "push_slipping")):
                rng = __import__("random").Random(7000 + spec * 10 + mode)
                if name == "push_forgetful":
                    result = REF[name](level, 0.35, rng, 80, 4000)
                else:
                    result = REF[name](level, 0.35, rng, 80, 4000)
                ending = {"solved": 0, "stuck": 1,
                          "thinks it is done": 2, "adrift": 3}[result.ending]
                out.append(["foil", spec, mode, ending, result.steps])

        for facing in range(4):
            here = Pose(level.player, facing)
            sights = REF["look_around"](level, level.boxes, here,
                                        columns=24, fov=FOV)
            row = ["view", spec, facing]
            for sight in sights:
                row.extend((scaled(sight.distance),
                            -1 if sight.cell is None else sight.cell,
                            sight.side))
            out.append(row)
            found = REF["marks"](level, level.boxes, here, fov=FOV)
            row = ["marks", spec, facing, len(found)]
            for mote in found:
                row.extend((mote.cell, scaled(mote.across), scaled(mote.distance)))
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
