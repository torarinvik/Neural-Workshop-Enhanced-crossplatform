#!/usr/bin/env python3
"""Compare Scramble's ranked vocabulary with the installed source index."""
import os
from pathlib import Path
import subprocess
import sys

source = Path(os.environ['NW_SCRAMBLE_LEXICON']).resolve(strict=True)
sentence_source = Path(os.environ['NW_SCRAMBLE_SENTENCES']).resolve(strict=True)
rows = []
for line in source.read_text(encoding='utf-8').splitlines():
    word, rank, _clue = line.split('\t')
    if len(word) <= 15:
        rows.append((int(rank), word))

def expected(values, limit):
    effective = {}
    for rank, word in sorted(values, key=lambda row: row[0]):
        effective[word] = rank
    selected = sorted((rank, word) for word, rank in effective.items() if rank <= limit)
    mask = (1 << 64) - 1
    h = 14695981039346656037
    for rank, word in selected:
        for value in (rank, len(word), *(ord(c) - 97 for c in word)):
            h = ((h ^ value) * 1099511628211) & mask
    if h >= 1 << 63:
        h -= 1 << 64
    return f'{len(selected)},{sum(len(word) for _, word in selected)},{h}'

link = Path('/tmp/nw_scramble_real_index.tsv')
sentence_link = Path('/tmp/nw_scramble_real_sentences.txt')
link.symlink_to(source)
sentence_link.symlink_to(sentence_source)
try:
    result = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
finally:
    link.unlink()
    sentence_link.unlink()
wanted = [expected([(2, 'zoo'), (1, 'a'), (2, 'cat'), (4, 'a'), (2, 'cat')], 2), expected(rows, 3000), expected(rows, 60000)]
effective = {word: rank for rank, word in sorted(rows, key=lambda row: row[0])}
for low, high, limit in ((6, 9, 3000), (8, 14, 60000)):
    selected = [words for line in sentence_source.read_text(encoding='utf-8').splitlines()
                if (words := line.strip().split()) and low <= len(words) <= high
                and max(effective.get(word, 1 << 30) for word in words) <= limit]
    mask, h = (1 << 64) - 1, 14695981039346656037
    for sentence in selected:
        for value in (len(sentence), *(v for word in sentence for v in (len(word), *(ord(c) - 97 for c in word)))):
            h = ((h ^ value) * 1099511628211) & mask
    if h >= 1 << 63: h -= 1 << 64
    wanted.append(f'{len(selected)},{sum(map(len, selected))},{sum(len(word) for row in selected for word in row)},{h}')
if result.stdout.splitlines() != wanted:
    raise SystemExit(f'Scramble index mismatch: {result.stdout.splitlines()!r} != {wanted!r}')
print('PASS: 5 cases identical')
