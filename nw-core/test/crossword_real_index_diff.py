#!/usr/bin/env python3
"""Compare the core parser with a user-supplied original lexicon index."""
import os
from pathlib import Path
import random
import runpy
import subprocess
import sys

source = Path(os.environ["NW_CROSSWORD_LEXICON"]).resolve(strict=True)
temporary = Path("/tmp/nw_crossword_real_index.tsv")
limits = (3000, 10000, 30000, 1 << 30)
expected = {limit: [0, 0] for limit in limits}
reference = runpy.run_path(str(Path(__file__).with_name("crossword_diff.py")),
                           run_name="crossword_reference")
entries = []
offset = 0
with source.open("rb") as stream:
    for line in stream:
        word_bytes, rank_bytes, _clue = line.rstrip(b"\r\n").split(b"\t")
        word = word_bytes.decode("ascii")
        rank = int(rank_bytes)
        if rank < 10000 and 3 <= len(word) <= 6:
            clue_offset = offset + len(word_bytes) + len(rank_bytes) + 2
            entries.append(reference["Entry"](word, rank, clue_offset))
        if 3 <= len(word) <= 9:
            for limit in limits:
                if rank < limit:
                    expected[limit][0] += 1
                    expected[limit][1] += len(word)
        offset += len(line)
temporary.symlink_to(source)
try:
    result = subprocess.run([sys.argv[1]], check=True, capture_output=True, text=True)
finally:
    temporary.unlink()
lines = result.stdout.splitlines()
actual = [tuple(map(int, row.split(","))) for row in lines[:4]]
wanted = [(limit, *expected[limit]) for limit in limits]
if actual != wanted:
    raise SystemExit(f"real-index counts differ: {actual!r} != {wanted!r}")
lexicon = reference["Lexicon"](sorted(entries, key=lambda entry: entry.rank))
for rung, line in zip((1, 2), lines[4:], strict=True):
    puzzle = reference["REF"]["deal_one"](
        reference["REF"]["grade_of"](rung), random.Random(17), lexicon)
    row = ["deal", rung, int(puzzle is not None),
           puzzle.size if puzzle else 0, puzzle.tried if puzzle else 0]
    if puzzle:
        row.extend((puzzle.blanks(), puzzle.unclued()))
        for cell, letter in enumerate(puzzle.solution):
            row.extend((int(cell in puzzle.blocks),
                        ord(letter) - ord("a") if letter else -1,
                        int(cell in puzzle.givens)))
        row.append(len(puzzle.slots))
        for slot in puzzle.slots:
            row.extend((slot.number, int(slot.down), len(slot.cells),
                        slot.clue if slot.clue else -1, *slot.cells))
    expected_line = ",".join(map(str, row))
    if line != expected_line:
        raise SystemExit(f"real-index rung {rung} differs:\n{line}\n{expected_line}")
if len(lines) != 6:
    raise SystemExit(f"expected six result rows, got {len(lines)}")
print("PASS: 6 cases identical")
