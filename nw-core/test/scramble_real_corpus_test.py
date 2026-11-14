#!/usr/bin/env python3
"""Compare controller deals against the installed original text and index."""
import ast
import os
from pathlib import Path
import random
import runpy
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
core = app.load_core('scramble_set_corpus')
index = Path(os.environ['NW_SCRAMBLE_LEXICON']).read_bytes()
sentences = Path(os.environ['NW_SCRAMBLE_SENTENCES']).read_bytes()
reference = runpy.run_path(str(root / 'test/scramble_diff.py'), run_name='scramble_reference')
ranks = {}
rows = []
for line in index.decode('utf-8').splitlines():
    word, rank, _ = line.split('\t')
    if len(word) <= 15: rows.append((int(rank), word))
for rank, word in sorted(rows, key=lambda row: row[0]): ranks[word] = rank
original = root.parent / 'original-neural-workshop-enhanced/neural_workshop'
def assignment(filename, name):
    tree = ast.parse((original / filename).read_text(encoding='utf-8'))
    return next(n.value for n in tree.body if isinstance(n, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
seed_lines = ast.literal_eval(assignment('sentences.py', 'SEED_TEXT'))
seed_node = assignment('wordlist.py', 'SEED_WORDS')
seed_words = list(dict.fromkeys(ast.literal_eval(seed_node.func.value).split()))
for line in seed_lines:
    for word in line.split():
        if word not in seed_words: seed_words.append(word)
seed_ranks = {word: index + 1 for index, word in enumerate(seed_words)}
cases = [('both', index, sentences, ranks, sentences.decode('utf-8').splitlines()),
         ('index-only', index, b'', ranks, seed_lines),
         ('sentences-only', b'', sentences, seed_ranks, sentences.decode('utf-8').splitlines())]
for mode, active_index, active_sentences, active_ranks, bank_lines in cases:
    for rung in (1, 3, 12):
        grade = reference['grade_of'](rung)
        bank = [words for line in bank_lines
                if (words := line.strip().split()) and grade.span[0] <= len(words) <= grade.span[1]
                and max(active_ranks.get(word, 1 << 30) for word in words) <= grade.top_rank]
        seed = random.Random(17).randrange(1 << 30)
        rng = random.Random(seed)
        words = bank[rng.randrange(len(bank))]
        placing = reference['REF']['shuffle_order'](grade, len(words), rng)
        corrupt = [reference['REF']['scramble_word'](grade, words[i], rng) for i in placing]
        chunks = corrupt if grade.spaces < 1 else reference['REF']['respace'](grade, ''.join(corrupt), [len(w) for w in corrupt], rng)
        expected = ' '.join(chunks)
        handle = core.scramble_create(rung, 1, 1, 0, 17)
        assert handle > 0 and core.scramble_set_corpus(handle, active_index, active_sentences) == 0
        assert core.scramble_info(handle, 13) == 1
        assert core.scramble_info(handle, 14) == bool(active_index)
        assert core.scramble_info(handle, 15) == bool(active_sentences)
        assert core.scramble_action(handle, 0, 0, 0) == 1
        n = core.scramble_info(handle, 4)
        shown = ''.join(' ' if v == 26 else chr(97 + v) for v in (core.scramble_value(handle, 0, i) for i in range(n)))
        assert shown == expected, (mode, rung, shown, expected)
        for char in ' '.join(words):
            assert core.scramble_action(handle, 1, 26 if char == ' ' else ord(char) - 97, 1) == 1
        assert core.scramble_action(handle, 3, 0, 2) == 1
        assert core.scramble_info(handle, 6) == 1
        assert core.scramble_destroy(handle) == 0
print('scramble_real_corpus_test: PASS (both and mixed source data at levels 1, 3, 12)')
