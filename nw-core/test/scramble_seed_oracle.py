#!/usr/bin/env python3
"""Source-seeded Scramble deals for the production controller replay."""
import ast
import json
from pathlib import Path
import random
import runpy

root = Path(__file__).resolve().parents[2]
source = root / 'original-neural-workshop-enhanced/neural_workshop'

def node(file, name):
    tree = ast.parse((source / file).read_text(encoding='utf-8'))
    return next(n.value for n in tree.body if isinstance(n, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == name for t in n.targets))

words_node = node('wordlist.py', 'SEED_WORDS')
words = list(dict.fromkeys(ast.literal_eval(words_node.func.value).split()))
lines = ast.literal_eval(node('sentences.py', 'SEED_TEXT'))
for line in lines:
    for word in line.split():
        if word not in words:
            words.append(word)
reference = runpy.run_path(str(Path(__file__).with_name('scramble_diff.py')), run_name='scramble_reference')
pool = reference['Vocab'](words, list(range(1, len(words) + 1)))
result = []
for rung in range(1, 13):
    grade = reference['grade_of'](rung)
    bank = [line.split() for line in lines if grade.span[0] <= len(line.split()) <= grade.span[1]]
    deal_seed = random.Random(17).randrange(1 << 30)
    deal = reference['deal_one'](grade, bank, pool, random.Random(deal_seed))
    result.append({'rung': rung, 'shown': ' '.join(deal['chunks']),
                   'answer': ' '.join(deal['words']), 'words': len(deal['words'])})
print(json.dumps(result))
