#!/usr/bin/env python3
"""Compare source deals using a caller-supplied real index."""
import os
from pathlib import Path
import random
import runpy
import subprocess
import sys

source = Path(os.environ['NW_SCRABBLE_LEXICON']).resolve(strict=True)
reference = runpy.run_path(str(Path(__file__).with_name('scrabble_diff.py')), run_name='scrabble_reference')
rows = []
full_rows = []
for line in source.read_text(encoding='utf-8').splitlines():
    word, rank, _clue = line.split('\t')
    rank = int(rank)
    if rank < (1 << 30) and 2 <= len(word) <= 15:
        full_rows.append((rank, word))
    if rank < 3000 and 2 <= len(word) <= 7:
        rows.append((rank, word))
rows.sort(key=lambda row: row[0])
words = [word for _, word in rows]
lex = reference['Lexicon'](words)
ref = reference['REF']
link = Path('/tmp/nw_scrabble_real_index.tsv')
link.symlink_to(source)
try:
    result = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
finally:
    link.unlink()
actual = result.stdout.splitlines()
expected = [f"capacity,{len(full_rows)},{sum(len(word) for _, word in full_rows)}"]
for rung in (1, 2):
    deal = ref['deal_one'](ref['grade_of'](rung), random.Random(17), lex)
    row = [rung, len(words), sum(map(len, words)), int(deal is not None)]
    if deal:
        code = lambda word: [ord(ch) - 97 for ch in word]
        row += [ord(ch) - 97 if ch else -1 for ch in deal.board.letters]
        row += [len(deal.rack), *code(deal.rack), deal.best.score,
                int(deal.best.down), len(deal.best.word), *code(deal.best.word)]
    expected.append(','.join(map(str, row)))
if actual != expected:
    raise SystemExit(f'real Scrabble index mismatch:\n{actual!r}\n{expected!r}')
print('PASS: 3 cases identical')
