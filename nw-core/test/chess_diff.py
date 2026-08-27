#!/usr/bin/env python3
"""Differential harness for tasks/chess.elisa against chess.py.

Two halves, because chess.py has two.

`generate`'s own arithmetic touches no chess -- it samples candidates, sorts
them by how many legal moves the position allows, takes a half and draws -- so
it is LIFTED by AST and run as itself with `_candidate` stubbed to a scripted
stream.

The rest of it is geometry around five questions put to `python-chess`: is this
position legal, is the side to move in check, is the game already over, how
many legal moves end it in mate, and how many are there at all. Those five are
RECORDED here, live, off the real engine, and written to a file the sweep reads
back -- so the port replays the reference's own answers and has to ask the same
questions, in the same order, off the same number of draws, and land on the
same position. Nothing is a golden file: the transcript is re-derived from the
engine on every run, and a change in the engine shows up as a mismatch rather
than as a stale recording that still passes.

`python-chess` is a dependency, vendored under nw-core/vendor by

    python3 -m pip install --target nw-core/vendor 'python-chess>=1.999'

which is the requirement the program already declares. It is not ported: it is
a bitboard move generator with its own legality rules, and re-deriving it would
be porting a different program.

The one thing that had to be true before this shape was possible is that the
engine's move ORDER does not leak into the answer. Every call site of
`mating_moves` guards on `len(mates) == 1` before reading `mates[0]`, so what
crosses the boundary is a COUNT, and a count is something a transcript can
carry.
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
VENDOR = ROOT / "nw-core" / "vendor"
ORACLE_PATH = "/tmp/nw_chess_oracle.txt"

TREE = ast.parse(SOURCE.read_text())

sys.path.insert(0, str(VENDOR))
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))
try:
    import chess as chesslib
    from neural_workshop import chess as nwchess
except ImportError as bad:                                   # pragma: no cover
    raise SystemExit(
        "chess_diff: %s\n"
        "  python-chess is not installed. It is in the program's own\n"
        "  requirements.txt; vendor it with\n"
        "    python3 -m pip install --target nw-core/vendor 'python-chess>=1.999'"
        % bad)

#: The five answers, in the order they were asked for.
ORACLE = []
#: The board `_transformed` handed back, which `_candidate` then mutates in
#: place -- so reading it after the call gives the position it ended on.
LAST_BOARD = [None]
WATCHED = ("_candidate", "_add_decoy")


def placement(board):
    """A position as the sweep emits it: piece and colour, square by square."""
    out = []
    for square in chesslib.SQUARES:
        piece = board.piece_at(square)
        out.append(0 if piece is None
                   else piece.piece_type * 2 + (0 if piece.color else 1))
    out.append(1 if board.turn else 0)
    return out


def _watch(name):
    """Record `name`'s answer, but only where chess.py itself asks it.

    The frame check is not decoration: `is_game_over` reaches `is_check` on its
    own way down, and a class-level recorder would write those inner calls into
    the transcript beside the outer ones.
    """
    real = getattr(chesslib.Board, name)

    def wrapped(self, *args, **kw):
        got = real(self, *args, **kw)
        if sys._getframe(1).f_code.co_name in WATCHED:
            ORACLE.append(1 if got else 0)
        return got
    return wrapped


for _name in ("is_valid", "is_check", "is_game_over"):
    setattr(chesslib.Board, _name, _watch(_name))

_real_mating = nwchess.mating_moves


def _mating(board):
    """`len(mates)` doubled, plus one where the single mating move promotes.

    Recorded for every call whether or not that caller reads the promotion, so
    the transcript stays in step with the QUESTIONS rather than with which of
    their answers happened to be looked at.
    """
    mates = _real_mating(board)
    ORACLE.append(len(mates) * 2
                  + (1 if mates and mates[0].promotion is not None else 0))
    return mates


nwchess.mating_moves = _mating

_real_count = chesslib.LegalMoveGenerator.count


def _count(self):
    got = _real_count(self)
    if sys._getframe(1).f_code.co_name in WATCHED:
        ORACLE.append(got)
    return got


chesslib.LegalMoveGenerator.count = _count

_real_transformed = nwchess._transformed


def _transformed(rng):
    board = _real_transformed(rng)
    LAST_BOARD[0] = board
    return board


nwchess._transformed = _transformed


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

    # --- the half that asks the engine ------------------------------------
    #
    # The transcript is written as it is recorded, so the sweep replays these
    # exact answers. A port that asked one question more or fewer would read
    # the next case's answer and diverge, which is the point of counting them.
    transcript = []

    for level in range(1, 11):
        for seed in range(1, 4):
            del ORACLE[:]
            LAST_BOARD[0] = None
            rng = random.Random(level * 100 + seed)
            made = nwchess._candidate(level, rng)
            row = ["candidate", level, seed, 0 if made is None else 1,
                   0 if made is None else made.alternatives, len(ORACLE),
                   rng.randrange(1000000)]
            row.extend(placement(LAST_BOARD[0]))
            transcript.extend(ORACLE)
            out.append(row)

    for level in range(1, 11):
        del ORACLE[:]
        LAST_BOARD[0] = None
        rng = random.Random(9000 + level)
        try:
            puzzle = nwchess.generate(level, rng)
        except RuntimeError:
            puzzle = None
        row = ["generate", level, 0 if puzzle is None else 1,
               0 if puzzle is None else puzzle.alternatives, len(ORACLE),
               rng.randrange(1000000)]
        if puzzle is None:
            row.extend([0] * 65)
        else:
            row.extend(placement(chesslib.Board(puzzle.fen)))
        transcript.extend(ORACLE)
        out.append(row)

    with open(ORACLE_PATH, "w") as handle:
        handle.write("%d\n" % len(transcript))
        for one in transcript:
            handle.write("%d\n" % one)

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
