#!/usr/bin/env python3
"""Differential harness for tasks/chess.elisa against chess.py.

`generate` touches no chess at all -- it samples candidates, sorts them by how
many legal moves the position allows, takes a half and draws from it -- so it
is LIFTED by AST and run as itself with `_candidate` stubbed to hand back a
scripted stream. That is the whole of the portable half, and stubbing the
candidate is what makes it reachable: chess.py cannot be imported here at all,
because `python-chess` is neither installed nor vendored in this checkout.

The two level dials live inside `_candidate`, which does touch chess, so their
expressions are EXTRACTED from its source rather than retyped -- the reference
stays authoritative for the arithmetic even where it cannot be run.
"""
import ast
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "original-neural-workshop-enhanced" / "neural_workshop"
          / "chess.py")

TREE = ast.parse(SOURCE.read_text())


def lifted():
    keep = []
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == "generate":
            keep.append(node)
    if not keep:
        raise SystemExit("chess_diff: could not lift generate")
    space = {"random": random, "Optional": __import__("typing").Optional,
             "List": __import__("typing").List, "Puzzle": Puzzle,
             "_candidate": None}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"),
         space)
    return space


@dataclass(frozen=True)
class Puzzle:
    fen: str
    move: str
    hint: str
    alternatives: int


def dials():
    """`_candidate`'s two level dials, read out of its source.

    `_candidate` calls into the engine and cannot be run here, but the
    arithmetic that sets how dense a rung gets is plain Python sitting inside
    it. Lifting the expressions keeps the reference authoritative for them.
    """
    body = None
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_candidate":
            body = node
    if body is None:
        raise SystemExit("chess_diff: could not find _candidate")
    wanted = attempts = None
    for node in ast.walk(body):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "wanted"):
            wanted = node.value
        if isinstance(node, ast.While) and isinstance(node.test, ast.BoolOp):
            for part in node.test.values:
                if (isinstance(part, ast.Compare)
                        and isinstance(part.left, ast.Name)
                        and part.left.id == "attempts"):
                    attempts = part.comparators[0]
    if wanted is None or attempts is None:
        raise SystemExit("chess_diff: could not read _candidate's dials")
    return (compile(ast.Expression(wanted), str(SOURCE), "eval"),
            compile(ast.Expression(attempts), str(SOURCE), "eval"))


REF = lifted()
WANTED, ATTEMPTS = dials()


def scripted(spec, index):
    """One scripted candidate.

    `-1` is `_candidate` returning None -- a position that came out illegal, in
    check, already over, or with no unique mate. It costs an attempt and yields
    nothing, which is the only way `generate` can run out.

    Specs 24 to 26 are barren on purpose: one that never deals at all, so
    `generate` raises and nothing is drawn from the generator; one that deals a
    single candidate on the very last attempt; and one that deals three, which
    is fewer than the top rungs ask for.
    """
    if spec == 24:
        return -1
    if spec == 25:
        return 5 if index >= 63 else -1
    if spec == 26:
        if index < 61:
            return -1
        return 7 if index < 63 else 4
    step = (index * 7 + spec * 5) % 11
    return -1 if step < spec % 4 else 3 + (index * 13 + spec * 3) % 9


def stream(spec, count):
    return [scripted(spec, index) for index in range(count)]


def reference():
    out = []

    for level in range(-2, 14):
        row = ["dials", level, max(1, min(10, int(level))),
               2 + max(1, min(10, int(level))) // 3]
        wanted = eval(WANTED, {}, {"level": level, "round": round, "max": max})
        row.append(wanted)
        row.append(eval(ATTEMPTS, {}, {"wanted": wanted}))
        out.append(row)

    for spec in range(27):
        for level in range(1, 11):
            for seed in range(1, 4):
                script = stream(spec, 64)
                held = list(script)

                def fake(level_at, rng, held=held):
                    if not held:
                        return None
                    alternatives = held.pop(0)
                    if alternatives < 0:
                        return None
                    return Puzzle(fen=str(64 - len(held) - 1), move="",
                                  hint="", alternatives=alternatives)

                REF["_candidate"] = fake
                rng = random.Random(spec * 100 + level * 10 + seed)
                try:
                    puzzle = REF["generate"](level, rng)
                    chosen, density = int(puzzle.fen), puzzle.alternatives
                except RuntimeError:
                    chosen, density = -1, -1
                out.append(["select", spec, level, seed, chosen, density,
                            rng.randrange(1000000)])
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
